#!/usr/bin/env python3
"""
DPD (Demo Probe Driver) FSM State Machine Debugger

Interactive debugger for DPD FSM state machine testing.
Deploys bitstream, sets up routing, and provides interactive commands
to step through state machine transitions.

Usage:
    python debug_fsm_states.py <device_ip> [--slot SLOT] [--platform PLATFORM] [--bitstream PATH]

Examples:
    python debug_fsm_states.py 192.168.8.98
    python debug_fsm_states.py 192.168.8.98 --slot 2
    python debug_fsm_states.py 192.168.8.98 --bitstream ./DPD-bits.tar

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
import argparse
from pathlib import Path
from typing import Optional, Tuple

# Add parent directory to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    from loguru import logger
except ImportError:
    print("ERROR: loguru not installed. Run: uv sync")
    sys.exit(1)

try:
    from moku.instruments import MultiInstrument, CloudCompile, Oscilloscope
except ImportError:
    print("ERROR: moku package not found. Run: uv sync")
    sys.exit(1)

# Import shared CLI utilities
from moku_cli_common import connect_to_device, time_operation, setup_moku_debug_logging, parse_platform_id

# Configure loguru with nice formatting
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True
)


# FSM State Decoding (from OutputC via oscilloscope)
# Based on HVS (Hierarchical Voltage Scaling) encoding
# Encoding: 3277 digital units per state step (0.5V per state @ ±5V full scale)
# Voltage = (digital_units / 32768) * 5V
# Note: DPD only has 4 states (no DONE state exists in hardware)
STATE_MAP = {
    "IDLE":      0.0,    # State 0: 0 digital units → 0.0V
    "ARMED":     0.5,    # State 1: 3277 digital units → 0.5V
    "FIRING":    1.0,    # State 2: 6554 digital units → 1.0V
    "COOLING":   1.5,    # State 3: 9831 digital units → 1.5V
    "FAULT":     -0.5,   # Negative voltage = fault condition
}

# Reverse lookup with tolerance
def decode_fsm_state(voltage: float, tolerance: float = 0.15) -> Optional[str]:
    """Decode FSM state from oscilloscope voltage reading."""
    for state, expected_v in STATE_MAP.items():
        if abs(voltage - expected_v) < tolerance:
            return state
    return f"UNKNOWN({voltage:.2f}V)"


class DPDDebugger:
    """Debug DPD (Demo Probe Driver) FSM state machine."""

    def __init__(self, moku: MultiInstrument, osc_slot: int = 1, cc_slot: int = 2,
                 bitstream_path: Optional[Path] = None):
        """
        Initialize DPD debugger with MultiInstrument instance.

        Args:
            moku: Connected MultiInstrument instance
            osc_slot: Oscilloscope slot number (default: 1)
            cc_slot: CloudCompile slot number (default: 2)
            bitstream_path: Optional path to DPD bitstream (will deploy if provided)
        """
        self.m = moku
        self.osc_slot = osc_slot
        self.cc_slot = cc_slot

        logger.info("📡 Deploying instruments...")

        # Deploy oscilloscope
        logger.info(f"   Slot {osc_slot}: Oscilloscope")
        self.osc = self.m.set_instrument(osc_slot, Oscilloscope)

        # Deploy CloudCompile with or without bitstream
        if bitstream_path:
            logger.info(f"   Slot {cc_slot}: CloudCompile (loading {bitstream_path.name})")
            self.mcc = self.m.set_instrument(cc_slot, CloudCompile, bitstream=str(bitstream_path))
        else:
            logger.info(f"   Slot {cc_slot}: CloudCompile (using existing bitstream)")
            self.mcc = self.m.set_instrument(cc_slot, CloudCompile)

        # Set up routing (Moku:Go has only Output1 and Output2)
        logger.info("🔗 Setting up routing...")
        logger.info("   OutputC (FSM debug) → Output1 for easy scope observation")
        logger.info("   OutputB (intensity) → Output2")
        logger.info("   (OutputA trigger not routed to physical output - limited ports)")
        self.m.set_connections(connections=[
            {'source': 'Input1', 'destination': f'Slot{cc_slot}InA'},              # External trigger input
            {'source': f'Slot{cc_slot}OutB', 'destination': 'Output2'},            # Intensity output
            {'source': f'Slot{cc_slot}OutC', 'destination': 'Output1'},            # FSM debug (for scope)
            {'source': f'Slot{cc_slot}OutC', 'destination': f'Slot{osc_slot}InA'}, # Also to oscilloscope
        ])

        logger.success("✅ Instruments deployed and routing configured")

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
        logger.info(f"   📝 Control{reg} = 0x{value:08X}{desc_str}")

    def wait_and_check_state(self, expected_state: Optional[str] = None, timeout: float = 2.0):
        """Wait for state transition and verify."""
        time.sleep(0.2)  # Initial settling time

        start_time = time.time()
        while (time.time() - start_time) < timeout:
            state, voltage = self.read_fsm_state(poll_count=3)

            if expected_state and state == expected_state:
                logger.success(f"✅ State: {state} ({voltage:.2f}V)")
                return state
            elif not expected_state:
                logger.info(f"📊 State: {state} ({voltage:.2f}V)")
                return state

            time.sleep(0.1)

        # Timeout
        state, voltage = self.read_fsm_state(poll_count=3)
        if expected_state:
            logger.warning(f"⚠️  Timeout waiting for {expected_state}, got {state} ({voltage:.2f}V)")
        return state

    def initialize_forge_ready(self):
        """Initialize FORGE_READY bits in CR0[31:29]."""
        logger.info("\n🚀 Initializing FORGE_READY...")
        self.set_control(0, 0xE0000000, "forge_ready | user_enable | clk_enable")
        time.sleep(0.1)
        state = self.wait_and_check_state()
        return state

    def clear_fault(self):
        """Clear fault state using CR1[3] fault_clear edge detection."""
        logger.info("\n🔄 Clearing fault (if any)...")
        self.set_control(1, 0x00000008, "fault_clear=1 (edge trigger)")
        time.sleep(0.1)
        self.set_control(1, 0x00000000, "fault_clear=0 (clear)")
        return self.wait_and_check_state("IDLE")

    def arm_probe(self, timeout_ms: int = 2000):
        """Arm the probe (transition IDLE → ARMED)."""
        logger.info(f"\n🎯 Arming probe (timeout={timeout_ms}ms)...")

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
        logger.info(f"\n🔥 Force firing:")
        logger.info(f"   Intensity: {intensity_us}µs @ {intensity_mv}mV (OutputB)")
        logger.info(f"   Trigger:   {trig_out_us}µs @ {trig_out_mv}mV (OutputA)")
        logger.info(f"   Cooldown:  {cooling_us}µs")

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

        # Watch state transitions (FIRING → COOLING, then back to IDLE)
        logger.info("\n   Watching state transitions...")
        self.wait_and_check_state("FIRING", timeout=0.5)
        self.wait_and_check_state("COOLING", timeout=(intensity_us / 1000.0) + 0.5)
        # After cooling, FSM returns to IDLE (no DONE state in DPD)
        logger.info("   (FSM will return to IDLE after cooldown)")

    def run_state_machine_demo(self):
        """Run complete state machine demonstration."""
        logger.info("\n" + "="*60)
        logger.info("DPD (Demo Probe Driver) FSM State Machine Demo")
        logger.info("="*60)

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

        logger.info("\n" + "="*60)
        logger.success("✅ State machine demo complete!")
        logger.info("="*60)

    def interactive_mode(self):
        """Interactive control register twiddling."""
        logger.info("\n" + "="*60)
        logger.info("Interactive FSM Control Mode")
        logger.info("="*60)
        logger.info("\nCommands:")
        logger.info("  r      - Read current state")
        logger.info("  init   - Initialize FORGE_READY")
        logger.info("  clear  - Clear fault state")
        logger.info("  arm    - Arm probe")
        logger.info("  fire   - Force fire probe (software trigger)")
        logger.info("  demo   - Run full state machine demo")
        logger.info("  q      - Quit")
        logger.info("="*60)

        while True:
            try:
                cmd = input("\n> ").strip().lower()

                if cmd == 'q':
                    break
                elif cmd == 'r':
                    state, voltage = self.read_fsm_state()
                    logger.info(f"📊 Current state: {state} ({voltage:.2f}V)")
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
                    logger.warning(f"Unknown command: {cmd}")

            except KeyboardInterrupt:
                logger.info("\n\nExiting...")
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='DPD FSM State Machine Interactive Debugger',
        epilog="""
Examples:
  # Auto-detect platform and slot
  python debug_fsm_states.py 192.168.8.98

  # Specify slots
  python debug_fsm_states.py 192.168.8.98 --osc-slot 1 --cc-slot 2

  # Upload bitstream
  python debug_fsm_states.py 192.168.8.98 --bitstream ./DPD-bits.tar

  # Enable Moku debug logging
  python debug_fsm_states.py 192.168.8.98 --debug

  # Force connect (disconnect existing connections)
  python debug_fsm_states.py 192.168.8.98 --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Add device IP manually first, then use common args
    parser.add_argument('device_ip', help='IP address of the Moku device')
    parser.add_argument('--osc-slot', type=int, default=1, help='Oscilloscope slot number (default: 1)')
    parser.add_argument('--cc-slot', type=int, default=2, help='CloudCompile slot number (default: 2)')
    parser.add_argument(
        '--platform',
        choices=['moku_go', 'moku_lab', 'moku_pro', 'moku_delta'],
        help='Platform type (default: moku_go)'
    )
    parser.add_argument('--bitstream', type=Path, help='Path to DPD bitstream file')
    parser.add_argument('--force', action='store_true', help='Force connection (disconnect existing)')
    parser.add_argument(
        '--debug',
        nargs='?',
        const=True,
        type=str,
        metavar='FILE',
        help='Enable debug logging for Moku library. Optionally specify output file (default: stderr)'
    )

    args = parser.parse_args()

    # Enable Moku debug logging if requested
    setup_moku_debug_logging(args)

    # Parse platform ID from name
    platform_id = parse_platform_id(args)
    if platform_id is None:
        platform_id = 2  # Default to Moku:Go

    # Resolve bitstream path if provided
    bitstream_path = None
    if args.bitstream:
        bitstream_path = args.bitstream
        if not bitstream_path.is_absolute():
            bitstream_path = Path(__file__).parent / bitstream_path

    moku = None
    debugger = None

    try:
        # Connect to device
        logger.info(f"Connecting to {args.device_ip}...")
        with time_operation("Device connection"):
            moku = connect_to_device(args.device_ip, platform_id, force=args.force, read_timeout=5)

        # Initialize debugger
        debugger = DPDDebugger(moku, osc_slot=args.osc_slot, cc_slot=args.cc_slot,
                              bitstream_path=bitstream_path)

        # Run interactive mode
        debugger.interactive_mode()

    except KeyboardInterrupt:
        logger.info("\n\nInterrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if moku is not None:
            logger.info("\n👋 Disconnecting...")
            try:
                moku.relinquish_ownership()
                logger.success("Disconnected")
            except Exception as e:
                logger.warning(f"Disconnect warning: {e}")


if __name__ == "__main__":
    main()
