#!/usr/bin/env python3
"""
DPD (Demo Probe Driver) - Debug oscilloscope data acquisition

Tests basic oscilloscope reading and FSM state decoding.
Assumes bitstream already loaded in slot 2.
"""

import sys
import time
from pathlib import Path

try:
    from moku.instruments import MultiInstrument, CloudCompile, Oscilloscope
except ImportError:
    print("ERROR: Moku API not available")
    sys.exit(1)


print("Connecting to Moku at 192.168.8.98...")
m = MultiInstrument('192.168.8.98', platform_id=2, force_connect=True)

# Re-deploy instruments with DPD bitstream
bitstream = str(Path(__file__).parent / "DPD-bits.tar")
print(f"Loading bitstream: {bitstream}")
mcc = m.set_instrument(2, CloudCompile, bitstream=bitstream)
osc = m.set_instrument(1, Oscilloscope)

# Reapply routing (DPD outputs):
# - OutputA: Trigger output (to Output1)
# - OutputB: Intensity output (to Output2)
# - OutputC: FSM state debug (to Oscilloscope Ch1)
m.set_connections(connections=[
    {'source': 'Input1', 'destination': 'Slot2InA'},     # External trigger input
    {'source': 'Slot2OutA', 'destination': 'Output1'},   # Trigger output
    {'source': 'Slot2OutB', 'destination': 'Output2'},   # Intensity output
    {'source': 'Slot2OutC', 'destination': 'Slot1InA'},  # FSM debug to oscilloscope
])

print("✓ Connected")

# Check oscilloscope configuration
print("\n" + "=" * 70)
print("OSCILLOSCOPE DIAGNOSTICS")
print("=" * 70)

print("\nAttempting to read data...")
try:
    data = osc.get_data()
    print(f"✓ Data acquired")
    print(f"  Keys: {list(data.keys())}")

    if 'ch1' in data:
        print(f"  Ch1 samples: {len(data['ch1'])}")
        print(f"  Ch1 range: {min(data['ch1']):.3f}V to {max(data['ch1']):.3f}V")
        print(f"  Ch1 midpoint: {data['ch1'][len(data['ch1'])//2]:.3f}V")

        # Show first 10 samples
        print(f"  Ch1 first 10 samples: {[f'{v:.3f}' for v in data['ch1'][:10]]}")
    else:
        print("  ✗ No 'ch1' data!")

    if 'ch2' in data:
        print(f"  Ch2 samples: {len(data['ch2'])}")
        print(f"  Ch2 range: {min(data['ch2']):.3f}V to {max(data['ch2']):.3f}V")
    else:
        print("  Ch2: not present")

    if 'time' in data:
        print(f"  Time samples: {len(data['time'])}")
        print(f"  Time range: {min(data['time'])*1e3:.1f}ms to {max(data['time'])*1e3:.1f}ms")

except Exception as e:
    print(f"✗ Failed to read data: {e}")
    import traceback
    traceback.print_exc()

# Initialize FORGE_READY
print("\n" + "=" * 70)
print("INITIALIZING FORGE_READY")
print("=" * 70)

print("\nSetting CR0[31:29] = 0b111 (forge_ready | user_enable | clk_enable)...")
mcc.set_control(0, 0xE0000000)
time.sleep(0.1)

print("Reading initial state...")
try:
    data = osc.get_data()
    if 'ch1' in data:
        midpoint = data['ch1'][len(data['ch1'])//2]
        print(f"  Ch1 midpoint: {midpoint:.3f}V")

        if abs(midpoint - 0.0) < 0.15:
            print(f"  State: IDLE (correct!)")
        else:
            print(f"  State: UNKNOWN (expected IDLE)")
    else:
        print("  ✗ No ch1 data!")
except Exception as e:
    print(f"✗ Failed: {e}")

# Try arming the probe
print("\n" + "=" * 70)
print("TESTING ARM FUNCTION")
print("=" * 70)

print("\nSetting arm_enable=1 (CR1[0])...")
mcc.set_control(1, 0x00000001)

print("Waiting 0.5s for state change...")
time.sleep(0.5)

print("Reading oscilloscope data...")
try:
    data = osc.get_data()
    if 'ch1' in data:
        midpoint = data['ch1'][len(data['ch1'])//2]
        print(f"  Ch1 midpoint: {midpoint:.3f}V")

        # Decode state
        if abs(midpoint - 0.0) < 0.15:
            print(f"  State: IDLE (expected ARMED!)")
        elif abs(midpoint - 0.5) < 0.15:
            print(f"  State: ARMED (correct!)")
        elif abs(midpoint - 1.0) < 0.15:
            print(f"  State: FIRING (unexpected!)")
        else:
            print(f"  State: UNKNOWN")
    else:
        print("  ✗ No ch1 data!")
except Exception as e:
    print(f"✗ Failed: {e}")

# Clear fault to return to IDLE
print("\n" + "=" * 70)
print("CLEARING FAULT")
print("=" * 70)

print("\nPulsing fault_clear (CR1[3])...")
mcc.set_control(1, 0x00000008)
time.sleep(0.01)
mcc.set_control(1, 0x00000000)

print("\nDisconnecting...")
m.relinquish_ownership()
print("✓ Done")
