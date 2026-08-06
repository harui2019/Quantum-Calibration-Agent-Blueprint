# Qblox wrappers for NVIDIA Ising / Quantum Calibration Agent

Place these files in the Blueprint's `scripts/` directory.

## 1. Install your experiment project in the Qblox environment

```bash
conda activate qblox-env
cd /path/to/your/qblox/project
pip install -e .
```

## 2. Configure the runtime factory

Create a real runtime module from `example_qblox_runtime.py`, then:

```bash
export QBLOX_RUNTIME_FACTORY="your_package.qblox_runtime:create_runtime"
export QBLOX_ISING_ARTIFACT_DIR="/absolute/path/to/qca-artifacts"
```

The factory returns `(hw_agent, get_qubit)`.

## 3. Module-name overrides

The wrappers assume these importable modules:

- `cal00_time_of_flight`
- `cal02_resonator_spectroscopy`
- `cal03_resonator_punchout`
- `cal05a_qubit_spectroscopy_pulsed`
- `cal06_power_rabi`
- `cal10_ramsey`
- `cal14_t1`

Override them when needed:

```bash
export QBLOX_NODE_MODULE_TIMEOFFLIGHT="your_package.cal00_time_of_flight"
export QBLOX_NODE_MODULE_MULTIPLEXEDRESONATORSPECTROSCOPY="your_package.cal02_resonator_spectroscopy"
export QBLOX_NODE_MODULE_MULTIPLEXEDRESONATORPUNCHOUT="your_package.cal03_resonator_punchout"
export QBLOX_NODE_MODULE_MULTIPLEXEDRESONATORPUNCHOUTAMP="your_package.cal03_resonator_punchout"
export QBLOX_NODE_MODULE_MULTIPLEXEDPOWERRABI="your_package.cal06_power_rabi"
export QBLOX_NODE_MODULE_MULTIPLEXEDRAMSEY="your_package.cal10_ramsey"
export QBLOX_NODE_MODULE_MULTIPLEXEDT1="your_package.cal14_t1"
```

## 4. QCA-discovered experiment names

- `qblox_time_of_flight`
- `qblox_resonator_spectroscopy`
- `qblox_resonator_punchout_attenuation`
- `qblox_resonator_punchout_amplitude`
- `qblox_qubit_spectroscopy`
- `qblox_power_rabi`
- `qblox_ramsey`
- `qblox_t1`

Every public wrapper has typed parameters and returns a JSON-compatible `dict`. `qblox_t1` is the one exception to the `apply_update` convention below — its underlying node has no meaningful `post_run()`, so it never writes to device config.

## 5. Safety behavior

`apply_update=False` by default. A parameter is written only when deterministic
quality checks pass and the caller explicitly sets `apply_update=True`.

The wrappers save PNG plots and return their absolute paths so a vision-language
model can inspect them while numerical rules independently validate the result.

## Important

The punchout selection logic is intentionally conservative and generic. Validate
its thresholds against your chip before allowing unattended updates.
