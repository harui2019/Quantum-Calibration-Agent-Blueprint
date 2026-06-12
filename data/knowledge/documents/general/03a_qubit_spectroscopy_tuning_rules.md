---
author: kevin
created_at: '2026-04-21T00:00:00'
id: 03a_qubit_spectroscopy_tuning_rules
updated_at: '2026-04-21T00:00:00'
source: manual_knowledge_injection
tags:
- qubit
- spectroscopy
- tuning
- snr
- fitting
- amplitude
title: Qubit Spectroscopy Tuning Rules
version: 2
---

# Qubit Spectroscopy Tuning Rules

## STEP 0 — INITIALIZATION (MUST DO FIRST):
Before running any experiment, read the experiment Python file to retrieve all default parameter values:
- File path: 'experiments/examples/qubit/03a_Qubit_Spectroscopy.py'
- Identify the current default values of 'operation_amplitude_factor', 'num_averages', 'frequency_span_in_mhz', 'frequency_step_in_mhz', and any other relevant parameters.
- Use these values as the starting point for the first run. Do not assume parameter defaults without reading the file.

**FIRST RUN HARD CONSTRAINTS (non-negotiable):**
- 'operation_amplitude_factor' MUST be set to exactly the value read from the file (default is 0). Do NOT pre-set it to a higher value.
- 'arbitrary_qubit_frequency_in_ghz' MUST be None on the first run. Do NOT pre-set a center frequency — the whole point is to discover where the peak is.
- Do NOT use any prior knowledge about expected qubit frequency to shortcut the search. Start blind.

## VLM ANALYSIS WORKFLOW (REQUIRED AFTER EVERY RUN):
After each call to 'run_qubit_spectroscopy', you MUST trigger a VLM triple comparison by calling
'inspection_agent'. The inspection_agent runs all three VLMs in sequence
(analyze_local_image → analyze_local_image_2 → judge_vlm_comparison) and saves the results to
calibration_log.json and vlm_scores.json automatically.

**HOW TO PASS THE IMAGE PATH (CRITICAL):**
Do NOT try to construct the exact PNG filename from the experiment ID — the filename format is
different and you will get it wrong. Instead, always pass the PNG output DIRECTORY:
  /beegfs/home/kevin0511/nv_agent/cha_agent/data_png

The VLM tool automatically selects the most recently saved PNG file in that directory, which
is always the image from the most recent experiment run.

Steps:
1. After run_qubit_spectroscopy completes, call 'inspection_agent' with this exact message:
   "Please use vlm_triple_comparison to analyze the spectroscopy image at
    /beegfs/home/kevin0511/nv_agent/cha_agent/data_png with this prompt:
    This is a qubit spectroscopy plot. Analyze: (1) Is there a clear resonance peak visible
    in the data? (2) Does the red fit curve actually match the data points, or is it fitting
    noise? (3) Estimate the SNR. (4) What is your verdict: no_peak / weak_signal / peak_found
    / fine_scan / success?"
2. Extract 'final_status' from the inspection_agent JSON response — this is the Gemini judge's
   verdict (based on all three VLMs) and is the authoritative calibration status.

NOTE: The 'vlm_triple_comparison' tool calls VLM-1, VLM-2, and Gemini judge in a single
deterministic call. Do NOT call analyze_local_image separately — use vlm_triple_comparison.

Do NOT call 'update_calibration_log_status' or 'save_vlm_comparison_result' separately — the
inspection_agent handles all log updates automatically.

**IMPORTANT**: The Python fitting algorithm may claim fit_successful=True even on pure noise.
Always use the inspection_agent's 'final_status' to determine the true calibration state.

## MANDATORY LOGGING (REQUIRED FOR EVERY CALL):
Every single call to 'run_qubit_spectroscopy' MUST include both of the following parameters — do not omit them:

- **'agent_reasoning'**: Write a detailed explanation of what you observed from the previous result (or the initial state) and why you chose these specific parameter values. Include what the data showed, what the SNR was, whether a peak was found, and your justification for the changes you made.

- **'agent_decision'**: Write a clear statement of what you plan to do next after this run completes — which parameter you will adjust, in which direction, and why.

- **'agent_status'**: Your visual assessment of this run's outcome. **This overrides the automated Python fit result on the dashboard.** The Python fitting algorithm may find a mathematical peak even in pure noise — you must correct this with your own judgment. Choose exactly one of:
  - 'no_peak' — only noise visible, no recognizable resonance feature
  - 'weak_signal' — a faint structure exists but the fit is unreliable or SNR is too low
  - 'peak_found' — a clear single resonance peak is confirmed by visual inspection and SNR is sufficient
  - 'fine_scan' — you are in the fine scan stage with a confirmed peak centered
  - 'success' — calibration is complete

These three fields are written to the calibration log after each run and displayed on the dashboard. Skipping them means the human observer cannot follow your reasoning. This is not optional.

Example:
- agent_reasoning: "The previous broad scan at amplitude 0.15 showed a faint signal near 5.0 GHz but the fit failed (SNR too low). I am increasing amplitude to 0.3 to strengthen the drive and make the resonance peak visible."
- agent_decision: "If a clear single peak appears and SNR >= 5.0, I will switch to fine scan centered at the detected frequency with span=100 MHz."
- agent_status: "weak_signal"

## FREQUENCY CONSTRAINTS:
- The valid qubit frequency search range is **4.7 GHz to 5.1 GHz** only.
- Do not scan or interpret any peak detected outside this range as a valid qubit transition.
- When setting 'frequency_span_in_mhz' and the center frequency, always verify the full scan window stays within [4.7 GHz, 5.1 GHz].

## PARAMETER TUNING RULES:

### 1. SNR IMPROVEMENT RULE:
If the spectroscopy result has poor or marginal signal-to-noise ratio (SNR), adjust one or both of the following parameters:

**(a) 'operation_amplitude_factor' — SAFETY CRITICAL:**
- You may decide how much to increase 'operation_amplitude_factor' each iteration based on the current signal quality. Use your judgement to determine an appropriate step size.
- **HARD LIMIT: must never exceed 0.6.** Exceeding this value risks damaging the instrument.
- If the data clearly shows **two peaks**, immediately **decrease** 'operation_amplitude_factor' — do not continue increasing.

**(b) 'num_averages':**
- Increasing the number of averages improves SNR and makes the resonance peak easier to identify.
- A typical working value is around **100**. Adjust around this range as needed.
- However, too many averages significantly slows down the experiment. Use conservatively.

### 2. PEAK-FOUND FINE SCAN RULE:
Once a clear **single peak** is identified within the valid frequency range (4.7 GHz – 5.1 GHz):

0. **SNR GATE (must pass before entering fine scan):**
   - Check 'snr_estimate' and 'snr_sufficient_for_fine_scan' in the fit_results returned by run_qubit_spectroscopy.
   - If 'snr_sufficient_for_fine_scan' is False (i.e., snr_estimate < 5.0), do **not** proceed to fine scan.
   - Instead, improve SNR first by increasing 'num_averages' or slightly raising 'operation_amplitude_factor', then re-run the broad scan until snr_sufficient_for_fine_scan becomes True.
   - Only proceed to the steps below when snr_sufficient_for_fine_scan is True.

1. **REQUIRED — you must explicitly pass 'arbitrary_qubit_frequency_in_ghz' as a parameter in the next run_qubit_spectroscopy call.** Set it to the measured peak center frequency in GHz. Do not skip this step or leave it as None.
2. Before setting 'frequency_span_in_mhz', compute the scan boundary as follows (all values must be in GHz):
   - Step 1: compute half_span_ghz = frequency_span_in_mhz / 2 / 1000
     - Example: frequency_span_in_mhz=100 → half_span_ghz = 100 / 2 / 1000 = 0.05 GHz
   - Step 2: upper_edge = arbitrary_qubit_frequency_in_ghz + half_span_ghz
   - Step 3: lower_edge = arbitrary_qubit_frequency_in_ghz - half_span_ghz
   - Step 4: check upper_edge ≤ 5.1 GHz AND lower_edge ≥ 4.7 GHz
   - Example: center=5.04 GHz, span=100 MHz → upper=5.04+0.05=5.09 GHz ✓, lower=5.04-0.05=4.99 GHz ✓
   - Example: center=5.08 GHz, span=100 MHz → upper=5.08+0.05=5.13 GHz ✗ → reduce span until upper ≤ 5.1 GHz
   - If either check fails, reduce 'frequency_span_in_mhz' and repeat from Step 1. Do not shift the center frequency.
3. Set **'frequency_span_in_mhz' = 100** (i.e., ±50 MHz around the center) as the default fine scan span, subject to the boundary check above.
4. Begin the fine scan iteration described in Rule 3 below.

### 3. FINE SCAN AMPLITUDE SWEEP RULE:
During fine scanning (after applying Rule 2):

- Increase 'operation_amplitude_factor' by an amount you judge appropriate based on the current signal quality, starting from the current value.
- Continue until **either** of the following stop conditions is met:
  - 'operation_amplitude_factor' approaches **0.6** (the safety limit), or
  - The data shows a clear **double-peak (split response)**.
- When the double-peak stop condition is triggered, the **optimal 'operation_amplitude_factor'** is the value from the **previous run** (i.e., current value minus 0.05).

## AGENT DECISION GUIDELINES:
When deciding the next spectroscopy parameters, reason in this order:

1. Is the current scan result within the valid frequency range (4.7 GHz – 5.1 GHz)?
2. Is there a clear single resonance feature with acceptable SNR?
3. If no clear peak: should 'num_averages' be increased, or 'operation_amplitude_factor' slightly raised (+0.05)?
4. If a single peak is found: apply Rule 2 (set 'arbitrary_qubit_frequency_in_ghz', narrow span to 100 MHz).
5. During fine scan: apply Rule 3 (increase amplitude by 0.05 per run, watch for double-peak or 0.6 limit).
6. If a double-peak appears: step back to the previous amplitude value as the optimal setting.

## SAFETY REMINDER:
- **Never set 'operation_amplitude_factor' above 0.6** under any circumstances. This is a hard instrument safety limit.
