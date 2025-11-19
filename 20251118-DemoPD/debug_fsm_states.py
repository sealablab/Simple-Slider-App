#!/usr/bin/env python3
"""
DPD (Demo Probe Driver) FSM State Machine Debugger

Connects to an EXISTING Moku setup (does NOT push new config).
Assumption: User has manually loaded:
  - Slot 1: Oscilloscope
  - Slot 2: CloudCompile (DPD bitstream)
  - Routing: Slot2 OutputC → Slot1 InA (FSM debug signal on OutputC)

Usage:
    uv run python debug_fsm_states.py

Controls:
    - Reads FSM state from Oscilloscope Ch1 (monitoring OutputC)
    - Twiddles Control Registers to step through state machine
    - Displays real-time state transitions

Control Register Map (DPD - Demo Probe Driver):
    CR0[31:29] = FORGE_READY (forge_ready, user_enable, clk_enable)
    CR1[0]     = arm_enable (enable arming)
    CR1[1]     = sw_trigger (software trigger, edge-detected)
    CR1[2]     = auto_rearm_enable
    CR1[3]     = fault_clear (edge-detected)
    CR2[31:16] = input_trigger_voltage_threshold (mV, signed)
    CR2[15:0]  = trig_out_voltage (mV, signed)
    CR3[15:0]  = intensity_voltage (mV, signed)
    CR4[31:0]  = trig_out_duration (clock cycles)
    CR5[31:0]  = intensity_duration (clock cycles)
    CR6[31:0]  = trigger_wait_timeout (clock cycles)
    CR7[31:0]  = cooldown_interval (clock cycles)
    CR8[0]     = monitor_enable
    CR8[1]     = monitor_expect_negative
    CR8[31:16] = monitor_threshold_voltage (mV, signed)
    CR9[31:0]  = monitor_window_start (clock cycles)
    CR10[31:0] = monitor_window_duration (clock cycles)
"""

import time
import sys
from typing import Optional, Tuple

try:
    from moku.instruments import MultiInstrument
except ImportError:
    print("ERROR: moku package not found. Run: uv sync")
    sys.exit(1)


# FSM State Decoding (from OutputC via oscilloscope)
# Based on HVS (Half-Volt Spaced) encoding: signed 16-bit values
# Voltage = (state_value * 5V) / 32768
# For better discrimination, using ~0.5V steps
STATE_MAP = {
    "IDLE":      0.0,    # 0x0000 → 0.00V
    "ARMED":     0.5,    # State 1 → ~0.5V
    "FIRING":    1.0,    # State 2 → ~1.0V
    "COOLING":   1.5,    # State 3 → ~1.5V
    "DONE":      2.0,    # State 4 → ~2.0V
    "FAULT":     -2.5,   # Negative voltage = fault condition
}

# Reverse lookup with tolerance
def decode_fsm_state(voltage: float, tolerance: float = 0.15) -> Optional[str]:
    """Decode FSM state from oscilloscope voltage reading."""
    for state, expected_v in STATE_MAP.items():
        if abs(voltage - expected_v) < tolerance:
            return state
    return f"UNKNOWN({voltage:.2f}V)"


class DPDDebugger:
    """Debug DPD (Demo Probe Driver) FSM state machine via existing Moku setup."""

    def __init__(self, ip: str = "192.168.8.98", platform_id: int = 2):
        """
        Connect to existing MultiInstrument setup.
        Gets handles to already-deployed instruments (bitstream already loaded by user).
        """
        print(f"🔌 Connecting to Moku at {ip}...")
        self.m = MultiInstrument(ip, platform_id=platform_id, force_connect=True)

        # Import instrument classes
        from moku.instruments import Oscilloscope, CloudCompile

        print("📡 Getting instrument handles (no bitstream upload)...")

        # Get handles to existing instruments
        # Note: set_instrument() without bitstream parameter should connect to existing
        self.osc = self.m.set_instrument(1, Oscilloscope)
        self.mcc = self.m.set_instrument(2, CloudCompile)

        print("✅ Connected to existing setup")
        print(f"   Slot 1: Oscilloscope")
        print(f"   Slot 2: CloudCompile (DPD)")

    def read_fsm_state(self, poll_count: int = 5) -> Tuple[str, float]:
        """
        Read current FSM state from oscilloscope Ch1.

        Args:
            poll_count: Number of samples to average (handle latency)

        Returns:
            (state_name, voltage) tuple
        """
        voltages = []
        for _ in range(poll_count):
            data = self.osc.get_data()
            # Sample middle of waveform buffer
            midpoint = len(data['ch1']) // 2
            voltages.append(data['ch1'][midpoint])
            time.sleep(0.05)  # 50ms between samples

        avg_voltage = sum(voltages) / len(voltages)
        state = decode_fsm_state(avg_voltage)
        return state, avg_voltage

    def set_control(self, reg: int, value: int, description: str = ""):
        """Set control register and display action."""
        self.mcc.set_control(reg, value)
        desc_str = f" ({description})" if description else ""
        print(f"   📝 Control{reg} = 0x{value:08X}{desc_str}")

    def wait_and_check_state(self, expected_state: Optional[str] = None, timeout: float = 2.0):
        """Wait for state transition and verify."""
        time.sleep(0.2)  # Initial settling time

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            state, voltage = self.read_fsm_state(poll_count=3)

            if expected_state and state == expected_state:
                print(f"✅ State: {state} ({voltage:.2f}V)")
                return state
            elif not expected_state:
                print(f"📊 State: {state} ({voltage:.2f}V)")
                return state

            time.sleep(0.1)

        # Timeout
        state, voltage = self.read_fsm_state(poll_count=3)
        if expected_state:
            print(f"⚠️  Timeout waiting for {expected_state}, got {state} ({voltage:.2f}V)")
        return state

    def initialize_forge_ready(self):
        """Initialize FORGE_READY bits in CR0[31:29]."""
        print("\n🚀 Initializing FORGE_READY...")
        self.set_control(0, 0xE0000000, "forge_ready | user_enable | clk_enable")
        time.sleep(0.1)
        state = self.wait_and_check_state()
        return state

    def clear_fault(self):
        """Clear fault state using CR1[3] fault_clear edge detection."""
        print("\n🔄 Clearing fault (if any)...")
        self.set_control(1, 0x00000008, "fault_clear=1 (edge trigger)")
        time.sleep(0.1)
        self.set_control(1, 0x00000000, "fault_clear=0 (clear)")
        return self.wait_and_check_state("IDLE")

    def arm_probe(self, timeout_ms: int = 2000):
        """Arm the probe (transition IDLE → ARMED)."""
        print(f"\n🎯 Arming probe (timeout={timeout_ms}ms)...")

        # Set arm timeout in clock cycles (125 MHz = 8ns period)
        # timeout_cycles = timeout_ms * 1e-3 * 125e6
        timeout_cycles = int(timeout_ms * 125000)  # ms to cycles @ 125MHz
        self.set_control(6, timeout_cycles, f"Arm timeout {timeout_ms}ms ({timeout_cycles} cycles)")

        # Set arm_enable=1 (CR1[0])
        self.set_control(1, 0x00000001, "arm_enable=1")
        time.sleep(0.1)

        return self.wait_and_check_state("ARMED", timeout=1.0)

    def force_fire(self,
                   intensity_us: int = 200,
                   trig_out_us: int = 100,
                   cooling_us: int = 10,
                   intensity_mv: int = 2000,
                   trig_out_mv: int = 0):
        """
        Force fire the probe (software trigger: ARMED → FIRING → COOLING → DONE).

        Args:
            intensity_us: Intensity output duration (OutputB) in microseconds
            trig_out_us: Trigger output duration (OutputA) in microseconds
            cooling_us: Cooling interval in microseconds
            intensity_mv: Output intensity voltage (OutputB) in millivolts (±5000mV range)
            trig_out_mv: Trigger output voltage (OutputA) in millivolts (±5000mV range)
        """
        print(f"\n🔥 Force firing:")
        print(f"   Intensity: {intensity_us}µs @ {intensity_mv}mV (OutputB)")
        print(f"   Trigger:   {trig_out_us}µs @ {trig_out_mv}mV (OutputA)")
        print(f"   Cooldown:  {cooling_us}µs")

        # Convert times to clock cycles (125 MHz = 8ns period)
        intensity_cycles = int(intensity_us * 125)  # µs to cycles @ 125MHz
        trig_cycles = int(trig_out_us * 125)
        cooling_cycles = int(cooling_us * 125)

        # CR3[15:0] = intensity_voltage (mV, signed 16-bit)
        # CR2[15:0] = trig_out_voltage (mV, signed 16-bit)
        intensity_val = intensity_mv & 0xFFFF
        trig_val = trig_out_mv & 0xFFFF

        self.set_control(3, intensity_val, f"Intensity voltage {intensity_mv}mV")
        self.set_control(2, (trig_val & 0xFFFF) | (self.mcc.get_control(2) & 0xFFFF0000),
                        f"Trigger voltage {trig_out_mv}mV")
        self.set_control(5, intensity_cycles, f"Intensity duration {intensity_us}µs ({intensity_cycles} cycles)")
        self.set_control(4, trig_cycles, f"Trigger duration {trig_out_us}µs ({trig_cycles} cycles)")
        self.set_control(7, cooling_cycles, f"Cooldown {cooling_us}µs ({cooling_cycles} cycles)")

        # Software trigger via CR1[1] edge detection (must already be armed)
        # Set sw_trigger=1 while keeping arm_enable=1
        self.set_control(1, 0x00000003, "sw_trigger=1, arm_enable=1")
        time.sleep(0.05)
        self.set_control(1, 0x00000001, "sw_trigger=0 (edge detected), arm_enable=1")

        # Watch state transitions (FIRING → COOLING → DONE)
        print("\n   Watching state transitions...")
        self.wait_and_check_state("FIRING", timeout=0.5)
        self.wait_and_check_state("COOLING", timeout=(intensity_us / 1000.0) + 0.5)
        self.wait_and_check_state("DONE", timeout=(cooling_us / 1000.0) + 0.5)

    def run_state_machine_demo(self):
        """Run complete state machine demonstration."""
        print("\n" + "="*60)
        print("DPD (Demo Probe Driver) FSM State Machine Demo")
        print("="*60)

        # Initialize
        self.initialize_forge_ready()

        # Clear any faults
        self.clear_fault()

        # Arm probe
        self.arm_probe(timeout_ms=5000)

        # Force fire with short pulse
        self.force_fire(intensity_us=200, trig_out_us=100, cooling_us=10,
                       intensity_mv=1500, trig_out_mv=0)

        # Clear to return to IDLE
        self.clear_fault()

        print("\n" + "="*60)
        print("✅ State machine demo complete!")
        print("="*60)

    def interactive_mode(self):
        """Interactive control register twiddling."""
        print("\n" + "="*60)
        print("Interactive FSM Control Mode")
        print("="*60)
        print("\nCommands:")
        print("  r      - Read current state")
        print("  init   - Initialize FORGE_READY")
        print("  clear  - Clear fault state")
        print("  arm    - Arm probe")
        print("  fire   - Force fire probe (software trigger)")
        print("  demo   - Run full state machine demo")
        print("  q      - Quit")
        print("="*60)

        while True:
            try:
                cmd = input("\n> ").strip().lower()

                if cmd == 'q':
                    break
                elif cmd == 'r':
                    state, voltage = self.read_fsm_state()
                    print(f"📊 Current state: {state} ({voltage:.2f}V)")
                elif cmd == 'init':
                    self.initialize_forge_ready()
                elif cmd == 'clear':
                    self.clear_fault()
                elif cmd == 'arm':
                    self.arm_probe()
                elif cmd == 'fire':
                    self.force_fire()
                elif cmd == 'demo':
                    self.run_state_machine_demo()
                else:
                    print(f"Unknown command: {cmd}")

            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"❌ Error: {e}")

    def close(self):
        """Close connection."""
        print("\n👋 Closing connection...")
        self.m.close()


def main():
    """Main entry point."""
    debugger = None
    try:
        debugger = DPDDebugger(ip="192.168.8.98")

        # Run interactive mode by default
        debugger.interactive_mode()

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if debugger:
            debugger.close()


if __name__ == "__main__":
    main()
