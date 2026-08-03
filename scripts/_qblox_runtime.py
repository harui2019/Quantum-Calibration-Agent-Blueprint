from __future__ import annotations

import os
import shutil
import sys
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

from qblox_scheduler.qblox.hardware_agent import HardwareAgent

HARDWARE_REPO_PATH = Path(
    os.getenv(
        "QBLOX_HARDWARE_REPO_PATH",
        "/home/reny871224/flux-tunable-transmons-with-flux-tunable-couplers-share_with_AS_for_training/docs/applications/superconducting",
    )
).expanduser().resolve()

sys.path.append(str(HARDWARE_REPO_PATH))

from single_qubit_experiment_helpers.experiment import Experiment, SingleQubitExperiment
from custom_elements import FluxTunableTransmonElement


PROJECT_ROOT = Path(__file__).resolve().parents[1]

HARDWARE_CONFIG = Path(
    os.getenv(
        "QBLOX_HARDWARE_CONFIG",
        str(HARDWARE_REPO_PATH / "dependencies/configs/7SQ/hw_config_AS_QRC.json"),
    )
).expanduser().resolve()

DEVICE_CONFIG = Path(
    os.getenv(
        "QBLOX_DEVICE_CONFIG", str(HARDWARE_REPO_PATH / "dependencies/configs/7SQ/dut_config_AS_QRC.json"),
    )
).expanduser().resolve()

OUTPUT_DIR = Path(
    os.getenv(
        "QBLOX_OUTPUT_DIR",
         "/home/reny871224/Desktop/qblox/7SQ",
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

    # HardwareAgent does not connect to the clusters on construction; accessing
    # hardware_configuration (or running a schedule) before this raises
    # TypeError("Hardware not initialized yet, please do so with `connect_clusters`").
    hw_agent.connect_clusters()

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


def _backup(path: Path) -> str | None:
    """Copy an existing config file aside before overwriting it. Returns the backup path, if any."""
    if not path.exists():
        return None
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_path = path.with_name(f"{path.stem}.{timestamp}.bak{path.suffix}")
    shutil.copy2(path, backup_path)
    return str(backup_path)


def save_device_config(hw_agent: HardwareAgent) -> dict[str, Any]:
    """Persist in-memory device/hardware config changes back to the exact files
    they were loaded from (HARDWARE_CONFIG/DEVICE_CONFIG — env-var configurable,
    never a hardcoded chip-topology path).

    node.post_run() in the calibration node classes only mutates the in-memory
    quantum_device / hardware_configuration objects; nothing here happens unless
    this is called explicitly after a successful post_run().
    """
    backups = {
        str(DEVICE_CONFIG): _backup(DEVICE_CONFIG),
        str(HARDWARE_CONFIG): _backup(HARDWARE_CONFIG),
    }
    DEVICE_CONFIG.write_text(hw_agent.quantum_device.to_json())
    HARDWARE_CONFIG.write_text(hw_agent.hardware_configuration.to_json())
    return {
        "device_config": str(DEVICE_CONFIG),
        "hardware_config": str(HARDWARE_CONFIG),
        "backups": backups,
    }


