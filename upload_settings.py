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
except ImportError:
    logger.error("moku library not installed. Run: uv sync")
    sys.exit(1)

# Import shared CLI utilities
from moku_cli_common import handle_arg_parsing, connect_to_device, get_cloudcompile_instance

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




def validate_config_file(config_path: Path) -> Path:
    """Validate and resolve config file path."""
    logger.debug("Validating configuration file...")
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
    
    return config_path


def main():
    args, platform_id = handle_arg_parsing(
        description='Upload settings to Moku CloudCompile instrument',
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
        """,
        require_bitstream=True,
        add_verbose=True,
        additional_positional=[
            ('config_file', {'type': Path, 'help': 'Path to .mokuconf configuration file'})
        ]
    )
    
    # Setup logging based on verbosity (upload_settings has its own setup_logging)
    setup_logging(verbose=args.verbose)
    
    # Validate config file
    config_path = validate_config_file(args.config_file)
    
    # Connect to device
    logger.info(f"Connecting to {args.device_ip}...")
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
        logger.info(f"Accessing CloudCompile in slot {slot_num}...")
        try:
            cc = get_cloudcompile_instance(moku, slot_num, args.bitstream, require_bitstream=True)
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

