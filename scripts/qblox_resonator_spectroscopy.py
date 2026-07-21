from __future__ import annotations

import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from datetime import datetime
import json

from _qblox_runtime import get_hardware_agent, get_qubit

sys.path.append("/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting")

from custom_elements import FluxTunableTransmonElement
from cal02_resonator_spectroscopy import MultiplexedResonatorSpectroscopy

from _ising_utils import (
    array_to_list, common_payload, finite_or_none, make_artifact_dir, stdout_to_stderr,
)

def qblox_resonator_spectroscopy(
    qubits: list[str],
    frequency_width_hz: float = 20e6,
    frequency_npoints: int = 201,
    repetitions: int = 200,
    readout_amplitude: float | None = None,
    fit_method: str = "complex",
    minimum_r_squared: float = 0.90,
    minimum_edge_margin_fraction: float = 0.08,
    apply_update: bool = False,
) -> dict:
    """Run multiplexed resonator spectroscopy with deterministic fit validation."""
    
    get_hardware_agent()
    qobjs = [get_qubit(qubit_name) for qubit_name in qubits]
    node = MultiplexedResonatorSpectroscopy(qobjs)

    with stdout_to_stderr():
        node.execute(
            frequency_width=frequency_width_hz,
            frequency_npoints=frequency_npoints,
            repetitions=repetitions,
            ro_amp=readout_amplitude,
        )
        node.analyze(qubits_to_analyze=qubits, fit_method=fit_method)

    payload = common_payload(node, "resonator_spectroscopy", qubits)
    artifact_dir = make_artifact_dir(payload["tuid"], "resonator_spectroscopy")
    results = {}
    accepted_all = True

    for qname, res in node.analyses.items():
        freqs = np.asarray(res["freqs"], dtype=float)
        s21 = np.asarray(res["s21"], dtype=complex)
        fit = res["fit_result"]
        fr = float(res["fr"])
        span = float(freqs.max() - freqs.min())
        edge_margin = min(fr - freqs.min(), freqs.max() - fr) / span if span > 0 else -1.0

        if fit.success:
            if fit_method == "complex":
                prediction = np.asarray(fit.eval(f=freqs), dtype=complex)
                observed = np.abs(s21)
                predicted = np.abs(prediction)
            else:
                observed = np.abs(s21)
                predicted = np.asarray(fit.eval(f_ghz=freqs / 1e9), dtype=float)
            ss_res = float(np.sum((observed - predicted) ** 2))
            ss_tot = float(np.sum((observed - np.mean(observed)) ** 2))
            r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
        else:
            prediction = None
            r_squared = float("nan")

        reasons = []
        if not bool(fit.success):
            reasons.append("fit_failed")
        if not np.isfinite(r_squared) or r_squared < minimum_r_squared:
            reasons.append("low_r_squared")
        if edge_margin < minimum_edge_margin_fraction:
            reasons.append("resonance_near_scan_edge")
        if not (freqs.min() <= fr <= freqs.max()):
            reasons.append("fitted_frequency_outside_scan")

        accepted = len(reasons) == 0
        accepted_all &= accepted

        image_path = artifact_dir / f"{qname}.png"
        fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
        axes[0].plot(freqs / 1e9, np.abs(s21), "o", markersize=3, label="data")
        if fit.success:
            fine = np.linspace(freqs.min(), freqs.max(), 800)
            if fit_method == "complex":
                fit_curve = fit.eval(f=fine)
                axes[0].plot(fine / 1e9, np.abs(fit_curve), label="fit")
                axes[1].plot(np.real(fit_curve), np.imag(fit_curve), label="fit")
            else:
                axes[0].plot(fine / 1e9, fit.eval(f_ghz=fine / 1e9), label="fit")
        axes[0].axvline(fr / 1e9, linestyle="--")
        axes[0].set_xlabel("Frequency (GHz)")
        axes[0].set_ylabel("|S21|")
        axes[0].legend()
        axes[0].grid(alpha=0.2)
        axes[1].plot(s21.real, s21.imag, "o", markersize=3, label="data")
        axes[1].set_xlabel("I")
        axes[1].set_ylabel("Q")
        axes[1].legend()
        axes[1].grid(alpha=0.2)
        fig.suptitle(f"Resonator Spectroscopy - {qname}")
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)

        if accepted:
            action = "update_readout_frequency"
        elif "resonance_near_scan_edge" in reasons:
            action = "recenter_scan_at_candidate_frequency_and_repeat"
        elif "low_r_squared" in reasons:
            action = "increase_repetitions_or_change_fit_method"
        else:
            action = "repeat_with_wider_frequency_span"

        results[qname] = {
            "accepted": accepted,
            "failure_reasons": reasons,
            "resonance_frequency_hz": finite_or_none(fr),
            "qi_or_q_loaded": finite_or_none(res["qi"]),
            "qc": finite_or_none(res["qc"]),
            "fit_success": bool(fit.success),
            "r_squared": finite_or_none(r_squared),
            "edge_margin_fraction": finite_or_none(edge_margin),
            "recommended_action": action,
            "image_path": str(image_path.resolve()),
            "data": {
                "frequency_hz": array_to_list(freqs),
                "s21": array_to_list(s21),
            },
        }


    with open(Path(__file__).parent / "logs" / f"{datetime.now().strftime('%d%m%Y_%H%M%S')}.json", mode="w+", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        print()

    update_applied = False
    if apply_update and accepted_all:
        with stdout_to_stderr():
            node.post_run()
        update_applied = True

    payload.update({
        "status": "success" if accepted_all else "needs_retry",
        "accepted": accepted_all,
        "update_applied": update_applied,
        "results": results,
    })
    return payload
