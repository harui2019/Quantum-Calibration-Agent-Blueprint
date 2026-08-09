from __future__ import annotations

import sys
from typing import Annotated

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _qblox_runtime import HARDWARE_REPO_PATH, get_hardware_agent, get_qubit
from _ising_utils import (
    array_to_list, common_payload, make_artifact_dir, png_plot_entry, stdout_to_stderr,
)

sys.path.append(str(HARDWARE_REPO_PATH))

from cal14_t1 import MultiplexedT1


def qblox_t1(
    qubits: list[str],
    tau_start_s: Annotated[float, (0.0, 1e-3)] = 1e-6,
    tau_stop_s: Annotated[float, (1e-9, 1e-3)] = 200e-6,
    tau_step_s: Annotated[float, (1e-9, 1e-4)] = 5e-6,
    repetitions: Annotated[int, (1, 10000)] = 200,
    drive_att_db: int | None = None,
    minimum_t1_s: float = 1e-7,
    maximum_t1_s: float = 1e-3,
) -> dict:
    """Measure qubit energy-relaxation time (T1) via a delayed-readout exponential
    decay sweep.

    Note: unlike the other calibration wrappers, this experiment does not support
    `apply_update` — the underlying node's `post_run()` is a no-op (T1 is a reported
    diagnostic, not a parameter fed back into device config).

    Args:
        qubits:
            Target hardware qubit names, e.g. ["q1", "q2"].
        tau_start_s:
            Post-pi-pulse delay sweep start (s).
        tau_stop_s:
            Post-pi-pulse delay sweep stop (s).
        tau_step_s:
            Post-pi-pulse delay step (s).
        repetitions:
            Number of repeated shots per delay point.
        drive_att_db:
            Optional output attenuation (dB) applied to every requested qubit's
            drive line before the sweep. None leaves the current hardware config.
        minimum_t1_s:
            Reject the fit if the extracted T1 falls below this floor (likely a
            fit that locked onto noise or a decoherence-dominated trace).
        maximum_t1_s:
            Reject the fit if the extracted T1 exceeds this ceiling (likely an
            unconstrained/diverging fit).
    """

    get_hardware_agent()
    qobjs = [get_qubit(qubit_name) for qubit_name in qubits]
    node = MultiplexedT1(qobjs)

    with stdout_to_stderr():
        node.execute(
            tau_start=tau_start_s,
            tau_stop=tau_stop_s,
            tau_step=tau_step_s,
            repetitions=repetitions,
            drive_att=drive_att_db,
        )
        node.analyze()

    payload = common_payload(node, "t1", qubits)
    artifact_dir = make_artifact_dir(payload["tuid"], "t1")
    results, plots = {}, []

    for qname, res in node.analyses.items():
        fit_result = res["fit_result"]
        t1_val = float(res["t1_val"])
        taus = np.asarray(res["taus"], dtype=float)
        rotated_real = np.asarray(res["rotated_real"], dtype=float)

        fit_success = bool(fit_result.success)
        reasons = []
        if not fit_success:
            reasons.append("fit_failed")
        if not np.isfinite(t1_val) or t1_val < minimum_t1_s:
            reasons.append("t1_too_short")
        elif t1_val > maximum_t1_s:
            reasons.append("t1_too_long")
        accepted = len(reasons) == 0

        image_path = artifact_dir / f"{qname}.png"
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(taus * 1e6, rotated_real, "o", markersize=3, label="data")
        if fit_success:
            fine_taus = np.linspace(taus.min(), taus.max(), 300)
            ax.plot(fine_taus * 1e6, fit_result.eval(x=fine_taus), "r-", label="fit")
        ax.set_xlabel("Tau (us)")
        ax.set_ylabel("Rotated signal (V)")
        ax.set_title(f"T1 - {qname}")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)
        plots.append(png_plot_entry(image_path, f"T1 - {qname}"))

        results[qname] = {
            "accepted": accepted,
            "failure_reasons": reasons,
            "t1_s": t1_val,
            "fit_success": fit_success,
            "image_path": str(image_path.resolve()),
            "recommended_action": (
                "proceed_to_echo_or_dispersive_shift"
                if accepted else
                "repeat_with_adjusted_delay_range"
            ),
            "sweep": {
                "tau_s": array_to_list(taus),
                "rotated_signal": array_to_list(rotated_real),
            },
        }

    accepted_all = len(results) > 0 and all(v["accepted"] for v in results.values())

    payload.update({
        "status": "success" if accepted_all else "failed",
        "accepted": accepted_all,
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
