---
name: qblox-hardware-environment
description: Reference for locating the Qblox hardware config, the correct Python environment, and the human-validated reference notebook needed to run any `qblox_*` experiment (resonator/qubit spectroscopy, punchout, time of flight). Read this BEFORE running or troubleshooting any `qblox_*` experiment, or whenever asked to connect to Qblox hardware.
---

# Qblox Hardware Environment

Everything qblox-related in this repo depends on one specific external project checked out locally on this machine. Read this first so you don't have to rediscover it by trial and error every session.

**⚠️ This repo swaps physical samples periodically** (it has moved from a "2x2" sample to the current 7-qubit "7SQ" sample already). Every path, qubit list, and module number below is a snapshot, not a permanent fact. `scripts/_qblox_runtime.py` — not this doc — decides which config is active, via env-var-overridable constants (`HARDWARE_REPO_PATH`/`QBLOX_HARDWARE_REPO_PATH`, `HARDWARE_CONFIG`/`QBLOX_HARDWARE_CONFIG`, `DEVICE_CONFIG`/`QBLOX_DEVICE_CONFIG`). When in doubt, read that file and the live JSON it points to instead of trusting a number here.

## Source project

All qblox calibration node classes (`cal00_time_of_flight`, `cal02_resonator_spectroscopy`, `cal03_resonator_punchout`, `cal05_qubit_spectroscopy`, ...), `custom_elements.py`, `analysis.py`, and the working reference notebook live at whatever path `HARDWARE_REPO_PATH` in `scripts/_qblox_runtime.py` resolves to. As of the last inspection:

```
/home/reny871224/flux-tunable-transmons-with-flux-tunable-couplers-share_with_AS_for_training/docs/applications/superconducting/
```

Every `qblox_*.py` wrapper in `scripts/` imports `HARDWARE_REPO_PATH` from `_qblox_runtime` and appends it to `sys.path` at import time (rather than hardcoding their own copy) — it must exist for any qblox experiment to import successfully.

## Hardware / device config

Set in `scripts/_qblox_runtime.py`, overridable via environment variables:

| Env var | Default (as of last inspection — currently the `7SQ` sample) |
|---|---|
| `QBLOX_HARDWARE_REPO_PATH` | `.../superconducting` (see Source project above) |
| `QBLOX_HARDWARE_CONFIG` | `.../superconducting/dependencies/configs/7SQ/hw_config_AS_QRC.json` |
| `QBLOX_DEVICE_CONFIG` | `.../superconducting/dependencies/configs/7SQ/dut_config_AS_QRC.json` |
| `QBLOX_OUTPUT_DIR` | `/home/reny871224/Desktop/qblox/7SQ` |
| `QBLOX_ISING_ARTIFACT_DIR` | `artifacts/` (relative to wherever the experiment subprocess runs; defaults to repo root) |

**Known qubits — read this from the live config, don't hardcode it.** As of the last inspection, `dut_config_AS_QRC.json`'s `elements` key lists `q1` through `q7`, and `edges` is empty — **no tunable couplers on the current sample**. An earlier "2x2" sample had `q1`–`q4` plus couplers `c12`/`c23`/`c34`/`c14`; that layout no longer applies. `scripts/agent_qubit_load.py` still has the old 2x2 paths/qubit assumptions hardcoded — it's a stale scratch script, not a source of truth.

**Module map** (needed for `qblox_time_of_flight`'s required `module_number` param, which has no default — **always confirm this against the live `hw_config` JSON's `hardware_description`/`connectivity.graph`, don't reuse a number from a previous sample or from memory**):

As of the last inspection of the `7SQ` sample's `hw_config_AS_QRC.json`: `hardware_description.cluster_A.modules` declares module `6` (`QCM_RF`) and module `8` (`QRM_RF`); `connectivity.graph` wires module `8` to all seven `qN:res` ports (multiplexed readout) but wires drive (`qN:mw`) to `module4` — a module number not declared in `hardware_description` at all. **That inconsistency is in the live file itself**, not a doc error. For readout time-of-flight, module `8` is the best-supported reading, but verify against the current live file before relying on it — do not assume it'll still be `8` (or still be module-8-does-readout) after the next sample swap.

`config.yaml` (VLM/model settings) lives at the repo root — `config.yaml`, not inside any environment or nested package. Don't glob-search for it.

**Experiment names always carry the `qblox_` prefix.** Pass `"qblox_resonator_spectroscopy"` to `run_experiment`/`lab`, not `"resonator_spectroscopy"` — the bare name will be rejected with a "not found" error and you'll waste a round trip re-querying `lab(action="schema", ...)` to get it right. The five valid names are exactly the five in `data/knowledge/documents/03_Experiment_API.md`.

## Cluster connection

`get_hardware_agent()` in `scripts/_qblox_runtime.py` builds the `HardwareAgent` **and calls `hw_agent.connect_clusters()` immediately after** — `HardwareAgent()` does not connect on its own. If you ever see:

```
TypeError: Hardware not initialized yet, please do so with `connect_clusters`
```

it means some code path touched `hw_agent.hardware_configuration` (or another property that needs a live connection) before `connect_clusters()` ran. Do not go looking for a separate "connection setup script" or try to reimplement `HardwareAgent` init by hand — the fix is simply to make sure `connect_clusters()` runs right after construction, which `_qblox_runtime.py` already does. If you hit this error through `run_experiment`, the actual cause is more likely that a cluster is unreachable (e.g. another process — a live notebook kernel — is still holding the connection) than a missing setup step.

## If `run_experiment` fails on a `qblox_*` call

**Never hand-roll your own subprocess, wrapper script, or `sys.path`/import setup to work around a failure.** `tools/lab_tool.py` and `core/runner.py` already handle the interpreter selection and `sys.path` setup correctly (including making the private `_qblox_runtime`/`_ising_utils` helper modules importable). Improvised workarounds bypass the fit validation, `status`/`error` formatting, and `plots` output that the real wrapper produces, so even if they "work" the result isn't usable by the rest of the system.

Two different failure shapes need two different responses — **do not treat them the same, and do not retry more than once without stopping to report:**

- **The call itself raises/exits non-zero** (an exception surfaces as an error, not a normal `{"status": "failed", ...}` dict — e.g. `ModuleNotFoundError`, an import error, a subprocess crash): this is a plumbing bug, not a measurement outcome. Retry **at most once** in case it was transient (a subprocess race, a cluster mid-connect). If it fails the same way again, **stop calling tools and report the exact error to the user** — do not keep retrying, do not go searching for a workaround, do not start investigating unrelated files.
- **The call returns normally with `"status": "failed"`** (a real, structured result — e.g. a bad fit, an unmet threshold, a parameter validation error): this is a legitimate measurement/validation outcome, not a bug to retry past. **Do not automatically retry with different parameters on your own judgment.** Report the result (including `error`/`failure_reasons`) to the user and let them decide whether to adjust parameters and try again. Blindly retrying a genuinely-failing measurement — possibly repeatedly adjusting parameters between attempts — is a common cause of the agent appearing to "never stop thinking": each retry is a full reasoning + tool-call round trip, and there is no automatic cap on how many times you might do this to yourself.

**When a validation `error` names the fix, the fix is exactly what it says — nothing more.** e.g. `"flux_mode must be \"joint\", \"independent\", or \"arbitrary\"."` means: set `flux_mode` to one of those three strings (or just omit it — the default `"joint"` is valid). It does not mean some other, unnamed parameter is also required. Every parameter every `qblox_*` function accepts is listed in full in `data/knowledge/documents/03_Experiment_API.md` — if a parameter you're about to pass isn't in that list, it doesn't exist; don't invent one because an error seemed to imply it.

## Python environment

**Never use the default `python`/system interpreter for anything qblox-related — it does not have `qblox_scheduler` installed.** The environment is a micromamba env, activated with `micromamba activate qblox-training`.

- `run_experiment` already handles this for you: `tools/lab_tool.py` hardcodes the interpreter for any experiment name starting with `qblox_` to:
  ```
  /home/reny871224/micromamba/envs/qblox-training/bin/python
  ```
  You don't need to (and shouldn't) pass `python_path` yourself for `qblox_*` experiments.
- If you ever need to run or test qblox-related Python code **outside** of `run_experiment` (e.g. a one-off diagnostic snippet), you MUST explicitly invoke that same interpreter. Using the default `python3`/`python` will fail with `ModuleNotFoundError: No module named 'qblox_scheduler'` — that error means you used the wrong interpreter, not that the package is missing. Do not try to `pip install qblox_scheduler` to fix it.

## Reference notebook

For "what parameters should this experiment actually use" or "why did my result differ from a manual run," compare against the human-validated tune-up sequence for the **current sample** — as of the last inspection, that's the `7SQ` notebook:

```
/home/reny871224/flux-tunable-transmons-with-flux-tunable-couplers-share_with_AS_for_training/docs/applications/superconducting/multiplexed_tuneup_notebook_AS_7SQ.ipynb
```

If the active sample changes again, this filename changes too (it was `multiplexed_tuneup_notebook_AS_2x2.ipynb` for the earlier 2x2 sample) — confirm the notebook name matches whatever `HARDWARE_REPO_PATH`/`HARDWARE_CONFIG` currently point to rather than assuming this one still applies.

The `qblox_*.py` wrapper default parameters are not guaranteed to match this notebook. If a result looks unexpected, diff the wrapper's parameters (and any pre-experiment setup the notebook does, e.g. attenuation resets) against the corresponding notebook cell before assuming a hardware problem.
