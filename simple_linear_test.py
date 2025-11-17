#!/usr/bin/env python3
"""
Simple linear test for Moku device Control10 register.

Connects to a Moku device and sets power levels to 10%, 20%, 30% sequentially
with detailed timing introspection to identify bottlenecks.

Usage:
    python simple_linear_test.py <device-ip> [--slot SLOT] [--platform PLATFORM] [--bitstream PATH]

Examples:
    python simple_linear_test.py 192.168.1.100
    python simple_linear_test.py 192.168.1.100 --slot 1
    python simple_linear_test.py 192.168.1.100 --platform moku_go
"""

import argparse
import sys
import time
from pathlib import Path
from contextlib import contextmanager

# Add moku-models to path
PROJECT_ROOT = Path(__file__).parent
MOKU_MODELS = PROJECT_ROOT / "moku-models-v4"
sys.path.insert(0, str(MOKU_MODELS))

try:
    from moku.instruments import MultiInstrument, CloudCompile
    from moku import logging as moku_logging
except ImportError:
    print("Error: moku library not installed. Run: uv sync")
    sys.exit(1)


@contextmanager
def time_operation(operation_name: str):
    """Context manager to time an operation and print the result."""
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start
        print(f"  {operation_name}: {elapsed*1000:.2f} ms")


def percent_to_register(percent: float) -> int:
    """Convert percentage (0-100) to register value (0-32767)."""
    return int((percent / 100.0) * 32767)


def register_to_percent(register_value: int) -> float:
    """Convert register value (0-32767) to percentage (0-100)."""
    return (register_value / 32767.0) * 100.0


def find_cloudcompile_slot(moku: MultiInstrument) -> int | None:
    """Find which slot contains CloudCompile instrument."""
    with time_operation("Finding CloudCompile slot"):
        instruments = moku.get_instruments() or []
        for slot_num, instrument_name in enumerate(instruments, start=1):
            if instrument_name and instrument_name.strip() == 'CloudCompile':
                return slot_num
        return None


def connect_to_device(device_ip: str, platform_id: int | None = None, force: bool = False) -> MultiInstrument:
    """Connect to Moku device with platform detection."""
    platform_id_map = {
        1: "Moku:Lab",
        2: "Moku:Go",
        3: "Moku:Pro",
        4: "Moku:Delta",
    }
    
    with time_operation("Device connection"):
        if platform_id is None:
            # Try each platform
            for pid in [2, 1, 3, 4]:  # Go, Lab, Pro, Delta
                try:
                    moku = MultiInstrument(
                        device_ip,
                        platform_id=pid,
                        force_connect=force,
                        persist_state=True,  # Preserve existing state
                        read_timeout=5  # 5 second timeout for faster failure detection
                    )
                    print(f"✓ Connected to {platform_id_map[pid]} at {device_ip}")
                    return moku
                except Exception as e:
                    error_msg = str(e).lower()
                    if "already exists" in error_msg or "busy" in error_msg:
                        continue
                    continue
            raise ConnectionError(f"Could not connect to {device_ip}. Try --force to disconnect existing connections.")
        else:
            # Use specified platform
            moku = MultiInstrument(
                device_ip,
                platform_id=platform_id,
                force_connect=force,
                persist_state=True,
                read_timeout=5  # 5 second timeout for faster failure detection
            )
            platform_name = platform_id_map.get(platform_id, f"Platform {platform_id}")
            print(f"✓ Connected to {platform_name} at {device_ip}")
            return moku


def get_cloudcompile_instance(moku: MultiInstrument, slot_num: int, bitstream_path: Path | None = None) -> CloudCompile:
    """Get CloudCompile instance from specified slot.
    
    Args:
        moku: MultiInstrument instance
        slot_num: Slot number containing CloudCompile
        bitstream_path: Optional path to bitstream file. If provided, will upload it.
    
    Returns:
        CloudCompile instance
    """
    with time_operation("Getting CloudCompile instance"):
        try:
            if bitstream_path:
                # Upload bitstream and get instance
                if not bitstream_path.exists():
                    raise FileNotFoundError(f"Bitstream file not found: {bitstream_path}")
                cc = moku.set_instrument(slot_num, CloudCompile, bitstream=str(bitstream_path))
                return cc
            else:
                # Try to get existing instance (without bitstream parameter)
                cc = moku.set_instrument(slot_num, CloudCompile)
                return cc
        except TypeError:
            # If set_instrument requires bitstream, we can't proceed without it
            raise RuntimeError(
                f"CloudCompile in slot {slot_num} requires bitstream parameter. "
                "The instrument may not be deployed yet. Please provide --bitstream or deploy it first."
            )
        except Exception as e:
            raise RuntimeError(f"Could not access CloudCompile in slot {slot_num}: {e}")


def set_control_with_timing(cc: CloudCompile, control_num: int, value: int) -> None:
    """Set control value with detailed timing breakdown."""
    print(f"\nSetting Control{control_num} to {value} ({register_to_percent(value):.2f}%)")
    
    # Time the actual set_control call
    start = time.perf_counter()
    try:
        cc.set_control(control_num, value)
        elapsed = time.perf_counter() - start
        print(f"  set_control({control_num}, {value}): {elapsed*1000:.2f} ms")
    except Exception as e:
        elapsed = time.perf_counter() - start
        error_msg = str(e)
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            print(f"  set_control({control_num}, {value}) TIMED OUT after {elapsed*1000:.2f} ms")
            print(f"  ⚠️  This may indicate a device/firmware issue. The operation may have succeeded despite the timeout.")
            print(f"  Error details: {error_msg}")
        else:
            print(f"  set_control({control_num}, {value}) FAILED after {elapsed*1000:.2f} ms: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description='Linear test for Moku Control10 register with timing introspection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect platform and slot
  python simple_linear_test.py 192.168.1.100

  # Specify slot
  python simple_linear_test.py 192.168.1.100 --slot 1

  # Specify platform
  python simple_linear_test.py 192.168.1.100 --platform moku_go

  # Upload bitstream and test
  python simple_linear_test.py 192.168.1.100 --bitstream ./my_bitstream.tar

  # Force connect (disconnect existing connections)
  python simple_linear_test.py 192.168.1.100 --force
        """
    )
    parser.add_argument('device_ip', help='Moku device IP address')
    parser.add_argument(
        '--slot',
        type=int,
        help='Slot number containing CloudCompile (auto-detected if not specified)'
    )
    parser.add_argument(
        '--platform',
        choices=['moku_go', 'moku_lab', 'moku_pro', 'moku_delta'],
        help='Platform type (auto-detected if not specified)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force connect (disconnect existing connections)'
    )
    parser.add_argument(
        '--bitstream',
        type=Path,
        help='Path to bitstream file (.tar) to upload to CloudCompile'
    )
    
    args = parser.parse_args()
    
    # Enable debug logging for Moku library
    moku_logging.enable_debug_logging()
    
    # Map platform name to ID
    platform_id = None
    if args.platform:
        platform_map = {
            'moku_go': 2,
            'moku_lab': 1,
            'moku_pro': 3,
            'moku_delta': 4,
        }
        platform_id = platform_map[args.platform]
    
    # Overall timing
    total_start = time.perf_counter()
    
    # Initialize moku to None to handle cleanup in finally block
    moku = None
    
    # Connect to device
    print(f"Connecting to {args.device_ip}...")
    try:
        moku = connect_to_device(args.device_ip, platform_id, force=args.force)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Find CloudCompile slot
        if args.slot:
            slot_num = args.slot
            # Verify slot exists
            with time_operation("Verifying slot exists"):
                instruments = moku.get_instruments() or []
                if slot_num < 1 or slot_num > len(instruments):
                    print(f"Error: Slot {slot_num} does not exist", file=sys.stderr)
                    sys.exit(1)
            
            # If bitstream is provided, we can deploy to this slot even if it's not CloudCompile
            if args.bitstream:
                instrument_name = instruments[slot_num - 1] if slot_num <= len(instruments) else None
                if instrument_name and instrument_name.strip() and instrument_name.strip() != 'CloudCompile':
                    print(f"Warning: Slot {slot_num} contains '{instrument_name}'. Will deploy CloudCompile with bitstream.", file=sys.stderr)
            else:
                # Without bitstream, verify it's actually CloudCompile
                instrument_name = instruments[slot_num - 1]
                if not instrument_name or instrument_name.strip() != 'CloudCompile':
                    print(f"Error: Slot {slot_num} contains '{instrument_name}', not CloudCompile. Use --bitstream to deploy.", file=sys.stderr)
                    sys.exit(1)
        else:
            # Auto-detect CloudCompile slot
            slot_num = find_cloudcompile_slot(moku)
            if slot_num is None:
                if args.bitstream:
                    # If bitstream provided but no CloudCompile found, default to slot 1
                    slot_num = 1
                    print(f"No CloudCompile found. Will deploy to slot {slot_num} with bitstream.")
                else:
                    print("Error: No CloudCompile instrument found. Please specify --slot or provide --bitstream", file=sys.stderr)
                    sys.exit(1)
            else:
                print(f"Found CloudCompile in slot {slot_num}")
        
        # Resolve bitstream path if provided
        bitstream_path = None
        if args.bitstream:
            bitstream_path = args.bitstream
            # Resolve relative paths
            if not bitstream_path.is_absolute():
                bitstream_path = PROJECT_ROOT / bitstream_path
            if not bitstream_path.exists():
                print(f"Error: Bitstream file not found: {bitstream_path}", file=sys.stderr)
                sys.exit(1)
            print(f"Using bitstream: {bitstream_path.name}")
        
        # Get CloudCompile instance
        print(f"\nAccessing CloudCompile in slot {slot_num}...")
        try:
            cc = get_cloudcompile_instance(moku, slot_num, bitstream_path)
            if bitstream_path:
                print(f"✓ CloudCompile instance ready (bitstream uploaded)")
            else:
                print("✓ CloudCompile instance ready")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Set power levels sequentially: 10%, 20%, 30%
        print("\n" + "="*60)
        print("TIMING INTROSPECTION - Control10 Operations")
        print("="*60)
        power_levels = [10.0, 20.0, 30.0]
        
        print("\n" + "="*60)
        print("Setting power levels sequentially")
        print("="*60)
        
        for percent in power_levels:
            register_value = percent_to_register(percent)
            try:
                set_control_with_timing(cc, 10, register_value)
            except Exception as e:
                error_msg = str(e)
                if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                    print(f"  ⚠️  Continuing despite timeout...")
                else:
                    # Re-raise non-timeout exceptions
                    raise
        
        # Summary
        total_elapsed = time.perf_counter() - total_start
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Total execution time: {total_elapsed:.3f} s ({total_elapsed*1000:.2f} ms)")
        print(f"Power levels set: {', '.join(f'{p}%' for p in power_levels)}")
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Disconnect
        if moku is not None:
            print("\nDisconnecting...")
            with time_operation("Disconnect (relinquish_ownership)"):
                try:
                    moku.relinquish_ownership()
                    print("✓ Disconnected")
                except Exception as e:
                    print(f"  Disconnect warning: {e}")


if __name__ == "__main__":
    main()

