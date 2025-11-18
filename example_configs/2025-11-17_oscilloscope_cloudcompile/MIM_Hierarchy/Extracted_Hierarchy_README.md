

# Moku .mokuconf File Structure Analysis

This directory contains extracted and pretty-printed contents from `.mokuconf` files captured using `moku_grab.py`.

## What Are .mokuconf Files?

`.mokuconf` files are **ZIP archives** that store Moku device configurations. They can be saved at two levels:
1. **MIM (Multi-Instrument Mode) level** - Entire device configuration including all slots
2. **Individual instrument level** - Single instrument settings for a specific slot

## Extraction Process

The analysis was performed by:
1. Running `moku_grab.py` to capture device state from Moku at 192.168.13.147
2. Extracting the ZIP archives using `unzip`
3. Pretty-printing all JSON files for human readability
4. Analyzing the hierarchical structure of configuration data

## File Structure Overview

### MIM-Level Configuration (`mim_config.mokuconf`)

Contains 4 files:



| File | Description | Link |
|------|-------------|------|
| `MI_Config` | Main configuration with hierarchical node structure | [MI_Config.json](MI_Config.json) |
| `MI_Config_compatibility.json` | Platform and hardware compatibility info | [MI_Config_compatibility.json](MI_Config_compatibility.json) |
| `metadata.json` | App version and tool info | [MIM_metadata.json](MIM_metadata.json) |
| `compatibility.json` | Archive and libmoku version | [MIM_compatibility.json](MIM_compatibility.json) |

**MI_Config Structure:**
- Platform settings (platform ID, hardware version)
- Layout (slots: 2, analog I/O: 2 in/2 out, buses: 1, DIO ports: 1)
- Instrument assignments (slot 1: Oscilloscope ID=1, slot 2: CloudCompile ID=255)
- Signal routing (input/output connections)
- AFE (Analog Front End) settings:
  - Input coupling (AC/DC)
  - Input impedance (1MΩ / 50Ω)
  - Input/output ranges (Vpp)
- DIO directions

### Slot 1: Oscilloscope (`slot1_Oscilloscope.mokuconf`)

Contains 4 files:

| File | Description | Link |
|------|-------------|------|
| `2_0_Oscilloscope` | Instrument-specific settings | [Slot1_Oscilloscope.json](Slot1_Oscilloscope.json) |
| `2_0_Oscilloscope_compatibility.json` | Instrument compatibility info | [Slot1_Oscilloscope_compatibility.json](Slot1_Oscilloscope_compatibility.json) |
| `metadata.json` | App version | [Slot1_metadata.json](Slot1_metadata.json) |
| `compatibility.json` | Archive version | [Slot1_compatibility.json](Slot1_compatibility.json) |

**Oscilloscope Settings (64 total parameters):**
- Channel configuration (A, B, Math channel)
- Timebase settings (acquisition mode, interpolation, frame length, time span/offset)
- Trigger configuration (mode, channel, type, edge, levels, hysteresis, noise reject)
- Output waveform generators (A, B with waveform type, frequency, amplitude, etc.)
- UI state (active channel, drawer state, axis ranges, measurements)

### Slot 2: CloudCompile (`slot2_CloudCompile.mokuconf`)

Contains 4 files:

| File | Description | Link |
|------|-------------|------|
| `2_1_Cloud Compile` | Custom instrument control registers | [Slot2_CloudCompile.json](Slot2_CloudCompile.json) |
| `2_1_Cloud Compile_compatibility.json` | Instrument compatibility info | [Slot2_CloudCompile_compatibility.json](Slot2_CloudCompile_compatibility.json) |
| `metadata.json` | App version | [Slot2_metadata.json](Slot2_metadata.json) |
| `compatibility.json` | Archive version | [Slot2_compatibility.json](Slot2_compatibility.json) |

**CloudCompile Settings:**
- 16 control registers (CR0-CR15) with values
- UI auto-commit setting
- Note: Control register meanings are custom instrument-specific

## Hierarchical Node Structure

All main configuration files use a common JSON structure:

```json
{
  "name": ["Instrument state", "InstrumentName"],
  "node_serialization_version": 1,
  "uid": "unique-identifier",
  "subnodes": [
    {
      "name": ["Parameter", "Subparameter"],
      "uid": "unique-identifier",
      "value": "base64-encoded-value",
      "value_string": "human-readable-value"
    }
  ]
}
```

### Key Fields:
- **`name`**: Hierarchical path (array of strings)
- **`uid`**: Unique identifier for the parameter (UUID format)
- **`value`**: Base64-encoded binary representation
- **`value_string`**: Human-readable string representation (for display)
- **`subnodes`**: Child parameters (recursive structure)

## Compatibility Information

### Platform Details:
- **Platform ID**: 2 (Moku:Go)
- **Hardware Version**: [4, 0, 0]
- **Layout**: 2 slots, 2 analog inputs, 2 analog outputs, 1 bus, 1 DIO port

### Software Versions:
- **App**: Moku REST API
- **App Version**: 4.0.3.1
- **libmoku Version**: [4, 0, 3]
- **Archive Version**: 0

## Usage for moku_set.py

This structure analysis informs the design of `moku_set.py`, which will:
1. Accept a directory containing `.mokuconf` files
2. Extract and validate compatibility information
3. Load MIM-level configuration via `MultiInstrument.load_configuration()`
4. Load individual instrument settings via `Instrument.load_settings()`
5. Handle special cases (CloudCompile requires bitstream path)

## Files in This Directory

```
MIM_Hierarchy/
├── Extracted_Hierarchy_README.md          # This file
├── MI_Config.json                         # MIM-level main config
├── MI_Config_compatibility.json           # MIM compatibility info
├── MIM_metadata.json                      # MIM metadata
├── MIM_compatibility.json                 # MIM archive version
├── Slot1_Oscilloscope.json               # Oscilloscope settings
├── Slot1_Oscilloscope_compatibility.json # Oscilloscope compatibility
├── Slot1_metadata.json                   # Slot 1 metadata
├── Slot1_compatibility.json              # Slot 1 archive version
├── Slot2_CloudCompile.json               # CloudCompile registers
├── Slot2_CloudCompile_compatibility.json # CloudCompile compatibility
├── Slot2_metadata.json                   # Slot 2 metadata
└── Slot2_compatibility.json              # Slot 2 archive version
```
