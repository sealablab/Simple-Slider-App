# Example Config: Oscilloscope + CloudCompile (2025-11-17)

## Overview

This directory contains a captured Moku device configuration from a Moku:Go running:
- **Slot 1**: Oscilloscope
- **Slot 2**: CloudCompile (custom instrument)

## Device Info

- **Platform**: Moku:Go (Platform ID: 2)
- **Serial Number**: 007985
- **MokuOS Version**: 4.0.3
- **Captured**: 2025-11-17 20:31:10

## Files

### Configuration Files (.mokuconf)
- `mim_config.mokuconf` - Multi-Instrument Mode configuration (device-level)
- `slot1_Oscilloscope.mokuconf` - Oscilloscope instrument settings
- `slot2_CloudCompile.mokuconf` - CloudCompile instrument settings
- `metadata.json` - Capture metadata (device info, timestamp)

### Analysis
- `MIM_Hierarchy/` - Extracted and analyzed .mokuconf file structure
  - See [MIM_Hierarchy/Extracted_Hierarchy_README.md](MIM_Hierarchy/Extracted_Hierarchy_README.md) for detailed structure analysis

## Usage

### Capture (how this was created)
```bash
python moku_grab.py 192.168.13.147 \
  --platform 2 \
  --output example_configs/2025-11-17_oscilloscope_cloudcompile \
  --bitstream cr10_bits.tar
```

### Restore to Device
```bash
# Dry run first to preview
python moku_set.py 192.168.13.147 \
  example_configs/2025-11-17_oscilloscope_cloudcompile \
  --dry-run

# Actual restore
python moku_set.py 192.168.13.147 \
  example_configs/2025-11-17_oscilloscope_cloudcompile \
  --bitstream cr10_bits.tar
```

## Notes

- **CloudCompile**: Requires `--bitstream cr10_bits.tar` argument for both capture and restore
- **Platform compatibility**: This config is for Moku:Go (2 slots) and won't work on Moku:Lab/Pro without modification
