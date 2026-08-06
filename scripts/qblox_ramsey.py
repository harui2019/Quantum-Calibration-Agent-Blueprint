from __future__ import annotations

import sys
from typing import Annotated

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _qblox_runtime import HARDWARE_REPO_PATH, get_hardware_agent, get_qubit, save_device_config
from _ising_utils import (
    array_to_list, common_payload, finite_or_none, make_artifact_dir, png_plot_entry,
    stdout_to_stderr,
)

sys.path.append(str(HARDWARE_REPO_PATH))

from cal10_ramsey import MultiplexedRamsey

_BRANCH_STYLE = {1: ("tab:blue", "tab:red", "+detuning"), -1: ("tab:green", "tab:orange", "-detuning")}


def qblox_ramsey(
    qubits: list[str],
    tau_start_s: Annotated[float, (0.0, 1e-3)] = 0.0,
    tau_stop_s: Annotated[float, (1e-9, 1e-3)] = 80e-6,
    tau_step_s: Annotated[float, (1e-9, 1e-4)] = 400e-9,
    frequency_detuning_hz: Annotated[float, (0.0, 50e6)] = 1e5,
    repetitions: Annotated[int, (1, 10000)] = 100,
    minimum_t2_star_s: float = 1e-7,
    maximum_t2_star_s: float = 1e-3,
    apply_update: bool = False,
) -> dict:
    """Interleaved +/-detuning Ramsey experiment; fits T2* and the qubit f01
    frequency error for each qubit.

    Args:
        qubits:
            Target hardware qubit names, e.g. ["q1", "q2"].
        tau_start_s:
            Free-evolution delay sweep start (s).
        tau_stop_s:
            Free-evolution delay sweep stop (s).
        tau_step_s:
            Free-evolution delay step (s).
        frequency_detuning_hz:
            Artificial detuning applied symmetrically (+/-) around f01. Interleaving
            both signs every shot (rather than two separate sweeps) resolves the
            sign of a real frequency error and cancels slow drift.
        repetitions:
            Number of repeated shots per delay point.
        minimum_t2_star_s:
            Reject the fit if the extracted T2* falls below this floor (likely a
            fit that locked onto noise).
        maximum_t2_star_s:
            Reject the fit if the extracted T2* exceeds this ceiling (likely an
            unconstrained/diverging fit).
        apply_update:
            If True and every qubit's fit is accepted, correct each qubit's f01
            in device config by the fitted frequency error.
    """

    hw_agent = get_hardware_agent()
    qobjs = [get_qubit(qubit_name) for qubit_name in qubits]
    node = MultiplexedRamsey(qobjs)

    with stdout_to_stderr():
        node.execute(
            tau_start=tau_start_s,
            tau_stop=tau_stop_s,
            tau_step=tau_step_s,
            frequency_detuning=frequency_detuning_hz,
            repetitions=repetitions,
        )
        node.analyze()

    payload = common_payload(node, "ramsey", qubits)
    artifact_dir = make_artifact_dir(payload["tuid"], "ramsey")
    results, plots = {}, []

    for qname, res in node.analyses.items():
        freq_offset = res["freq_offset"]
        t2_star = res["t2_star"]
        branches = res["branches"]
        plus_success = bool(branches[1]["fit_result"].success)
        minus_success = bool(branches[-1]["fit_result"].success)

        reasons = []
        if not (plus_success and minus_success):
            reasons.append("fit_failed_on_one_or_both_branches")
        if not np.isfinite(freq_offset):
            reasons.append("frequency_offset_non_finite")
        if not np.isfinite(t2_star) or t2_star < minimum_t2_star_s:
            reasons.append("t2_star_too_short")
        elif t2_star > maximum_t2_star_s:
            reasons.append("t2_star_too_long")
        accepted = len(reasons) == 0

        image_path = artifact_dir / f"{qname}.png"
        fig, ax = plt.subplots(figsize=(8, 5))
        for sign in (1, -1):
            branch = branches[sign]
            data_color, fit_color, label = _BRANCH_STYLE[sign]
            taus_us = np.asarray(branch["taus"], dtype=float) * 1e6
            # branch["rotated_real"] is raw (Volts), but branch["fit_result"] was fit
            # against microvolt-scaled y-values (see cal10_ramsey.py's analyze()) — scale
            # the raw data the same way so it's plotted on the same axis as its own fit.
            rotated_real_uv = np.asarray(branch["rotated_real"], dtype=float) * 1e6
            ax.plot(taus_us, rotated_real_uv, "o", color=data_color, markersize=3, label=f"data ({label})")
            if branch["fit_result"].success:
                fine_taus_us = np.linspace(taus_us.min(), taus_us.max(), 300)
                ax.plot(
                    fine_taus_us,
                    branch["fit_result"].eval(x_us=fine_taus_us),
                    "-", color=fit_color, label=f"fit ({label})",
                )
        ax.set_xlabel("Tau (us)")
        ax.set_ylabel("Rotated signal (µV)")
        ax.set_title(f"Ramsey - {qname}")
        ax.legend(fontsize="small")
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)
        plots.append(png_plot_entry(image_path, f"Ramsey - {qname}"))

        results[qname] = {
            "accepted": accepted,
            "failure_reasons": reasons,
            "frequency_error_hz": finite_or_none(freq_offset),
            "t2_star_s": finite_or_none(t2_star),
            "image_path": str(image_path.resolve()),
            "recommended_action": (
                "apply_f01_correction_and_proceed_to_pi_pulse_error_amplification"
                if accepted else
                "repeat_with_adjusted_detuning_or_delay_range"
            ),
            "sweep": {
                "tau_s": array_to_list(branches[1]["taus"]),
                "rotated_signal_plus_detuning": array_to_list(branches[1]["rotated_real"]),
                "rotated_signal_minus_detuning": array_to_list(branches[-1]["rotated_real"]),
            },
        }

    accepted_all = len(results) > 0 and all(v["accepted"] for v in results.values())
    update_applied = False
    config_saved = None
    if apply_update and accepted_all:
        with stdout_to_stderr():
            node.post_run()
        config_saved = save_device_config(hw_agent)
        update_applied = True

    payload.update({
        "status": "success" if accepted_all else "failed",
        "accepted": accepted_all,
        "update_applied": update_applied,
        "config_saved": config_saved,
        "results": results,
        "plots": plots,
    })
    if not accepted_all:
        payload["error"] = "; ".join(
            f"{qname}: {', '.join(res['failure_reasons'])}"
            for qname, res in results.items()
            if not res["accepted"]
        ) or "No analysis results were produced."
    return payload
