# Writing Experiment Scripts

This document covers the conventions specific to writing a **real-hardware `qblox_*.py` wrapper** (adding a new calibration stage from `02_Calibration_Workflow.md` that isn't in `03_Experiment_API.md` yet). For the generic auto-discovery mechanics that apply to *any* script (type hints, `Annotated` ranges, one-function-per-file vs multi-function-per-file, the `qca experiments validate` CLI), read `data/knowledge/skills/writing-experiment-scripts/SKILL.md` first — this document does not repeat that material.

## Directory Layout

All experiment scripts live flat in `scripts/` (no subpackages). Two naming conventions distinguish public (discoverable) from private (helper) modules:

| Prefix | Discoverable? | Examples |
|---|---|---|
| `qblox_*.py` | yes | `qblox_resonator_spectroscopy.py`, `qblox_time_of_flight.py` |
| `_*.py` | no (private) | `_qblox_runtime.py`, `_ising_utils.py` |

A file starting with `_` is never scanned by `core/discovery.py` — that's where shared helpers belong. A file's every top-level public function (no leading `_`) with a `-> dict` return annotation and at least one typed parameter becomes its own separately callable experiment, even multiple in one file (see `qblox_resonator_punchout.py`, which defines both `qblox_resonator_punchout_attenuation` and `qblox_resonator_punchout_amplitude`).

## Standard Wrapper Skeleton

```python
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import sys

from _qblox_runtime import get_hardware_agent, get_qubit, save_device_config

sys.path.append("/Users/renychang/flux-tunable-transmons-with-flux-tunable-couplers/docs/applications/superconducting")
from calNN_whatever import SomeNodeClass

from _ising_utils import (
    array_to_list, common_payload, finite_or_none, make_artifact_dir,
    png_plot_entry, stdout_to_stderr,
)


def qblox_my_new_experiment(
    qubits: list[str],
    some_param: float = 1.0,
    apply_update: bool = False,
) -> dict:
    """One-line description of the experiment."""

    hw_agent = get_hardware_agent()
    qobjs = [get_qubit(q) for q in qubits]
    node = SomeNodeClass(qobjs)

    with stdout_to_stderr():
        node.execute(some_param=some_param)
        node.analyze(qubits_to_analyze=qubits)

    payload = common_payload(node, "my_new_experiment", qubits)
    artifact_dir = make_artifact_dir(payload["tuid"], "my_new_experiment")
    results, plots = {}, []
    accepted_all = True

    for qname, res in node.analyses.items():
        accepted = ...  # deterministic pass/fail check
        accepted_all &= accepted

        image_path = artifact_dir / f"{qname}.png"
        fig, ax = plt.subplots(figsize=(8, 5))
        # ... plot res ...
        fig.tight_layout()
        fig.savefig(image_path, dpi=160)
        plt.close(fig)
        plots.append(png_plot_entry(image_path, f"My New Experiment - {qname}"))

        results[qname] = {
            "accepted": accepted,
            "image_path": str(image_path.resolve()),
            # ... numeric results, "data"/"trace"/"sweep" arrays via array_to_list ...
        }

    update_applied = False
    config_saved = None
    if apply_update and accepted_all:
        with stdout_to_stderr():
            node.post_run()
        # node.post_run() only mutates in-memory objects — it never touches disk.
        # Without this call, the update is silently lost when the subprocess exits.
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
            f"{q}: {', '.join(r.get('failure_reasons', ['unspecified']))}"
            for q, r in results.items() if not r["accepted"]
        )
    return payload
```

Every existing wrapper in `scripts/` follows this shape. Deviating from it (e.g. returning `"needs_retry"` as a status) breaks `core/runner.py`'s result validation — see `05_Result_Format.md`.

## Plot Conventions

- `matplotlib.use("Agg")` **before** `import matplotlib.pyplot as plt`, at module level, every time — there is no display attached to the subprocess that runs these.
- Never call `plt.show()`.
- Always `fig.savefig(image_path, dpi=160)` then `plt.close(fig)` — leaked figures accumulate across repeated calls within the same process.
- Save the PNG to `artifact_dir` (from `make_artifact_dir`), then wrap it for the result payload with `png_plot_entry(image_path, name)` from `_ising_utils.py` — this base64-encodes it into the `{"name", "format": "png", "data"}` shape `05_Result_Format.md` and the UI/`vlm_inspect` expect. Saving the file alone is not enough; if you skip `png_plot_entry` and don't add it to a top-level `"plots"` list, neither the UI nor `vlm_inspect` will ever see it (they only exist on disk, referenced by `image_path`).
- Keep `image_path` in the per-qubit result too — it's the one thing a human (or an agent reading the raw file) can open directly without going through the plot pipeline.

## Logging / stdout Discipline

`core/runner.py` executes the wrapper in a subprocess and expects **exactly one line of JSON on stdout** (the final `print(json.dumps(result))` it wraps around your function call). Anything your wrapper or the underlying node class prints to stdout (compiled-schedule dumps, progress messages, warnings) will corrupt that JSON.

- Wrap any call into node/experiment code that might print with `stdout_to_stderr()` from `_ising_utils.py` — it's a context manager that redirects stdout to stderr for its duration.
- If `log_file` is passed through (it always is, from `tools/lab_tool.py`), that redirected stderr is what ends up as the real-time progress log at `data/<experiment_id>/output.log` — so redirecting to stderr isn't just "hiding" the output, it's where it's supposed to go.
- Don't add your own `print()` calls for status/debug info outside of that redirected context — same corruption risk.

## Error Handling

Two acceptable patterns, both already in use:

1. **Fail fast on bad parameters, before touching hardware** (see `qblox_qubit_spectroscopy`'s even-attenuation / enum checks): validate inputs at the top of the function and `return {"status": "failed", "error": "..."}` immediately if invalid. Cheap and avoids wasting hardware time on a call that was never going to work.
2. **Deterministic quality gates after the fact** (see the other four wrappers): always run the measurement, always fit, then decide `accepted` per qubit from numeric thresholds (R², SNR, contrast, edge margin, etc.) and set the top-level `status` accordingly. Prefer this pattern when the "failure" is a legitimate measurement outcome (bad resonance, low contrast) rather than a programming error — record *why* it failed in `failure_reasons`/`error` rather than raising an exception.

Do **not** let a Python exception escape uncaught to the top level unless it's a genuine bug — an uncaught exception makes the whole subprocess exit non-zero, and `core/runner.py` surfaces that as `"Experiment subprocess failed: <stderr tail>"`, which loses the structured per-qubit detail a `status: "failed"` return would have preserved.

`apply_update` always defaults to `False`. Never flip a wrapper's default to `True` — writing to device config should always be an explicit, opt-in action by whoever calls the experiment (see `07_Best_Practices.md`).
