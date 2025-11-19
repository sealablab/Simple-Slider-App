# Quick Start - Hardware Progressive Tests

## 1-Minute Setup

### Prerequisites Check

```bash
# 1. Verify Moku device is accessible
ping 192.168.8.98  # Replace with your device IP

# 2. Ensure Python environment is ready
cd /Users/johnycsh/workspace/SimpleSliderApp
uv sync  # Install dependencies

# 3. Verify instruments are deployed
# - Slot 1: Oscilloscope
# - Slot 2: CloudCompile with DPD bitstream
```

### Run P1 Tests

```bash
# Option 1: From SimpleSliderApp root (recommended)
cd /Users/johnycsh/workspace/SimpleSliderApp
uv run python3 ./20251118-DemoPD/hardware_progressive_tests/run_hw_tests.py 192.168.8.98

# Option 2: From hardware_progressive_tests directory
cd 20251118-DemoPD/hardware_progressive_tests
uv run python3 run_hw_tests.py 192.168.8.98

# Verbose output (recommended for first run)
uv run python3 run_hw_tests.py 192.168.8.98 --verbose
```

### Expected Output (MINIMAL)

```
======================================================================
DPD Hardware Progressive Tests
======================================================================
Device: 192.168.8.98
Test Level: P1_BASIC
Verbosity: MINIMAL
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

## Common Issues

### "Failed to get instruments"

**Cause:** Instruments not deployed or wrong slots

**Fix:** Deploy instruments first using the Moku app or:
```python
from moku.instruments import MultiInstrument, Oscilloscope, CloudCompile
moku = MultiInstrument('192.168.8.98', platform_id=2, force_connect=True)
osc = moku.set_instrument(1, Oscilloscope)
mcc = moku.set_instrument(2, CloudCompile, bitstream="DPD-bits.tar")
```

### "Routing validation failed"

**Cause:** OutputC not routed to OscInA

**Fix:** Tests auto-configure routing. If persistent, check Moku connections manually.

### "FSM did not reach IDLE after reset"

**Cause:** Bitstream not working or control registers stuck

**Fix:** Use interactive debugger:
```bash
cd ..  # Go to DPD root
python debug_fsm_states.py 192.168.8.98
```

---

## Next Steps

- **Read full docs:** See [README.md](README.md)
- **Add P2 tests:** Edit [P2_hw_intermediate.py](P2_hw_intermediate.py)
- **Compare with CocoTB:** Check `../cocotb_tests/README.md`
- **Interactive debug:** Use `../debug_fsm_states.py`

---

## File Overview

```
hardware_progressive_tests/
├── run_hw_tests.py           ← START HERE (test runner)
├── P1_hw_basic.py            ← P1 test suite (implemented)
├── P2_hw_intermediate.py     ← P2 stub (future work)
├── P3_hw_comprehensive.py    ← P3 stub (future work)
├── hw_test_base.py           ← Base class (like CocoTB TestBase)
├── hw_test_helpers.py        ← FSM control utilities
├── hw_test_constants.py      ← Timing configs, state maps
├── README.md                 ← Full documentation
└── QUICK_START.md            ← This file
```

**Total Lines:** ~1600 lines of Python + documentation
**Test Count:** 6 P1 tests (implemented), P2/P3 stubbed
**Runtime:** <2 minutes for P1

---

**Happy Testing! 🚀**
