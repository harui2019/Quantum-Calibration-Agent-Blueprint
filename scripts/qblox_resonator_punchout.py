from __future__ import annotations

import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _qblox_runtime import get_hardware_agent, get_qubit
from _ising_utils import (
    array_to_list, common_payload, make_artifact_dir, stdout_to_stderr,
)

sys.path.append("/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting")

from cal03_resonator_punchout import MultiplexedResonatorPunchout, MultiplexedResonatorPunchoutAmp


def _select_operating_index(
    sweeps,
    resonance_hz,
    max_shift_fraction: float,
    min_contrast_fraction: float,
    contrast,
):

    sweeps = np.asarray(sweeps, dtype=float)
    resonance_hz = np.asarray(resonance_hz, dtype=float)
    contrast = np.asarray(contrast, dtype=float)

    low_power_reference = resonance_hz[-1]
    span = max(float(np.ptp(resonance_hz)), 1.0)
    normalized_shift = np.abs(resonance_hz - low_power_reference) / span
    valid = (
        (normalized_shift <= max_shift_fraction)
        & (contrast >= min_contrast_fraction)
        & np.isfinite(resonance_hz)
    )
    indices = np.where(valid)[0]
    return int(indices[0]) if len(indices) else None


def qblox_resonator_punchout_attenuation(
    qubits: list[str],
    frequency_width_hz: float = 20e6,
    frequency_npoints: int = 101,
    attenuation_start_db: int = 0,
    attenuation_stop_db: int = 30,
    attenuation_step_db: int = 2,
    repetitions: int = 100,
    readout_amplitude: float | None = None,
    maximum_normalized_frequency_shift: float = 0.20,
    minimum_normalized_contrast: float = 0.10,
    apply_update: bool = False,
) -> dict:
    """Sweep output attenuation and recommend a conservative readout point."""
    
    get_hardware_agent()
    qobjs = [get_qubit(qubit_name) for qubit_name in qubits]
    node = MultiplexedResonatorPunchout(qobjs)

    with stdout_to_stderr():
        node.execute(
            frequency_width=frequency_width_hz,
            frequency_npoints=frequency_npoints,
            att_start=attenuation_start_db,
            att_stop=attenuation_stop_db,
            att_step=attenuation_step_db,
            repetitions=repetitions,
            ro_amp=readout_amplitude,
        )
        node.analyze()

    payload = common_payload(node, "resonator_punchout_attenuation", qubits)
    artifact_dir = make_artifact_dir(payload["tuid"], "resonator_punchout_attenuation")
    results, selected = {}, {}

    for qname, res in node.analyses.items():
        pivot = res["pivot_mag"]
        sweeps = np.asarray(res["unique_sweeps"], dtype=float)
        min_freqs = np.asarray(res["min_freqs"], dtype=float)
        row_max = pivot.max(axis=1).values.astype(float)
        row_min = pivot.min(axis=1).values.astype(float)
        contrast = (row_max - row_min) / np.maximum(row_max, np.finfo(float).eps)

        index = _select_operating_index(
            sweeps, min_freqs,
            maximum_normalized_frequency_shift,
            minimum_normalized_contrast,
            contrast,
        )
        accepted = index is not None
        recommendation = int(sweeps[index]) if accepted else None
        if accepted:
            selected[qname] = recommendation

        image_path = artifact_dir / f"{qname}.png"
        freqs = pivot.columns.values.astype(float)
        norm = pivot.div(pivot.max(axis=1), axis=0).values
        fig, ax = plt.subplots(figsize=(8, 5))
        mesh = ax.pcolormesh(freqs / 1e9, sweeps, norm, shading="auto")
        ax.plot(min_freqs / 1e9, sweeps, "--")
        if accepted:
            ax.axhline(recommendation, linestyle=":")
        fig.colorbar(mesh, ax=ax, label="Normalized magnitude")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Output attenuation (dB)")
        ax.set_title(f"Resonator Punchout - {qname}")
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)

        results[qname] = {
            "accepted": accepted,
            "recommended_attenuation_db": recommendation,
            "recommended_action": (
                "apply_readout_attenuation_and_repeat_spectroscopy"
                if accepted else
                "repeat_with_adjusted_power_range"
            ),
            "image_path": str(image_path.resolve()),
            "sweep": {
                "attenuation_db": array_to_list(sweeps),
                "tracked_resonance_hz": array_to_list(min_freqs),
                "normalized_contrast": array_to_list(contrast),
            },
        }

    accepted_all = len(results) > 0 and all(v["accepted"] for v in results.values())
    # Existing node accepts only one attenuation for all qubits. Apply only if all agree.
    unique_values = set(selected.values())
    update_applied = False
    update_reason = None
    if apply_update and accepted_all:
        if len(unique_values) == 1:
            with stdout_to_stderr():
                node.post_run(readout_attenuation=next(iter(unique_values)))
            update_applied = True
        else:
            update_reason = "Per-qubit recommendations differ; node post_run supports one shared value."

    payload.update({
        "status": "success" if accepted_all else "needs_retry",
        "accepted": accepted_all,
        "update_applied": update_applied,
        "update_reason": update_reason,
        "results": results,
    })
    return payload


def qblox_resonator_punchout_amplitude(
    qubits: list[str],
    frequency_width_hz: float = 20e6,
    frequency_npoints: int = 101,
    amplitude_start: float = 0.005,
    amplitude_stop: float = 0.20,
    amplitude_nsteps: int = 20,
    repetitions: int = 100,
    readout_attenuation_db: int | None = None,
    maximum_normalized_frequency_shift: float = 0.20,
    minimum_normalized_contrast: float = 0.10,
    apply_update: bool = False,
) -> dict:
    """Sweep readout amplitude and recommend a conservative operating point."""

    get_hardware_agent()
    qobjs = [get_qubit(qubit_name) for qubit_name in qubits]
    node = MultiplexedResonatorPunchoutAmp(qobjs)

    with stdout_to_stderr():
        node.execute(
            frequency_width=frequency_width_hz,
            frequency_npoints=frequency_npoints,
            amp_start=amplitude_start,
            amp_stop=amplitude_stop,
            amp_nsteps=amplitude_nsteps,
            repetitions=repetitions,
            ro_att=readout_attenuation_db,
        )
        node.analyze()

    payload = common_payload(node, "resonator_punchout_amplitude", qubits)
    artifact_dir = make_artifact_dir(payload["tuid"], "resonator_punchout_amplitude")
    results, selected = {}, {}

    for qname, res in node.analyses.items():
        pivot = res["pivot_mag"]
        sweeps = np.asarray(res["unique_sweeps"], dtype=float)
        min_freqs = np.asarray(res["min_freqs"], dtype=float)
        row_max = pivot.max(axis=1).values.astype(float)
        row_min = pivot.min(axis=1).values.astype(float)
        contrast = (row_max - row_min) / np.maximum(row_max, np.finfo(float).eps)

        # For amplitude, inspect from low to high and choose first point with enough contrast.
        reference = min_freqs[0]
        frequency_scale = max(float(np.ptp(min_freqs)), 1.0)
        normalized_shift = np.abs(min_freqs - reference) / frequency_scale
        valid = (
            (normalized_shift <= maximum_normalized_frequency_shift)
            & (contrast >= minimum_normalized_contrast)
            & np.isfinite(min_freqs)
        )
        indices = np.where(valid)[0]
        index = int(indices[0]) if len(indices) else None
        accepted = index is not None
        recommendation = float(sweeps[index]) if accepted else None
        if accepted:
            selected[qname] = recommendation

        image_path = artifact_dir / f"{qname}.png"
        freqs = pivot.columns.values.astype(float)
        norm = pivot.div(pivot.max(axis=1), axis=0).values
        fig, ax = plt.subplots(figsize=(8, 5))
        mesh = ax.pcolormesh(freqs / 1e9, sweeps, norm, shading="auto")
        ax.plot(min_freqs / 1e9, sweeps, "--")
        if accepted:
            ax.axhline(recommendation, linestyle=":")
        fig.colorbar(mesh, ax=ax, label="Normalized magnitude")
        ax.set_xlabel("Frequency (GHz)")
        ax.set_ylabel("Readout amplitude")
        ax.set_title(f"Resonator Punchout Amplitude - {qname}")
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)

        results[qname] = {
            "accepted": accepted,
            "recommended_readout_amplitude": recommendation,
            "recommended_action": (
                "apply_readout_amplitude_and_repeat_spectroscopy"
                if accepted else
                "repeat_with_adjusted_amplitude_range"
            ),
            "image_path": str(image_path.resolve()),
            "sweep": {
                "readout_amplitude": array_to_list(sweeps),
                "tracked_resonance_hz": array_to_list(min_freqs),
                "normalized_contrast": array_to_list(contrast),
            },
        }

    accepted_all = len(results) > 0 and all(v["accepted"] for v in results.values())
    update_applied = False
    if apply_update and accepted_all:
        with stdout_to_stderr():
            node.post_run(readout_amplitudes=selected)
        update_applied = True

    payload.update({
        "status": "success" if accepted_all else "needs_retry",
        "accepted": accepted_all,
        "update_applied": update_applied,
        "results": results,
    })
    return payload
