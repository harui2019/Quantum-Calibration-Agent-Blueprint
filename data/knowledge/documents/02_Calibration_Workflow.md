# Calibration Workflow

The full tune-up sequence, as implemented by the calibration node classes (`calNN_*.py`) in the superconducting project and exercised in `multiplexed_tuneup_notebook_AS_2x2.ipynb`. Each stage lists whether QCA has a working wrapper in `scripts/` today (see `03_Experiment_API.md` for the ones that do) or whether it only exists as an underlying node class you'd have to write a new wrapper for (see `04_Writing_Experiment_Scripts.md`).

**Do not invent a different ordering.** Later stages assume earlier ones already wrote a value into `dut_config_AS_QRC.json`; running them out of order against stale/default values will produce results that look like failures but are actually just "upstream parameter was never set."

## Stage Sequence

| # | Node | Purpose | QCA wrapper | Depends on |
|---|---|---|---|---|
| 00 | `cal00_time_of_flight` | Measure readout pulse round-trip delay (`tof`) and NCO propagation delay | `qblox_time_of_flight` | Nothing (first thing run on new hardware) |
| 01/02 | `cal01_resonator_spectroscopy_full_bandwidth` / `cal02_resonator_spectroscopy` | Locate bare/dressed resonator frequency per qubit | `qblox_resonator_spectroscopy` (targeted, `cal02`) | Time of flight |
| 03 | `cal03_resonator_punchout` | Sweep readout power/attenuation to find the high-power (bare) vs low-power (dressed) regime and pick an operating point | `qblox_resonator_punchout_attenuation` / `qblox_resonator_punchout_amplitude` | Resonator spectroscopy |
<!-- | 04 | `cal04_resonator_flux_spectroscopy` / `cal04b_compensated_flux_spectroscopy` | Map resonator frequency vs flux bias to find the sweet spot | — (not wrapped) | Resonator spectroscopy + punchout | -->
| 05 | `cal05_qubit_spectroscopy` (+ `05a` pulsed, `05b` joint res+qubit) | Locate qubit `f01` via CW/pulsed drive spectroscopy | `qblox_qubit_spectroscopy` | Resonator frequency + operating point known |
<!-- | 06 | `cal06_power_rabi` | Calibrate drive amplitude for a π pulse (`amp180`) | — (not wrapped) | Qubit spectroscopy (`f01`) | -->
<!-- | 07 | `cal07_pulsed_flux_qubit_spectroscopy` / `07b` CW variant | Qubit spectroscopy vs flux bias | — (not wrapped) | Qubit spectroscopy | -->
<!-- | 08/09 | `cal08_pi_pulse_error_amplification` / `cal09_pi_half_pulse_error_amplification` | Refine `amp180`/`amp90` via error amplification | — (not wrapped) | Power Rabi | -->
<!-- | 10 | `cal10_ramsey` (+ `11` vs flux) | Measure detuning / `T2*`, correct `f01` | — (not wrapped) | π pulse calibrated | -->
<!-- | 12 | `cal12_drag_pulse_calibration` | Calibrate DRAG `beta` to suppress leakage to `f12` | — (not wrapped) | Ramsey, π pulse | -->
<!-- | 13 | `cal13_dispersive_shift` | Measure the qubit-state-dependent resonator shift (`chi`) | — (not wrapped) | Qubit + resonator both calibrated | -->
<!-- | 14/15 | `cal14_t1` / `cal15_echo` | Measure `T1` / `T2` (echo) | — (not wrapped) | π pulse calibrated | -->
<!-- | 16 | `cal16_ssro` (+ `16b` thermometer, `16c` readout frequency opt, `16d` readout power opt) | Single-shot readout fidelity, readout frequency/power optimization | — (not wrapped) | Dispersive shift known | -->
<!-- | 17 | `cal17_readout_amplitude_calibration` | Final readout amplitude tune | — (not wrapped) | SSRO | -->
<!-- | 18 | `cal18_allxy` | AllXY sequence — verifies single-qubit gate quality | — (not wrapped) | π and π/2 pulses calibrated | -->
<!-- | 19 | `cal19_active_reset` | Calibrate active (measurement-based) reset | — (not wrapped) | SSRO, readout optimized | -->
<!-- | 20 | `cal20_cryoscope` | Characterize flux-pulse distortion | — (not wrapped) | Flux control calibrated | -->
<!-- | 21 | `cal21_defect_spectroscopy` | Look for TLS defects vs flux | — (not wrapped) | Flux spectroscopy | -->
<!-- | 22 | `cal22_coupled_qubits_chevron` | Two-qubit iSWAP/CZ chevron mapping | — (not wrapped) | Both qubits individually calibrated | -->
<!-- | 23 | `cal23_unit_cell_crosstalk` | Flux crosstalk calibration across the unit cell | — (not wrapped) | Flux spectroscopy on all involved elements | -->

Randomized benchmarking (RB) has no dedicated `calNN` node in this project as of the last inspection — if asked to run RB, check whether one has been added since, rather than assuming `03_Experiment_API.md`'s list is exhaustive.

## Dependency Diagram (single qubit, single-qubit gates only)

```
time_of_flight
      │
resonator_spectroscopy ──▶ resonator_punchout ──▶ resonator_flux_spectroscopy
      │                                                    │
      └──────────────────▶ qubit_spectroscopy ◀────────────┘
                                   │
                             power_rabi (amp180)
                                   │
                  ┌────────────────┼─────────────────────┐
              ramsey (f01 fix)  pi/pi-half amp     dispersive_shift
                  │                │                     │
                  └───────┬────────┘                     │
                          │
                          │                               │
                      T1 / echo                     readout opt (power/ frequency)
                          │                               │
                          └───────────┬───────────────────┘
                                 drag_calibration
                                        │
                                  AllXY (verify)
                                       │
                              active_reset (optional)
```

Two-qubit calibration (coupled chevron, CZ optimization) only makes sense after **both** qubits in the pair have independently passed AllXY.

## Practical Notes for the Agent

- **QCA today only automates stages 00, 02/03, 05.** Everything past qubit spectroscopy currently has to be run manually in the notebook, or a new wrapper has to be written (`04_Writing_Experiment_Scripts.md`) before QCA can drive it. Don't tell a user "I ran a Ramsey experiment" unless a `qblox_ramsey`-style wrapper actually exists in `scripts/` — check `list_experiments` first.
- Every wrapped stage writes its result into `dut_config_AS_QRC.json`/`hw_config_AS_QRC.json` only when called with `apply_update=True` **and** the deterministic quality checks in that wrapper pass. A `status: "success"` result with `apply_update` left at its default `False` has **not** changed the device config — say so explicitly rather than assuming the next stage will see the new value.
- If a later stage's results look wrong, the first thing to check is whether the upstream stage's value was actually applied (`update_applied` in its result) before assuming the later stage's own fit is broken.



```