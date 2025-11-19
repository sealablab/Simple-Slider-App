#!/usr/bin/env python3
"""
CocoTB Test Runner for Demo Probe Driver

Runs P1 (BASIC) tests with GHDL simulator with intelligent output filtering.

Usage:
    python run.py                    # Run P1 tests with minimal output
    COCOTB_VERBOSITY=NORMAL python run.py  # More verbose output
    TEST_LEVEL=P2_INTERMEDIATE python run.py  # Run P2 tests (when implemented)
    GHDL_FILTER=none python run.py   # Disable GHDL output filtering

Environment Variables:
    COCOTB_VERBOSITY: Test output level (MINIMAL, NORMAL, VERBOSE, DEBUG)
    TEST_LEVEL: Test suite level (P1_BASIC, P2_INTERMEDIATE, etc.)
    GHDL_FILTER: GHDL output filter level (aggressive, normal, minimal, none)
                 Default: auto-selected based on COCOTB_VERBOSITY

Author: Moku Instrument Forge Team
Date: 2025-11-18
"""

import os
import sys
from pathlib import Path

# Ensure we're in the cocotb_tests directory
os.chdir(Path(__file__).parent)

# Import constants for HDL sources
from dpd_wrapper_tests.dpd_wrapper_constants import (
    HDL_SOURCES,
    HDL_TOPLEVEL,
    MODULE_NAME,
)

# Import GHDL filter for output reduction
from ghdl_filter import FilterLevel


def get_ghdl_filter_level():
    """
    Determine GHDL filter level based on COCOTB_VERBOSITY or explicit override.

    Auto-mapping:
        COCOTB_VERBOSITY=MINIMAL  → GHDL_FILTER=aggressive (max reduction for LLM)
        COCOTB_VERBOSITY=NORMAL   → GHDL_FILTER=normal (balanced)
        COCOTB_VERBOSITY=VERBOSE  → GHDL_FILTER=minimal (light touch)
        COCOTB_VERBOSITY=DEBUG    → GHDL_FILTER=none (no filtering)

    Returns:
        FilterLevel enum value
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
        return FilterLevel.AGGRESSIVE  # Maximum reduction for P1 tests
    elif verbosity == "NORMAL":
        return FilterLevel.NORMAL
    elif verbosity == "VERBOSE":
        return FilterLevel.MINIMAL
    elif verbosity == "DEBUG":
        return FilterLevel.NONE  # No filtering for debug
    else:
        return FilterLevel.NORMAL  # Safe default


def main():
    """Run CocoTB tests using GHDL simulator"""

    # Set environment variables for CocoTB
    os.environ.setdefault("COCOTB_REDUCED_LOG_FMT", "1")  # Minimal logging
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
        from cocotb_test.simulator import run as cocotb_run

        # Configure GHDL filtering via environment variable
        # This will be picked up by the GHDL wrapper if we use sim_build hooks
        os.environ["GHDL_FILTER_LEVEL"] = filter_level.value

        # Run tests
        cocotb_run(
            vhdl_sources=[str(src) for src in HDL_SOURCES],
            toplevel=HDL_TOPLEVEL,  # GHDL lowercases this automatically
            toplevel_lang="vhdl",
            module="dpd_wrapper_tests.P1_dpd_wrapper_basic",
            simulator=sim,
            waves=False,  # Disable waveform dump for fast P1 tests
            extra_args=["--std=08"],  # VHDL-2008 standard
        )

        print(f"\n✅ Tests completed successfully!")

    except ImportError:
        print("\n❌ ERROR: cocotb-test not installed")
        print("Install with: pip install cocotb-test")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
