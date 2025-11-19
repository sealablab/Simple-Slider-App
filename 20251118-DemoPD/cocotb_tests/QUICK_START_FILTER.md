# GHDL Filter - Quick Start

## TL;DR

The GHDL filter **automatically suppresses repetitive GHDL warnings** to save LLM context while preserving all test results and errors.

**No configuration needed** - it works automatically when you run:
```bash
python run.py
```

---

## Common Usage

### Default (Automatic Filtering)
```bash
python run.py
```
- Auto-selects filter level based on test verbosity
- P1 tests use `aggressive` filtering (max LLM savings)

### Force Maximum Filtering
```bash
GHDL_FILTER=aggressive python run.py
```
- Suppress ~95% of GHDL noise
- Best for LLM-assisted development

### Disable Filtering (Debug Mode)
```bash
GHDL_FILTER=none python run.py
```
- See full GHDL output
- Use when debugging new HDL code

### Medium Filtering
```bash
GHDL_FILTER=normal python run.py
```
- Balanced filtering (~70% reduction)
- Good for manual review

---

## What Gets Hidden?

✅ **Always Hidden:**
- Metavalue warnings (`NUMERIC_STD.*: metavalue detected`)
- Null argument warnings
- Duplicate warnings (same message repeated)
- Initialization warnings (time 0)

❌ **Never Hidden:**
- Errors (`ERROR`)
- Test results (`PASS`, `FAIL`)
- Assertion failures
- Test summaries

---

## Expected Output Reduction

| Test Type | Lines Before | Lines After | Reduction |
|-----------|--------------|-------------|-----------|
| P1 Basic  | ~500         | ~20         | 96%       |
| P2 Intermediate | ~1200  | ~200        | 83%       |

---

## Troubleshooting

**Problem:** Output still too verbose
```bash
GHDL_FILTER=aggressive python run.py
```

**Problem:** Missing expected warnings
```bash
GHDL_FILTER=minimal python run.py
```

**Problem:** Need to see everything
```bash
GHDL_FILTER=none python run.py
```

---

## Files Modified

- ✅ `run.py` - Auto-selects filter level
- ✅ `conftest.py` - Updated documentation
- ✅ `ghdl_filter.py` - Filter implementation (standalone)
- ✅ `ghdl_filtered` - Bash wrapper (optional)

---

## Testing

Verify filter works:
```bash
python3 test_ghdl_filter.py
```

Should output:
```
✅ All tests PASSED
```

---

**Full docs:** See [GHDL_FILTER_README.md](GHDL_FILTER_README.md)
