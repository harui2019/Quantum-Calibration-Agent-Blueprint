from __future__ import annotations

import sys
from typing import Annotated

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _qblox_runtime import HARDWARE_REPO_PATH, get_hardware_agent, get_qubit, save_device_config
from _ising_utils import (
    array_to_list, common_payload, make_artifact_dir, png_plot_entry, stdout_to_stderr,
)

sys.path.append(str(HARDWARE_REPO_PATH))

from cal06_power_rabi import MultiplexedPowerRabi


def qblox_power_rabi(
    qubits: list[str],
    amp_start: Annotated[float, (0.0, 1.0)] = 0.0,
    amp_stop: Annotated[float, (0.0, 1.0)] = 0.5,
    amp_npoints: Annotated[int, (11, 501)] = 200,
    repetitions: Annotated[int, (1, 10000)] = 600,
    drive_att_db: int | None = None,
    drive_duration_s: float | None = None,
    minimum_amp180: float = 1e-4,
    apply_update: bool = False,
) -> dict:
    """Sweep drive amplitude and fit a Power Rabi oscillation to find each qubit's
    pi-pulse amplitude (amp180).

    Args:
        qubits:
            Target hardware qubit names, e.g. ["q1", "q2"].
        amp_start:
            Sweep start amplitude (arb. units, same scale as rxy.amp180).
        amp_stop:
            Sweep stop amplitude.
        amp_npoints:
            Number of amplitude points.
        repetitions:
            Number of repeated shots per amplitude point.
        drive_att_db:
            Optional output attenuation (dB) applied to every requested qubit's
            drive line before the sweep. None leaves the current hardware config.
        drive_duration_s:
            Optional X-pulse duration (s) override applied to every requested
            qubit. None leaves the current device config.
        minimum_amp180:
            Reject the fit if the extracted pi-pulse amplitude is below this floor.
        apply_update:
            If True and every qubit's fit is accepted, write the fitted amp180
            into each qubit's device config (dut_config_AS_QRC.json).
    """

    hw_agent = get_hardware_agent()
    qobjs = [get_qubit(qubit_name) for qubit_name in qubits]
    node = MultiplexedPowerRabi(qobjs)

    with stdout_to_stderr():
        node.execute(
            amp_start=amp_start,
            amp_stop=amp_stop,
            amp_npoints=amp_npoints,
            repetitions=repetitions,
            drive_att=drive_att_db,
            drive_duration=drive_duration_s,
        )
        node.analyze()

    payload = common_payload(node, "power_rabi", qubits)
    artifact_dir = make_artifact_dir(payload["tuid"], "power_rabi")
    results, plots = {}, []

    for qname, res in node.analyses.items():
        fit_result = res["fit_result"]
        amp180 = float(res["amp180"])
        amps = np.asarray(res["amps"], dtype=float)
        rotated_real = np.asarray(res["rotated_real"], dtype=float)

        fit_success = bool(fit_result.success)
        reasons = []
        if not fit_success:
            reasons.append("fit_failed")
        if not np.isfinite(amp180) or amp180 < minimum_amp180:
            reasons.append("amp180_non_finite_or_too_small")
        elif not (amp_start <= amp180 <= amp_stop):
            reasons.append("amp180_out_of_swept_range")
        accepted = len(reasons) == 0

        image_path = artifact_dir / f"{qname}.png"
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(amps, rotated_real, "o", markersize=3, label="data")
        if fit_success:
            fine_amps = np.linspace(amps.min(), amps.max(), 300)
            ax.plot(fine_amps, fit_result.eval(x=fine_amps), "r-", label="fit")
            ax.axvline(amp180, linestyle="--")
        ax.set_xlabel("Drive amplitude (arb. units)")
        ax.set_ylabel("Rotated signal (V)")
        ax.set_title(f"Power Rabi - {qname}")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)
        plots.append(png_plot_entry(image_path, f"Power Rabi - {qname}"))

        results[qname] = {
            "accepted": accepted,
            "failure_reasons": reasons,
            "fitted_amp180": amp180,
            "fit_success": fit_success,
            "image_path": str(image_path.resolve()),
            "recommended_action": (
                "apply_amp180_and_proceed_to_pi_pulse_error_amplification"
                if accepted else
                "repeat_with_adjusted_amplitude_range"
            ),
            "sweep": {
                "amplitude": array_to_list(amps),
                "rotated_signal": array_to_list(rotated_real),
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
