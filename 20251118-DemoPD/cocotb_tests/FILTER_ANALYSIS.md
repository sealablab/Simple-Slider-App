# GHDL Filter Analysis - Current Issues

## Problem Summary

**The filter is configured but NOT applied** - output shows 12,589 lines (1.6MB) instead of expected ~20 lines.

## Root Causes Identified

### 1. **Filter Not in Execution Path**
- `run.py:122` sets `GHDL_FILTER_LEVEL` environment variable
- But `cocotb_run()` doesn't pipe output through the filter
- GHDL warnings come through CocoTB's VPI interface, not stdout
- No wrapper script intercepts the GHDL process

### 2. **Wrong Integration Point**
The filter needs to intercept GHDL output **before** CocoTB wraps it with `INFO cocotb:` prefixes.

Current flow:
```
GHDL → VPI → CocoTB → stdout (unfiltered)
```

Desired flow:
```
GHDL → VPI → CocoTB → Filter → stdout (filtered)
```

### 3. **CocoTB Logging Captures Everything**
All GHDL warnings are wrapped as:
```
INFO cocotb: ../../src/ieee2008/numeric_std-body.vhdl:3117:7:@100240ns:(assertion warning): NUMERIC_STD.TO_SIGNED: vector truncated
```

The filter patterns expect unwrapped GHDL output, so they don't match.

## Statistics from Test Run

- **Total lines:** 12,589
- **Vector truncated warnings:** 12,501 (99.3%)
- **Metavalue warnings:** 22
- **Actual test output:** ~66 lines
- **Expected after filtering:** ~20 lines (96% reduction)

## Failed Filter Patterns

These patterns in `ghdl_filter.py` don't match because of CocoTB wrapping:

```python
# Expected: "NUMERIC_STD.TO_SIGNED: vector truncated"
# Actual:   "INFO cocotb: ../../src/ieee2008/numeric_std-body.vhdl:3117:7:@100240ns:(assertion warning): NUMERIC_STD.TO_SIGNED: vector truncated"
```

## Solutions

### Option A: Post-Process CocoTB Output (RECOMMENDED)
Wrap the entire `cocotb_run()` call and filter stdout in real-time.

**Pros:**
- Works with existing CocoTB infrastructure
- No GHDL wrapper needed
- Patterns can match CocoTB-wrapped output

**Cons:**
- Must handle CocoTB's `INFO cocotb:` prefix
- Slightly more complex pattern matching

### Option B: Monkey-Patch CocoTB Logger
Intercept CocoTB's logging handler to filter before output.

**Pros:**
- Most elegant solution
- Filters at the source

**Cons:**
- Fragile (depends on CocoTB internals)
- May break with CocoTB updates

### Option C: GHDL Wrapper Script
Create `ghdl_filtered` wrapper that filters GHDL's direct output.

**Pros:**
- Clean separation of concerns
- Works at GHDL level

**Cons:**
- Doesn't work with CocoTB's VPI integration
- GHDL output goes through VPI, not stdout

## Recommended Implementation: Option A

### Step 1: Update Filter Patterns
Add CocoTB-aware patterns:

```python
METAVALUE_PATTERNS = [
    r".*NUMERIC_STD\.[A-Z_]+: metavalue detected.*",
    r".*INFO cocotb:.*NUMERIC_STD\.[A-Z_]+: metavalue detected.*",  # NEW
]

TRUNCATED_PATTERNS = [
    r".*NUMERIC_STD\.TO_SIGNED: vector truncated.*",
    r".*INFO cocotb:.*NUMERIC_STD\.TO_SIGNED: vector truncated.*",  # NEW
]
```

### Step 2: Wrap cocotb_run() in run.py
Replace direct call with filtered subprocess:

```python
import subprocess
import sys
from ghdl_filter import GHDLOutputFilter, FilterLevel

# Build cocotb command
cmd = [
    "cocotb-test",
    "--vhdl-sources", ",".join([str(s) for s in HDL_SOURCES]),
    "--toplevel", HDL_TOPLEVEL,
    # ... etc
]

# Run with real-time filtering
proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
filter = GHDLOutputFilter(level=filter_level)
filter.filter_stream(input_stream=proc.stdout, output_stream=sys.stdout)
proc.wait()
```

### Step 3: Add Vector Truncated Filter
This is the biggest offender (12,501 lines!):

```python
TRUNCATED_PATTERNS = [
    r".*NUMERIC_STD\.TO_SIGNED: vector truncated.*",
    r".*NUMERIC_STD\.TO_UNSIGNED: vector truncated.*",
]
```

## Expected Results After Fix

**Before filtering:** 12,589 lines
**After filtering (aggressive):** ~20 lines
- Test summary: 15 lines
- Python deprecation warnings: 3 lines
- Filter summary: 5 lines

**Reduction:** 99.8%
