"""
Common CLI argument parsing utilities for Moku device scripts.

Provides shared argument parsing functionality to reduce code duplication
across scripts.
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

try:
    from loguru import logger
except ImportError:
    print("Error: loguru not installed. Run: uv sync")
    sys.exit(1)

try:
    from moku import logging as moku_logging
except ImportError:
    # moku_logging is optional - scripts can handle this
    moku_logging = None


# Platform name to ID mapping
PLATFORM_MAP = {
    'moku_go': 2,
    'moku_lab': 1,
    'moku_pro': 3,
    'moku_delta': 4,
}


def add_common_args(parser: argparse.ArgumentParser, 
                     require_bitstream: bool = False,
                     default_slot: Optional[int] = None,
                     add_verbose: bool = False) -> None:
    """
    Add common Moku device arguments to an ArgumentParser.
    
    Args:
        parser: ArgumentParser instance to add arguments to
        require_bitstream: If True, --bitstream is required; otherwise optional
        default_slot: Default value for --slot (None means no default)
        add_verbose: If True, add --verbose/-v flag for loguru verbosity
    """
    parser.add_argument('device_ip', help='Moku device IP address')
    
    slot_kwargs = {'type': int, 'help': 'Slot number containing CloudCompile (auto-detected if not specified)'}
    if default_slot is not None:
        slot_kwargs['default'] = default_slot
        slot_kwargs['help'] = f'Slot number containing CloudCompile (default: {default_slot})'
    parser.add_argument('--slot', **slot_kwargs)
    
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
    
    bitstream_kwargs = {
        'type': Path,
        'help': 'Path to bitstream file (.tar) to upload to CloudCompile'
    }
    if require_bitstream:
        bitstream_kwargs['required'] = True
        bitstream_kwargs['help'] = 'Path to bitstream file (.tar) - REQUIRED: CloudCompile always needs a bitstream, even for existing instances'
    parser.add_argument('--bitstream', **bitstream_kwargs)
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging for Moku library'
    )
    
    if add_verbose:
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose/debug logging output'
        )


def parse_platform_id(args) -> Optional[int]:
    """Map platform name from args to platform ID."""
    if args.platform:
        return PLATFORM_MAP.get(args.platform)
    return None


def setup_moku_debug_logging(args) -> None:
    """Enable Moku debug logging if --debug flag is set."""
    if args.debug and moku_logging:
        moku_logging.enable_debug_logging()
        logger.info("Moku debug logging enabled")


def handle_arg_parsing(
    description: str,
    epilog: Optional[str] = None,
    require_bitstream: bool = False,
    default_slot: Optional[int] = None,
    add_verbose: bool = False,
    additional_positional: Optional[list] = None,
    additional_optional: Optional[list] = None
):
    """
    Parse command line arguments with common Moku device options.
    
    Args:
        description: Description for ArgumentParser
        epilog: Optional epilog text (examples, etc.)
        require_bitstream: If True, --bitstream is required
        default_slot: Default value for --slot
        add_verbose: If True, add --verbose/-v flag
        additional_positional: List of (name, kwargs) tuples for additional positional args
        additional_optional: List of (name, kwargs) tuples for additional optional args
    
    Returns:
        Tuple of (args, platform_id) where platform_id is None or int
    """
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=epilog
    )
    
    # Add common arguments
    add_common_args(parser, require_bitstream, default_slot, add_verbose)
    
    # Add additional positional arguments
    if additional_positional:
        for name, kwargs in additional_positional:
            parser.add_argument(name, **kwargs)
    
    # Add additional optional arguments
    if additional_optional:
        for name, kwargs in additional_optional:
            parser.add_argument(name, **kwargs)
    
    args = parser.parse_args()
    
    # Setup Moku debug logging
    setup_moku_debug_logging(args)
    
    # Map platform name to ID
    platform_id = parse_platform_id(args)
    
    return args, platform_id

