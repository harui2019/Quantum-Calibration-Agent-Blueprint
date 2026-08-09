from __future__ import annotations

import sys
from typing import Annotated
import contextlib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from _qblox_runtime import HARDWARE_REPO_PATH, get_hardware_agent, get_qubit, save_device_config
from _ising_utils import make_artifact_dir, png_plot_entry

sys.path.append(str(HARDWARE_REPO_PATH))

from cal05a_qubit_spectroscopy_pulsed import MultiplexedQubitSpectroscopyPulsed


def _real_list(values) -> list[float]:
    array = np.asarray(values)
    return [float(x) for x in array.reshape(-1)]


def _complex_components(values) -> tuple[list[float], list[float]]:
    array = np.asarray(values).reshape(-1)
    return (
        [float(x) for x in array.real],
        [float(x) for x in array.imag],
    )


def qblox_qubit_spectroscopy(
    qubit_name: str = "q1",
    f01_width_mhz: Annotated[float, (1.0, 1000.0)] = 100.0,
    f01_npoints: Annotated[int, (21, 2001)] = 200,
    repetitions: Annotated[int, (1, 10000)] = 200,
    saturation_amp: Annotated[float, (0.0, 1.0)] = 0.130335,
    saturation_duration_s: Annotated[float, (1e-9, 100e-6)] = 1.6e-5,
    drive_att_db: Annotated[int, (0, 30)] = 0,
    minimum_linewidth_mhz: float = 0.05,
    maximum_linewidth_mhz: float = 50.0,
    apply_update: bool = False,
) -> dict:
    """Run Qblox pulsed (sequential saturation-pulse) qubit spectroscopy and fit the
    qubit frequency. Drive and readout never overlap in time, avoiding the AC-Stark
    contamination a continuous-wave drive can cause.

    Args:
        qubit_name:
            Target hardware qubit name, such as q1 or q2.
        f01_width_mhz:
            Total spectroscopy sweep width in MHz.
        f01_npoints:
            Number of frequency points.
        repetitions:
            Number of repeated spectroscopy sweeps.
        saturation_amp:
            Saturation pulse amplitude in volts.
        saturation_duration_s:
            Saturation pulse duration in seconds.
        drive_att_db:
            Qblox output attenuation in dB. Must be even and between 0 and 30.
        minimum_linewidth_mhz:
            Reject the fit if the fitted linewidth is below this (likely a spurious peak).
        maximum_linewidth_mhz:
            Reject the fit if the fitted linewidth is above this (likely a bad/noisy fit).
        apply_update:
            If True and the fit passes acceptance checks, write the fitted f01 into the
            qubit's device config (dut_config_AS_QRC.json) so downstream experiments pick
            it up automatically.
    """

    if drive_att_db % 2 != 0:
        return {
            "status": "failed",
            "error": "drive_att_db must be an even integer between 0 and 30.",
        }

    try:
        # Initialize hardware and resolve the requested hardware qubit.
        hw_agent = get_hardware_agent()
        qubit = get_qubit(qubit_name)

        experiment = MultiplexedQubitSpectroscopyPulsed([qubit])

        # Your experiment currently prints compiled schedules and analysis
        # messages. Send these to stderr so QCA stdout remains valid JSON.
        with contextlib.redirect_stdout(sys.stderr):
            experiment.execute(
                f01_width=f01_width_mhz * 1e6,
                f01_npoints=f01_npoints,
                repetitions=repetitions,
                saturation_amp=saturation_amp,
                saturation_duration=saturation_duration_s,
                drive_att={qubit_name: drive_att_db},
            )

            experiment.analyze(qubits_to_analyze=[qubit_name])

        if experiment.dataset is None:
            return {
                "status": "failed",
                "error": "Qblox returned no dataset.",
            }

        if qubit_name not in experiment.analyses:
            return {
                "status": "failed",
                "error": f"No analysis result was produced for {qubit_name}.",
            }

        analysis = experiment.analyses[qubit_name]

        frequencies_hz = np.asarray(analysis["freqs"])
        rotated_signal = np.asarray(analysis["rotated_real"])
        raw_s21 = np.asarray(analysis["s21_raw"])

        s21_real, s21_imag = _complex_components(raw_s21)

        fitted_f01_hz = float(analysis["f01"])
        linewidth_hz = float(analysis["linewidth"])
        fit_success = bool(analysis["fit_result"].success)
        linewidth_mhz = linewidth_hz / 1e6

        reasons = []
        if not fit_success:
            reasons.append("fit_failed")
        if not np.isfinite(linewidth_mhz) or linewidth_mhz < minimum_linewidth_mhz:
            reasons.append("linewidth_too_narrow")
        if not np.isfinite(linewidth_mhz) or linewidth_mhz > maximum_linewidth_mhz:
            reasons.append("linewidth_too_wide")
        accepted = len(reasons) == 0

        tuid = str(experiment.dataset.attrs.get("tuid", ""))

        fit_result = analysis["fit_result"]
        artifact_dir = make_artifact_dir(tuid, "qubit_spectroscopy")
        image_path = artifact_dir / f"{qubit_name}.png"
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.plot(
            frequencies_hz / 1e9, rotated_signal, "o", markersize=3, label="data"
        )
        if fit_success:
            fine_freqs = np.linspace(frequencies_hz.min(), frequencies_hz.max(), 300)
            ax.plot(
                fine_freqs / 1e9, fit_result.eval(x=fine_freqs), "r-", label="fit"
            )
            ax.axvline(fitted_f01_hz / 1e9, linestyle="--")
        ax.set_xlabel("Drive frequency (GHz)")
        ax.set_ylabel("Rotated signal (V)")
        ax.set_title(f"Qubit Spectroscopy - {qubit_name}")
        ax.legend()
        ax.grid(alpha=0.2)
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)
        plots = [png_plot_entry(image_path, f"Qubit Spectroscopy - {qubit_name}")]

        update_applied = False
        config_saved = None
        if apply_update and accepted:
            with contextlib.redirect_stdout(sys.stderr):
                experiment.post_run([qubit_name])
            config_saved = save_device_config(hw_agent)
            update_applied = True

        result = {
            "status": "success" if accepted else "failed",
            "accepted": accepted,
            "failure_reasons": reasons,
            "update_applied": update_applied,
            "config_saved": config_saved,
            "plots": plots,
            "data": {
                "fitted_f01": {
                    "type": "scalar",
                    "value": fitted_f01_hz / 1e9,
                    "unit": "GHz",
                    "name": f"{qubit_name} fitted qubit frequency",
                },
                "linewidth": {
                    "type": "scalar",
                    "value": linewidth_hz / 1e6,
                    "unit": "MHz",
                    "name": f"{qubit_name} spectroscopy linewidth",
                },
                "fit_success": {
                    "type": "scalar",
                    "value": fit_success,
                    "unit": "boolean",
                    "name": "Lorentzian fit success",
                },
                "frequency": {
                    "type": "array",
                    "value": _real_list(frequencies_hz / 1e9),
                    "unit": "GHz",
                    "name": "Drive frequency",
                },
                "rotated_signal": {
                    "type": "array",
                    "value": _real_list(rotated_signal),
                    "unit": "V",
                    "name": "PCA-rotated spectroscopy response",
                },
                "s21_real": {
                    "type": "array",
                    "value": s21_real,
                    "unit": "V",
                    "name": "Raw S21 real component",
                },
                "s21_imag": {
                    "type": "array",
                    "value": s21_imag,
                    "unit": "V",
                    "name": "Raw S21 imaginary component",
                },
                "image_path": {
                    "type": "scalar",
                    "value": str(image_path.resolve()),
                    "unit": "",
                    "name": "Spectroscopy plot file path",
                },
                "tuid": {
                    "type": "scalar",
                    "value": tuid,
                    "unit": "",
                    "name": "Qblox experiment identifier",
                },
            },
        }
        if not accepted:
            result["error"] = f"{qubit_name}: {', '.join(reasons)}"
        return result

    except Exception as exc:
        return {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }