# Experiment API

Authoritative reference for every `qblox_*` experiment QCA can currently call through `run_experiment`. **This list is exhaustive as of the last inspection — there is no `measure_CZ`, `measure_RB`, etc.** If you need one of those, it does not exist yet; see `02_Calibration_Workflow.md` for which underlying node class it would wrap and `04_Writing_Experiment_Scripts.md` for how to build the wrapper. Never claim to have run an experiment that isn't in this document — call `lab(action="list_experiments")` if you're unsure the list is still current.

All eight live in `scripts/`, all require the qblox Python environment (`data/knowledge/skills/qblox-hardware-environment/SKILL.md`), and all are subject to the general result contract in `05_Result_Format.md`. Frequencies are in Hz unless the parameter name says otherwise; times are in seconds.

---

## `qblox_resonator_spectroscopy`

**Purpose**: Multiplexed resonator spectroscopy with deterministic fit validation. First experiment to run after time-of-flight; locates each qubit's readout resonator frequency.

**Inputs**

| Param | Type | Default | Notes |
|---|---|---|---|
| `qubits` | `list[str]` | required | e.g. `["q1", "q2"]` |
| `frequency_width_hz` | float | `20e6` | Total sweep span |
| `frequency_npoints` | int | `201` | |
| `repetitions` | int | `200` | |
| `readout_amplitude` | float or `None` | `None` | `None` uses the hardware config default |
| `fit_method` | str | `"complex"` | `"complex"` or another fit mode supported by the node's analysis |
| `minimum_r_squared` | float | `0.90` | Acceptance threshold |
| `minimum_edge_margin_fraction` | float | `0.08` | Reject fits whose peak sits too close to the scan edge |
| `r_squared_window_linewidths` | float | `5.0` | `r_squared` is computed only over points within this many fitted linewidths of the resonance, not the full scan span — off-resonance baseline ripple (e.g. impedance mismatch) doesn't count against fit quality. Falls back to the full span if the window would contain fewer than 5 points (e.g. `qi`/`qc` not finite, or too few sweep points) |
| `apply_update` | bool | `False` | Must be explicitly `True` to write the fitted frequency back to device config |

**Required calibration parameters**: none upstream (this is the first frequency-domain experiment).

**Per-qubit outputs** (`results[qubit]`): `accepted`, `failure_reasons` (list — see `08_Common_Failures.md`), `resonance_frequency_hz`, `qi_or_q_loaded`, `qc`, `fit_success`, `r_squared`, `r_squared_linewidth_hz` (the fitted linewidth used to size the R² window), `r_squared_window_points` (how many sweep points fell inside that window), `edge_margin_fraction`, `recommended_action`, `image_path`, `data.frequency_hz`, `data.s21` (list of `{real, imag}`).

**Plots**: one PNG per qubit — |S21| vs frequency with fit overlay, plus an I/Q scatter panel.

**Side effects when accepted and `apply_update=True`**: writes the readout frequency into the device config.

---

## `qblox_resonator_punchout_attenuation`

**Purpose**: Sweep output attenuation at fixed frequency span to find a readout operating point where the resonator is still in (or near) the dispersive/high-contrast regime, and recommend a conservative attenuation.

**Inputs**

| Param | Type | Default |
|---|---|---|
| `qubits` | `list[str]` | required |
| `frequency_width_hz` | float | `4e6` |
| `frequency_npoints` | int | `101` |
| `attenuation_start_db` | int | `0` |
| `attenuation_stop_db` | int | `30` |
| `attenuation_step_db` | int | `2` |
| `repetitions` | int | `100` |
| `readout_amplitude` | float or `None` | `None` |
| `maximum_normalized_frequency_shift` | float | `0.20` |
| `minimum_normalized_contrast` | float | `0.10` |
| `apply_update` | bool | `False` |

**Required calibration parameters**: resonator frequency (from `qblox_resonator_spectroscopy`) should already be reasonably close, since the scan is centered using the existing device config.

**Per-qubit outputs**: `accepted`, `recommended_attenuation_db`, `recommended_action`, `image_path`, `sweep.attenuation_db`, `sweep.tracked_resonance_hz`, `sweep.normalized_contrast`.

**Plots**: 2D heatmap (attenuation vs frequency, normalized magnitude) with the tracked resonance and recommended attenuation overlaid.

**Multi-qubit caveat**: `post_run` on the underlying node only accepts **one shared attenuation value** for all qubits in the batch. If per-qubit recommendations disagree, `apply_update=True` will not apply anything even if every individual qubit was `accepted` — check `update_reason` in the result.

---

## `qblox_resonator_punchout_amplitude`

**Purpose**: Same idea as the attenuation sweep, but sweeps readout **amplitude** instead (low → high, picks the first point with sufficient contrast and acceptable frequency shift).

**Inputs**

| Param | Type | Default |
|---|---|---|
| `qubits` | `list[str]` | required |
| `frequency_width_hz` | float | `4e6` |
| `frequency_npoints` | int | `101` |
| `amplitude_start` | float | `0.005` |
| `amplitude_stop` | float | `0.20` |
| `amplitude_nsteps` | int | `20` |
| `repetitions` | int | `100` |
| `readout_attenuation_db` | int or `None` | `None` |
| `maximum_normalized_frequency_shift` | float | `0.20` |
| `minimum_normalized_contrast` | float | `0.10` |
| `apply_update` | bool | `False` |

**Per-qubit outputs**: `accepted`, `recommended_readout_amplitude`, `recommended_action`, `image_path`, `sweep.readout_amplitude`, `sweep.tracked_resonance_hz`, `sweep.normalized_contrast`.

**Plots**: same heatmap style as the attenuation variant, y-axis is amplitude instead of dB.

Unlike the attenuation version, this one applies **per-qubit** amplitudes independently (`post_run(readout_amplitudes=selected)`), so there's no shared-value restriction.

---

## `qblox_qubit_spectroscopy`

**Purpose**: Pulsed (sequential saturation-pulse) qubit spectroscopy to locate `f01`. Drive and readout never overlap in time — avoids the AC-Stark contamination a continuous-wave drive can cause. **Single qubit per call** — this is the one wrapper that doesn't take a `qubits` list.

**Inputs**

| Param | Type | Default | Notes |
|---|---|---|---|
| `qubit_name` | str | `"q1"` | Single qubit, not a list |
| `f01_width_mhz` | float, range (1, 1000) | `400.0` | |
| `f01_npoints` | int, range (21, 2001) | `200` | |
| `repetitions` | int, range (1, 10000) | `200` | |
| `saturation_amp` | float, range (0, 1) | `0.005` | Saturation pulse amplitude (V) |
| `saturation_duration_s` | float, range (1e-9, 100e-6) | `20e-6` | Saturation pulse duration (s) |
| `drive_att_db` | int, range (0, 30) | `0` | **Must be even** or the call returns `status: "failed"` before touching hardware |
| `minimum_linewidth_mhz` | float | `0.05` | Fit rejected below this (likely a spurious peak) |
| `maximum_linewidth_mhz` | float | `50.0` | Fit rejected above this (likely a bad/noisy fit) |
| `apply_update` | bool | `False` | If `True` and the fit passes the linewidth acceptance checks, writes the fitted `f01` into the qubit's device config so downstream experiments pick it up automatically |

**Required calibration parameters**: resonator frequency and a working readout operating point (from the punchout experiments) for the target qubit.

**Outputs** (top-level `data`, not `results` — see `05_Result_Format.md`): `fitted_f01` (GHz), `linewidth` (MHz), `fit_success`, `frequency` (array, GHz), `rotated_signal` (array), `s21_real` / `s21_imag` (arrays), `image_path`, `tuid`.

**Plots**: one PNG — rotated signal vs drive frequency, with the Lorentzian fit overlaid and `fitted_f01` marked when the fit succeeds. Unlike the other four wrappers, the plot entry is returned as a top-level `plots` list (single entry) alongside `data`, not nested under a per-qubit `results` dict — there's only one qubit per call.

---

## `qblox_time_of_flight`

**Purpose**: Measure the readout pulse round-trip delay and NCO propagation delay for a given cluster module. Run once per module before any resonator work on qubits behind that module.

**Inputs**

| Param | Type | Default | Notes |
|---|---|---|---|
| `qubits` | `list[str]` | required | Qubits behind the module being characterized |
| `module_number` | int | required, no default | Which cluster module (see `01_Hardware_Environment.md` for the module map) |
| `frequency_detuning_hz` | float | `10e6` | |
| `pulse_duration_s` | float | `2e-6` | |
| `pulse_amplitude` | float | `0.1` | |
| `acquisition_duration_s` | float | `4e-6` | |
| `repetitions` | int | `100` | |
| `acquisition_delay_s` | float | `0.0` | |
| `playback_delay_s` | float | `146e-9` | Reference offset used when fitting the delay — **the human-validated notebook run for this hardware used `267e-9`, not this default**; if results disagree with a manual run, this is the first parameter to check |
| `apply_update` | bool | `False` | |

Before executing, this wrapper resets input attenuation to 0 dB for the requested qubits (`set_input_attenuation`) so the measured trace amplitude is comparable run to run.

**Per-qubit outputs**: `accepted`, `tof_s`, `nco_propagation_delay_s`, `message`, `image_path`, `trace.time_ns`, `trace.magnitude_v`, `recommended_action`.

**Plots**: one PNG per qubit — magnitude vs acquisition time, with the fitted delay marked.

---

## `qblox_power_rabi`

**Purpose**: Sweep drive amplitude and fit a Power Rabi oscillation to find each qubit's pi-pulse amplitude (`amp180`). Wraps `cal06_power_rabi.MultiplexedPowerRabi`.

**Inputs**

| Param | Type | Default | Notes |
|---|---|---|---|
| `qubits` | `list[str]` | required | e.g. `["q1", "q2"]` |
| `amp_start` | float | `0.0` | Sweep start amplitude (arb. units, same scale as `rxy.amp180`) |
| `amp_stop` | float | `1.0` | Sweep stop amplitude |
| `amp_npoints` | int | `41` | |
| `repetitions` | int | `100` | |
| `drive_att_db` | int or `None` | `None` | Applied to every requested qubit's drive line before the sweep |
| `drive_duration_s` | float or `None` | `None` | X-pulse duration override applied to every requested qubit |
| `minimum_amp180` | float | `1e-4` | Reject the fit if the extracted `amp180` is below this floor |
| `apply_update` | bool | `False` | Must be explicitly `True` to write the fitted `amp180` back to device config |

**Required calibration parameters**: qubit frequency (`f01`) from `qblox_qubit_spectroscopy` and a working readout operating point.

**Per-qubit outputs**: `accepted`, `failure_reasons`, `fitted_amp180`, `fit_success`, `image_path`, `recommended_action`, `sweep.amplitude`, `sweep.rotated_signal`.

**Plots**: one PNG per qubit — rotated signal vs drive amplitude with the cosine fit and fitted `amp180` overlaid.

---

## `qblox_ramsey`

**Purpose**: Interleaved `+`/`-` detuning Ramsey experiment; fits `T2*` and the qubit `f01` frequency error per qubit. Interleaving both detuning signs every shot (rather than two separate sweeps) resolves the sign of a real frequency error and cancels slow drift. Wraps `cal10_ramsey.MultiplexedRamsey`.

**Inputs**

| Param | Type | Default | Notes |
|---|---|---|---|
| `qubits` | `list[str]` | required | e.g. `["q1", "q2"]` |
| `tau_start_s` | float | `0.0` | Free-evolution delay sweep start |
| `tau_stop_s` | float | `20e-6` | Free-evolution delay sweep stop |
| `tau_step_s` | float | `200e-9` | Free-evolution delay step |
| `frequency_detuning_hz` | float | `1e6` | Artificial detuning applied symmetrically around `f01` |
| `repetitions` | int | `100` | |
| `minimum_t2_star_s` | float | `1e-7` | Reject the fit if `T2*` falls below this floor |
| `maximum_t2_star_s` | float | `1e-3` | Reject the fit if `T2*` exceeds this ceiling |
| `apply_update` | bool | `False` | Must be explicitly `True` to correct `f01` in device config by the fitted frequency error |

**Required calibration parameters**: qubit frequency (`f01`) from `qblox_qubit_spectroscopy`.

**Per-qubit outputs**: `accepted`, `failure_reasons`, `frequency_error_hz`, `t2_star_s`, `image_path`, `recommended_action`, `sweep.tau_s`, `sweep.rotated_signal_plus_detuning`, `sweep.rotated_signal_minus_detuning`.

**Plots**: one PNG per qubit — rotated signal vs delay for both detuning branches, each with its damped-oscillator fit overlaid.

---

## `qblox_t1`

**Purpose**: Measure qubit energy-relaxation time (`T1`) via a delayed-readout exponential decay sweep. Wraps `cal14_t1.MultiplexedT1`.

**Does not support `apply_update`** — the underlying node's `post_run()` is a no-op (`T1` is a reported diagnostic, not a parameter fed back into device config). Its result therefore has no `update_applied`/`config_saved` keys, unlike every other wrapper above.

**Inputs**

| Param | Type | Default | Notes |
|---|---|---|---|
| `qubits` | `list[str]` | required | e.g. `["q1", "q2"]` |
| `tau_start_s` | float | `0.0` | Post-pi-pulse delay sweep start |
| `tau_stop_s` | float | `100e-6` | Post-pi-pulse delay sweep stop |
| `tau_step_s` | float | `2e-6` | Post-pi-pulse delay step |
| `repetitions` | int | `100` | |
| `drive_att_db` | int or `None` | `None` | Applied to every requested qubit's drive line before the sweep |
| `minimum_t1_s` | float | `1e-7` | Reject the fit if `T1` falls below this floor |
| `maximum_t1_s` | float | `1e-3` | Reject the fit if `T1` exceeds this ceiling |

**Required calibration parameters**: pi pulse calibrated (`amp180` from `qblox_power_rabi`).

**Per-qubit outputs**: `accepted`, `failure_reasons`, `t1_s`, `fit_success`, `image_path`, `recommended_action`, `sweep.tau_s`, `sweep.rotated_signal`.

**Plots**: one PNG per qubit — rotated signal vs delay with the exponential-decay fit overlaid.

---

## Quick Reference

| Experiment | Scope | `apply_update` supported | Plots |
|---|---|---|---|
| `qblox_resonator_spectroscopy` | multi-qubit | yes | yes |
| `qblox_resonator_punchout_attenuation` | multi-qubit (shared value) | yes | yes |
| `qblox_resonator_punchout_amplitude` | multi-qubit (per-qubit values) | yes | yes |
| `qblox_qubit_spectroscopy` | single qubit | yes | yes (1) |
| `qblox_time_of_flight` | multi-qubit (one module) | yes | yes |
| `qblox_power_rabi` | multi-qubit | yes | yes |
| `qblox_ramsey` | multi-qubit | yes | yes |
| `qblox_t1` | multi-qubit | no (`post_run()` is a no-op) | yes |
