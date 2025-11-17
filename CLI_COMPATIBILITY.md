# CLI Compatibility Analysis

This document describes CLI argument compatibility across all scripts after refactoring to use `moku_cli_common.py`.

## Common Arguments (All Scripts)

All scripts now share these common arguments:

- `device_ip` (positional, required) - Moku device IP address
- `--slot` (optional int) - Slot number containing CloudCompile
- `--platform` (optional) - Platform type: `moku_go`, `moku_lab`, `moku_pro`, `moku_delta`
- `--force` (flag) - Force connect (disconnect existing connections)
- `--bitstream` (optional Path) - Path to bitstream file (.tar)
- `--debug` (flag) - Enable debug logging for Moku library

## Script-Specific Differences

### control_slider.py
- **No incompatibilities** - Uses standard common arguments
- `--bitstream`: Optional

### upload_settings.py
- **Additional positional argument**: `config_file` (required Path)
- **Additional flag**: `--verbose` / `-v` (enables verbose loguru logging)
- `--bitstream`: **REQUIRED** (unlike other scripts where it's optional)

**CLI Incompatibility Note**: 
- `upload_settings.py` is the only script that requires `--bitstream`
- `upload_settings.py` is the only script with `--verbose` flag
- `upload_settings.py` is the only script with a second positional argument (`config_file`)

### set_and_get_test.py
- **No incompatibilities** - Uses standard common arguments
- `--slot`: Has **default value of 2** (other scripts have no default)
- `--bitstream`: Optional (not typically used)

**CLI Incompatibility Note**:
- `set_and_get_test.py` is the only script with a default value for `--slot`

### simple_linear_test.py
- **No incompatibilities** - Uses standard common arguments
- `--bitstream`: Optional

## Summary of CLI Incompatibilities

1. **`--bitstream` requirement**: Only `upload_settings.py` requires this argument
2. **`--verbose` flag**: Only `upload_settings.py` has this flag
3. **`--slot` default**: Only `set_and_get_test.py` has a default value (2)
4. **Positional arguments**: Only `upload_settings.py` has a second positional argument (`config_file`)

## Code Reduction

**Before refactoring**: ~280 lines of argument parsing code across 4 scripts
**After refactoring**: ~156 lines in `moku_cli_common.py` + ~20 lines per script = ~236 lines total

**Reduction**: ~44 lines (15.7% reduction) + improved maintainability

## Migration Notes

All scripts maintain backward compatibility - existing command-line invocations will continue to work exactly as before. The refactoring only changes internal implementation, not external CLI interface.

