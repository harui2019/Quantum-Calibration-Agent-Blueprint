---
author: kevin
created_at: '2026-03-13T10:10:00.000000'
id: c3c3c3c3-d4d4-e5e5-f6f6-a7a7a7a7a7a7
updated_at: '2026-03-13T10:10:00.000000'
source: manual_knowledge_injection
category: EXPERIMENTS
tags:
- qubit
- spectroscopy
- fine_amplitude
- phase2
title: SOP Phase 2 Fine Loop
version: 1
---

# SOP Phase 2 Fine Loop

## EXECUTION STEPS
Loop `operation_amplitude_factor` from 0.05 to 0.5 in steps of 0.05.
1. Call `experiment_execution_agent` to run `run_qubit_spectroscopy`.
2. You MUST STRICTLY use the following parameters:
   - `qubits`: The name of the target qubit
   - `arbitrary_qubit_frequency_in_ghz`: null
   - `frequency_span_in_mhz`: 100.0
   - `frequency_step_in_mhz`: 0.4
   - `num_averages`: 1000
   - `timeout`: 600
   - `operation_amplitude_factor`: Current loop value (start at 0.05)

## VLM INSPECTION
Extract the clean image path. Call `vlm_inspection_agent` with prompt: "Visually count the number of distinct resonance dips/peaks. Answer strictly with '1 peak' or '2+ peaks'."
- IF 2+ peaks: STOP the loop. The PREVIOUS amplitude is optimal. Phase 2 SUCCESS.
- IF 1 peak: Continue loop, add 0.05 to amplitude, repeat Phase 2.