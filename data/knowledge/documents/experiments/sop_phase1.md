---
author: kevin
created_at: '2026-03-13T10:10:00.000000'
id: b2b2b2b2-c3c3-d4d4-e5e5-f6f6f6f6f6f6
updated_at: '2026-03-13T10:10:00.000000'
source: manual_knowledge_injection
category: EXPERIMENTS
tags:
- qubit
- spectroscopy
- coarse_sweep
- phase1
title: SOP Phase 1 Coarse Sweep
version: 1
---

# SOP Phase 1 Coarse Sweep

## EXECUTION STEPS
1. Call `experiment_execution_agent` to run `run_qubit_spectroscopy`.
2. You MUST STRICTLY use the following parameters (Do NOT use schema defaults):
   - `qubits`: The name of the target qubit (e.g., "q1")
   - `arbitrary_qubit_frequency_in_ghz`: null
   - `frequency_span_in_mhz`: 790.0
   - `frequency_step_in_mhz`: 2.0
   - `num_averages`: 1000
   - `timeout`: 600
   - `operation_amplitude_factor`: 0.15

## VLM INSPECTION
After execution, extract the clean absolute image path from the success message.
Call `vlm_inspection_agent` with the image path and prompt: "Visually count the number of distinct resonance dips/peaks. Answer strictly with '0 peaks', '1 peak', or '2+ peaks'."
- IF 1 peak: SUCCESS. Proceed to Phase 2.
- IF 0 peaks: Increase amplitude by 0.05 and repeat Phase 1.
- IF 2+ peaks: Decrease amplitude by 0.05 and repeat Phase 1.