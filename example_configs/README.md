# Example Moku Configurations

This directory contains example configurations captured from Moku devices using `moku_grab.py`.

## Available Examples

### [2025-11-17_oscilloscope_cloudcompile/](2025-11-17_oscilloscope_cloudcompile/)
- **Platform**: Moku:Go (2 slots)
- **Instruments**: Oscilloscope (Slot 1) + CloudCompile (Slot 2)
- **Special requirements**: Requires bitstream file for CloudCompile
- **Use case**: Example of custom instrument with standard monitoring

## Using These Examples

### To Restore a Configuration
```bash
# Preview what will be loaded (dry run)
python moku_set.py <device-ip> example_configs/<config-name> --dry-run

# Load configuration to device
python moku_set.py <device-ip> example_configs/<config-name>
```

### To Create New Examples
```bash
# Capture current device state
python moku_grab.py <device-ip> --output example_configs/<name>
```

## Directory Structure

Each example configuration directory contains:
- `*.mokuconf` - Configuration archive files (ZIP format)
- `metadata.json` - Capture metadata (device info, timestamp)
- `README.md` - Example-specific documentation
- `MIM_Hierarchy/` - (Optional) Detailed structure analysis

## File Format

See [2025-11-17_oscilloscope_cloudcompile/MIM_Hierarchy/Extracted_Hierarchy_README.md](2025-11-17_oscilloscope_cloudcompile/MIM_Hierarchy/Extracted_Hierarchy_README.md) for detailed information about the .mokuconf file format and structure.
