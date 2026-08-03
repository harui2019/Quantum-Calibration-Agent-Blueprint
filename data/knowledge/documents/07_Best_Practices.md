# Best Practices

Engineering conventions for operating and extending this system — grounded in how it's actually built, not generic advice.

## Trust the Tool Layer, Don't Reimplement It

`run_experiment` already handles Python environment selection, `sys.path` setup, subprocess isolation, and result validation correctly (`data/knowledge/skills/qblox-hardware-environment/SKILL.md`, `05_Result_Format.md`). When a `qblox_*` call fails with a Python-level error:

- **Retry through `run_experiment` again first.** Most transient issues (a subprocess race, a cluster that was mid-connect) resolve on retry.
- **Do not** hand-write a substitute subprocess call, a standalone script, or a reimplementation of `HardwareAgent` setup to "work around" a failure. Anything that bypasses the real wrapper also bypasses its fit validation, `status`/`error` formatting, and `plots` output — even if the workaround technically runs, the result isn't usable by `lab`, the UI, or `vlm_inspect`.
- If the same Python-level error survives a retry, that's a bug in this repo's plumbing (a missing helper function, a broken import, a config issue) — report it precisely (the exact exception, which experiment, which parameters) rather than improvising around it.

## Every Experiment Run Is Stateless

Each `run_experiment` call is a brand-new subprocess (`core/runner.py`). Nothing carries over between calls — not Python-level caches (`@lru_cache` on `get_hardware_agent()` only lives for one subprocess), not in-memory state, nothing. Two consequences:

- Never assume "I already connected to the cluster earlier in this conversation" — every call reconnects from scratch.
- Never assume a variable, a monkeypatch, or a global set in one experiment call is visible to the next one. The only thing that actually persists between calls is what got written to disk: the device/hardware config JSON files, and the `data/`/`artifacts/` history.

## Explicit Opt-In for Hardware Writes

`apply_update` defaults to `False` on every wrapper that has it. A `status: "success"` result with `apply_update` unset has measured and fit something, but **has not changed device configuration**. Don't tell a user a parameter was updated unless the result's `update_applied` field says so. When proposing to run an experiment with `apply_update=True`, say so explicitly — that's the one call in the whole pipeline that mutates shared, physical state, and it now genuinely writes `hw_config_AS_QRC.json`/`dut_config_AS_QRC.json` to disk (`05_Result_Format.md`), not just an in-memory object that gets thrown away with the subprocess. Every write backs up the previous file version first (timestamped `.bak.json` next to the original) — if a bad update slips through the acceptance thresholds, the previous config is recoverable from that backup, not just from git history.

## Determinism and Separation of Concerns

- Acquisition (`node.execute(...)`) and analysis (`node.analyze(...)`) are separate calls in every wrapper — don't merge them into a single opaque step if you're writing a new one; keeping them separate is what lets a script re-analyze a dataset without re-measuring.
- Plotting is separate from the pass/fail decision: compute `accepted`/`failure_reasons` from numeric thresholds first, generate the plot second. The plot should visualize the decision that was already made, not make it.
- Keep threshold parameters (minimum R², contrast, edge margin) as function parameters with sane defaults, not hardcoded constants buried in the analysis — every current wrapper does this; it's what lets a caller tighten or loosen acceptance criteria per qubit without editing code.

## Logging and Parameters

- Always let the actual parameters used for a run flow into the stored result (`params` field, `05_Result_Format.md`) — never silently substitute a different value than what was requested.
- Route anything printed by third-party code through `stdout_to_stderr()` (`04_Writing_Experiment_Scripts.md`) rather than suppressing it — suppressed output is invisible even in the real-time log; redirected output at least ends up in `data/<experiment_id>/output.log`.

## Validate Fits, Don't Trust `fit_success` Alone

A fit library reporting `success=True` (e.g. scipy/lmfit convergence) is a necessary but not sufficient condition for a good result — it converged, not that it converged to something physical. Every wrapper in `03_Experiment_API.md` additionally checks R², edge margin, or contrast on top of `fit_success` before setting `accepted`. When writing a new wrapper, do the same rather than reporting `fit_success` as the whole story — and prefer visual confirmation via `vlm_inspect` (`06_VLM_Guidelines.md`) for the failure modes numeric thresholds can miss (multiple resonances, saturation).

## Respect the Calibration Order

Don't run an experiment against a qubit whose upstream dependencies (`02_Calibration_Workflow.md`) haven't actually been applied (`update_applied: true`), and don't assume a fresh config value propagated just because the previous stage reported `status: "success"`. When a downstream experiment looks anomalous, checking "did the upstream update actually land" is a cheaper first step than assuming the downstream fit itself is broken.

## Config File Hygiene

`hw_config_AS_QRC.json` / `dut_config_AS_QRC.json` (`01_Hardware_Environment.md`) are hand-editable JSON with no schema validation on save. A single malformed number breaks the *entire* file for *every* qubit at hardware-agent construction time, not just the field that's wrong. If you or the user need to hand-edit these, validate with `json.load()` immediately after — don't wait for the next experiment run to discover a typo.
