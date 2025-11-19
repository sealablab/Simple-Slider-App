#!/usr/bin/env python3
"""
DPD (Demo Probe Driver) - Debug oscilloscope data acquisition

Tests basic oscilloscope reading and FSM state decoding.
Performs quick diagnostic test of instrument deployment and state reading.

Usage:
    python debug_oscilloscope.py <device_ip> [--slot SLOT] [--platform PLATFORM] [--bitstream PATH]

Examples:
    python debug_oscilloscope.py 192.168.8.98
    python debug_oscilloscope.py 192.168.8.98 --bitstream ./DPD-bits.tar
"""

import sys
import time
import argparse
from pathlib import Path

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
    logger.error("ERROR: Moku API not available")
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


def decode_state(voltage: float) -> str:
    """Decode FSM state from voltage reading."""
    if abs(voltage - 0.0) < 0.15:
        return "IDLE"
    elif abs(voltage - 0.5) < 0.15:
        return "ARMED"
    elif abs(voltage - 1.0) < 0.15:
        return "FIRING"
    elif abs(voltage - 1.5) < 0.15:
        return "COOLING"
    elif abs(voltage - 2.0) < 0.15:
        return "DONE"
    elif voltage < -1.0:
        return "FAULT"
    else:
        return f"UNKNOWN({voltage:.3f}V)"


def main():
    parser = argparse.ArgumentParser(
        description='DPD Oscilloscope Diagnostic Test',
        epilog="""
Examples:
  # Auto-detect platform
  python debug_oscilloscope.py 192.168.8.98

  # Upload bitstream
  python debug_oscilloscope.py 192.168.8.98 --bitstream ./DPD-bits.tar

  # Enable Moku debug logging
  python debug_oscilloscope.py 192.168.8.98 --debug

  # Force connect
  python debug_oscilloscope.py 192.168.8.98 --force
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('device_ip', help='IP address of the Moku device')
    parser.add_argument('--osc-slot', type=int, default=1, help='Oscilloscope slot (default: 1)')
    parser.add_argument('--cc-slot', type=int, default=2, help='CloudCompile slot (default: 2)')
    parser.add_argument(
        '--platform',
        choices=['moku_go', 'moku_lab', 'moku_pro', 'moku_delta'],
        help='Platform type (default: moku_go)'
    )
    parser.add_argument('--bitstream', type=Path, help='Path to DPD bitstream file')
    parser.add_argument('--force', action='store_true', help='Force connection')
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

    # Resolve bitstream path
    bitstream_path = None
    if args.bitstream:
        bitstream_path = args.bitstream
        if not bitstream_path.is_absolute():
            bitstream_path = Path(__file__).parent / bitstream_path

    moku = None

    try:
        # Connect to device
        logger.info(f"Connecting to {args.device_ip}...")
        with time_operation("Device connection"):
            moku = connect_to_device(args.device_ip, platform_id, force=args.force)

        # Deploy instruments
        logger.info("📡 Deploying instruments...")
        if bitstream_path:
            logger.info(f"   Slot {args.cc_slot}: CloudCompile (loading {bitstream_path.name})")
            mcc = moku.set_instrument(args.cc_slot, CloudCompile, bitstream=str(bitstream_path))
        else:
            logger.info(f"   Slot {args.cc_slot}: CloudCompile (using existing)")
            mcc = moku.set_instrument(args.cc_slot, CloudCompile)

        logger.info(f"   Slot {args.osc_slot}: Oscilloscope")
        osc = moku.set_instrument(args.osc_slot, Oscilloscope)

        # Set up routing
        logger.info("🔗 Setting up routing...")
        moku.set_connections(connections=[
            {'source': 'Input1', 'destination': f'Slot{args.cc_slot}InA'},
            {'source': f'Slot{args.cc_slot}OutA', 'destination': 'Output1'},
            {'source': f'Slot{args.cc_slot}OutB', 'destination': 'Output2'},
            {'source': f'Slot{args.cc_slot}OutC', 'destination': f'Slot{args.osc_slot}InA'},
        ])

        logger.success("✓ Connected")

        # Check oscilloscope configuration
        logger.info("\n" + "=" * 70)
        logger.info("OSCILLOSCOPE DIAGNOSTICS")
        logger.info("=" * 70)

        logger.info("\nAttempting to read data...")
        try:
            data = osc.get_data()
            logger.success("✓ Data acquired")
            logger.info(f"  Keys: {list(data.keys())}")

            if 'ch1' in data:
                logger.info(f"  Ch1 samples: {len(data['ch1'])}")
                logger.info(f"  Ch1 range: {min(data['ch1']):.3f}V to {max(data['ch1']):.3f}V")
                midpoint = data['ch1'][len(data['ch1'])//2]
                logger.info(f"  Ch1 midpoint: {midpoint:.3f}V")

                # Show first 10 samples
                samples_str = [f'{v:.3f}' for v in data['ch1'][:10]]
                logger.info(f"  Ch1 first 10 samples: {samples_str}")
            else:
                logger.error("  ✗ No 'ch1' data!")

            if 'time' in data:
                logger.info(f"  Time samples: {len(data['time'])}")
                logger.info(f"  Time range: {min(data['time'])*1e3:.1f}ms to {max(data['time'])*1e3:.1f}ms")

        except Exception as e:
            logger.error(f"✗ Failed to read data: {e}")
            import traceback
            traceback.print_exc()

        # Initialize FORGE_READY
        logger.info("\n" + "=" * 70)
        logger.info("INITIALIZING FORGE_READY")
        logger.info("=" * 70)

        logger.info("\nSetting CR0[31:29] = 0b111 (forge_ready | user_enable | clk_enable)...")
        mcc.set_control(0, 0xE0000000)
        time.sleep(0.1)

        logger.info("Reading initial state...")
        try:
            data = osc.get_data()
            if 'ch1' in data:
                midpoint = data['ch1'][len(data['ch1'])//2]
                state = decode_state(midpoint)
                logger.info(f"  Ch1 midpoint: {midpoint:.3f}V")
                logger.info(f"  State: {state}" + (" (correct!)" if state == "IDLE" else " (expected IDLE)"))
            else:
                logger.error("  ✗ No ch1 data!")
        except Exception as e:
            logger.error(f"✗ Failed: {e}")

        # Try arming the probe
        logger.info("\n" + "=" * 70)
        logger.info("TESTING ARM FUNCTION")
        logger.info("=" * 70)

        logger.info("\nSetting arm_enable=1 (CR1[0])...")
        mcc.set_control(1, 0x00000001)

        logger.info("Waiting 0.5s for state change...")
        time.sleep(0.5)

        logger.info("Reading oscilloscope data...")
        try:
            data = osc.get_data()
            if 'ch1' in data:
                midpoint = data['ch1'][len(data['ch1'])//2]
                state = decode_state(midpoint)
                logger.info(f"  Ch1 midpoint: {midpoint:.3f}V")
                logger.info(f"  State: {state}")
            else:
                logger.error("  ✗ No ch1 data!")
        except Exception as e:
            logger.error(f"✗ Failed: {e}")

        # Clear fault to return to IDLE
        logger.info("\n" + "=" * 70)
        logger.info("CLEARING FAULT")
        logger.info("=" * 70)

        logger.info("\nPulsing fault_clear (CR1[3])...")
        mcc.set_control(1, 0x00000008)
        time.sleep(0.01)
        mcc.set_control(1, 0x00000000)

        logger.success("\n✓ Diagnostic test complete")

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if moku is not None:
            logger.info("\nDisconnecting...")
            try:
                moku.relinquish_ownership()
                logger.success("✓ Done")
            except Exception as e:
                logger.warning(f"Disconnect warning: {e}")


if __name__ == "__main__":
    main()
