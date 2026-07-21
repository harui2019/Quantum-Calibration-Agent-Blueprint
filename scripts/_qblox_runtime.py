from __future__ import annotations

import os
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

from qblox_scheduler.qblox.hardware_agent import HardwareAgent

sys.path.append("/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting")

from single_qubit_experiment_helpers.experiment import Experiment, SingleQubitExperiment
from custom_elements import FluxTunableTransmonElement


PROJECT_ROOT = Path(__file__).resolve().parents[1]

HARDWARE_CONFIG = Path(
    os.getenv(
        "QBLOX_HARDWARE_CONFIG",
        "/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting/dependencies/configs/2x2/hw_config_AS_QRC.json",
    )
).expanduser().resolve()

DEVICE_CONFIG = Path(
    os.getenv(
        "QBLOX_DEVICE_CONFIG","/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting/dependencies/configs/2x2/dut_config_AS_QRC.json",
    )
).expanduser().resolve()

OUTPUT_DIR = Path(
    os.getenv(
        "QBLOX_OUTPUT_DIR",
         "/Users/renychang/Desktop/qblox/2x2",
    )
).expanduser().resolve()


@lru_cache(maxsize=1)
def get_hardware_agent() -> HardwareAgent:
    """Create and configure the Qblox HardwareAgent."""

    if not HARDWARE_CONFIG.exists():
        raise FileNotFoundError(
            f"Hardware configuration not found: {HARDWARE_CONFIG}"
        )

    if not DEVICE_CONFIG.exists():
        raise FileNotFoundError(
            f"Quantum-device configuration not found: {DEVICE_CONFIG}"
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    hw_agent = HardwareAgent(
        hardware_configuration=str(HARDWARE_CONFIG),
        quantum_device_configuration=str(DEVICE_CONFIG),
        output_dir=str(OUTPUT_DIR),
    )

    # Preserve the mechanism currently used by your Experiment classes.
    Experiment.hw_agent = hw_agent
    Experiment.quantum_device = hw_agent.quantum_device

    return hw_agent


def get_qubit(qubit_name: str) -> Any:
    """Resolve a qubit object from the configured QuantumDevice."""

    hw_agent = get_hardware_agent()
    quantum_device = hw_agent.quantum_device

    # Common Qblox/Quantify accessor.
    try:
        return quantum_device.get_element(qubit_name)
    except (AttributeError, KeyError):
        pass

    # Alternative accessor used by some local wrappers.
    try:
        return quantum_device.elements()[qubit_name]
    except (AttributeError, KeyError, TypeError):
        pass

    # Alternative dictionary-like access.
    try:
        return quantum_device[qubit_name]
    except (KeyError, TypeError):
        pass

    raise KeyError(
        f"Unable to find qubit {qubit_name!r} in the configured QuantumDevice. "
        "Replace get_qubit() with the same accessor currently used to create "
        "q1 and q2 in your notebook."
    )


