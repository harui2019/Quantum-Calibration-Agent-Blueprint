# 1D Laser Scan Parameter Ranges

This document describes the valid parameter ranges for the 1DLaserScan experiment type.

## Overview

The 1D Laser Scan experiment allows scanning individual MOT (Magneto-Optical Trap) parameters while keeping all others fixed. Each scan type has specific valid ranges that **must be respected** when specifying `scan_start` and `scan_stop` values.

## Critical Rule

**ALWAYS specify `scan_start` and `scan_stop` values within the valid range for your chosen `scan_type`.** Using default values (like -0.5) without checking compatibility will cause validation errors.

## Valid Ranges by Scan Type

| Scan Type | Valid Min | Valid Max | Unit | Description |
|-----------|-----------|-----------|------|-------------|
| `trapping_frequency` | -9.9 | 9.9 | V | Frequency during MOT loading |
| `trapping_amplitude` | -1.0 | 0.0 | V | Amplitude during MOT loading (0=max power, -1=no power) |
| `cooling_frequency` | -9.9 | 9.9 | V | Frequency during PGC cooling |
| `cooling_amplitude` | -1.0 | 0.0 | V | Amplitude during PGC cooling (0=max power, -1=no power) |
| `magnetic_gradient` | 0.0 | 9.0 | V | Main MOT coil gradient |
| `bias_coil_z` | 0.0 | 9.0 | V | Bias coil Z arm value |
| `bias_coil_a` | 0.0 | 9.0 | V | Bias coil A arm value |
| `bias_coil_c` | 0.0 | 9.0 | V | Bias coil C arm value |
| `cooling_duration` | 1.0 | 100.0 | ms | PGC cooling duration |
| `cooling_ramp_duration` | 0.01 | 100.0 | ms | PGC ramp duration |

## Recommended Scan Ranges for Optimization

When performing parameter optimization and you don't have prior knowledge about optimal values, use these recommended ranges:

| Scan Type | Recommended Start | Recommended Stop | Rationale |
|-----------|------------------|------------------|-----------|
| `trapping_frequency` | -0.5 | 2.2 | Typical detuning range for Rb MOT |
| `trapping_amplitude` | -1.0 | 0.0 | Full power range |
| `cooling_frequency` | -0.5 | 5.0 | Typical PGC detuning range |
| `cooling_amplitude` | -1.0 | -0.5 | Typical PGC power range |
| `magnetic_gradient` | 0.0 | 9.0 | Full gradient range |
| `bias_coil_z` | 0.0 | 9.0 | Full bias coil range |
| `bias_coil_a` | 0.0 | 9.0 | Full bias coil range |
| `bias_coil_c` | 0.0 | 9.0 | Full bias coil range |
| `cooling_duration` | 1.0 | 100.0 | Full duration range |
| `cooling_ramp_duration` | 0.01 | 100.0 | Full ramp duration range |

## Common Mistakes to Avoid

### ❌ Wrong: Using default -0.5 for bias coils
```python
# This will FAIL - bias coils must be >= 0.0V
epii_run_experiment(
    experiment_type="1DLaserScan",
    parameters={
        "scan_type": "bias_coil_z",
        "scan_start": -0.5,  # ❌ INVALID - negative value!
        "scan_stop": 2.2
    }
)
```

### ✅ Correct: Using valid range for bias coils
```python
# This will SUCCEED
epii_run_experiment(
    experiment_type="1DLaserScan",
    parameters={
        "scan_type": "bias_coil_z",
        "scan_start": 0.0,   # ✓ VALID
        "scan_stop": 9.0     # ✓ VALID
    }
)
```

### ❌ Wrong: Using -0.5 for durations
```python
# This will FAIL - durations must be positive
epii_run_experiment(
    experiment_type="1DLaserScan",
    parameters={
        "scan_type": "cooling_duration",
        "scan_start": -0.5,  # ❌ INVALID - negative duration!
        "scan_stop": 100.0
    }
)
```

### ✅ Correct: Using valid range for durations
```python
# This will SUCCEED
epii_run_experiment(
    experiment_type="1DLaserScan",
    parameters={
        "scan_type": "cooling_duration",
        "scan_start": 1.0,    # ✓ VALID - minimum 1.0ms
        "scan_stop": 100.0    # ✓ VALID
    }
)
```

## Example: Sequential Parameter Optimization

When optimizing multiple parameters sequentially, always use the appropriate range for each parameter:

```python
# Step 1: Optimize trapping_frequency
experiment_1 = {
    "scan_type": "trapping_frequency",
    "scan_start": -0.5,   # ✓ Valid for frequency
    "scan_stop": 2.2
}

# Step 2: Optimize bias_coil_z (different range!)
experiment_2 = {
    "scan_type": "bias_coil_z",
    "scan_start": 0.0,    # ✓ Must be >= 0.0 for bias coils
    "scan_stop": 9.0
}

# Step 3: Optimize cooling_duration (different range!)
experiment_3 = {
    "scan_type": "cooling_duration",
    "scan_start": 1.0,    # ✓ Must be >= 1.0ms for duration
    "scan_stop": 100.0
}
```

## Parameter Groups by Range Type

To help remember which parameters use which ranges:

### Frequency Parameters (range: -9.9V to 9.9V)
- `trapping_frequency`
- `cooling_frequency`

### Amplitude Parameters (range: -1.0V to 0.0V)
- `trapping_amplitude` (0=max power, -1=no power)
- `cooling_amplitude` (0=max power, -1=no power)

### Magnetic/Coil Parameters (range: 0.0V to 9.0V)
- `magnetic_gradient`
- `bias_coil_z`
- `bias_coil_a`
- `bias_coil_c`

### Duration Parameters (positive values in ms)
- `cooling_duration` (1.0ms to 100.0ms)
- `cooling_ramp_duration` (0.01ms to 100.0ms)

## Error Messages

If you see an error like:
```
ValueError: scan_start (-0.5V) out of range for bias coil scan. Must be between 0.0 and 9.0 V
```

This means you used an invalid `scan_start` value for the chosen `scan_type`. Check the valid ranges table above and adjust your parameters accordingly.

## References

- Physics implementation: `experiments/examples/mot/shared/mot_physics.py`
- Helper functions: `get_scan_type_valid_ranges()`, `get_recommended_scan_ranges()`
