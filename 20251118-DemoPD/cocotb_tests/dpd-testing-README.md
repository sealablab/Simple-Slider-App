# Demo Probe Driver (DPD) - CocoTB Testing Guide

> [!info] Purpose
> Complete guide for running CocoTB progressive tests on the Demo Probe Driver custom instrument. Tests verify FSM state transitions, FORGE control scheme, and hardware/software triggering via OutputC (HVS encoding) observation.

---

## Quick Start

### Prerequisites

- Python 3.10+ with `uv` package manager
- GHDL simulator (VHDL-2008 support)
- Access to FORGE-v5 monorepo

### 1. Initial Setup (One-Time)

Navigate to the FORGE-v5 root directory and initialize the Python environment:

```bash
cd /Users/johnycsh/Forge/FORGE-v5

# Initialize uv environment (creates .venv/)
uv sync

# Activate the virtual environment
source .venv/bin/activate

# Verify CocoTB is installed
uv pip list | grep cocotb
```

> [!tip] What does `uv sync` do?
> - Reads `pyproject.toml` and creates a virtual environment
> - Installs all dependencies (cocotb, cocotb-test, etc.)
> - Sets up forge-vhdl Python packages for test infrastructure

### 2. Navigate to Test Directory

```bash
cd examples/demo-probe-driver/cocotb_tests
```

### 3. Run P1 (BASIC) Tests

```bash
# Run with minimal output (<20 lines, LLM-optimized)
python run.py
```

**Expected output:**
```
======================================================================
Running dpd_wrapper tests
======================================================================
Simulator: ghdl
Top-level: customwrapper
Test Level: P1_BASIC
Verbosity: MINIMAL
GHDL Filter: aggressive
Sources: 7 VHDL files
======================================================================

P1 - BASIC TESTS
T1: Reset behavior
  ✓ PASS
T2: FORGE control scheme
  ✓ PASS
T3: FSM cycle (software trigger)
  ✓ PASS
T4: FSM cycle (hardware trigger)
  ✓ PASS
T5: Output pulses during FIRING
  ✓ PASS
ALL 5 TESTS PASSED

[GHDL Output Filter - Level: aggressive]
  Total lines: 523
  Filtered: 518 (99.0% reduction)
  - Metavalue warnings: 502

✅ Tests completed successfully!
```

---

## Testing from External Projects (SimpleSliderApp Pattern)

> [!note] Multi-Project Testing
> The DPD tests can be run from external projects that use the FORGE codebase as a dependency. This pattern is used in SimpleSliderApp development.

### External Project Structure

When developing in an external project (e.g., `/Users/johnycsh/workspace/SimpleSliderApp`):

```
SimpleSliderApp/
├── 20251118-DemoPD/              # DPD development branch
│   ├── cocotb_tests/              # ← Tests live here (symlink or copy)
│   │   ├── dpd_wrapper_tests/
│   │   ├── conftest.py
│   │   └── run.py
│   ├── DPD.vhd                    # VHDL sources
│   ├── DPD_shim.vhd
│   └── DPD_main.vhd
└── pyproject.toml                 # Dependencies point to FORGE-v5
```

### Running Tests from External Project

```bash
# 1. Navigate to external project root
cd /Users/johnycsh/workspace/SimpleSliderApp

# 2. Initialize uv environment (if not already done)
uv sync

# 3. Navigate to test directory
cd 20251118-DemoPD/cocotb_tests

# 4. Run tests (Python environment from SimpleSliderApp root)
python run.py
```

> [!important] Path Resolution
> The test runner (`run.py`) automatically resolves paths relative to the test directory, so it works from both FORGE-v5 and external projects.

### Syncing Tests Between Projects

**Option 1: Symlink (recommended for active development)**
```bash
cd /Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD
ln -s /Users/johnycsh/Forge/FORGE-v5/examples/demo-probe-driver/cocotb_tests cocotb_tests
```

**Option 2: Copy tests manually**
```bash
cp -r /Users/johnycsh/Forge/FORGE-v5/examples/demo-probe-driver/cocotb_tests \
      /Users/johnycsh/workspace/SimpleSliderApp/20251118-DemoPD/
```

**Option 3: Git submodule**
```bash
cd /Users/johnycsh/workspace/SimpleSliderApp
git submodule add /Users/johnycsh/Forge/FORGE-v5 forge-v5
# Tests accessible at: forge-v5/examples/demo-probe-driver/cocotb_tests
```

---

## Test Verbosity Levels

Control output detail with the `COCOTB_VERBOSITY` environment variable:

### MINIMAL (Default)

```bash
python run.py
# OR
COCOTB_VERBOSITY=MINIMAL python run.py
```

**Output:** ~10 lines, test names + PASS/FAIL only
**GHDL Filter:** Aggressive (96% output reduction)

### NORMAL

```bash
COCOTB_VERBOSITY=NORMAL python run.py
```

**Output:** ~30 lines, includes state transition logs
**GHDL Filter:** Normal (70% output reduction)

### VERBOSE

```bash
COCOTB_VERBOSITY=VERBOSE python run.py
```

**Output:** ~100 lines, detailed step-by-step execution
**GHDL Filter:** Minimal (30% output reduction)

### DEBUG

```bash
COCOTB_VERBOSITY=DEBUG python run.py
```

**Output:** Full debug information, waveform hints
**GHDL Filter:** None (no filtering, full GHDL output)

---

## GHDL Output Filtering

> [!info] Automatic LLM-Friendly Output
> Tests automatically filter repetitive GHDL warnings to preserve LLM context while keeping all errors and test results visible.

### What Gets Filtered

✅ **Automatically Suppressed:**
- Metavalue warnings (`NUMERIC_STD.*: metavalue detected`)
- Null argument warnings (`NUMERIC_STD.*: null argument detected`)
- Duplicate warnings (same message repeated)
- Initialization warnings (simulation time 0)
- GHDL internal messages

❌ **Always Preserved:**
- All errors (`ERROR`, `assertion error`)
- Test results (`PASS`, `FAIL`, test summaries)
- Custom assertion messages
- FSM state transitions

### Manual Filter Control

Override automatic filter selection:

```bash
# Maximum filtering (LLM-optimized)
GHDL_FILTER=aggressive python run.py

# Balanced filtering
GHDL_FILTER=normal python run.py

# Light filtering
GHDL_FILTER=minimal python run.py

# Disable filtering (see everything)
GHDL_FILTER=none python run.py
```

### Expected Output Reduction

| Test Level | Unfiltered | Filtered (aggressive) | Reduction |
|------------|------------|----------------------|-----------|
| P1 Basic   | ~500 lines | ~20 lines           | 96%       |
| P2 Intermediate | ~1200 lines | ~200 lines     | 83%       |

### Filter Documentation

For complete details:
- **Quick reference:** [QUICK_START_FILTER.md](QUICK_START_FILTER.md)
- **Full documentation:** [GHDL_FILTER_README.md](GHDL_FILTER_README.md)
- **Unit tests:** Run `python3 test_ghdl_filter.py`

---

## Progressive Test Levels

The DPD test suite uses progressive testing (P1/P2/P3) for efficient iteration:

### P1 - BASIC (Default)

**Purpose:** Fast smoke tests, LLM-optimized output

**Tests:**
1. Reset behavior
2. FORGE control scheme (CR0[31:29])
3. FSM cycle (software trigger)
4. FSM cycle (hardware trigger)
5. Output pulse verification

**Timing:** Uses reduced durations for speed
- Trigger pulse: 1000 cycles (8μs) vs 12500 cycles (100μs) default
- Intensity pulse: 2000 cycles (16μs) vs 25000 cycles (200μs) default
- Cooldown: 500 cycles (4μs) vs 1250 cycles (10μs) default

**Runtime:** <5 seconds

```bash
python run.py
# OR explicitly:
TEST_LEVEL=P1_BASIC python run.py
```

### P2 - INTERMEDIATE (Future)

**Purpose:** Comprehensive validation with production timing

**Additional tests:**
- auto_rearm_enable (COOLDOWN → ARMED loop)
- FAULT state injection and recovery
- Probe monitor feedback (InputB)
- Edge case timing values

```bash
TEST_LEVEL=P2_INTERMEDIATE python run.py
```

> [!warning] Not Yet Implemented
> P2 tests are planned but not yet implemented. Running this command will only execute P1 tests.

### P3 - COMPREHENSIVE (Future)

**Purpose:** Stress testing and corner cases

**Additional tests:**
- Rapid trigger cycles
- Concurrent trigger sources
- Register changes during FSM operation
- Full status register verification

```bash
TEST_LEVEL=P3_COMPREHENSIVE python run.py
```

---

## Test Architecture

### File Structure

```
cocotb_tests/
├── dpd_wrapper_tests/           # Test module package
│   ├── __init__.py
│   ├── dpd_wrapper_constants.py # Constants, HVS values, timing
│   ├── dpd_helpers.py           # DPD-specific utilities
│   └── P1_dpd_wrapper_basic.py  # P1 test suite
├── conftest.py                  # CocoTB fixtures
├── run.py                       # Test runner
└── README.md                    # Technical documentation
```

### Key Components

#### `dpd_wrapper_constants.py`

Defines all test constants:

```python
# HVS Digital Values (OutputC encoding)
HVS_DIGITAL_IDLE = 0       # State 0 × 200
HVS_DIGITAL_ARMED = 200    # State 1 × 200
HVS_DIGITAL_FIRING = 400   # State 2 × 200
HVS_DIGITAL_COOLDOWN = 600 # State 3 × 200
HVS_DIGITAL_TOLERANCE = 20 # ±20 digital units

# FORGE Control Scheme
MCC_CR0_ALL_ENABLED = 0xE0000000  # Bits 31+30+29 set

# P1 Timing (reduced for fast tests)
P1TestValues.TRIG_OUT_DURATION = 1000     # 8μs @ 125MHz
P1TestValues.INTENSITY_DURATION = 2000    # 16μs @ 125MHz
P1TestValues.COOLDOWN_INTERVAL = 500      # 4μs @ 125MHz
```

#### `dpd_helpers.py`

Test utilities for FSM observation:

```python
# State observation via OutputC (HVS encoding)
wait_for_state(dut, HVS_DIGITAL_ARMED, timeout_us=100)
assert_state(dut, HVS_DIGITAL_FIRING, context="after trigger")

# FSM control
await arm_dpd(dut, trig_duration=1000, intensity_duration=2000, cooldown=500)
await software_trigger(dut)  # CR1[1] edge detection
await hardware_trigger(dut, voltage_mv=1500, threshold_mv=950)

# Relaxed timing (20% margin by default)
await wait_cycles_relaxed(dut, 1000, margin_percent=20)
```

#### `conftest.py`

CocoTB fixtures (adapted from forge-vhdl):

```python
# Clock and reset
await setup_clock(dut, period_ns=8, clk_signal="Clk")  # 125MHz
await reset_active_high(dut, rst_signal="Reset", cycles=10)

# Control register management
await mcc_set_regs(dut, {0: 0xE0000000, 1: 0x00000001})
await wait_for_mcc_ready(dut, settle_cycles=10)

# FORGE control validation
validate_control0(cr0_value, context="test_setup")
```

---

## Understanding Test Output

### HVS (Hierarchical Voltage Encoding)

Tests observe FSM state via **OutputC** which uses HVS encoding:

```python
digital_value = state_integer × 200 + status_offset
```

**State Mapping:**
| FSM State | state_vector | Base Digital | Observed Range |
|-----------|--------------|--------------|----------------|
| IDLE | 0 | 0 | [-10, +10] |
| ARMED | 1 | 200 | [190, 210] |
| FIRING | 2 | 400 | [390, 410] |
| COOLDOWN | 3 | 600 | [590, 610] |
| FAULT | 63 | -12600 | Negative value |

> [!note] Why ±20 tolerance?
> The ±20 digital unit tolerance accounts for the `status_offset` contribution (status_vector[6:0] × 0.78125). This allows the FSM to encode additional state information beyond just the major state.

### Reading Test Logs

**Successful state transition:**
```
✓ Reached state 200 (OutputC=205) after 15 cycles
```
- Target: 200 (ARMED state)
- Actual: 205 (within tolerance of 200±20)
- Transition time: 15 cycles (very fast)

**Timeout (bug detected):**
```
AssertionError: Timeout waiting for OutputC=400±20,
stuck at 205 after 100μs (12500 cycles)
```
- Expected: FIRING state (400)
- Stuck in: ARMED state (205 ≈ 200)
- Diagnosis: FSM didn't respond to trigger

---

## Debugging Failed Tests

### Disable Output Filtering

When debugging, you may want to see all GHDL warnings:

```bash
GHDL_FILTER=none python run.py
```

Or combine with verbose output:

```bash
GHDL_FILTER=none COCOTB_VERBOSITY=VERBOSE python run.py
```

### Enable Verbose Output

```bash
COCOTB_VERBOSITY=VERBOSE python run.py
```

This automatically sets `GHDL_FILTER=minimal` for light filtering.

### Enable Waveforms

Edit `run.py`, line ~40:

```python
cocotb_run(
    # ... other args ...
    waves=True,  # Change from False
    # ...
)
```

Run tests, then view waveforms:

```bash
gtkwave dump.vcd
```

### Common Failure Modes

| Symptom | Likely Cause | Debug Steps |
|---------|-------------|-------------|
| Stuck in IDLE after arm | FORGE control incomplete (CR0[31:29] ≠ 111) | Check CR0 value in logs |
| Stuck in ARMED after sw_trigger | CR1[1] edge detection broken | Verify sw_trigger edge in waveform |
| Stuck in ARMED after hardware trigger | InputA voltage threshold not crossed | Check InputA value, threshold |
| Both triggers fail | FSM trigger input not connected | Review DPD_main.vhd trigger logic |
| FIRING → COOLDOWN timeout | Duration counter not decrementing | Check firing_timer in waveform |
| OutputA/B wrong timing | Pulse generator duration bug | Measure pulse width in waveform |

### Manual Register Inspection

Add diagnostic prints to tests:

```python
# In test function
cr0_value = int(dut.Control0.value)
cr1_value = int(dut.Control1.value)
output_c = int(dut.OutputC.value.signed_integer)

print(f"CR0={cr0_value:#010x}, CR1={cr1_value:#010x}, OutputC={output_c}")
```

---

## Voltage Conversion Reference

Tests use **millivolts** for human readability, converting to **16-bit signed digital** for VHDL:

```python
from dpd_wrapper_tests.dpd_wrapper_constants import mv_to_digital, digital_to_mv

# Moku ADC/DAC: ±5V = ±32768 digital (16-bit signed)
digital = mv_to_digital(1500)  # 1500mV → 9830 digital
voltage = digital_to_mv(9830)  # 9830 digital → 1500.0mV
```

**Common test voltages:**
| Description | mV | Digital | Hex |
|-------------|-----|---------|-----|
| Trigger threshold (default) | 950 | 6225 | 0x1851 |
| Test trigger voltage | 1500 | 9830 | 0x2666 |
| Trigger output (test) | 2000 | 13107 | 0x3333 |
| Intensity output (test) | 1500 | 9830 | 0x2666 |
| Monitor threshold (default) | -200 | -1310 | 0xFADE |

---

## Register Mapping Quick Reference

### CR0 - FORGE Control Scheme

```
CR0[31:29] - FORGE control (REQUIRED for all modules)
  [31] = forge_ready   (set after deployment)
  [30] = user_enable   (user control)
  [29] = clk_enable    (clock gating)

All three bits MUST be set: CR0 = 0xE0000000
```

### CR1 - Lifecycle Control

```
CR1[0] = arm_enable           (IDLE → ARMED)
CR1[1] = sw_trigger           (ARMED → FIRING, edge-detected)
CR1[2] = auto_rearm_enable    (COOLDOWN → ARMED loop)
CR1[3] = fault_clear          (FAULT → IDLE)
```

### CR2 - Trigger Configuration

```
CR2[31:16] = input_trigger_voltage_threshold (mV, signed 16-bit)
CR2[15:0]  = trig_out_voltage (mV, signed 16-bit)
```

### CR3-CR7 - Timing and Output

```
CR3[15:0]  = intensity_voltage (mV, signed 16-bit)
CR4[31:0]  = trig_out_duration (clock cycles)
CR5[31:0]  = intensity_duration (clock cycles)
CR6[31:0]  = trigger_wait_timeout (clock cycles)
CR7[31:0]  = cooldown_interval (clock cycles)
```

### CR8-CR10 - Monitor (Future)

```
CR8[0]     = monitor_enable
CR8[1]     = monitor_expect_negative
CR8[31:16] = monitor_threshold_voltage (mV, signed 16-bit)
CR9[31:0]  = monitor_window_start (clock cycles)
CR10[31:0] = monitor_window_duration (clock cycles)
```

---

## Extending Tests (P2/P3 Development)

### Adding New Test Cases

1. **Create test function** in `P1_dpd_wrapper_basic.py`:

```python
async def test_auto_rearm(self):
    """Verify auto_rearm_enable loops COOLDOWN → ARMED"""
    # Enable auto-rearm
    await mcc_set_regs(self.dut, {
        1: 0x00000005  # arm_enable=1, auto_rearm_enable=1
    }, set_forge_ready=False)

    # Trigger and verify loop
    await software_trigger(self.dut)
    await wait_for_fsm_complete_cycle(self.dut, ...)

    # Should return to ARMED, not IDLE
    await wait_for_state(self.dut, HVS_DIGITAL_ARMED, timeout_us=100)
```

2. **Add to test suite** in `run_p2_intermediate()`:

```python
async def run_p2_intermediate(self):
    """P2 test suite entry point"""
    # ... P1 setup ...

    await self.test("Auto-rearm functionality", self.test_auto_rearm)
```

3. **Run P2 tests**:

```bash
TEST_LEVEL=P2_INTERMEDIATE python run.py
```

### Creating Helper Functions

Add reusable utilities to `dpd_helpers.py`:

```python
async def wait_for_fault(dut, timeout_us: int = 1000):
    """Wait for FSM to enter FAULT state (negative OutputC value)."""
    timeout_cycles = int((timeout_us * 1000) / CLK_PERIOD_NS)

    for cycle in range(timeout_cycles):
        actual = read_output_c(dut)
        if actual < 0:  # FAULT state (sign flip)
            dut._log.info(f"  ✓ Reached FAULT state (OutputC={actual})")
            return
        await ClockCycles(dut.Clk, 1)

    raise AssertionError(f"Timeout waiting for FAULT state after {timeout_us}μs")
```

---

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: DPD CocoTB Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install GHDL
        run: |
          sudo apt-get update
          sudo apt-get install -y ghdl

      - name: Install Python dependencies
        run: |
          pip install uv
          uv sync

      - name: Run P1 tests
        working-directory: examples/demo-probe-driver/cocotb_tests
        run: |
          source ../../.venv/bin/activate
          python run.py
```

---

## Related Documentation

- **[[DPD-RTL.yaml]]** - Authoritative register specification
- **[[HVS.md]]** - Hierarchical Voltage Encoding scheme
- **[[FORGE_ARCHITECTURE.md]]** - 3-layer FORGE architecture (in basic-probe-driver/)
- **[[examples/demo-probe-driver/cocotb_tests/README.md]]** - Technical test documentation
- **[[libs/forge-vhdl/CLAUDE.md]]** - CocoTB progressive testing standards
- **[GHDL_FILTER_README.md](GHDL_FILTER_README.md)** - GHDL output filtering documentation
- **[QUICK_START_FILTER.md](QUICK_START_FILTER.md)** - GHDL filter quick reference

---

## Troubleshooting

### `ModuleNotFoundError: No module named 'cocotb'`

**Cause:** Virtual environment not activated or dependencies not installed

**Fix:**
```bash
cd /Users/johnycsh/Forge/FORGE-v5
uv sync
source .venv/bin/activate
```

### `ghdl: command not found`

**Cause:** GHDL simulator not installed

**Fix (macOS):**
```bash
brew install ghdl
```

**Fix (Ubuntu):**
```bash
sudo apt-get install ghdl
```

### `No module named 'forge_cocotb.test_base'`

**Cause:** forge-vhdl Python package not in path

**Fix:** Ensure running from FORGE-v5 root with `uv sync`:
```bash
cd /Users/johnycsh/Forge/FORGE-v5
uv sync  # Installs forge-vhdl package in editable mode
cd examples/demo-probe-driver/cocotb_tests
python run.py
```

### Tests hang indefinitely

**Cause:** Infinite loop in VHDL or simulator stuck

**Fix:** Use wall-clock timeout (built into tests):
```python
# Tests automatically timeout after 10 seconds
# Check for stuck state in timeout message
```

### `RuntimeError: Can not find root handle 'CustomWrapper'`

**Cause:** Case mismatch between VHDL entity name and CocoTB toplevel

**Error message:**
```
VPI: Toplevel instances: CustomWrapper != customwrapper...
```

**Fix:** GHDL lowercases entity names by default. Use lowercase in constants:
```python
# In dpd_wrapper_constants.py
HDL_TOPLEVEL = "customwrapper"  # GHDL lowercases entity names!
```

### `AttributeError: 'HierarchyObject' object has no attribute 'OutputC'`

**Cause:** DUT top-level entity mismatch or wrong entity loaded

**Fix:** Verify `HDL_TOPLEVEL` matches what GHDL reports:
```python
HDL_TOPLEVEL = "customwrapper"  # lowercase for GHDL!
```

---

## Contributing

When adding new tests:

1. **Follow P1 standards** - <20 line output, <5 second runtime
2. **Use relaxed timing** - Don't enforce strict cycle counts
3. **Observe via OutputC** - No internal signal peeking
4. **Document helpers** - Add docstrings with examples
5. **Update README** - Add test descriptions and usage

---

**Last Updated:** 2025-01-26
**Version:** 1.1.0 (P1 + GHDL Filter Integration)
**Author:** Moku Instrument Forge Team
