---
author: kevin
created_at: '2026-04-09T00:00:00'
id: 04_power_rabi
updated_at: '2026-04-09T00:00:00'
source: manual_knowledge_injection
tags:
- qubit
- rabi
- amplitude
- pi_pulse
- calibration
- error_amplification
title: Power Rabi Calibration Guide
version: 1
---

# Power Rabi Calibration Guide

## Purpose

`power rabi` is used to calibrate the drive pulse amplitude for a qubit operation.

In this project, the corresponding calibration script is:

- `04_Power_Rabi.py`

The main goal is to determine a reliable `pi pulse amplitude` for the selected operation, usually `x180`.

## Physical Picture

In a standard power Rabi experiment, the pulse duration is fixed and the drive amplitude is swept.

The measured response should oscillate approximately sinusoidally as a function of amplitude:

$$
f(A) = B \cos(\omega A + \phi) + C
$$

where `A` is the applied pulse amplitude.

If the qubit starts in the ground state, the first amplitude that drives the qubit to the excited state corresponds to the `pi pulse amplitude`.

## Two Analysis Modes In `04_Power_Rabi.py`

The script supports two closely related modes:

### Mode 1: Single-pulse power Rabi

If `max_number_rabi_pulses_per_sweep = 1`, the script fits a sinusoidal oscillation versus amplitude.

This mode is used to directly estimate the pulse amplitude from the fitted oscillation.

### Mode 2: Error-amplified power Rabi

If `max_number_rabi_pulses_per_sweep > 1`, the script repeats the pulse many times.

This amplifies amplitude calibration errors and makes the optimal amplitude easier to identify.

In this mode, the best amplitude is selected from the response map instead of a single sinusoidal fit.

## Preconditions

Before running or interpreting power Rabi, verify the following:

- resonator spectroscopy has already identified the readout resonance
- qubit spectroscopy has already identified the target qubit transition
- the pulse duration for the selected operation is already chosen
- the flux bias is already set to the intended operating point
- readout is stable enough to resolve state oscillations or I/Q response changes

## Expected Successful Pattern

A successful single-pulse power Rabi experiment usually shows:

- a clear oscillation versus amplitude
- at least one visible rise and fall
- a reasonably smooth sinusoidal trend
- a fitted curve that visually follows the measured data

A successful error-amplified power Rabi experiment usually shows:

- a clear amplitude-dependent contrast across repeated pulse counts
- a stable optimal amplitude that stands out in the 2D map
- a selected amplitude that is consistent with the expected pulse family

## How To Identify The Pi Pulse

When sweeping amplitude from zero upward, the qubit should begin near the ground-state response at zero drive.

For a clean oscillation:

- the first extremum corresponding to the excited-state response identifies the `pi pulse amplitude`
- the next return toward the ground-state response corresponds to a `2pi pulse`

The exact first extremum can appear as either the first maximum or the first minimum depending on the readout convention and oscillation phase.

Do not assume that the first peak is always the correct answer without checking the initial baseline and the fitted phase.

## Internal Update Rule In `04_Power_Rabi.py`

After a successful calibration, the script updates:

- `q.xy.operations[operation].amplitude`

If the calibrated operation is `x180` and `update_x90 = True`, the script also updates:

- `q.xy.operations["x90"].amplitude = q.xy.operations["x180"].amplitude / 2`

This means the experiment is not only diagnostic; it directly changes the pulse amplitude stored in the QuAM state.

## Validation Rule

After finding a `pi pulse amplitude`, a useful consistency check is:

- double the pulse duration
- repeat the power Rabi scan
- verify that the required `pi pulse amplitude` becomes approximately half of the original value

This is not a strict mathematical requirement in every nonideal system, but it is a strong sanity check for pulse calibration consistency.

## Failure Modes

### Case 1: No clear oscillation

If the data does not show a clean oscillatory pattern, possible causes include:

- insufficient averaging
- poor signal-to-noise ratio
- wrong qubit transition frequency
- unstable reset or readout

Recommended actions:

- increase averaging
- verify the qubit spectroscopy frequency first
- confirm readout stability

### Case 2: Oscillation exists but is noisy or irregular

If oscillations are visible but the period is not stable or the curve is distorted, possible causes include:

- reset time is too short
- pulse duration is not appropriate
- the selected transition is not the intended one
- pulse distortion or hardware instability is affecting the response

Recommended actions:

- increase qubit reset time or thermalization time
- try a longer pulse duration
- re-check the target transition frequency

### Case 3: Fitted amplitude is too large

If the fitted `pi pulse amplitude` exceeds the allowed instrument limit, the result should not be trusted as a normal successful calibration.

Recommended actions:

- verify the target transition frequency
- re-check mixer and drive calibration
- reduce the scan range and re-run with cleaner settings

## Agent Interpretation Rules

When an agent analyzes a power Rabi result, it should answer these questions in order:

1. Is there a clear oscillatory response or a clear optimal-amplitude region?
2. Is the response smooth enough to support calibration?
3. Is the extracted `pi pulse amplitude` physically reasonable?
4. Does the result remain within instrument amplitude limits?
5. Should the amplitude update be accepted, or should the experiment be repeated with adjusted settings?

## Suggested Structured Outputs

If the agent needs to summarize the result in structured form, the following fields are useful:

- `fit_successful`
- `oscillation_visible`
- `pi_pulse_identifiable`
- `recommended_pi_amplitude`
- `amplitude_within_limits`
- `possible_failure_causes`
- `recommended_next_action`

## Calibration Implication

The main goal of power Rabi is to determine a reliable amplitude for the selected qubit pulse.

If the oscillation is clear and the extracted amplitude is stable and within limits, the calibration can be accepted.

If the data is noisy, irregular, or inconsistent with the expected Rabi pattern, the amplitude update should not be accepted without another scan or a frequency cross-check.
