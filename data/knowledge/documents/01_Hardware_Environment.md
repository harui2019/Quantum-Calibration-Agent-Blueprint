# Hardware Environment

Reference for the physical setup, wiring, and software stack behind every `qblox_*` experiment. See also `data/knowledge/skills/qblox-hardware-environment/SKILL.md`, which is the operational (config paths / Python env) counterpart to this document — read that one before running anything; read this one to understand *what* the hardware actually is.

**⚠️ Everything sample-specific in this document (chip layout, qubit/coupler count, module map, cluster IP) is a snapshot, not ground truth.** The actual sample gets swapped out periodically (e.g. this repo has moved from a 2x2 sample to the current 7-qubit "7SQ" sample), and every path/value below can change with it. `scripts/_qblox_runtime.py` is the single source of truth — it decides which config files are active (via `HARDWARE_REPO_PATH`/`HARDWARE_CONFIG`/`DEVICE_CONFIG`, all env-var overridable: `QBLOX_HARDWARE_REPO_PATH`, `QBLOX_HARDWARE_CONFIG`, `QBLOX_DEVICE_CONFIG`). If anything here looks inconsistent with a live result, **trust `scripts/_qblox_runtime.py` and the JSON files it points to, not this doc** — and if you confirm this doc is stale, say so rather than silently working around it.

## System Overview

This lab controls an array of flux-tunable transmon qubits, driven by a Qblox Cluster. The control software lives in a separate checked-out project, at whatever path `HARDWARE_REPO_PATH` in `scripts/_qblox_runtime.py` currently resolves to. As of the last inspection:

```
/home/reny871224/flux-tunable-transmons-with-flux-tunable-couplers-share_with_AS_for_training/docs/applications/superconducting/
```

QCA does not talk to hardware directly — every `qblox_*.py` script in `scripts/` imports calibration node classes (`cal00_time_of_flight`, `cal02_resonator_spectroscopy`, etc.) from that project and drives them through a `HardwareAgent`.

## Qblox Cluster

Single cluster, `cluster_A`. As of the last inspection of the live `hw_config_AS_QRC.json` (currently the `configs/7SQ/` sample):

- IP: `192.168.1.242`
- `hardware_description.cluster_A.modules` declares module `6` (`QCM_RF`) and module `8` (`QRM_RF`)
- `connectivity.graph` wires module `8`'s complex I/O to all seven `qN:res` ports (multiplexed readout for `q1`–`q7`), and — inconsistently — wires drive (`qN:mw`) to `module4`, a module number not declared in `hardware_description` at all. This mismatch is in the live config file itself, not a doc error; don't assume either number is authoritative without checking `connect_clusters()` actually succeeds and re-reading the file yourself.

**Don't hardcode a module number anywhere** (e.g. as a default for `qblox_time_of_flight`'s required `module_number` param) based on the table above — read `hardware_description`/`connectivity.graph` from the live `hw_config` JSON every time you need one, since it changes per sample.

Module type reference (this part doesn't change per sample):
- **QCM** — baseband output only, no RF upconversion. Used for DC/flux lines.
- **QCM-RF** — QCM with an integrated RF up-converter (built-in LO). Used for qubit drive.
- **QRM-RF** — QCM-RF plus an acquisition (readout) input path. Used for dispersive readout; can multiplex several qubits on one module.
- **QRM** (baseband readout, no RF) — not currently used in this setup.

There is no separate local-oscillator instrument in this config — the RF modules generate their own LO internally (`lo_freq` per port, set in `hardware_options.modulation_frequencies`).

Cryostat, external attenuators/amplifiers on the input/output lines, and any wiring outside the cluster are physical lab infrastructure QCA has no visibility into or control over — they are not represented in the config files. If an experiment fails in a way that isn't explained by config or fit quality, a cold-chain/wiring issue outside the cluster is a real possibility that no amount of config inspection will reveal (see `08_Common_Failures.md`).

## Chip Layout

**Sample-dependent — do not assume a fixed qubit count, coupler layout, or geometric arrangement.** As of the last inspection, the active `dut_config_AS_QRC.json` (`configs/7SQ/`) has `elements: {q1, ..., q7}` and an **empty `edges` dict** — seven single qubits, no tunable couplers wired at all. This is a different topology from an earlier 2x2 sample this repo used (4 qubits + 4 couplers in a nearest-neighbor ring) — don't reuse that layout, coupler-naming convention (`c12`, `c23`, ...), or any assumption of coupler elements existing; check `dut_config_AS_QRC.json`'s `elements`/`edges` keys directly for the current sample's actual qubits/couplers.

**Port naming** (used throughout hardware config and in `connectivity.graph`): `<element>:<line>`, e.g. `q1:mw` (drive), `q1:fl` (flux), `q1:res` (readout), `c12:fl` (coupler flux, if couplers exist on the current sample). Clock/port-clock strings used in `hardware_options` combine element and mode, e.g. `q1:mw-q1.01` (qubit 1, 0↔1 transition drive), `q1:res-q1.ro` (qubit 1 readout).

All qubits (and couplers, on samples that have them) are instances of `FluxTunableTransmonElement` (from `custom_elements.py` in the superconducting project) — a custom `DeviceElement` subclass, not a stock `quantify-scheduler` element.

**Element status**: don't trust a cached claim about which qubits are calibrated — read `clock_freqs`/`rxy`/`measure` directly from the live `dut_config_AS_QRC.json` (or `qubit.clock_freqs.f01` etc. via `get_qubit()`) for current values; they change as calibration progresses and this doc isn't updated per run.

## Configuration Files

Two JSON files, both under `.../superconducting/dependencies/configs/<sample>/` (currently `7SQ`, previously `2x2` — the active sample is whatever `scripts/_qblox_runtime.py` points to, don't hardcode a directory name), loaded by that file (env-var overridable — see the SKILL.md):

| File | Env var override | Purpose |
|---|---|---|
| `hw_config_AS_QRC.json` | `QBLOX_HARDWARE_CONFIG` | Cluster/module map, port↔element wiring (`connectivity.graph`), per-port attenuation/gain, LO frequencies. This is a `QbloxHardwareCompilationConfig`. |
| `dut_config_AS_QRC.json` | `QBLOX_DEVICE_CONFIG` | Per-qubit/coupler calibrated parameters (`f01`, readout frequency, `amp180`, flux sweet spot, acquisition rotation/threshold, etc.) as a serialized `QuantumDevice`. |

Both are plain JSON — hand-edited by scripts and, occasionally, by humans. Two important gotchas learned from real incidents in this project:

1. **`dut_config_AS_QRC.json` embeds a *snapshot* of the hardware config** inside itself (a `hardware_config` key written by `qblox_scheduler` at compile time). That embedded copy can drift out of sync with the live, independent `hw_config_AS_QRC.json` — the file `_qblox_runtime.py` actually loads is the standalone `hw_config_AS_QRC.json`, not the embedded snapshot. Don't debug against the embedded copy.
2. **Malformed JSON in either file breaks the *entire* file, for *every* qubit**, not just the one field that's wrong. A single stray space in a number (e.g. `3.9 e9` instead of `3.9e9`) makes the whole file fail to parse, so `HardwareAgent(...)` construction fails immediately for every experiment on every qubit — even ones unrelated to the broken field. If an experiment on qubit A fails at the hardware-agent-construction stage, check the config JSON validity globally, not just qubit A's section.

## Software Stack

Installed in a dedicated environment (not the QCA repo's own environment — see the SKILL.md for why). Currently a micromamba environment, activated with `micromamba activate qblox-training`, interpreter at:

```
/home/reny871224/micromamba/envs/qblox-training/bin/python
```

This is the exact path `tools/lab_tool.py` hardcodes as `python_path` for any `qblox_*`-prefixed experiment — that's the actual source of truth for which interpreter is used, not this doc. Package versions below are a snapshot; check `pip list` (or `micromamba list -n qblox-training`) in that environment for current versions rather than trusting these numbers indefinitely.

| Package | Version (verified in `qblox-training` this session) |
|---|---|
| Python | 3.10.20 |
| `qblox-scheduler` | 1.0.0b6 |
| `qblox_instruments` | 1.3.0 |
| `quantify-core` | 0.8.3 |
| `qcodes` | 0.43.0 |
| `numpy` | 1.26.4 |
| `scipy` | 1.15.3 |
| `matplotlib` | 3.10.9 |

Note: this stack uses **`qblox-scheduler`**, not a separate `quantify-scheduler` package — `qblox-scheduler` is the current unified scheduling/compilation/hardware-backend package (`HardwareAgent`, `QbloxHardwareCompilationConfig`, the compilation-pass pipeline, etc. all live there). `quantify-core` remains a separate dependency (dataset/analysis utilities, `MeasurementControl`). Don't go looking for a `quantify_scheduler` import — it won't be there.

On top of this stack, the superconducting project adds two local (non-pip) modules that QCA's wrappers depend on directly:

- **`single_qubit_experiment_helpers.experiment`** — `Experiment` / `SingleQubitExperiment` base classes that the `calNN_*` node classes (`TimeOfFlight`, `MultiplexedResonatorSpectroscopy`, etc.) are built on.
- **`custom_elements`** — defines `FluxTunableTransmonElement`.
- **`analysis`** — helper functions including `set_attenuation` / `set_input_attenuation` for dynamically adjusting per-port attenuation before a run.

QCA's own repo (this one) never reimplements any of this — it only imports and drives it.
