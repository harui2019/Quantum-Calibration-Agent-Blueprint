from __future__ import annotations

import sys
from typing import Annotated
import contextlib
import numpy as np

from _qblox_runtime import get_hardware_agent, get_qubit

sys.path.append("/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting")

from cal05_qubit_spectroscopy import MultiplexedQubitSpectroscopy


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
    f01_width_mhz: Annotated[float, (1.0, 1000.0)] = 400.0,
    f01_npoints: Annotated[int, (21, 2001)] = 200,
    repetitions: Annotated[int, (1, 10000)] = 200,
    voltage_offset: Annotated[float, (0.0, 1.0)] = 0.2,
    drive_att_db: Annotated[int, (0, 30)] = 0,
    flux_mode: str = "joint",
    reset_type: str = "thermal",
) -> dict:
    """Run Qblox continuous-wave qubit spectroscopy and fit the qubit frequency.

    Args:
        qubit_name:
            Target hardware qubit name, such as q1 or q2.
        f01_width_mhz:
            Total spectroscopy sweep width in MHz.
        f01_npoints:
            Number of frequency points.
        repetitions:
            Number of repeated spectroscopy sweeps.
        voltage_offset:
            Continuous-wave microwave drive amplitude in volts.
        drive_att_db:
            Qblox output attenuation in dB. Must be even and between 0 and 30.
        flux_mode:
            Flux-point mode: joint, independent, or arbitrary.
        reset_type:
            Reset method: thermal or active.
    """

    if drive_att_db % 2 != 0:
        return {
            "status": "failed",
            "error": "drive_att_db must be an even integer between 0 and 30.",
        }

    if flux_mode not in {"joint", "independent", "arbitrary"}:
        return {
            "status": "failed",
            "error": (
                "flux_mode must be 'joint', 'independent', or 'arbitrary'."
            ),
        }

    if reset_type not in {"thermal", "active"}:
        return {
            "status": "failed",
            "error": "reset_type must be 'thermal' or 'active'.",
        }

    try:
        # Initialize hardware and resolve the requested hardware qubit.
        get_hardware_agent()
        qubit = get_qubit(qubit_name)

        experiment = MultiplexedQubitSpectroscopy([qubit])

        # Your experiment currently prints compiled schedules and analysis
        # messages. Send these to stderr so QCA stdout remains valid JSON.
        with contextlib.redirect_stdout(sys.stderr):
            experiment.execute(
                flux_point_joint_or_independent_or_arbitrary=flux_mode,
                f01_width=f01_width_mhz * 1e6,
                f01_npoints=f01_npoints,
                repetitions=repetitions,
                voltage_offset={qubit_name: voltage_offset},
                drive_att={qubit_name: drive_att_db},
                reset_type=reset_type,
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

        tuid = str(experiment.dataset.attrs.get("tuid", ""))

        return {
            "status": "success",
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
                "tuid": {
                    "type": "scalar",
                    "value": tuid,
                    "unit": "",
                    "name": "Qblox experiment identifier",
                },
            },
        }

    except Exception as exc:
        return {
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}",
        }