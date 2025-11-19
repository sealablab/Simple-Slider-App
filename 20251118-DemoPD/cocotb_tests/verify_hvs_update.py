#!/usr/bin/env python3
"""
HVS Encoding Verification Script

Verifies that the HVS constants match the updated encoding scheme.
Run this after updating DIGITAL_UNITS_PER_STATE to ensure consistency.

Author: Moku Instrument Forge Team
Date: 2025-01-18
"""

from dpd_wrapper_tests.dpd_wrapper_constants import (
    HVS_DIGITAL_UNITS_PER_STATE,
    HVS_DIGITAL_IDLE,
    HVS_DIGITAL_ARMED,
    HVS_DIGITAL_FIRING,
    HVS_DIGITAL_COOLDOWN,
    HVS_DIGITAL_TOLERANCE,
    DIGITAL_MAX,
    V_MAX_MV,
)


def digital_to_voltage_v(digital_units):
    """Convert digital units to voltage in volts"""
    return (digital_units / DIGITAL_MAX) * (V_MAX_MV / 1000.0)


def main():
    print("=" * 70)
    print("HVS Encoding Verification (Updated 2025-01-18)")
    print("=" * 70)
    print()
    print(f"Configuration:")
    print(f"  DIGITAL_UNITS_PER_STATE = {HVS_DIGITAL_UNITS_PER_STATE}")
    print(f"  HVS_DIGITAL_TOLERANCE   = ±{HVS_DIGITAL_TOLERANCE} digital units")
    print(f"  Full Scale Range        = ±{V_MAX_MV}mV (±{V_MAX_MV/1000.0}V)")
    print(f"  Digital Range           = ±{DIGITAL_MAX}")
    print()

    print("State Encoding Table:")
    print("-" * 70)
    print(f"{'State':<15} {'Digital Units':<20} {'Voltage (V)':<15} {'Voltage (mV)':<15}")
    print("-" * 70)

    states = [
        ("IDLE", HVS_DIGITAL_IDLE),
        ("ARMED", HVS_DIGITAL_ARMED),
        ("FIRING", HVS_DIGITAL_FIRING),
        ("COOLDOWN", HVS_DIGITAL_COOLDOWN),
    ]

    for state_name, digital_val in states:
        voltage_v = digital_to_voltage_v(digital_val)
        voltage_mv = voltage_v * 1000
        print(f"{state_name:<15} {digital_val:<20} {voltage_v:<15.3f} {voltage_mv:<15.1f}")

    print("-" * 70)
    print()

    # Calculate voltage step between states
    step_digital = HVS_DIGITAL_UNITS_PER_STATE
    step_voltage_v = digital_to_voltage_v(step_digital)
    step_voltage_mv = step_voltage_v * 1000

    print("Voltage Steps:")
    print(f"  Per-State Step   = {step_digital} digital units")
    print(f"                   = {step_voltage_v:.3f}V = {step_voltage_mv:.1f}mV")
    print()

    # Calculate tolerance in voltage
    tolerance_v = digital_to_voltage_v(HVS_DIGITAL_TOLERANCE)
    tolerance_mv = tolerance_v * 1000

    print("Tolerance Range:")
    print(f"  Tolerance        = ±{HVS_DIGITAL_TOLERANCE} digital units")
    print(f"                   = ±{tolerance_v:.3f}V = ±{tolerance_mv:.1f}mV")
    print()

    # Verify expectations
    print("Verification Checks:")
    print("-" * 70)

    checks = []

    # Check 1: IDLE should be 0
    check1 = HVS_DIGITAL_IDLE == 0
    checks.append(("IDLE state = 0", check1))

    # Check 2: State steps should be consistent
    check2 = (HVS_DIGITAL_ARMED - HVS_DIGITAL_IDLE) == HVS_DIGITAL_UNITS_PER_STATE
    checks.append(("ARMED - IDLE = UNITS_PER_STATE", check2))

    check3 = (HVS_DIGITAL_FIRING - HVS_DIGITAL_ARMED) == HVS_DIGITAL_UNITS_PER_STATE
    checks.append(("FIRING - ARMED = UNITS_PER_STATE", check3))

    check4 = (HVS_DIGITAL_COOLDOWN - HVS_DIGITAL_FIRING) == HVS_DIGITAL_UNITS_PER_STATE
    checks.append(("COOLDOWN - FIRING = UNITS_PER_STATE", check4))

    # Check 5: Step size should be ~0.5V (target from spec)
    target_step_v = 0.5
    step_error = abs(step_voltage_v - target_step_v)
    check5 = step_error < 0.001  # Within 1mV
    checks.append((f"Step size ≈ {target_step_v}V (error={step_error*1000:.1f}mV)", check5))

    # Check 6: Tolerance should be large enough for status offset (±100 digital units max)
    check6 = HVS_DIGITAL_TOLERANCE >= 100
    checks.append(("Tolerance ≥ 100 (status offset range)", check6))

    all_passed = True
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {check_name}")
        if not passed:
            all_passed = False

    print("-" * 70)
    print()

    if all_passed:
        print("✅ All verification checks PASSED!")
        print("   CocoTB tests are ready to run with updated HVS encoding.")
        return 0
    else:
        print("❌ Some verification checks FAILED!")
        print("   Please review dpd_wrapper_constants.py")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
