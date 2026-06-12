---
author: kevin
created_at: '2026-03-13T10:10:00.000000'
id: a1a1a1a1-b2b2-c3c3-d4d4-e5e5e5e5e5e5
updated_at: '2026-03-13T10:10:00.000000'
source: manual_knowledge_injection
category: EXPERIMENTS
tags:
- qubit
- calibration
- autonomous
- main_workflow
title: Qubit Calibration Main Workflow
version: 1
---

# Qubit Calibration Main Workflow

## CRITICAL EXECUTION OVERRIDE
When asked to calibrate qubits, treat this as a STRICT MULTI-STEP TASK.
1. Process qubits one by one (e.g., q1, then q2).
2. For EACH qubit, you MUST execute two phases in order.
3. **Phase 1**: Call `knowledge_management_agent` to search for exactly "SOP Phase 1 Coarse Sweep". Read the parameters and execute it.
4. **Phase 2**: If Phase 1 succeeds (VLM reports 1 peak), call `knowledge_management_agent` to search for exactly "SOP Phase 2 Fine Loop". Read the parameters and execute it.

## ANTI-AMNESIA RULE
After any successful experiment execution, explicitly print: "Current execution successful. Checking the Per-Qubit Workflow tracker. Proceeding to the next step."