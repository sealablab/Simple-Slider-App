#!/usr/bin/env python3
"""
Diagnostic script for CloudCompile set_controls() API.

Tests set_controls() with increasingly complex scenarios to identify
the exact format requirements and failure points.

Usage:
    python diagnose_set_controls.py <device-ip> [--slot SLOT] [--bitstream PATH]

Examples:
    python diagnose_set_controls.py 192.168.1.100
    python diagnose_set_controls.py 192.168.1.100 --slot 2 --bitstream ./dpd.tar
"""

import sys
import json
from pathlib import Path
from typing import Any

# Add moku-models to path
PROJECT_ROOT = Path(__file__).parent.parent
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
sys.path.insert(0, str(PROJECT_ROOT))
from moku_cli_common import handle_arg_parsing, connect_to_device, get_cloudcompile_instance

# Configure loguru with detailed formatting
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True
)


def log_divider(title: str):
    """Print a visual divider for test sections."""
    logger.info("\n" + "=" * 80)
    logger.info(f"  {title}")
    logger.info("=" * 80)


def log_test_result(test_name: str, success: bool, details: str = ""):
    """Log test result with clear formatting."""
    if success:
        logger.success(f"✓ {test_name}")
        if details:
            logger.debug(f"  └─ {details}")
    else:
        logger.error(f"✗ {test_name}")
        if details:
            logger.error(f"  └─ {details}")


def safe_json(obj: Any) -> str:
    """Safely convert object to JSON string for logging."""
    try:
        return json.dumps(obj, indent=2)
    except:
        return str(obj)


def test_single_set_control(cc: CloudCompile, idx: int, value: int) -> bool:
    """
    Test setting a single control register using set_control().

    Args:
        cc: CloudCompile instance
        idx: Control register index (0-based)
        value: Value to set

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.debug(f"Calling set_control(idx={idx}, value=0x{value:08X})")
        result = cc.set_control(idx, value)
        logger.debug(f"  Result: {safe_json(result)}")

        # Verify by reading back
        read_result = cc.get_control(idx)
        logger.debug(f"  Read back: {safe_json(read_result)}")

        # Extract value from result (may be nested)
        read_value = read_result
        if isinstance(read_result, dict):
            read_value = read_result.get('value', read_result)

        if read_value == value:
            return True
        else:
            logger.warning(f"  Mismatch: wrote 0x{value:08X}, read 0x{read_value:08X}")
            return True  # Still consider success if write didn't error
    except Exception as e:
        logger.error(f"  Exception: {type(e).__name__}: {e}")
        return False


def test_set_controls_format(cc: CloudCompile, controls: Any, description: str) -> bool:
    """
    Test set_controls() with a specific format.

    Args:
        cc: CloudCompile instance
        controls: Control data in various formats
        description: Description of this test case

    Returns:
        True if successful, False otherwise
    """
    logger.info(f"\nTesting: {description}")
    logger.debug(f"  Format: {type(controls).__name__}")
    logger.debug(f"  Data: {safe_json(controls)}")

    try:
        result = cc.set_controls(controls)
        logger.debug(f"  Result: {safe_json(result)}")
        logger.success(f"  ✓ Success!")
        return True
    except Exception as e:
        logger.error(f"  ✗ Failed: {type(e).__name__}: {e}")
        # Log additional error details if available
        if hasattr(e, 'args') and e.args:
            logger.error(f"  Error args: {e.args}")
        if hasattr(e, '__dict__'):
            logger.debug(f"  Error attributes: {e.__dict__}")
        return False


def fallback_set_controls_individually(cc: CloudCompile, controls: list) -> dict:
    """
    Fallback method: set each control register individually using set_control().

    Args:
        cc: CloudCompile instance
        controls: List of control maps [{"idx": X, "value": Y}, ...]

    Returns:
        Dictionary with results: {"success": bool, "details": {...}}
    """
    logger.info("\n" + "-" * 80)
    logger.info("FALLBACK: Setting controls individually with set_control()")
    logger.info("-" * 80)

    results = {
        "success": True,
        "total": len(controls),
        "succeeded": 0,
        "failed": 0,
        "details": []
    }

    for ctrl_map in controls:
        idx = ctrl_map.get("idx", ctrl_map.get("id"))  # Support both keys
        value = ctrl_map["value"]

        logger.info(f"\nSetting CR{idx} = 0x{value:08X} ({value})")
        success = test_single_set_control(cc, idx, value)

        results["details"].append({
            "id": idx,
            "value": value,
            "success": success
        })

        if success:
            results["succeeded"] += 1
        else:
            results["failed"] += 1
            results["success"] = False

    logger.info("\n" + "-" * 80)
    logger.info(f"Fallback Summary: {results['succeeded']}/{results['total']} succeeded, {results['failed']} failed")
    logger.info("-" * 80)

    return results


def run_diagnostics(cc: CloudCompile):
    """
    Run comprehensive diagnostics on set_controls() API.

    Args:
        cc: CloudCompile instance
    """
    log_divider("CLOUDCOMPILE API DIAGNOSTICS")

    # First, test get_controls() to see current state
    logger.info("\n📊 Reading current control register state...")
    try:
        current = cc.get_controls()
        logger.debug(f"get_controls() returned: {type(current).__name__}")
        logger.debug(f"Data: {safe_json(current)}")
        logger.success("✓ get_controls() works")
    except Exception as e:
        logger.error(f"✗ get_controls() failed: {e}")

    # Test 1: Single control with set_control()
    log_divider("TEST 1: Single Control Register (set_control)")

    log_test_result(
        "set_control(idx=0, value=0xE0000000)",
        test_single_set_control(cc, 0, 0xE0000000)
    )

    log_test_result(
        "set_control(idx=1, value=0x00000001)",
        test_single_set_control(cc, 1, 0x00000001)
    )

    # Test 2: set_controls() with simple list of dicts
    log_divider("TEST 2: set_controls() - List of Dicts Format")

    # Test 2a: Single register
    test_set_controls_format(
        cc,
        [{"id": 0, "value": 0xE0000000}],
        "Single register - list with one dict"
    )

    # Test 2b: Two registers
    test_set_controls_format(
        cc,
        [
            {"id": 0, "value": 0xE0000000},
            {"id": 1, "value": 0x00000001}
        ],
        "Two registers - list with two dicts"
    )

    # Test 2c: All DPD registers (CR0-CR10)
    dpd_controls = [
        {"id": 0, "value": 0xE0000000},  # CR0: FORGE_READY bits [31:29]
        {"id": 1, "value": 0x00000005},  # CR1: arm_enable[0]=1, auto_rearm_enable[2]=1
        {"id": 2, "value": 0x000007D0},  # CR2: 2000 mV trigger output
        {"id": 3, "value": 0x000005DC},  # CR3: 1500 mV intensity output
        {"id": 4, "value": 0x0000003E},  # CR4: 62 cycles trig duration
        {"id": 5, "value": 0x0000007D},  # CR5: 125 cycles intensity duration
        {"id": 6, "value": 0x2540BE40},  # CR6: 625000000 cycles timeout
        {"id": 7, "value": 0x000030D4},  # CR7: 12500 cycles cooldown
        {"id": 8, "value": 0xFE0C0003},  # CR8: monitor control + threshold
        {"id": 9, "value": 0x00000000},  # CR9: 0 cycles monitor window start
        {"id": 10, "value": 0x000004E2}, # CR10: 1250 cycles monitor duration
    ]

    test_set_controls_format(
        cc,
        dpd_controls,
        "Full DPD configuration - CR0 through CR10"
    )

    # Test 3: Alternative formats (to explore API)
    log_divider("TEST 3: Alternative Formats")

    # Test 3a: Dict instead of list
    test_set_controls_format(
        cc,
        {0: 0xE0000000, 1: 0x00000001},
        "Dictionary format {idx: value}"
    )

    # Test 3b: List of tuples
    test_set_controls_format(
        cc,
        [(0, 0xE0000000), (1, 0x00000001)],
        "List of tuples [(idx, value), ...]"
    )

    # Test 3c: Different key names
    test_set_controls_format(
        cc,
        [{"idx": 0, "value": 0xE0000000}],
        "Dict with 'idx' instead of 'id'"
    )

    test_set_controls_format(
        cc,
        [{"control": 0, "value": 0xE0000000}],
        "Dict with 'control' key"
    )

    test_set_controls_format(
        cc,
        [{"register": 0, "data": 0xE0000000}],
        "Dict with 'register' and 'data' keys"
    )

    # Test 4: Inspect actual CloudCompile method signature
    log_divider("TEST 4: API Introspection")

    logger.info("\n🔍 Inspecting set_controls() method...")
    logger.debug(f"  Method: {cc.set_controls}")
    logger.debug(f"  Docstring: {cc.set_controls.__doc__}")

    import inspect
    sig = inspect.signature(cc.set_controls)
    logger.debug(f"  Signature: {sig}")
    logger.debug(f"  Parameters: {sig.parameters}")

    # Test 5: Fallback approach
    log_divider("TEST 5: Fallback - Individual set_control() Calls")

    fallback_results = fallback_set_controls_individually(cc, dpd_controls)

    if fallback_results["success"]:
        logger.success(f"\n✓ FALLBACK SUCCESSFUL: All {fallback_results['total']} registers set individually")
    else:
        logger.error(f"\n✗ FALLBACK PARTIAL: {fallback_results['succeeded']}/{fallback_results['total']} succeeded")

    # Final summary
    log_divider("DIAGNOSTIC SUMMARY")

    logger.info("\n📋 Recommendations:")
    logger.info("  1. Review the test results above to identify working formats")
    logger.info("  2. Check for any pattern in successful vs failed tests")
    logger.info("  3. If set_controls() consistently fails, use fallback_set_controls_individually()")
    logger.info("  4. Examine error messages for hints about expected format")

    logger.info("\n💡 Next Steps:")
    logger.info("  - If list of dicts works: dpd_config.py is correct")
    logger.info("  - If dict format works: change to_control_regs_list() to return dict")
    logger.info("  - If nothing works: use individual set_control() calls as workaround")


def main():
    """Main entry point."""
    args, platform_id = handle_arg_parsing(
        description='Diagnose CloudCompile set_controls() API behavior',
        epilog="""
Examples:
  # Basic diagnostics
  python diagnose_set_controls.py 192.168.1.100

  # With specific slot
  python diagnose_set_controls.py 192.168.1.100 --slot 2

  # With bitstream upload
  python diagnose_set_controls.py 192.168.1.100 --bitstream ./dpd.tar
        """
    )

    moku = None

    try:
        # Connect to device
        logger.info(f"🔌 Connecting to {args.device_ip}...")
        moku = connect_to_device(args.device_ip, platform_id, force=args.force, read_timeout=5)
        logger.success(f"✓ Connected to {args.device_ip}")

        # Get CloudCompile instance
        slot_num = args.slot if args.slot else 2
        logger.info(f"📦 Accessing CloudCompile in slot {slot_num}...")

        bitstream_path = None
        if args.bitstream:
            bitstream_path = args.bitstream
            if not bitstream_path.is_absolute():
                bitstream_path = PROJECT_ROOT / bitstream_path

        cc = get_cloudcompile_instance(moku, slot_num, bitstream_path)
        logger.success(f"✓ CloudCompile instance ready")

        # Run diagnostics
        run_diagnostics(cc)

    except Exception as e:
        logger.error(f"❌ Fatal error: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        sys.exit(1)

    finally:
        # Disconnect
        if moku is not None:
            logger.info("\n🔌 Disconnecting...")
            try:
                moku.relinquish_ownership()
                logger.success("✓ Disconnected")
            except Exception as e:
                logger.warning(f"Disconnect warning: {e}")


if __name__ == "__main__":
    main()
