from __future__ import annotations

import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _qblox_runtime import get_hardware_agent, get_qubit

sys.path.append("/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting")

from cal00_time_of_flight import TimeOfFlight

from _ising_utils import (
    array_to_list, common_payload, finite_or_none, make_artifact_dir,
    node_class, stdout_to_stderr,
)

def qblox_time_of_flight(
    qubits: list[str],
    module_number: int,
    frequency_detuning_hz: float = 10e6,
    pulse_duration_s: float = 2e-6,
    pulse_amplitude: float = 0.1,
    acquisition_duration_s: float = 4e-6,
    repetitions: int = 100,
    acquisition_delay_s: float = 0.0,
    playback_delay_s: float = 146e-9,
    apply_update: bool = False,
) -> dict:
    """Measure readout time of flight and NCO propagation delay."""
    

    get_hardware_agent()
    qobjs = [get_qubit(qubit_name) for qubit_name in qubits]
    node = TimeOfFlight(qobjs, module_number=module_number)

    with stdout_to_stderr():
        node.execute(
            frequency_detuning=frequency_detuning_hz,
            pulse_duration=pulse_duration_s,
            pulse_amp=pulse_amplitude,
            acquisition_duration=acquisition_duration_s,
            repetitions=repetitions,
        )
        node.analyze(
            acquisition_delay=acquisition_delay_s,
            playback_delay=playback_delay_s,
            qubits_to_analyze=qubits,
        )

    payload = common_payload(node, "time_of_flight", qubits)
    artifact_dir = make_artifact_dir(payload["tuid"], "time_of_flight")
    results = {}
    accepted_all = True

    for qname, res in node.analyses.items():
        mag = np.asarray(res["mag"], dtype=float)
        time_ns = np.asarray(res["time_array_ns"], dtype=float)
        success = bool(res["success"])
        accepted_all &= success

        image_path = artifact_dir / f"{qname}.png"
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(time_ns, mag)
        if success:
            ax.axvline(float(res["tof"]) * 1e9, linestyle="--")
        ax.set_title(f"Time of Flight - {qname}")
        ax.set_xlabel("Trace acquisition sample (ns)")
        ax.set_ylabel("Magnitude (V)")
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)

        results[qname] = {
            "accepted": success,
            "tof_s": finite_or_none(res["tof"]),
            "nco_propagation_delay_s": finite_or_none(res["nco_prop_delay"]),
            "message": str(res["msg"]),
            "image_path": str(image_path.resolve()),
            "trace": {
                "time_ns": array_to_list(time_ns),
                "magnitude_v": array_to_list(mag),
            },
            "recommended_action": (
                "apply_delay_update" if success
                else "reduce_acquisition_delay_and_repeat"
            ),
        }

    update_applied = False
    if apply_update and accepted_all:
        with stdout_to_stderr():
            node.post_run(qobjs)
        update_applied = True

    payload.update({
        "status": "success" if accepted_all else "needs_retry",
        "accepted": accepted_all,
        "update_applied": update_applied,
        "results": results,
    })
    return payload
