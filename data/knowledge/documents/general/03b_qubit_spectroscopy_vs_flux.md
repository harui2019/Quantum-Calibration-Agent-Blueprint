---
author: kevin
created_at: '2026-04-09T00:00:00'
id: 03b_qubit_spectroscopy_vs_flux
updated_at: '2026-04-09T00:00:00'
source: manual_knowledge_injection
tags:
- qubit
- spectroscopy
- flux
- sweet_spot
- fitting
- calibration
title: Qubit Spectroscopy vs Flux Interpretation Guide
version: 1
---

# Qubit Spectroscopy vs Flux Interpretation Guide

## Purpose

`qubit spectroscopy vs flux` is used to measure how the qubit transition frequency changes with flux bias.

This experiment is typically used to determine:

- the approximate `flux sweet spot`
- the qubit frequency at the sweet spot
- the local quadratic coefficient `freq_vs_flux_01_quad_term`

This experiment is usually performed after single-point `qubit spectroscopy`.

## Physical Picture

For a transmon or another SQUID-based qubit, the transition frequency depends on magnetic flux.

A common approximation is:

$$
f_{01} \approx \sqrt{8 E_j(\Phi) E_c} - E_c
$$

with

$$
E_j(\Phi) = E_{j,\max}\left|\cos\left(\pi \Phi / \Phi_0\right)\right|
$$

Near the sweet spot, the frequency-flux relation is often locally well approximated by a downward-opening parabola.

## Preconditions

Before running or interpreting this experiment, verify the following:

- single-point `qubit spectroscopy` has already identified an approximate qubit transition
- the drive amplitude is low enough that the main response is dominated by the `|0⟩ -> |1⟩` transition
- the readout is stable enough to resolve the spectroscopy response across the full flux sweep
- the selected flux sweep range is centered near the expected sweet spot

## Drive Amplitude Rule

The drive amplitude should be chosen to make the main qubit transition visible without strongly exciting additional lines.

Preferred behavior:

- one dominant transition line is visible
- the line remains reasonably narrow
- the spectrum is not crowded by many extra resonances

If the drive amplitude is too large, the result may include:

- higher-level transitions
- broadened lines
- parasitic resonances
- unstable or misleading fitting

## Expected Successful Pattern

A successful `qubit spectroscopy vs flux` plot usually shows:

- one dominant resonance branch
- a smooth frequency shift as flux changes
- a locally downward-opening parabolic trend near the sweet spot
- a fitted vertex that visually agrees with the measured heatmap

If fitting is reliable, the calibration can be used to update:

- flux offset
- qubit `intermediate_frequency`
- `freq_vs_flux_01_quad_term`

## Success Criteria

Treat the experiment as successful when all of the following are approximately true:

- a single main qubit branch can be identified
- the branch changes continuously with flux
- the branch can be fit reasonably well by a quadratic model near the operating region
- the fitted vertex is visually consistent with the measured heatmap
- the fit is not dominated by crossings, multiple competing branches, or strong artifacts

## Failure Modes

### Case 1: Frequency does not move with flux

If the resonance appears almost flat over the full flux scan, possible causes include:

- the tracked resonance is not the intended qubit transition
- the selected scan range is too small or misplaced
- the flux tunability is weak in the chosen region
- the SQUID or flux control path may be abnormal

Recommended actions:

- re-check the transition identified in single-point `qubit spectroscopy`
- expand or shift the flux sweep range
- verify that the same transition can produce sensible `Rabi oscillation`

Do not conclude that the SQUID is damaged based on this plot alone.

### Case 2: Multiple branches move with flux

If several lines shift with flux at the same time, possible causes include:

- drive amplitude is too strong
- higher-level transitions are being excited
- neighboring qubits or couplers are contributing extra spectral lines
- nearby bias settings place other modes close to the target qubit frequency

Recommended actions:

- reduce the drive amplitude
- increase averaging if needed after reducing power
- inspect neighboring coupler or qubit bias conditions
- avoid fitting multiple branches with a single parabola

### Case 3: Flux dependence is visible but fitting is unstable

If a branch is visible but the quadratic fit is unreliable, possible causes include:

- the flux range is too narrow to resolve curvature
- the flux range is too wide and includes crossings or nonlocal behavior
- the frequency step is too coarse
- the signal-to-noise ratio is too low

Recommended actions:

- re-center the sweep around the likely sweet spot
- reduce `frequency_step`
- increase averaging
- repeat the scan with a cleaner drive amplitude

## Agent Interpretation Rules

When an agent analyzes a `qubit spectroscopy vs flux` plot, it should answer these questions in order:

1. Is there one dominant resonance branch?
2. Does that branch move continuously with flux?
3. Is the branch approximately parabolic near the operating region?
4. Does the fitted vertex match the visual trend of the heatmap?
5. Are there competing lines or crossings that make the identification ambiguous?

The agent should stay conservative when the evidence is weak.

Preferred cautious language:

- "The main qubit branch is not uniquely identifiable in the current plot."
- "Flux dependence is visible, but the data is not clean enough for a stable quadratic fit."
- "Additional coupled modes or excessive drive power may be producing multiple moving lines."

## Suggested Structured Outputs

If the agent needs to summarize the result in structured form, the following fields are useful:

- `fit_successful`
- `main_transition_identifiable`
- `sweet_spot_visible`
- `estimated_flux_offset`
- `estimated_qubit_frequency`
- `possible_failure_causes`
- `recommended_next_action`

## Calibration Implication

The main goal of this experiment is not merely to detect a signal.

The real goal is to identify a single reliable qubit branch and use its flux dependence to estimate:

- the correct flux offset
- the correct qubit frequency near the sweet spot
- the local curvature of the frequency-flux relation

If the plot shows multiple branches, almost no flux dependence, or a fit inconsistent with the measured heatmap, the calibration should not be accepted without an additional scan or cross-check.
