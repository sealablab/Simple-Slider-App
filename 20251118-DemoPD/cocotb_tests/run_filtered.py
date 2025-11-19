#!/usr/bin/env python3
"""
CocoTB Test Runner with GHDL Output Filtering

This is a drop-in replacement for run.py that pipes cocotb-test output
through the GHDL filter in real-time.

Usage:
    python run_filtered.py                  # Run P1 tests with filtered output
    COCOTB_VERBOSITY=NORMAL python run_filtered.py
    GHDL_FILTER=none python run_filtered.py  # Disable filtering
"""

import os
import sys
import subprocess
from pathlib import Path

# Ensure we're in the cocotb_tests directory
os.chdir(Path(__file__).parent)

# Import constants for HDL sources
from dpd_wrapper_tests.dpd_wrapper_constants import (
    HDL_SOURCES,
    HDL_TOPLEVEL,
    MODULE_NAME,
)

# Import GHDL filter
from ghdl_filter import GHDLOutputFilter, FilterLevel


def get_ghdl_filter_level():
    """
    Determine GHDL filter level based on COCOTB_VERBOSITY or explicit override.
    (Same logic as run.py)
    """
    # Explicit override takes precedence
    if "GHDL_FILTER" in os.environ:
        filter_str = os.environ["GHDL_FILTER"].lower()
        if filter_str == "aggressive":
            return FilterLevel.AGGRESSIVE
        elif filter_str == "normal":
            return FilterLevel.NORMAL
        elif filter_str == "minimal":
            return FilterLevel.MINIMAL
        elif filter_str == "none":
            return FilterLevel.NONE
        else:
            print(f"⚠️  Warning: Unknown GHDL_FILTER='{filter_str}', using 'normal'")
            return FilterLevel.NORMAL

    # Auto-select based on COCOTB_VERBOSITY
    verbosity = os.environ.get("COCOTB_VERBOSITY", "MINIMAL").upper()

    if verbosity == "MINIMAL":
        return FilterLevel.AGGRESSIVE
    elif verbosity == "NORMAL":
        return FilterLevel.NORMAL
    elif verbosity == "VERBOSE":
        return FilterLevel.MINIMAL
    elif verbosity == "DEBUG":
        return FilterLevel.NONE
    else:
        return FilterLevel.NORMAL


def main():
    """Run CocoTB tests with real-time output filtering"""

    # Set environment variables for CocoTB
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")
    os.environ.setdefault("COCOTB_VERBOSITY", os.environ.get("COCOTB_VERBOSITY", "MINIMAL"))
    os.environ.setdefault("TEST_LEVEL", os.environ.get("TEST_LEVEL", "P1_BASIC"))

    # Simulator configuration
    sim = os.environ.get("SIM", "ghdl")

    # GHDL output filter configuration
    filter_level = get_ghdl_filter_level()

    print(f"=" * 70)
    print(f"Running {MODULE_NAME} tests")
    print(f"=" * 70)
    print(f"Simulator: {sim}")
    print(f"Top-level: {HDL_TOPLEVEL}")
    print(f"Test Level: {os.environ['TEST_LEVEL']}")
    print(f"Verbosity: {os.environ['COCOTB_VERBOSITY']}")
    print(f"GHDL Filter: {filter_level.value}")
    print(f"Sources: {len(HDL_SOURCES)} VHDL files")
    print(f"=" * 70)

    # Check that all source files exist
    missing_sources = [str(src) for src in HDL_SOURCES if not src.exists()]
    if missing_sources:
        print(f"\n❌ ERROR: Missing source files:")
        for src in missing_sources:
            print(f"  - {src}")
        sys.exit(1)

    try:
        # Build cocotb-test command
        cmd = [
            sys.executable, "-m", "cocotb_test.simulator",
            "--compile-args", "--std=08",
            "--simulator", sim,
            "--toplevel", HDL_TOPLEVEL,
            "--toplevel-lang", "vhdl",
            "--module", "dpd_wrapper_tests.P1_dpd_wrapper_basic",
            "--waves", "0",  # Disable waveforms
        ]

        # Add VHDL sources
        for src in HDL_SOURCES:
            cmd.extend(["--vhdl-sources", str(src)])

        # Run cocotb-test with filtered output
        if filter_level == FilterLevel.NONE:
            # No filtering - direct execution
            result = subprocess.run(cmd, check=False)
            exit_code = result.returncode
        else:
            # Run with real-time filtering
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,  # Line buffered
                universal_newlines=True
            )

            # Create filter and process output in real-time
            ghdl_filter = GHDLOutputFilter(level=filter_level)

            try:
                for line in proc.stdout:
                    ghdl_filter.stats.total_lines += 1

                    if not ghdl_filter.should_filter(line.rstrip('\n')):
                        sys.stdout.write(line)
                        sys.stdout.flush()
                    else:
                        ghdl_filter.stats.filtered_lines += 1
            except KeyboardInterrupt:
                proc.terminate()
                sys.exit(130)

            # Wait for process to complete
            exit_code = proc.wait()

            # Print filter summary
            if ghdl_filter.stats.filtered_lines > 0:
                ghdl_filter.print_summary(sys.stdout)

        if exit_code == 0:
            print(f"\n✅ Tests completed successfully!")
        else:
            print(f"\n❌ Tests failed with exit code {exit_code}")

        sys.exit(exit_code)

    except ImportError:
        print("\n❌ ERROR: cocotb-test not installed")
        print("Install with: pip install cocotb-test")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
