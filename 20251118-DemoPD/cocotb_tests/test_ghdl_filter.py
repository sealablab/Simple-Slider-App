#!/usr/bin/env python3
"""
Unit tests for GHDL output filter

Verifies filter behavior without running actual GHDL simulations.

Usage:
    python test_ghdl_filter.py
"""

import sys
from ghdl_filter import GHDLOutputFilter, FilterLevel


def test_metavalue_filtering():
    """Test that metavalue warnings are filtered"""
    filter = GHDLOutputFilter(level=FilterLevel.AGGRESSIVE)

    test_lines = [
        "  0.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0",
        "✓ Reset complete",
        "  8.00ns NUMERIC_STD.TO_UNSIGNED: metavalue detected, returning 0",
        "T1: Reset behavior",
        "  ✓ PASS",
    ]

    filtered = filter.filter_lines(test_lines)

    # Should only have 3 lines (filtered out 2 metavalue warnings)
    assert len(filtered) == 3, f"Expected 3 lines, got {len(filtered)}: {filtered}"
    assert "✓ Reset complete" in filtered
    assert "T1: Reset behavior" in filtered
    assert "  ✓ PASS" in filtered

    # Check stats
    assert filter.stats.metavalue_warnings == 2, f"Expected 2 metavalue warnings, got {filter.stats.metavalue_warnings}"
    assert filter.stats.filtered_lines == 2, f"Expected 2 filtered lines, got {filter.stats.filtered_lines}"

    print("✓ test_metavalue_filtering PASSED")


def test_preserve_patterns():
    """Test that important messages are always preserved"""
    filter = GHDLOutputFilter(level=FilterLevel.AGGRESSIVE)

    test_lines = [
        "ERROR: Something went wrong",
        "  0.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0",
        "FAIL: Test failed",
        "PASS: Test passed",
        "assertion error at line 42",
        "  8.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0",
    ]

    filtered = filter.filter_lines(test_lines)

    # Should preserve all important messages (4 lines), filter metavalue (2 lines)
    assert len(filtered) == 4, f"Expected 4 lines, got {len(filtered)}"
    assert "ERROR: Something went wrong" in filtered
    assert "FAIL: Test failed" in filtered
    assert "PASS: Test passed" in filtered
    assert "assertion error at line 42" in filtered

    print("✓ test_preserve_patterns PASSED")


def test_duplicate_filtering():
    """Test that duplicate warnings are filtered"""
    filter = GHDLOutputFilter(level=FilterLevel.NORMAL)

    test_lines = [
        "  0.00ns dpd.vhd:123:45: (assertion warning): NUMERIC_STD.TO_INTEGER: metavalue detected",
        "  8.00ns dpd.vhd:123:45: (assertion warning): NUMERIC_STD.TO_INTEGER: metavalue detected",
        "  16.00ns dpd.vhd:123:45: (assertion warning): NUMERIC_STD.TO_INTEGER: metavalue detected",
        "✓ Test complete",
    ]

    filtered = filter.filter_lines(test_lines)

    # All three warnings should be filtered (metavalue pattern matches)
    # Only test complete message remains
    assert len(filtered) == 1, f"Expected 1 line, got {len(filtered)}"
    assert "✓ Test complete" in filtered

    print("✓ test_duplicate_filtering PASSED")


def test_filter_levels():
    """Test different filter levels"""

    test_line = "  0.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0"

    # NONE - should not filter
    filter_none = GHDLOutputFilter(level=FilterLevel.NONE)
    assert filter_none.should_filter(test_line) == False

    # MINIMAL - should filter (metavalue)
    filter_minimal = GHDLOutputFilter(level=FilterLevel.MINIMAL)
    assert filter_minimal.should_filter(test_line) == False  # First occurrence
    assert filter_minimal.should_filter(test_line) == True   # Second occurrence (duplicate)

    # NORMAL - should filter
    filter_normal = GHDLOutputFilter(level=FilterLevel.NORMAL)
    assert filter_normal.should_filter(test_line) == True

    # AGGRESSIVE - should filter
    filter_aggressive = GHDLOutputFilter(level=FilterLevel.AGGRESSIVE)
    assert filter_aggressive.should_filter(test_line) == True

    print("✓ test_filter_levels PASSED")


def test_warning_normalization():
    """Test that warnings are normalized for deduplication"""
    filter = GHDLOutputFilter(level=FilterLevel.NORMAL)

    # Same warning at different times and line numbers
    line1 = "  0.00ns dpd.vhd:100:20: (assertion warning): Signal not initialized"
    line2 = "  8.00ns dpd.vhd:100:20: (assertion warning): Signal not initialized"
    line3 = "  16.00ns dpd.vhd:105:30: (assertion warning): Signal not initialized"

    norm1 = filter.normalize_warning(line1)
    norm2 = filter.normalize_warning(line2)
    norm3 = filter.normalize_warning(line3)

    # All should normalize to the same string (timestamps and line numbers removed)
    assert norm1 == norm2, f"Different normalization:\n  '{norm1}'\n  '{norm2}'"
    assert norm1 == norm3, f"Different normalization:\n  '{norm1}'\n  '{norm3}'"

    print("✓ test_warning_normalization PASSED")


def test_statistics():
    """Test that statistics are tracked correctly"""
    filter = GHDLOutputFilter(level=FilterLevel.AGGRESSIVE)

    test_lines = [
        "  0.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0",
        "  0.00ns NUMERIC_STD.TO_UNSIGNED: null argument detected, returning 0",
        "✓ Test passed",
        "  8.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0",
    ]

    filtered = filter.filter_lines(test_lines)

    # Should filter 3 lines (2 metavalue, 1 null), keep 1 line (test passed)
    assert filter.stats.total_lines == 4, f"Expected 4 total lines, got {filter.stats.total_lines}"
    assert filter.stats.filtered_lines == 3, f"Expected 3 filtered lines, got {filter.stats.filtered_lines}"
    assert filter.stats.metavalue_warnings == 2, f"Expected 2 metavalue, got {filter.stats.metavalue_warnings}"
    assert filter.stats.null_warnings == 1, f"Expected 1 null, got {filter.stats.null_warnings}"
    assert len(filtered) == 1, f"Expected 1 output line, got {len(filtered)}"
    assert "✓ Test passed" in filtered

    print("✓ test_statistics PASSED")


def run_all_tests():
    """Run all unit tests"""
    print("Running GHDL Filter Unit Tests...")
    print("=" * 60)

    try:
        test_metavalue_filtering()
        test_preserve_patterns()
        test_duplicate_filtering()
        test_filter_levels()
        test_warning_normalization()
        test_statistics()

        print("=" * 60)
        print("✅ All tests PASSED")
        return 0

    except AssertionError as e:
        print("=" * 60)
        print(f"❌ Test FAILED: {e}")
        return 1
    except Exception as e:
        print("=" * 60)
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
