#!/usr/bin/env python3
"""
Upload settings to Moku device CloudCompile instrument.

Loads a previously saved .mokuconf configuration file and uploads it to
a CloudCompile instrument on the device.

Usage:
    python upload_settings.py <device-ip> <config-file> --bitstream PATH [--slot SLOT] [--platform PLATFORM]

Examples:
    python upload_settings.py 192.168.1.100 my_config.mokuconf --bitstream ./my_bitstream.tar
    python upload_settings.py 192.168.1.100 my_config.mokuconf --bitstream ./my_bitstream.tar --slot 1
    python upload_settings.py 192.168.1.100 my_config.mokuconf --bitstream ./my_bitstream.tar --platform moku_go
"""

import argparse
import sys
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

def setup_logging(verbose: bool = False):
    """Configure loguru with nice formatting."""
    logger.remove()  # Remove default handler
    
    level = "DEBUG" if verbose else "INFO"
    
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )


def find_cloudcompile_slot(moku: MultiInstrument) -> int | None:
    """Find which slot contains CloudCompile instrument."""
    logger.debug("Searching for CloudCompile instrument in slots...")
    instruments = moku.get_instruments() or []
    logger.debug(f"Found {len(instruments)} instrument slot(s)")
    
    for slot_num, instrument_name in enumerate(instruments, start=1):
        logger.debug(f"Slot {slot_num}: {instrument_name or '(empty)'}")
        if instrument_name and instrument_name.strip() == 'CloudCompile':
            logger.info(f"Found CloudCompile in slot {slot_num}")
            return slot_num
    
    logger.warning("No CloudCompile instrument found in any slot")
    return None


def connect_to_device(device_ip: str, platform_id: int | None = None, force: bool = False) -> MultiInstrument:
    """Connect to Moku device with platform detection."""
    platform_id_map = {
        1: "Moku:Lab",
        2: "Moku:Go",
        3: "Moku:Pro",
        4: "Moku:Delta",
    }
    
    logger.info(f"Connecting to device at {device_ip}...")
    logger.debug(f"Platform ID: {platform_id}, Force connect: {force}")
    
    if platform_id is None:
        # Try each platform
        logger.debug("Auto-detecting platform type...")
        for pid in [2, 1, 3, 4]:  # Go, Lab, Pro, Delta
            platform_name = platform_id_map[pid]
            logger.debug(f"Trying {platform_name} (platform_id={pid})...")
            try:
                moku = MultiInstrument(
                    device_ip,
                    platform_id=pid,
                    force_connect=force,
                    persist_state=True  # Preserve existing state
                )
                logger.success(f"Connected to {platform_name} at {device_ip}")
                return moku
            except Exception as e:
                error_msg = str(e).lower()
                logger.debug(f"Failed to connect as {platform_name}: {e}")
                if "already exists" in error_msg or "busy" in error_msg:
                    logger.debug("Device is busy, trying next platform...")
                    continue
                continue
        logger.error(f"Could not connect to {device_ip} with any platform type")
        raise ConnectionError(f"Could not connect to {device_ip}. Try --force to disconnect existing connections.")
    else:
        # Use specified platform
        platform_name = platform_id_map.get(platform_id, f"Platform {platform_id}")
        logger.debug(f"Using specified platform: {platform_name} (platform_id={platform_id})")
        try:
            moku = MultiInstrument(
                device_ip,
                platform_id=platform_id,
                force_connect=force,
                persist_state=True
            )
            logger.success(f"Connected to {platform_name} at {device_ip}")
            return moku
        except Exception as e:
            logger.error(f"Failed to connect to {platform_name}: {e}")
            raise


def get_cloudcompile_instance(moku: MultiInstrument, slot_num: int, bitstream_path: Path) -> CloudCompile:
    """Get CloudCompile instance from specified slot.
    
    Args:
        moku: MultiInstrument instance
        slot_num: Slot number containing CloudCompile
        bitstream_path: Path to bitstream file (required - CloudCompile always needs a bitstream)
    
    Returns:
        CloudCompile instance
    """
    logger.debug(f"Getting CloudCompile instance for slot {slot_num}...")
    
    if not bitstream_path:
        raise ValueError("Bitstream path is required for CloudCompile")
    
    try:
        # CloudCompile always requires a bitstream, even for existing instances
        logger.info(f"Using bitstream: {bitstream_path.name}")
        logger.debug(f"Bitstream path (absolute): {bitstream_path.absolute()}")
        
        if not bitstream_path.exists():
            logger.error(f"Bitstream file not found: {bitstream_path}")
            raise FileNotFoundError(f"Bitstream file not found: {bitstream_path}")
        
        file_size = bitstream_path.stat().st_size
        logger.debug(f"Bitstream file size: {file_size / (1024*1024):.2f} MB")
        
        logger.debug(f"Calling moku.set_instrument({slot_num}, CloudCompile, bitstream={bitstream_path})")
        cc = moku.set_instrument(slot_num, CloudCompile, bitstream=str(bitstream_path))
        logger.success(f"CloudCompile instance ready for slot {slot_num}")
        return cc
    except Exception as e:
        logger.error(f"Exception when accessing CloudCompile in slot {slot_num}: {e}")
        logger.debug("Exception details:", exc_info=True)
        raise RuntimeError(f"Could not access CloudCompile in slot {slot_num}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Upload settings to Moku CloudCompile instrument',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect platform and slot
  python upload_settings.py 192.168.1.100 my_config.mokuconf

  # Specify slot
  python upload_settings.py 192.168.1.100 my_config.mokuconf --slot 1

  # Specify platform
  python upload_settings.py 192.168.1.100 my_config.mokuconf --platform moku_go

  # Load settings (bitstream is required)
  python upload_settings.py 192.168.1.100 my_config.mokuconf --bitstream ./my_bitstream.tar

  # Force connect (disconnect existing connections)
  python upload_settings.py 192.168.1.100 my_config.mokuconf --force
        """
    )
    parser.add_argument('device_ip', help='Moku device IP address')
    parser.add_argument('config_file', type=Path, help='Path to .mokuconf configuration file')
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
        required=True,
        help='Path to bitstream file (.tar) - REQUIRED: CloudCompile always needs a bitstream, even for existing instances'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose/debug logging output'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging for Moku library'
    )
    
    args = parser.parse_args()
    
    # Setup logging based on verbosity
    setup_logging(verbose=args.verbose)
    
    # Enable Moku debug logging if requested
    if args.debug:
        moku_logging.enable_debug_logging()
        logger.info("Moku debug logging enabled")
    
    # Validate config file
    logger.debug("Validating configuration file...")
    config_path = args.config_file
    logger.debug(f"Config file path (provided): {config_path}")
    
    if not config_path.is_absolute():
        config_path = PROJECT_ROOT / config_path
        logger.debug(f"Resolved to absolute path: {config_path}")
    
    if not config_path.exists():
        logger.error(f"Configuration file not found: {config_path}")
        sys.exit(1)
    
    file_size = config_path.stat().st_size
    logger.debug(f"Config file size: {file_size} bytes ({file_size / 1024:.2f} KB)")
    
    if config_path.suffix.lower() != '.mokuconf':
        logger.warning(f"Configuration file should have .mokuconf extension: {config_path}")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            logger.info("User cancelled operation")
            sys.exit(0)
        logger.debug("User confirmed to continue with non-standard extension")
    
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
        logger.debug(f"Mapped platform '{args.platform}' to platform_id={platform_id}")
    
    # Connect to device
    try:
        moku = connect_to_device(args.device_ip, platform_id, force=args.force)
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(1)
    
    try:
        # Find CloudCompile slot
        logger.debug("Determining CloudCompile slot...")
        if args.slot:
            slot_num = args.slot
            logger.debug(f"Using specified slot: {slot_num}")
            # Verify slot exists
            instruments = moku.get_instruments() or []
            logger.debug(f"Device has {len(instruments)} instrument slot(s)")
            if slot_num < 1 or slot_num > len(instruments):
                logger.error(f"Slot {slot_num} does not exist (device has {len(instruments)} slot(s))")
                sys.exit(1)
            
            # Bitstream is always provided (required), so we can deploy/redeploy CloudCompile
            instrument_name = instruments[slot_num - 1] if slot_num <= len(instruments) else None
            logger.debug(f"Slot {slot_num} currently contains: {instrument_name or '(empty)'}")
            if instrument_name and instrument_name.strip() and instrument_name.strip() != 'CloudCompile':
                logger.warning(f"Slot {slot_num} contains '{instrument_name}'. Will deploy CloudCompile with bitstream.")
        else:
            # Auto-detect CloudCompile slot
            slot_num = find_cloudcompile_slot(moku)
            if slot_num is None:
                # Bitstream is always provided (required), so default to slot 1
                slot_num = 1
                logger.info(f"No CloudCompile found. Will deploy to slot {slot_num} with bitstream.")
        
        # Resolve bitstream path (required)
        bitstream_path = args.bitstream
        logger.debug(f"Bitstream path (provided): {bitstream_path}")
        
        # Resolve relative paths
        if not bitstream_path.is_absolute():
            bitstream_path = PROJECT_ROOT / bitstream_path
            logger.debug(f"Resolved to absolute path: {bitstream_path}")
        
        if not bitstream_path.exists():
            logger.error(f"Bitstream file not found: {bitstream_path}")
            sys.exit(1)
        
        # Get CloudCompile instance
        try:
            cc = get_cloudcompile_instance(moku, slot_num, bitstream_path)
        except Exception as e:
            logger.error(f"Failed to get CloudCompile instance: {e}")
            sys.exit(1)
        
        # Load settings from file
        logger.info(f"Loading settings from {config_path.name}...")
        logger.debug(f"Config file absolute path: {config_path.absolute()}")
        try:
            logger.debug("Calling cc.load_settings()...")
            cc.load_settings(str(config_path))
            logger.success(f"Settings loaded successfully from {config_path.name}")
        except Exception as e:
            logger.error(f"Error loading settings: {e}")
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
        try:
            logger.debug("Disconnecting from device...")
            moku.relinquish_ownership()
            logger.success("Disconnected from device")
        except Exception as e:
            logger.debug(f"Error during disconnect: {e}")


if __name__ == "__main__":
    main()

