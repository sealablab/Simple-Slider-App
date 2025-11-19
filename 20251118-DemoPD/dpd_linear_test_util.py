#!/usr/bin/env python3
"""
DPD Linear Test - Sequential configuration test for Demo Probe Driver.

Connects to a Moku device and applies 10 different DPDConfig instances sequentially
with varying parameters and detailed timing introspection.

Varying parameters (10 iterations):
- trig_out_voltage: 2.4V → 3.5V (linear steps)
- trig_out_duration: 64ns + 2 cycles per iteration
- intensity_voltage: 0.5V → 3.0V (linear steps)

Usage:
    python dpd_linear_test_util.py <device-ip> [--slot SLOT] [--platform PLATFORM] [--bitstream PATH]

Examples:
    python dpd_linear_test_util.py 192.168.1.100
    python dpd_linear_test_util.py 192.168.1.100 --slot 1
    python dpd_linear_test_util.py 192.168.1.100 --platform moku_go
"""

import sys
import time
import threading
from pathlib import Path

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

# Add parent directory to path for imports
DPD_DIR = Path(__file__).parent
sys.path.insert(0, str(DPD_DIR))

# Import DPD utilities
try:
    from dpd_config import DPDConfig
    from clk_utils import ns_to_cycles, cycles_to_ns
except ImportError as e:
    logger.error(f"Failed to import DPD utilities: {e}")
    logger.error("Ensure dpd_config.py and clk_utils.py are in the same directory")
    sys.exit(1)

# Import shared CLI utilities
sys.path.insert(0, str(PROJECT_ROOT))
from moku_cli_common import handle_arg_parsing, connect_to_device, get_cloudcompile_instance, time_operation

# Configure loguru with nice formatting
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)


def voltage_mv(volts: float) -> int:
    """Convert volts to millivolts (mV)."""
    return int(volts * 1000)


def extra_sanity_checking(moku: MultiInstrument, args, platform_id: int | None,
                          total_start: float) -> CloudCompile:
    """
    Get CloudCompile instance with minimal validation (skips expensive checks).

    This function skips expensive sanity checking but still provides a CloudCompile
    instance needed for operations. Uses args directly without validation.

    Args:
        moku: Connected MultiInstrument instance
        args: Parsed command line arguments
        platform_id: Platform ID (if specified) - unused but kept for compatibility
        total_start: Start time for overall timing - unused but kept for compatibility

    Returns:
        CloudCompile instance
    """
    # Skip expensive validation - just use args directly
    slot_num = args.slot if args.slot else 2  # Default to slot 2 if not specified

    # Resolve bitstream path if provided (minimal - no existence check)
    bitstream_path = None
    if args.bitstream:
        bitstream_path = args.bitstream
        # Resolve relative paths only
        if not bitstream_path.is_absolute():
            bitstream_path = PROJECT_ROOT / bitstream_path

    # Get CloudCompile instance (skip expensive validation)
    logger.info(f"Accessing CloudCompile in slot {slot_num}...")
    try:
        cc = get_cloudcompile_instance(moku, slot_num, bitstream_path)
        logger.success("CloudCompile instance ready")
        return cc
    except Exception as e:
        logger.error(f"Failed to get CloudCompile instance: {e}")
        sys.exit(1)


def set_controls_with_timeout(cc: CloudCompile, config: DPDConfig, iteration: int, timeout: float = 1.0) -> None:
    """
    Set DPD controls with timeout and detailed timing breakdown.

    Args:
        cc: CloudCompile instance
        config: DPDConfig instance to apply
        iteration: Iteration number (for logging)
        timeout: Timeout in seconds (default: 1.0)

    Raises:
        TimeoutError: If the operation exceeds the timeout
        Exception: Any other exception from set_controls
    """
    logger.info(f"\n{'='*60}")
    logger.info(f"Iteration {iteration}: Applying DPDConfig")
    logger.info(f"{'='*60}")
    logger.info(f"  trig_out_voltage:   {config.trig_out_voltage} mV ({config.trig_out_voltage/1000:.2f}V)")
    logger.info(f"  trig_out_duration:  {cycles_to_ns(config.trig_out_duration):.1f} ns ({config.trig_out_duration} cycles)")
    logger.info(f"  intensity_voltage:  {config.intensity_voltage} mV ({config.intensity_voltage/1000:.2f}V)")
    logger.info(f"  intensity_duration: {cycles_to_ns(config.intensity_duration):.1f} ns ({config.intensity_duration} cycles)")

    # Use threading to implement timeout
    result = [None]  # Use list to allow modification from nested function
    exception = [None]

    def set_controls_thread():
        """Run set_controls in a separate thread."""
        try:
            regs_dict = config.to_control_regs_dict()
            result[0] = cc.set_controls(regs_dict)
        except Exception as e:
            exception[0] = e

    # Start the thread
    thread = threading.Thread(target=set_controls_thread)
    thread.daemon = True
    start = time.perf_counter()
    thread.start()
    thread.join(timeout=timeout)

    elapsed = time.perf_counter() - start

    # Check if thread is still alive (timed out)
    if thread.is_alive():
        logger.warning(f"  set_controls() TIMED OUT after {elapsed*1000:.2f} ms (timeout: {timeout*1000:.0f} ms)")
        logger.warning(f"  ⚠️  This may indicate a device/firmware issue. The operation may have succeeded despite the timeout.")
        raise TimeoutError(f"set_controls() timed out after {timeout}s")

    # Check for exceptions
    if exception[0] is not None:
        error_msg = str(exception[0])
        if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
            logger.warning(f"  set_controls() TIMED OUT after {elapsed*1000:.2f} ms")
            logger.warning(f"  ⚠️  This may indicate a device/firmware issue. The operation may have succeeded despite the timeout.")
            logger.warning(f"  Error details: {error_msg}")
        else:
            logger.error(f"  set_controls() FAILED after {elapsed*1000:.2f} ms: {exception[0]}")
        raise exception[0]

    # Success
    logger.success(f"  set_controls() completed: {elapsed*1000:.2f} ms")


def generate_dpd_configs(num_iterations: int = 10) -> list[DPDConfig]:
    """
    Generate list of DPDConfig instances with linearly varying parameters.

    Varying parameters:
    - trig_out_voltage: 2.4V → 3.5V (linear)
    - trig_out_duration: 64ns + 2 cycles per iteration
    - intensity_voltage: 0.5V → 3.0V (linear)

    Fixed parameters:
    - arm_enable = True
    - auto_rearm_enable = True
    - All other parameters at defaults

    Args:
        num_iterations: Number of configurations to generate (default: 10)

    Returns:
        List of DPDConfig instances
    """
    configs = []

    # Define linear ranges
    trig_voltage_start_v = 2.4
    trig_voltage_end_v = 3.5

    intensity_voltage_start_v = 0.5
    intensity_voltage_end_v = 3.0

    trig_duration_start_ns = 64.0
    trig_duration_cycles_per_iter = 2  # Add 2 cycles per iteration

    for i in range(num_iterations):
        # Calculate linear interpolation factor (0.0 to 1.0)
        t = i / (num_iterations - 1) if num_iterations > 1 else 0.0

        # Calculate trig_out_voltage (linear: 2.4V → 3.5V)
        trig_voltage_v = trig_voltage_start_v + t * (trig_voltage_end_v - trig_voltage_start_v)
        trig_voltage_mv = voltage_mv(trig_voltage_v)

        # Calculate trig_out_duration (64ns + 2 cycles per iteration)
        trig_duration_cycles = ns_to_cycles(trig_duration_start_ns) + (i * trig_duration_cycles_per_iter)

        # Calculate intensity_voltage (linear: 0.5V → 3.0V)
        intensity_voltage_v = intensity_voltage_start_v + t * (intensity_voltage_end_v - intensity_voltage_start_v)
        intensity_voltage_mv = voltage_mv(intensity_voltage_v)

        # Create config with varying parameters
        config = DPDConfig(
            arm_enable=True,
            auto_rearm_enable=True,
            trig_out_voltage=trig_voltage_mv,
            trig_out_duration=trig_duration_cycles,
            intensity_voltage=intensity_voltage_mv,
            # intensity_duration uses default
            # All other parameters use defaults
        )

        configs.append(config)

    return configs


def main():
    args, platform_id = handle_arg_parsing(
        description='DPD Linear Test - Sequential DPDConfig application with timing introspection',
        epilog="""
Examples:
  # Auto-detect platform and slot
  python dpd_linear_test_util.py 192.168.1.100

  # Specify slot
  python dpd_linear_test_util.py 192.168.1.100 --slot 1

  # Specify platform
  python dpd_linear_test_util.py 192.168.1.100 --platform moku_go

  # Upload bitstream and test
  python dpd_linear_test_util.py 192.168.1.100 --bitstream ./dpd_bitstream.tar

  # Force connect (disconnect existing connections)
  python dpd_linear_test_util.py 192.168.1.100 --force
        """
    )

    # Overall timing
    total_start = time.perf_counter()

    # Initialize moku to None to handle cleanup in finally block
    moku = None

    # Connect to device
    logger.info(f"Connecting to {args.device_ip}...")
    try:
        with time_operation("Device connection"):
            moku = connect_to_device(args.device_ip, platform_id, force=args.force, read_timeout=5)
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(1)

    # Get CloudCompile instance (skips expensive sanity checking)
    cc = extra_sanity_checking(moku, args, platform_id, total_start)

    # Generate 10 DPDConfig instances
    logger.info("\n" + "="*60)
    logger.info("GENERATING DPD CONFIGURATIONS")
    logger.info("="*60)
    configs = generate_dpd_configs(num_iterations=10)
    logger.info(f"Generated {len(configs)} DPDConfig instances")

    # Apply configurations sequentially
    logger.info("\n" + "="*60)
    logger.info("TIMING INTROSPECTION - DPD set_controls() Operations")
    logger.info("="*60)

    successful_iterations = 0
    failed_iterations = 0

    for i, config in enumerate(configs, start=1):
        try:
            set_controls_with_timeout(cc, config, iteration=i, timeout=0.4)
            successful_iterations += 1
            time.sleep(0.2)  # Brief pause between iterations
        except Exception as e:
            error_msg = str(e)
            if "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                logger.warning(f"  ⚠️  Continuing despite timeout...")
                failed_iterations += 1
            else:
                # Re-raise non-timeout exceptions
                logger.error(f"  ❌ Fatal error on iteration {i}")
                raise

    # Summary
    total_elapsed = time.perf_counter() - total_start
    logger.info("\n" + "="*60)
    logger.info("SUMMARY")
    logger.info("="*60)
    logger.info(f"Total execution time: {total_elapsed:.3f} s ({total_elapsed*1000:.2f} ms)")
    logger.info(f"Successful iterations: {successful_iterations}/{len(configs)}")
    if failed_iterations > 0:
        logger.warning(f"Failed/timeout iterations: {failed_iterations}/{len(configs)}")
    logger.info(f"\nParameter ranges:")
    logger.info(f"  trig_out_voltage:   2.4V → 3.5V")
    logger.info(f"  trig_out_duration:  64ns + 2 cycles/iter")
    logger.info(f"  intensity_voltage:  0.5V → 3.0V")

    # Disconnect
    if moku is not None:
        logger.info("\nDisconnecting...")
        with time_operation("Disconnect (relinquish_ownership)"):
            try:
                moku.relinquish_ownership()
                logger.success("Disconnected")
            except Exception as e:
                logger.warning(f"Disconnect warning: {e}")


if __name__ == "__main__":
    main()
