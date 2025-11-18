"""
Clock cycle conversion utilities for Moku FPGA timing calculations.

Converts time values (seconds, microseconds, nanoseconds) to clock cycles
for use in FPGA register configurations.
"""

import math
from typing import Literal

# Default clock frequency for Moku Go (125 MHz)
DEFAULT_CLK_FREQ_HZ = 125_000_000

# Maximum value for 32-bit unsigned integer
MAX_32BIT = 2**32 - 1


class CycleCountOverflowError(ValueError):
    """Raised when a cycle count exceeds 32-bit unsigned integer range."""
    pass


def s_to_cycles(
    seconds: float,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ,
    round_direction: Literal["up", "down"] = "down"
) -> int:
    """
    Convert seconds to clock cycles.

    Args:
        seconds: Time in seconds
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)
        round_direction: "up" for ceiling, "down" for floor

    Returns:
        Number of clock cycles as integer

    Raises:
        CycleCountOverflowError: If result exceeds 32-bit unsigned integer range
    """
    cycles_float = seconds * clk_freq_hz

    if round_direction == "up":
        cycles = math.ceil(cycles_float)
    else:
        cycles = math.floor(cycles_float)

    if cycles > MAX_32BIT:
        raise CycleCountOverflowError(
            f"Cycle count {cycles} exceeds 32-bit range (max: {MAX_32BIT})"
        )

    if cycles < 0:
        raise ValueError(f"Negative cycle count {cycles} is invalid")

    return cycles


def us_to_cycles(
    microseconds: float,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ,
    round_direction: Literal["up", "down"] = "down"
) -> int:
    """
    Convert microseconds to clock cycles.

    Args:
        microseconds: Time in microseconds
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)
        round_direction: "up" for ceiling, "down" for floor

    Returns:
        Number of clock cycles as integer

    Raises:
        CycleCountOverflowError: If result exceeds 32-bit unsigned integer range
    """
    seconds = microseconds / 1_000_000
    return s_to_cycles(seconds, clk_freq_hz, round_direction)


def ns_to_cycles(
    nanoseconds: float,
    clk_freq_hz: int = DEFAULT_CLK_FREQ_HZ,
    round_direction: Literal["up", "down"] = "down"
) -> int:
    """
    Convert nanoseconds to clock cycles.

    Args:
        nanoseconds: Time in nanoseconds
        clk_freq_hz: Clock frequency in Hz (default: 125 MHz for Moku Go)
        round_direction: "up" for ceiling, "down" for floor

    Returns:
        Number of clock cycles as integer

    Raises:
        CycleCountOverflowError: If result exceeds 32-bit unsigned integer range
    """
    seconds = nanoseconds / 1_000_000_000
    return s_to_cycles(seconds, clk_freq_hz, round_direction)


if __name__ == "__main__":
    # Example usage
    print(f"Default clock frequency: {DEFAULT_CLK_FREQ_HZ / 1e6} MHz")
    print(f"\nExample conversions:")
    print(f"  1 second = {s_to_cycles(1)} cycles")
    print(f"  100 microseconds = {us_to_cycles(100)} cycles")
    print(f"  1000 nanoseconds = {ns_to_cycles(1000)} cycles")
    print(f"  1.5 nanoseconds (round down) = {ns_to_cycles(1.5, round_direction='down')} cycles")
    print(f"  1.5 nanoseconds (round up) = {ns_to_cycles(1.5, round_direction='up')} cycles")
