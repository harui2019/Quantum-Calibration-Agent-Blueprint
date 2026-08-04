# Common Failures

Failure modes actually observed in this system, in two groups: **plumbing failures** (Python/config/connection — nothing physical is wrong, something in the stack is misconfigured) and **measurement failures** (the hardware ran fine, the physics/fit just didn't cooperate). Telling these apart correctly matters — retrying a plumbing failure without fixing the cause just wastes hardware time; retrying a measurement failure with the same parameters usually reproduces the same result.

## Plumbing Failures

### `ModuleNotFoundError: No module named 'qblox_scheduler'`

- **Symptoms**: import error, immediately, before anything hardware-related happens.
- **Cause**: wrong Python interpreter. The default `python`/system interpreter does not have `qblox_scheduler` installed — only the dedicated venv does (`data/knowledge/skills/qblox-hardware-environment/SKILL.md`).
- **Action**: use `run_experiment` (it selects the right interpreter automatically for any `qblox_*` experiment name) rather than a hand-written subprocess/script. Do **not** try to `pip install qblox_scheduler` into the wrong environment.
- **Retry or stop**: retry immediately through the correct path; this is never a hardware issue.

### `ModuleNotFoundError: No module named '_qblox_runtime'`

- **Symptoms**: import error for a private helper module specifically (not `qblox_scheduler` itself).
- **Cause**: historically, a fragile `sys.path` setup where `scripts/` itself wasn't guaranteed to be importable. `core/runner.py` now inserts both `scripts/`'s parent (for the package-qualified `from scripts.<module> import <name>` import) and `scripts/` itself (so the scripts' own bare `from _qblox_runtime import ...` / `from _ising_utils import ...` imports resolve regardless of the subprocess's working directory) for every `run_experiment` call, so this should not recur through the normal path.
- **Action**: if seen again, first check whether the call actually went through `run_experiment` or through some improvised script that skipped the normal subprocess setup — see `07_Best_Practices.md` on not hand-rolling workarounds.
- **Retry or stop**: retry through `run_experiment`; if it recurs there, stop and report — that's a regression in `core/runner.py`, not something to patch around per-call.

### `TypeError: Hardware not initialized yet, please do so with connect_clusters`

- **Symptoms**: raised as soon as something touches `hw_agent.hardware_configuration` (or another property requiring a live connection).
- **Cause**: `HardwareAgent` does not connect to the cluster on construction — `connect_clusters()` must be called explicitly. `scripts/_qblox_runtime.py::get_hardware_agent()` does this immediately after construction.
- **Action**: don't go looking for a separate "connection setup script," and don't try to reimplement `HardwareAgent` initialization by hand. If this error appears despite `_qblox_runtime.py` calling `connect_clusters()`, the more likely cause at that point is the next failure mode below.
- **Retry or stop**: if it's really the missing-call bug, this is a code regression — stop and report. If `_qblox_runtime.py` is intact, suspect a connection problem instead.

### Cluster connection refused / times out

- **Symptoms**: `connect_clusters()` itself fails, or hangs, rather than the property-access `TypeError` above.
- **Cause**: Qblox clusters generally accept only one active connection. The most common real cause is another process — frequently a live Jupyter kernel that still has `multiplexed_tuneup_notebook_AS_2x2.ipynb`'s `hw_agent` open — holding the connection. Every `run_experiment` call builds a brand-new `HardwareAgent` from scratch (`07_Best_Practices.md` — nothing persists between calls), so this can happen on literally any call, not just the first one of a session.
- **Action**: ask whether a notebook kernel or another QCA session is currently connected to the same cluster; that needs to be closed/released first. Check basic network reachability to the cluster IP (`01_Hardware_Environment.md`) as a second possibility.
- **Retry or stop**: stop and ask the user — retrying without freeing the other connection will just fail again.

### Malformed hardware/device config JSON

- **Symptoms**: `HardwareAgent(...)` construction fails immediately with a `JSONDecodeError`, for **every** qubit, even ones unrelated to the actual typo.
- **Cause**: `hw_config_AS_QRC.json` / `dut_config_AS_QRC.json` are hand-editable with no schema validation on save. A single malformed token (e.g. a stray space inside a number, `3.9 e9` instead of `3.9e9`) breaks parsing of the whole file.
- **Action**: `json.load()` the file directly to get a precise line/column for the syntax error, rather than guessing from the qblox-side error message.
- **Retry or stop**: stop; this needs a manual edit to the config file, then retry.

### `RuntimeError: Experiment subprocess failed: <stderr tail>` with no structured detail

- **Symptoms**: the runner reports a bare stderr tail instead of a normal `status: "failed"` result with `error`.
- **Cause**: an uncaught Python exception inside the wrapper (a real bug, not a deliberate "failed" return) — see `04_Writing_Experiment_Scripts.md`'s error-handling patterns.
- **Action**: read the stderr tail for the actual traceback; this is a code bug in the wrapper or the node class it calls, not a measurement problem.
- **Retry or stop**: stop; retrying with the same parameters will hit the same bug.

### `vlm_inspect` returns "No plots found in experiment"

- **Cause**: every current `qblox_*` experiment (`03_Experiment_API.md`) is expected to produce at least one plot, so this means a wrapper failed to populate the top-level `plots` list (`05_Result_Format.md`) — check the script for a missing `png_plot_entry()` call or a plot generation step that silently failed.
- **Action**: check `03_Experiment_API.md` for the plot(s) that experiment is expected to produce, then inspect the wrapper source for why `plots` came back empty.

## Measurement Failures (hardware ran, physics/fit didn't cooperate)

| Failure reason (as it appears in `failure_reasons`/`error`) | Experiment(s) | Meaning | Recommended action |
|---|---|---|---|
| `fit_failed` | resonator spectroscopy | The fitter itself didn't converge | Increase `repetitions` (more averaging) or widen `frequency_width_hz` |
| `low_r_squared` | resonator spectroscopy | Fit converged but tracks the data poorly *within `r_squared_window_linewidths` fitted linewidths of the dip* — off-resonance baseline ripple (e.g. impedance mismatch) is already excluded from this check, so a low value here means the dip itself is poorly tracked, not just a noisy baseline | Try `fit_method` change, or increase averaging (low SNR). Only widen `r_squared_window_linewidths` if you have a specific reason the window is too tight for this resonance's linewidth — don't loosen it just to make a bad dip fit pass |
| `resonance_near_scan_edge` | resonator spectroscopy | Peak/dip sits within `minimum_edge_margin_fraction` of the window edge — the true resonance may be outside the scanned range | Recenter the scan on the candidate frequency and widen it, then repeat |
| `fitted_frequency_outside_scan` | resonator spectroscopy | Fit extrapolated a resonance outside the swept window entirely — treat as no real signal found | Widen the span significantly; check whether the qubit/resonator is even connected on the assumed port |
| "no operating point met the contrast/shift thresholds" | punchout (attenuation/amplitude) | No attenuation/amplitude step in the sweep satisfied both the contrast and frequency-shift criteria | Widen `maximum_normalized_frequency_shift`/lower `minimum_normalized_contrast` cautiously, or widen the sweep range |
| TOF `message` indicating no clean edge | time_of_flight | The magnitude trace didn't show a clean enough rising edge to fit a delay | Increase `pulse_amplitude`, check `acquisition_delay_s` isn't cutting off the edge |
| `drive_att_db must be an even integer...` | qubit spectroscopy | Parameter validation failed before touching hardware | Fix the parameter — this is a caller error, not a hardware issue |

For all of the resonator/punchout/TOF cases above, the failure is real data telling you the current parameters or config assumption is wrong — the correct response is almost always **adjust and retry**, not repeat identically. For the qubit-spectroscopy parameter-validation cases, fix the input; retrying unchanged will fail identically every time.

## Suspicious-But-Not-Erroring Results

Things that return `status: "success"` but deserve a second look before trusting them:

- **Duplicate calibration values across different qubits** (e.g. identical `amp180`/`acq_rotation`/`acq_threshold` to many decimal places between two qubits) usually means one qubit's calibration was copy-pasted from another and never independently run — not a coincidence.
- **`accepted: true` on every qubit in a multi-qubit punchout call, but `update_applied: false`** — check `update_reason`; the attenuation variant only applies a shared value across all qubits, so per-qubit disagreement silently blocks the write even though every individual qubit "passed."
- **A downstream experiment's fit looking systematically off** — check whether the upstream stage's `update_applied` was actually `true` (`02_Calibration_Workflow.md`) before assuming the downstream fit itself is broken.
