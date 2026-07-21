from __future__ import annotations

import contextlib
import io
import math
import os
import sys
from pathlib import Path
from typing import Any

import numpy as np


@contextlib.contextmanager
def stdout_to_stderr():
    """Keep QCA subprocess stdout clean for its final JSON payload."""
    with contextlib.redirect_stdout(sys.stderr):
        yield


def finite_or_none(value: Any) -> float | int | str | bool | None:
    if value is None:
        return None
    if isinstance(value, (bool, str)):
        return value
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        value = float(value)
        return value if math.isfinite(value) else None
    return value


def array_to_list(values: Any) -> list:
    array = np.asarray(values)
    if np.iscomplexobj(array):
        return [
            {"real": finite_or_none(v.real), "imag": finite_or_none(v.imag)}
            for v in array.ravel()
        ]
    return [finite_or_none(v) for v in array.ravel()]


def make_artifact_dir(tuid: str | None, experiment: str) -> Path:
    root = Path(os.environ.get("QBLOX_ISING_ARTIFACT_DIR", "artifacts"))
    safe_tuid = str(tuid or "unknown").replace("/", "_")
    path = root / f"{experiment}_{safe_tuid}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def common_payload(node: Any, experiment: str, qubits: list[str]) -> dict:
    attrs = getattr(getattr(node, "dataset", None), "attrs", {}) or {}
    return {
        "experiment": experiment,
        "backend": "qblox",
        "qubits": qubits,
        "tuid": str(attrs.get("tuid", "unknown")),
    }
