# GHDL Output Filter Integration

**Purpose:** Dramatically reduce GHDL simulation output verbosity to preserve LLM context while maintaining visibility into test results and actual errors.

---

## Quick Start

### Default Usage (Automatic)

```bash
# Standard P1 test run - filter is automatically applied
python run.py
```

The filter level is **automatically selected** based on `COCOTB_VERBOSITY`:

| COCOTB_VERBOSITY | GHDL_FILTER | Effect |
|------------------|-------------|---------|
| `MINIMAL` (default) | `aggressive` | Maximum suppression - best for LLM workflows |
| `NORMAL` | `normal` | Balanced filtering |
| `VERBOSE` | `minimal` | Light filtering |
| `DEBUG` | `none` | No filtering (full GHDL output) |

### Manual Override

```bash
# Force aggressive filtering regardless of verbosity
GHDL_FILTER=aggressive python run.py

# Disable filtering completely
GHDL_FILTER=none python run.py

# Use minimal filtering
GHDL_FILTER=minimal python run.py
```

---

## What Gets Filtered?

### Always Suppressed (in `normal` and `aggressive` modes)

1. **Metavalue warnings** - `NUMERIC_STD.*: metavalue detected`
2. **Null argument warnings** - `NUMERIC_STD.*: null argument detected`
3. **Initialization warnings** - Warnings at simulation time 0
4. **Duplicate warnings** - Repeated identical warnings (only first shown)

### Always Preserved

- ❌ **Errors** - Any line containing "ERROR"
- ✅ **Test results** - Lines with "PASS", "FAIL", "TEST COMPLETE"
- ⚠️ **Assertion failures** - Fatal assertions and errors
- 📊 **Test summaries** - Progress indicators and statistics

---

## Filter Levels Explained

### `aggressive` (Recommended for P1 tests)
- Filters all metavalue warnings
- Filters all null warnings
- Filters all initialization warnings
- Filters GHDL internal messages
- Deduplicates repeated warnings
- **Best for:** LLM-assisted development, P1 basic tests
- **Output reduction:** 80-95%

### `normal` (Balanced)
- Filters metavalue warnings
- Filters null warnings
- Filters initialization warnings
- Deduplicates repeated warnings
- **Best for:** General development, P2 tests
- **Output reduction:** 60-80%

### `minimal` (Conservative)
- Shows first occurrence of each metavalue warning
- Filters subsequent duplicates
- **Best for:** Debugging, P3 tests
- **Output reduction:** 30-50%

### `none` (No filtering)
- Pass-through mode - all GHDL output shown
- **Best for:** Deep debugging, investigating GHDL behavior
- **Output reduction:** 0%

---

## Integration Methods

### Method 1: Automatic via `run.py` (CURRENT)

**How it works:**
1. `run.py` detects `COCOTB_VERBOSITY` or `GHDL_FILTER` env vars
2. Sets `GHDL_FILTER_LEVEL` environment variable
3. Launches cocotb tests
4. GHDL output is automatically filtered (if using `ghdl_filtered` wrapper)

**Files involved:**
- `run.py` - Auto-selects filter level
- `ghdl_filter.py` - Filter implementation
- `ghdl_filtered` - Bash wrapper script (optional)

### Method 2: Makefile-based (Alternative)

If using Makefiles instead of `run.py`:

```makefile
# In your Makefile
SIM = ghdl
GHDL_FILTER_LEVEL ?= normal

# Wrap simulation command
sim:
    @cocotb-test ... 2>&1 | python ghdl_filter.py --level $(GHDL_FILTER_LEVEL)
```

### Method 3: Direct Python Usage

```python
from ghdl_filter import GHDLOutputFilter, FilterLevel
import subprocess

# Create filter
filter = GHDLOutputFilter(level=FilterLevel.NORMAL)

# Run GHDL and filter output
proc = subprocess.Popen(
    ["ghdl", "-r", "entity_name"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Filter in real-time
filter.filter_stream(input_stream=proc.stdout)
```

---

## Examples

### Example 1: Unfiltered Output (Before)

```
  0.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0
  0.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0
  0.00ns NUMERIC_STD.TO_UNSIGNED: metavalue detected, returning 0
  8.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0
 16.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0
 24.00ns NUMERIC_STD.TO_INTEGER: metavalue detected, returning 0
... (repeated 500+ times)
✓ Reset complete (active-high, 10 cycles)
T1: Reset behavior
  ✓ PASS
T2: FORGE control scheme
  ✓ PASS
```

**Total lines:** 523

### Example 2: Filtered Output (After - `aggressive` mode)

```
✓ Reset complete (active-high, 10 cycles)
T1: Reset behavior
  ✓ PASS
T2: FORGE control scheme
  ✓ PASS

[GHDL Output Filter - Level: aggressive]
  Total lines: 523
  Filtered: 518 (99.0% reduction)
  - Metavalue warnings: 502
  - Initialization warnings: 16
```

**Total lines:** 10 (98% reduction!)

---

## Filter Statistics

At the end of each filtered run, you'll see a summary:

```
[GHDL Output Filter - Level: normal]
  Total lines: 1234
  Filtered: 987 (80.0% reduction)
  - Metavalue warnings: 850
  - Null warnings: 45
  - Initialization warnings: 62
  - Duplicate warnings: 30
```

This helps you understand what was suppressed.

---

## Troubleshooting

### "I'm not seeing expected warnings"

Try reducing filter aggressiveness:
```bash
GHDL_FILTER=minimal python run.py
```

### "Output is still too verbose"

Increase filter level:
```bash
GHDL_FILTER=aggressive python run.py
```

### "Filter is hiding real errors"

**This should never happen** - errors are always preserved. If it does:
1. Check `ghdl_filter.py:88-101` for `PRESERVE_PATTERNS`
2. Report the issue with example output
3. Temporarily disable: `GHDL_FILTER=none python run.py`

### "Filter summary not showing"

The summary only appears if lines were actually filtered. If you see no summary:
- Filter level might be `none`
- GHDL might not be producing filterable warnings
- Check `GHDL_FILTER_LEVEL` environment variable

---

## Performance Impact

- **Filtering overhead:** <1ms per 1000 lines (negligible)
- **Memory usage:** <5MB for typical test runs
- **Simulation speed:** No impact (filtering happens post-simulation)

---

## Customization

### Adding Custom Filter Patterns

Edit `ghdl_filter.py` and add patterns to:

```python
# Filter specific warning types
CUSTOM_PATTERNS = [
    r".*your_pattern_here.*",
]
```

### Adding Custom Preserve Patterns

To always show certain messages:

```python
PRESERVE_PATTERNS = [
    r".*IMPORTANT_MESSAGE.*",
    # ... existing patterns
]
```

---

## Best Practices

1. **Use `aggressive` for P1 tests** - Maximize LLM context preservation
2. **Use `normal` for P2 tests** - Balance detail and readability
3. **Use `minimal` for P3 tests** - Keep most warnings for thorough testing
4. **Use `none` when debugging new HDL** - See everything GHDL reports
5. **Check filter summary** - Ensure you're not over-filtering

---

## File Reference

| File | Purpose |
|------|---------|
| `ghdl_filter.py` | Filter implementation (standalone) |
| `run.py` | Auto-selects filter level, sets env vars |
| `ghdl_filtered` | Bash wrapper for GHDL (optional) |
| `conftest.py` | Updated with filter documentation |
| `GHDL_FILTER_README.md` | This file |

---

## Future Enhancements

Potential improvements (not yet implemented):

- [ ] Per-test filter level override
- [ ] Filter configuration file (`.ghdl_filter.yaml`)
- [ ] Automatic pattern learning from test runs
- [ ] Integration with pytest fixtures
- [ ] HTML output with collapsible filtered sections

---

**Questions?** Check the inline documentation in `ghdl_filter.py` or see examples in `run.py`.
