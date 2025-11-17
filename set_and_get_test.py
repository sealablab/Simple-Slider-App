#!/usr/bin/env python3
"""
Simple script to read all control registers from an already deployed CloudCompile instrument.

Assumes a custom bitstream is already loaded in slot 2 of multi-instrument mode.

Usage:
    python set_and_get_test.py <device-ip> [--slot SLOT] [--platform PLATFORM] [--force]

Examples:
    python set_and_get_test.py 192.168.1.100
    python set_and_get_test.py 192.168.1.100 --slot 2
    python set_and_get_test.py 192.168.1.100 --platform moku_go
"""

import argparse
import sys
import time
from pathlib import Path

# Add moku-models to path
PROJECT_ROOT = Path(__file__).parent
MOKU_MODELS = PROJECT_ROOT / "moku-models-v4"
sys.path.insert(0, str(MOKU_MODELS))

try:
    from loguru import logger
except ImportError:
    print("Error: loguru not installed. Run: uv sync")
    sys.exit(1)

try:
    from moku.instruments import MultiInstrument, CloudCompile
    from moku import logging as moku_logging
except ImportError:
    logger.error("moku library not installed. Run: uv sync")
    sys.exit(1)

# Configure loguru with nice formatting
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)


def connect_to_device(device_ip: str, platform_id: int | None = None, force: bool = False) -> MultiInstrument:
    """Connect to Moku device with platform detection."""
    platform_id_map = {
        1: "Moku:Lab",
        2: "Moku:Go",
        3: "Moku:Pro",
        4: "Moku:Delta",
    }
    
    if platform_id is None:
        # Try each platform
        for pid in [2, 1, 3, 4]:  # Go, Lab, Pro, Delta
            try:
                moku = MultiInstrument(
                    device_ip,
                    platform_id=pid,
                    force_connect=force,
                    persist_state=True  # Preserve existing state
                )
                logger.success(f"Connected to {platform_id_map[pid]} at {device_ip}")
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
            persist_state=True
        )
        platform_name = platform_id_map.get(platform_id, f"Platform {platform_id}")
        logger.success(f"Connected to {platform_name} at {device_ip}")
        return moku


def get_cloudcompile_instance(moku: MultiInstrument, slot_num: int) -> CloudCompile:
    """Get CloudCompile instance from specified slot (assumes already deployed).
    
    Args:
        moku: MultiInstrument instance
        slot_num: Slot number containing CloudCompile
    
    Returns:
        CloudCompile instance
    """
    try:
        # Try to get existing instance without bitstream parameter
        # This works if the instrument is already deployed
        cc = moku.set_instrument(slot_num, CloudCompile)
        return cc
    except TypeError:
        # If set_instrument requires bitstream, we can't proceed
        raise RuntimeError(
            f"CloudCompile in slot {slot_num} requires bitstream parameter. "
            "The instrument may not be deployed yet. Please deploy it first."
        )
    except Exception as e:
        raise RuntimeError(f"Could not access CloudCompile in slot {slot_num}: {e}")


def handle_arg_parsing():
    """Parse command line arguments and configure logging."""
    parser = argparse.ArgumentParser(
        description='Read all control registers from deployed CloudCompile instrument',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect platform, use slot 2 (default)
  python set_and_get_test.py 192.168.1.100

  # Specify slot
  python set_and_get_test.py 192.168.1.100 --slot 2

  # Specify platform
  python set_and_get_test.py 192.168.1.100 --platform moku_go

  # Force connect (disconnect existing connections)
  python set_and_get_test.py 192.168.1.100 --force
        """
    )
    parser.add_argument('device_ip', help='Moku device IP address')
    parser.add_argument(
        '--slot',
        type=int,
        default=2,
        help='Slot number containing CloudCompile (default: 2)'
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
        '--debug',
        action='store_true',
        help='Enable debug logging for Moku library'
    )
    
    args = parser.parse_args()
    
    # Enable Moku debug logging if requested
    if args.debug:
        moku_logging.enable_debug_logging()
        logger.info("Moku debug logging enabled")
    
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
    
    return args, platform_id


def main():
    args, platform_id = handle_arg_parsing()
    
    # Initialize moku to None to handle cleanup in finally block
    moku = None
    
    # Connect to device
    logger.info(f"Connecting to {args.device_ip}...")
    try:
        moku = connect_to_device(args.device_ip, platform_id, force=args.force)
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(1)
    
    try:
        # Verify slot exists
        instruments = moku.get_instruments() or []
        if args.slot < 1 or args.slot > len(instruments):
            logger.error(f"Slot {args.slot} does not exist (device has {len(instruments)} slot(s))")
            sys.exit(1)
        
        instrument_name = instruments[args.slot - 1] if args.slot <= len(instruments) else None
        if instrument_name and instrument_name.strip() != 'CloudCompile':
            logger.warning(f"Slot {args.slot} contains '{instrument_name}', not CloudCompile")
            logger.info("Attempting to access anyway...")
        
        # Get CloudCompile instance
        logger.info(f"Accessing CloudCompile in slot {args.slot}...")
        try:
            cc = get_cloudcompile_instance(moku, args.slot)
            logger.success("CloudCompile instance ready")
        except Exception as e:
            logger.error(f"Failed to get CloudCompile instance: {e}")
            sys.exit(1)
        
        # Read all control registers using get_controls()
        logger.info("\n" + "="*60)
        logger.info("Reading all control registers...")
        logger.info("="*60)
        
        start = time.perf_counter()
        try:
            controls = cc.get_controls()
            elapsed = time.perf_counter() - start
            
            logger.success(f"get_controls() completed in {elapsed*1000:.2f} ms")
            logger.info(f"\nControl Registers:")
            logger.info("-" * 60)
            
            # Handle different return formats
            if isinstance(controls, dict):
                # If it's a dict, print key-value pairs
                if 'controls' in controls:
                    # Nested structure: {'controls': [...]}
                    control_list = controls['controls']
                elif 'values' in controls:
                    # Alternative structure: {'values': [...]}
                    control_list = controls['values']
                else:
                    # Direct dict mapping
                    control_list = controls
                
                # If control_list is a list of dicts with 'id' and 'value'
                if isinstance(control_list, list):
                    for item in control_list:
                        if isinstance(item, dict):
                            reg_id = item.get('id', item.get('idx', '?'))
                            reg_value = item.get('value', item.get('val', '?'))
                            logger.info(f"  Control{reg_id:2d}: {reg_value:6d} (0x{reg_value:04X})")
                        else:
                            # List of values, use index
                            logger.info(f"  Control{control_list.index(item):2d}: {item:6d} (0x{item:04X})")
                elif isinstance(control_list, dict):
                    # Dict mapping id -> value
                    for reg_id, reg_value in sorted(control_list.items()):
                        if isinstance(reg_id, str) and reg_id.isdigit():
                            reg_id = int(reg_id)
                        logger.info(f"  Control{reg_id:2d}: {reg_value:6d} (0x{reg_value:04X})")
                else:
                    # Unknown format, print raw
                    logger.info(f"  Raw response: {controls}")
            elif isinstance(controls, list):
                # List of values
                for idx, value in enumerate(controls):
                    logger.info(f"  Control{idx:2d}: {value:6d} (0x{value:04X})")
            else:
                # Unknown format, print raw
                logger.info(f"  Raw response: {controls}")
                logger.info(f"  Type: {type(controls)}")
            
            logger.info("-" * 60)
            logger.info(f"\nTotal registers read: {len(controls) if hasattr(controls, '__len__') else 'N/A'}")
            
        except Exception as e:
            elapsed = time.perf_counter() - start
            logger.error(f"get_controls() FAILED after {elapsed*1000:.2f} ms: {e}")
            logger.debug("Exception details:", exc_info=True)
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)
    finally:
        # Disconnect
        if moku is not None:
            logger.info("\nDisconnecting...")
            try:
                moku.relinquish_ownership()
                logger.success("Disconnected")
            except Exception as e:
                logger.warning(f"Disconnect warning: {e}")


if __name__ == "__main__":
    main()

