---
author: kevin
created_at: '2026-03-10T07:40:35.564029'
id: 11a22b33-c444-55d6-77e8-99f00a11b22c
updated_at: '2026-03-10T07:40:35.564029'
source: manual_knowledge_injection
tags:
- qubit
- spectroscopy
- safety
- power_limit
- amplitude
- attenuation
title: Qubit Spectroscopy Safety Rules
version: 1
---

# Qubit Spectroscopy Safety Rules

## CRITICAL SAFETY CONSTRAINTS (DO NOT VIOLATE):
When generating or modifying Qubit Spectroscopy scripts (e.g., `03a_Qubit_Spectroscopy.py`), you MUST strictly adhere to the following power limits to prevent hardware damage (such as Mixer burnout) and signal clipping:

1. **`full_scale_power_dBm` LIMIT:** - In the QuAM state or any configuration generation, the `full_scale_power_dBm` parameter **MUST NOT exceed 10**. 
   - This refers to the physical output power of the Local Oscillator (LO) / Microwave Generator.

2. **`amplitude` LIMIT:** - The digital amplitude parameter in the QUA program **MUST NOT exceed 0.6**. 
   - This provides necessary headroom for mixer correction matrices and prevents DAC digital clipping.