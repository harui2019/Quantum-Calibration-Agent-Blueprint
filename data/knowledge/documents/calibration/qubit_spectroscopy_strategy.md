---
id: qubit_spectroscopy_strategy
title: Qubit Spectroscopy Calibration Strategy
category: calibration
tags: [qubit_spectroscopy, transition_frequency, driving_pulse, amplitude, calibration_strategy]
created_at: "2026-03-13"
---

# Qubit Spectroscopy Calibration Strategy

## Purpose

The goal of qubit spectroscopy is to find the correct qubit transition frequency. The method uses a long driving pulse (on the order of tens of µs) to attempt excitation of the qubit into a mixed state at various frequencies. Because the readout signal differs between the mixed state and the ground state, the correct transition frequency can be identified.

## Initial Setup (New Chip)

On a brand-new chip, you must first ensure that the driving pulse amplitude is sufficient. Otherwise, even at the correct frequency, the qubit will not be excited.

**Recommended initial parameters:**
- `operation_amplitude_factor`: use the default value defined in the experiment Python file (do not assume a fixed value)
- `full_scale_power_dBm`: 10 (dBm)

Use a deliberately high-power driving pulse. When the frequency is near the correct transition, you should observe a response, which may include:
- A broadened signal (wider linewidth)
- Multiple signal responses

## Multi-Peak Analysis

If multiple frequency responses are observed:

1. **Identify the two highest-frequency signals** and check whether their frequency separation is approximately the design value of ~110 MHz.
2. **Progressively reduce the driving power** and verify that the frequency response still visible at the lowest driving power corresponds to the highest-frequency signal.
3. The frequency that remains visible at the lowest power is the true transition frequency.

## Frequency Verification

Once the frequency is determined, choose a verification method based on the qubit type:

### Flux Tunable Qubit
- Use **qubit spectroscopy vs flux** (sweep frequency while varying the magnetic field).
- Verification: the frequency should shift with the magnetic field.

### Non-Flux Tunable Qubit
- Use **Rabi oscillation** to verify.
- Verification: Rabi oscillations should be observable at the identified frequency.

## Visual Verification (REQUIRED at every step)

Every step in the above procedure requires visual inspection of the spectrum plot:

- **Coarse sweep (high amplitude)**: visually confirm whether a response is present and whether it is a single peak or multi-peak.
- **Multi-peak assessment**: visually confirm that the two highest-frequency peaks are separated by ~110 MHz.
- **After reducing amplitude**: visually confirm that peaks converge to a single frequency and that the fit (red dashed line) matches the data (blue).
- **Flux tunable verification**: inspect the spectroscopy-vs-flux heatmap to confirm the frequency varies with the magnetic field.

If the fit curve is noticeably broader than the data or shifted away from it, the amplitude is likely still too high and should be reduced further.

## Troubleshooting

If none of the above verification methods can confirm the correct transition frequency:
- Try a different frequency range and re-run qubit spectroscopy.
