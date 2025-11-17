#!/usr/bin/env python3
"""
Simple slider control for Moku device Control10 register.

Connects to a Moku device and provides a textual slider to control
the Control10 register value over the network.

Usage:
    python control_slider.py <device-ip> [--slot SLOT] [--platform PLATFORM]

Examples:
    python control_slider.py 192.168.1.100
    python control_slider.py 192.168.1.100 --slot 1
    python control_slider.py 192.168.1.100 --platform moku_go
"""

import argparse
import sys
from pathlib import Path

# Add moku-models to path
PROJECT_ROOT = Path(__file__).parent
MOKU_MODELS = PROJECT_ROOT / "moku-models-v4"
sys.path.insert(0, str(MOKU_MODELS))

try:
    from moku.instruments import MultiInstrument, CloudCompile
except ImportError:
    print("Error: moku library not installed. Run: uv sync")
    sys.exit(1)

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label
from textual_slider import Slider


class ControlSliderApp(App):
    """App for controlling Moku Control10 register via slider."""

    CSS = """
    Screen {
        align: center middle;
    }
    
    Container {
        width: 70;
        height: auto;
        border: solid $primary;
        padding: 1;
    }
    
    Horizontal {
        height: 5;
        align: center middle;
    }
    
    Vertical {
        width: 100%;
        align: center middle;
    }
    
    Label {
        width: 100%;
        text-align: center;
        margin: 1;
    }
    
    Static {
        width: 100%;
        text-align: center;
        margin: 1;
        padding: 1;
        background: $surface;
    }
    
    #status {
        height: 3;
    }
    """

    def __init__(self, moku_device: MultiInstrument, cloud_compile: CloudCompile, slot_num: int):
        """Initialize with Moku device connection."""
        super().__init__()
        self.moku = moku_device
        self.cc = cloud_compile
        self.slot_num = slot_num
        self.current_value = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Label("Moku Control10 Slider", id="title"),
                Static(f"Slot {self.slot_num}: CloudCompile", id="slot-info"),
                Horizontal(
                    Label("Control10 Value: ", id="value-label"),
                    Static("0", id="value-display"),
                ),
                Slider(
                    min=0,
                    max=65535,  # 16-bit unsigned
                    step=1,
                    value=0,
                    id="control-slider"
                ),
                Static("", id="status"),
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        self.title = "Moku Control10 Slider"
        # Try to read current Control10 value
        try:
            current = self.cc.get_control(10)
            if current is not None:
                self.current_value = current & 0xFFFF  # Mask to 16 bits
                slider = self.query_one("#control-slider", Slider)
                slider.value = self.current_value
                self.query_one("#value-display", Static).update(str(self.current_value))
                self.query_one("#status", Static).update(f"Read current value: {self.current_value}")
        except Exception as e:
            self.query_one("#status", Static).update(f"Could not read Control10: {e}")

    def on_slider_changed(self, event: Slider.Changed) -> None:
        """Handle slider value changes."""
        value = int(event.value)
        try:
            # Update Control10 register
            self.cc.set_control(10, value)
            self.current_value = value
            self.query_one("#value-display", Static).update(str(value))
            self.query_one("#status", Static).update(f"✓ Control10 set to {value}")
        except Exception as e:
            self.query_one("#status", Static).update(f"✗ Error setting Control10: {e}")

    def on_unmount(self) -> None:
        """Clean up on exit."""
        try:
            self.moku.relinquish_ownership()
        except Exception:
            pass


def find_cloudcompile_slot(moku: MultiInstrument) -> int | None:
    """Find which slot contains CloudCompile instrument."""
    instruments = moku.get_instruments() or []
    for slot_num, instrument_name in enumerate(instruments, start=1):
        if instrument_name and instrument_name.strip() == 'CloudCompile':
            return slot_num
    return None


def connect_to_device(device_ip: str, platform_id: int | None = None, force: bool = False) -> MultiInstrument:
    """Connect to Moku device with platform detection."""
    platform_id_map = {
        1: "Moku:Lab",
        2: "Moku:Go",
        3: "Moku:Pro",
        4: "Moku:Delta",
    }
    
    if platform_id is None:
        # Try each platform
        for pid in [2, 1, 3, 4]:  # Go, Lab, Pro, Delta
            try:
                moku = MultiInstrument(
                    device_ip,
                    platform_id=pid,
                    force_connect=force,
                    persist_state=True  # Preserve existing state
                )
                print(f"✓ Connected to {platform_id_map[pid]} at {device_ip}")
                return moku
            except Exception as e:
                error_msg = str(e).lower()
                if "already exists" in error_msg or "busy" in error_msg:
                    continue
                continue
        raise ConnectionError(f"Could not connect to {device_ip}. Try --force to disconnect existing connections.")
    else:
        # Use specified platform
        moku = MultiInstrument(
            device_ip,
            platform_id=platform_id,
            force_connect=force,
            persist_state=True
        )
        platform_name = platform_id_map.get(platform_id, f"Platform {platform_id}")
        print(f"✓ Connected to {platform_name} at {device_ip}")
        return moku


def get_cloudcompile_instance(moku: MultiInstrument, slot_num: int, bitstream_path: Path | None = None) -> CloudCompile:
    """Get CloudCompile instance from specified slot.
    
    Args:
        moku: MultiInstrument instance
        slot_num: Slot number containing CloudCompile
        bitstream_path: Optional path to bitstream file. If provided, will upload it.
    
    Returns:
        CloudCompile instance
    """
    try:
        if bitstream_path:
            # Upload bitstream and get instance
            if not bitstream_path.exists():
                raise FileNotFoundError(f"Bitstream file not found: {bitstream_path}")
            cc = moku.set_instrument(slot_num, CloudCompile, bitstream=str(bitstream_path))
            return cc
        else:
            # Try to get existing instance (without bitstream parameter)
            cc = moku.set_instrument(slot_num, CloudCompile)
            return cc
    except TypeError:
        # If set_instrument requires bitstream, we can't proceed without it
        raise RuntimeError(
            f"CloudCompile in slot {slot_num} requires bitstream parameter. "
            "The instrument may not be deployed yet. Please provide --bitstream or deploy it first."
        )
    except Exception as e:
        raise RuntimeError(f"Could not access CloudCompile in slot {slot_num}: {e}")


def main():
    parser = argparse.ArgumentParser(
        description='Control Moku Control10 register via slider',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-detect platform and slot
  python control_slider.py 192.168.1.100

  # Specify slot
  python control_slider.py 192.168.1.100 --slot 1

  # Specify platform
  python control_slider.py 192.168.1.100 --platform moku_go

  # Force connect (disconnect existing connections)
  python control_slider.py 192.168.1.100 --force
        """
    )
    parser.add_argument('device_ip', help='Moku device IP address')
    parser.add_argument(
        '--slot',
        type=int,
        help='Slot number containing CloudCompile (auto-detected if not specified)'
    )
    parser.add_argument(
        '--platform',
        choices=['moku_go', 'moku_lab', 'moku_pro', 'moku_delta'],
        help='Platform type (auto-detected if not specified)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force connect (disconnect existing connections)'
    )
    
    args = parser.parse_args()
    
    # Map platform name to ID
    platform_id = None
    if args.platform:
        platform_map = {
            'moku_go': 2,
            'moku_lab': 1,
            'moku_pro': 3,
            'moku_delta': 4,
        }
        platform_id = platform_map[args.platform]
    
    # Connect to device
    print(f"Connecting to {args.device_ip}...")
    try:
        moku = connect_to_device(args.device_ip, platform_id, force=args.force)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        # Find CloudCompile slot
        if args.slot:
            slot_num = args.slot
            # Verify it's actually CloudCompile
            instruments = moku.get_instruments() or []
            if slot_num < 1 or slot_num > len(instruments):
                print(f"Error: Slot {slot_num} does not exist", file=sys.stderr)
                sys.exit(1)
            instrument_name = instruments[slot_num - 1]
            if not instrument_name or instrument_name.strip() != 'CloudCompile':
                print(f"Error: Slot {slot_num} contains '{instrument_name}', not CloudCompile", file=sys.stderr)
                sys.exit(1)
        else:
            slot_num = find_cloudcompile_slot(moku)
            if slot_num is None:
                print("Error: No CloudCompile instrument found. Please specify --slot", file=sys.stderr)
                sys.exit(1)
            print(f"Found CloudCompile in slot {slot_num}")
        
        # Get CloudCompile instance
        print(f"Accessing CloudCompile in slot {slot_num}...")
        try:
            cc = get_cloudcompile_instance(moku, slot_num)
            print("✓ CloudCompile instance ready")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        
        # Run the slider app
        print("\nStarting slider control...")
        print("Use the slider to control Control10 register.")
        print("Press Ctrl+C or Q to exit.\n")
        
        app = ControlSliderApp(moku, cc, slot_num)
        app.run()
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Disconnect
        try:
            moku.relinquish_ownership()
            print("\n✓ Disconnected")
        except Exception:
            pass


if __name__ == "__main__":
    main()

