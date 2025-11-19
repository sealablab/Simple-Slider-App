# Demo Probe Driver (DPD) - Hardware Progressive Tests

> Real hardware validation using Moku oscilloscope to observe FSM state transitions via OutputC (HVS encoding).

---

## Quick Start

### Prerequisites

- Moku device with:
  - **Slot 1:** Oscilloscope (deployed)
  - **Slot 2:** CloudCompile with DPD bitstream (deployed)
- Python 3.10+ with Moku API (`uv sync`)
- Network connection to Moku device

### Running P1 (BASIC) Tests

```bash
# From SimpleSliderApp root (recommended)
cd /path/to/SimpleSliderApp
uv run python3 ./20251118-DemoPD/hardware_progressive_tests/run_hw_tests.py 192.168.8.98

# Or from hardware_progressive_tests directory
cd 20251118-DemoPD/hardware_progressive_tests
uv run python3 run_hw_tests.py 192.168.8.98

# Run with verbose output
uv run python3 run_hw_tests.py 192.168.8.98 --verbose

# Specify slots explicitly (if different from defaults)
uv run python3 run_hw_tests.py 192.168.8.98 --osc-slot 1 --cc-slot 2
```

**Note:** Use `uv run` to ensure the correct Python environment with all dependencies.

**Expected output (MINIMAL verbosity):**
```
======================================================================
DPD Hardware Progressive Tests
======================================================================
Device: 192.168.8.98
Test Level: P1_BASIC
Verbosity: MINIMAL
Oscilloscope Slot: 1
CloudCompile Slot: 2
======================================================================

P1 - BASIC TESTS
T1: Routing validation
  ✓ PASS
T2: FORGE initialization
  ✓ PASS
T3: Reset to IDLE
  ✓ PASS
T4: FORGE control scheme
  ✓ PASS
T5: FSM software trigger
  ✓ PASS
T6: FSM complete cycle
  ✓ PASS
ALL 6 TESTS PASSED

✅ ALL TESTS PASSED
```

---

## Test Levels

### P1 - BASIC (Implemented)

**Purpose:** Fast smoke tests, essential functionality

**Tests:**
1. **Routing validation** - Verify OutputC → OscInA connection
2. **FORGE initialization** - Set CR0[31:29] control bits
3. **Reset to IDLE** - Clear all registers, verify IDLE state
4. **FORGE control scheme** - Test partial vs complete enable
5. **FSM software trigger** - Trigger via CR1[1], verify state change
6. **FSM complete cycle** - Verify full IDLE → ARMED → FIRING → COOLDOWN → IDLE

**Runtime:** <2 minutes

```bash
python run_hw_tests.py 192.168.8.98
```

### P2 - INTERMEDIATE (Stub Only)

**Purpose:** Comprehensive validation with edge cases

**Planned Tests:**
- Auto-rearm functionality (COOLDOWN → ARMED loop)
- Fault state injection and recovery
- Hardware trigger via InputA (manual test)
- Edge case timing values
- Output pulse voltage verification

**Runtime:** <5 minutes (when implemented)

```bash
python run_hw_tests.py 192.168.8.98 --level P2
```

### P3 - COMPREHENSIVE (Stub Only)

**Purpose:** Stress testing and corner cases

**Planned Tests:**
- Rapid trigger cycles (100+ back-to-back)
- Concurrent trigger sources (software + hardware)
- Register changes during FSM operation
- Long-duration stress tests (1000+ cycles)

**Runtime:** <15 minutes (when implemented)

```bash
python run_hw_tests.py 192.168.8.98 --level P3
```

---

## Architecture

### File Structure

```
hardware_progressive_tests/
├── __init__.py                 # Package initialization
├── hw_test_constants.py        # Timing configs, state mappings
├── hw_test_helpers.py          # FSM control, state reading utilities
├── hw_test_base.py             # HardwareTestBase class (like TestBase)
├── P1_hw_basic.py              # P1 test suite (implemented)
├── P2_hw_intermediate.py       # P2 test suite (stub)
├── P3_hw_comprehensive.py      # P3 test suite (stub)
├── run_hw_tests.py             # Test runner (executable)
└── README.md                   # This file
```

### Key Components

#### `hw_test_constants.py`

Defines timing configurations and state mappings:

```python
# FSM State Voltage Map (HVS encoding on OutputC)
STATE_VOLTAGE_MAP = {
    "IDLE": 0.0,        # 0V
    "ARMED": 0.5,       # 0.5V
    "FIRING": 1.0,      # 1.0V
    "COOLDOWN": 1.5,    # 1.5V
    "FAULT": -0.5,      # Negative voltage
}

# P2 Timing (used for hardware tests - observable on oscilloscope)
P2TestValues.TRIG_OUT_DURATION_US = 100    # 100μs
P2TestValues.INTENSITY_DURATION_US = 200   # 200μs
P2TestValues.COOLDOWN_INTERVAL_US = 10     # 10μs
```

**Why P2 timing?** P1 CocoTB timing (8-16μs) is too fast for reliable oscilloscope polling. P2 timing (~310μs total) is human-observable.

#### `hw_test_helpers.py`

Utilities for FSM control and state observation:

```python
# Read FSM state from oscilloscope
state, voltage = read_fsm_state(osc, poll_count=5)

# Wait for state transition (with timeout)
success = wait_for_state(osc, "ARMED", timeout_ms=1000)

# FSM control
init_forge_ready(mcc)  # Set CR0[31:29] = 0b111
arm_probe(mcc, trig_duration_us=100, intensity_duration_us=200, cooldown_us=10)
software_trigger(mcc)  # Pulse CR1[1]
reset_fsm_to_idle(mcc, osc)

# Routing validation
is_valid = validate_routing(moku, osc_slot=1, cc_slot=2)
setup_routing(moku, osc_slot=1, cc_slot=2)
```

#### `hw_test_base.py`

Base class for hardware tests with progressive framework:

```python
class HardwareTestBase:
    """Base class with verbosity control and result tracking."""

    def test(self, test_name: str, test_func: Callable):
        """Run single test with error handling."""
        # Logs start, runs test, catches errors, logs result

    def run_all_tests(self, test_level: TestLevel):
        """Run P1/P2/P3 tests based on level."""
        # Runs run_p1_basic(), run_p2_intermediate(), etc.
```

---

## Test Philosophy

### Key Differences from CocoTB Tests

| Aspect | CocoTB Tests | Hardware Tests |
|--------|-------------|----------------|
| **Timing** | P1: 8-16μs pulses | P2: 100-200μs pulses (more observable) |
| **State Reading** | Direct signal access | Oscilloscope polling (averaged) |
| **Tolerance** | ±30mV (digital ±200 units) | ±150mV (real-world noise) |
| **Reset** | Apply reset signal | Clear all control registers |
| **Verification** | Cycle-accurate | Relaxed timing, state-based |

### State Observation Strategy

Tests observe FSM state via **OutputC voltage** on oscilloscope Ch1:

1. **Routing:** OutputC → Slot1.InA (oscilloscope)
2. **Encoding:** HVS (Hierarchical Voltage Encoding)
   - IDLE = 0.0V
   - ARMED = 0.5V
   - FIRING = 1.0V
   - COOLDOWN = 1.5V
   - FAULT = negative voltage
3. **Averaging:** Read 5 samples, average to reduce noise
4. **Tolerance:** ±150mV (accounts for ADC noise, OSC polling delay)

### Relaxed Timing Approach

Unlike CocoTB's cycle-accurate verification, hardware tests use **state-based verification**:

- ✅ **Verify:** State transitions occur (IDLE → ARMED → FIRING → COOLDOWN)
- ✅ **Verify:** Transitions happen within reasonable timeouts
- ❌ **Don't verify:** Exact cycle counts or pulse widths
- ❌ **Don't verify:** Output voltages (unless routed to Ch2)

**Rationale:** Oscilloscope polling introduces 20-50ms latency, making cycle-accurate timing impossible.

---

## Verbosity Levels

Control output detail with `--verbosity` or `--verbose`:

### MINIMAL (Default)

```bash
python run_hw_tests.py 192.168.8.98
```

**Output:** Test names + PASS/FAIL only (~10 lines)

### NORMAL

```bash
python run_hw_tests.py 192.168.8.98 --verbosity NORMAL
```

**Output:** Progress indicators + results (~30 lines)

### VERBOSE

```bash
python run_hw_tests.py 192.168.8.98 --verbose
# OR
python run_hw_tests.py 192.168.8.98 --verbosity VERBOSE
```

**Output:** Detailed step-by-step execution (~100 lines)

### DEBUG

```bash
python run_hw_tests.py 192.168.8.98 --verbosity DEBUG
```

**Output:** Full debug information, including oscilloscope readings

---

## Command-Line Reference

```bash
python run_hw_tests.py <device_ip> [OPTIONS]

Required:
  device_ip              IP address of Moku device (e.g., 192.168.8.98)

Options:
  --osc-slot SLOT        Oscilloscope slot number (default: 1)
  --cc-slot SLOT         CloudCompile slot number (default: 2)
  --level LEVEL          Test level: P1, P2, P3 (default: P1)
  --verbosity LEVEL      Output level: SILENT, MINIMAL, NORMAL, VERBOSE, DEBUG
  --verbose, -v          Shorthand for --verbosity VERBOSE
  --platform PLATFORM    Platform type: moku_go, moku_lab, moku_pro, moku_delta
  --force                Force connection (disconnect existing)
  --debug [FILE]         Enable Moku debug logging (optional file output)
  -h, --help             Show help message
```

### Environment Variables

```bash
# Set default test level
export HW_TEST_LEVEL=P2
python run_hw_tests.py 192.168.8.98

# Set default verbosity
export HW_TEST_VERBOSITY=VERBOSE
python run_hw_tests.py 192.168.8.98
```

---

## Prerequisites & Setup

### 1. Deploy Instruments

Before running tests, ensure instruments are deployed:

```python
# Example deployment (run once)
from moku.instruments import MultiInstrument, Oscilloscope, CloudCompile

moku = MultiInstrument('192.168.8.98', platform_id=2, force_connect=True)

# Deploy oscilloscope to slot 1
osc = moku.set_instrument(1, Oscilloscope)

# Deploy CloudCompile with DPD bitstream to slot 2
mcc = moku.set_instrument(2, CloudCompile, bitstream="DPD-bits.tar")

# Routing will be auto-configured by tests if needed
```

### 2. Validate Routing

Tests auto-validate and configure routing. Manual validation:

```python
connections = moku.get_connections()

# Required connection:
# Slot2OutC → Slot1InA (FSM state observation)
```

If routing is missing, tests will automatically configure it.

---

## Debugging Failed Tests

### Common Failure Modes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "Routing validation failed" | OutputC not routed to OscInA | Tests auto-configure, but check manually if persistent |
| "FORGE_READY bits not set" | CR0 write failed or not propagated | Check Moku API connection, increase delay |
| "FSM did not reach IDLE" | Control registers not clearing | Try manual reset via debug_fsm_states.py |
| "FSM should ARM with complete FORGE control" | Bitstream not deployed or wrong slot | Verify CloudCompile in slot 2 |
| "FSM should leave ARMED after trigger" | sw_trigger edge detection failed | Check CR1 writes in verbose mode |
| "Timeout waiting for state" | Timing too fast or OSC polling too slow | Increase timeout or use slower timing |

### Increase Verbosity

```bash
# See detailed state transitions
python run_hw_tests.py 192.168.8.98 --verbose

# See all oscilloscope readings
python run_hw_tests.py 192.168.8.98 --verbosity DEBUG
```

### Use Interactive Debugger

For manual FSM control and state inspection:

```bash
cd ..  # Go to DPD root directory
python debug_fsm_states.py 192.168.8.98
```

Interactive commands:
- `r` - Read current state
- `init` - Initialize FORGE_READY
- `arm` - Arm probe
- `fire` - Force fire probe
- `demo` - Run full state machine demo

---

## Extending Tests (P2/P3 Development)

### Adding New P2 Test

1. **Edit `P2_hw_intermediate.py`:**

```python
def test_auto_rearm(self):
    """Test auto-rearm functionality (CR1[2])."""
    # Reset to IDLE
    reset_fsm_to_idle(self.mcc, self.osc)

    # Enable auto-rearm
    arm_probe(self.mcc, ...)
    self.mcc.set_control(1, 0x00000005)  # arm_enable=1, auto_rearm_enable=1

    # Verify ARMED
    assert self.wait_state("ARMED"), "Should be ARMED"

    # Trigger
    software_trigger(self.mcc)

    # Wait for cycle to complete
    time.sleep(0.5)

    # Should return to ARMED (not IDLE) due to auto-rearm
    state, _ = self.read_state()
    assert state == "ARMED", f"Should auto-rearm to ARMED, got {state}"
```

2. **Add to `run_p2_intermediate()`:**

```python
def run_p2_intermediate(self):
    """P2 test suite entry point."""
    self.test("Auto-rearm functionality", self.test_auto_rearm)
    # ... more tests
```

3. **Run P2 tests:**

```bash
python run_hw_tests.py 192.168.8.98 --level P2
```

---

## Comparison with CocoTB Tests

### Similarities

✅ Both use progressive testing (P1/P2/P3)
✅ Both observe OutputC for FSM state (HVS encoding)
✅ Both use relaxed timing approach
✅ Both have VerbosityLevel and TestBase classes
✅ Both verify FORGE control scheme

### Differences

| Aspect | CocoTB | Hardware |
|--------|--------|----------|
| **Environment** | GHDL simulation | Real Moku device |
| **Timing** | P1 uses 8-16μs pulses | P2 uses 100-200μs (more observable) |
| **State Reading** | `dut.OutputC.value.signed_integer` | Oscilloscope `get_data()` + averaging |
| **Reset** | `dut.Reset.value = 1` | Clear all control registers |
| **Tolerance** | ±200 digital units (~30mV) | ±150mV (real-world noise) |
| **Runtime** | <5s for P1 | <2min for P1 (includes OSC polling) |

---

## Related Documentation

- **CocoTB Tests:** `../cocotb_tests/README.md` - Simulation-based tests
- **Debug Scripts:** `../debug_fsm_states.py` - Interactive FSM debugger
- **Register Spec:** `../DPD-RTL.yaml` - Control register mapping
- **HVS Encoding:** `../HVS.md` - Hierarchical Voltage Encoding (if exists)

---

## Troubleshooting

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'hw_test_base'`

**Fix:** Run from `hardware_progressive_tests/` directory:
```bash
cd hardware_progressive_tests
python run_hw_tests.py 192.168.8.98
```

### Connection Errors

**Error:** `Could not connect to 192.168.8.98`

**Fix:**
- Verify device IP with `ping 192.168.8.98`
- Try force connect: `--force`
- Check if another process owns the device

### Instrument Not Found

**Error:** `Failed to get instruments. Ensure Oscilloscope is in slot 1`

**Fix:** Deploy instruments first (see Prerequisites & Setup)

### Routing Validation Fails

**Error:** `Routing validation failed. Check Moku connections.`

**Fix:** Tests auto-configure routing. If persistent:
```python
from hw_test_helpers import setup_routing
setup_routing(moku, osc_slot=1, cc_slot=2)
```

---

**Last Updated:** 2025-01-18
**Version:** 1.0.0 (P1 only)
**Author:** Moku Instrument Forge Team
