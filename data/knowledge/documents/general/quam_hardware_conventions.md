---
id: quam_hardware_conventions
title: QuAM Hardware Naming Conventions
category: hardware
tags: [quam, qubit_naming, parameters, machine, active_qubits]
created_at: "2026-03-14"
---

# QuAM Hardware Naming Conventions

## Qubit Naming

QuAM uses **lowercase** qubit identifiers: `q1`, `q2`, `q3`, etc.

- Correct: `q1`, `q2`
- Incorrect: `Q1`, `Q2`, `qubit_1`, `Qubit1`

When the user says "Q1" or "qubit 1", translate to `q1` for the `qubits` parameter.

## The `qubits` Parameter

All experiment scripts accept an optional `qubits` parameter:

- **`qubits = None`** (default): The script uses `machine.active_qubits`, which includes all qubits currently configured in the system. This is the safest default.
- **`qubits = "q1"`**: Targets only qubit q1.
- **`qubits = "q1,q2"`**: Targets multiple specific qubits (comma-separated or list format depending on script).

### Recommendation

- If the user wants to calibrate a specific qubit and you know its QuAM name, pass it (e.g., `"q1"`).
- If unsure about the qubit name, **omit the `qubits` parameter entirely** (do not pass `"None"` as a string — simply exclude it from the parameters JSON). The script will default to `machine.active_qubits`.

## Available Qubits (as of 2026-03-14)

Known qubits in the system: `q1` (confirmed from QuAM state.json).
Additional qubits may exist — check `machine.qubits.keys()` if needed.
