# Moku Python API Documentation

This directory contains comprehensive markdown documentation for the Moku Python API package (v4.0.3.1). The documentation mirrors the structure of the installed pip package and provides high-level overviews of all modules, classes, and functions.

## Package Structure

### Core Modules

- [__init__.md](./__init__.md) - Main package initialization, `Moku` base class, and `MultiInstrumentSlottable` mixin
- [session.md](./session.md) - HTTP session management and API communication (`RequestSession`)
- [finder.md](./finder.md) - Device discovery via Zeroconf/mDNS (`Finder`)
- [exceptions.md](./exceptions.md) - Exception hierarchy (15 exception classes)
- [utilities.md](./utilities.md) - Utility functions (device discovery, version checking, config paths)
- [logging.md](./logging.md) - Logging infrastructure (`LoggingContext`, logger configuration)
- [version.md](./version.md) - Version constants and compatibility information
- [cli.md](./cli.md) - Deprecated CLI entry point

### Instruments

- [instruments/__init__.md](./instruments/__init__.md) - Instrument package exports (all 17 instruments)

#### Signal Generators
- [instruments/_waveformgenerator.md](./instruments/_waveformgenerator.md) - Basic waveform generation (Sine, Square, Ramp, Pulse, Noise, DC)
- [instruments/_awg.md](./instruments/_awg.md) - Arbitrary Waveform Generator with custom waveforms

#### Analyzers & Measurement
- [instruments/_oscilloscope.md](./instruments/_oscilloscope.md) - Oscilloscope with triggering and data acquisition
- [instruments/_spectrumanalyzer.md](./instruments/_spectrumanalyzer.md) - Frequency-domain analysis (0Hz-30MHz)
- [instruments/_phasemeter.md](./instruments/_phasemeter.md) - Phase and amplitude measurement (2-200MHz)
- [instruments/_logicanalyzer.md](./instruments/_logicanalyzer.md) - Digital signal analysis with protocol decoders
- [instruments/_tfa.md](./instruments/_tfa.md) - Time-Frequency Analyzer with sub-nanosecond precision
- [instruments/_fra.md](./instruments/_fra.md) - Frequency Response Analyzer

#### Signal Processing
- [instruments/_digitalfilterbox.md](./instruments/_digitalfilterbox.md) - IIR digital filtering
- [instruments/_firfilter.md](./instruments/_firfilter.md) - FIR digital filtering
- [instruments/_lockinamp.md](./instruments/_lockinamp.md) - Lock-In Amplifier with dual-phase demodulation

#### Control & Feedback
- [instruments/_pidcontroller.md](./instruments/_pidcontroller.md) - PID Controller with comprehensive control loops
- [instruments/_laserlockbox.md](./instruments/_laserlockbox.md) - Laser frequency stabilization

#### Data Acquisition
- [instruments/_datalogger.md](./instruments/_datalogger.md) - Voltage logging and waveform generation

#### Advanced Features
- [instruments/_mim.md](./instruments/_mim.md) - Multi-Instrument Mode for slot-based management
- [instruments/_cloudcompile.md](./instruments/_cloudcompile.md) - Cloud-compiled FPGA bitstream deployment
- [instruments/_nn.md](./instruments/_nn.md) - Neural Network inference engine
- [instruments/_stream.md](./instruments/_stream.md) - Streaming infrastructure base class

### Neural Network Utilities

- [nn/__init__.md](./nn/__init__.md) - Neural network package initialization
- [nn/_linn.md](./nn/_linn.md) - Keras to .linn model conversion utilities

## Quick Reference

### Most Common Classes

- **Device Management**: [Moku](./__init__.md) - Base class for all Moku devices
- **Device Discovery**: [Finder](./finder.md) - Find Moku devices on network
- **Session Management**: [RequestSession](./session.md) - HTTP API communication

### Instrument Categories

| Category | Instruments |
|----------|-------------|
| **Generators** | [WaveformGenerator](./instruments/_waveformgenerator.md), [ArbitraryWaveformGenerator](./instruments/_awg.md) |
| **Oscilloscopes** | [Oscilloscope](./instruments/_oscilloscope.md) |
| **Spectrum** | [SpectrumAnalyzer](./instruments/_spectrumanalyzer.md), [Phasemeter](./instruments/_phasemeter.md) |
| **Filters** | [DigitalFilterBox](./instruments/_digitalfilterbox.md), [FIRFilterBox](./instruments/_firfilter.md) |
| **Control** | [PIDController](./instruments/_pidcontroller.md), [LaserLockBox](./instruments/_laserlockbox.md) |
| **Analysis** | [FrequencyResponseAnalyzer](./instruments/_fra.md), [LockInAmp](./instruments/_lockinamp.md), [TimeFrequencyAnalyzer](./instruments/_tfa.md) |
| **Digital** | [LogicAnalyzer](./instruments/_logicanalyzer.md) |
| **Data** | [Datalogger](./instruments/_datalogger.md) |
| **Advanced** | [MultiInstrument](./instruments/_mim.md), [CloudCompile](./instruments/_cloudcompile.md), [NeuralNetwork](./instruments/_nn.md) |

## Documentation Format

Each markdown file includes:
- **YAML frontmatter** - Date, source file path, and title
- **Overview** - High-level description of the module's purpose
- **Key Dependencies** - Important imports and what they're used for
- **Classes** - Main classes with method signatures
- **Functions** - Module-level functions with parameters and return types
- **Obsidian callouts** - Important notes, warnings, and examples
- **See Also** - Links to related modules and official documentation

## About This Documentation

- **Source Package**: `moku` v4.0.3.1
- **Format**: Obsidian-friendly markdown
- **Level**: High-level overview focusing on public APIs
- **Generated**: 2025-11-17
- **Original Package Location**: `/Users/johnycsh/workspace/SimpleSliderApp/.venv/lib/python3.12/site-packages/moku`

## Additional Resources

- [Official Moku API Documentation](https://apis.liquidinstruments.com/starting.html)
- Original Python package: `pip install moku`
