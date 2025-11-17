#!/usr/bin/env python3
"""
Simple slider control for Moku device Control10 register.

Connects to a Moku device and provides a textual slider to control
the Control10 register value over the network.

Usage:
    python control_slider.py <device-ip> [--slot SLOT] [--platform PLATFORM] [--bitstream PATH]

Examples:
    python control_slider.py 192.168.1.100
    python control_slider.py 192.168.1.100 --slot 1
    python control_slider.py 192.168.1.100 --platform moku_go
    python control_slider.py 192.168.1.100 --bitstream ./my_bitstream.tar
"""

import argparse
import sys
import threading
import queue
from pathlib import Path

# Add moku-models to path
PROJECT_ROOT = Path(__file__).parent
MOKU_MODELS = PROJECT_ROOT / "moku-models-v4"
sys.path.insert(0, str(MOKU_MODELS))

try:
    from loguru import logger
except ImportError:
    print("Error: loguru not installed. Run: uv sync")
    sys.exit(1)

try:
    from moku.instruments import MultiInstrument, CloudCompile
    from moku import logging as moku_logging
except ImportError:
    logger.error("moku library not installed. Run: uv sync")
    sys.exit(1)

# Configure loguru with nice formatting
logger.remove()  # Remove default handler
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
    colorize=True
)

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label, Input, Button
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
    
    #percent-input {
        width: 20;
        margin: 1;
    }
    
    #apply-button {
        width: 30;
        margin: 1;
    }
    """

    def __init__(self, moku_device: MultiInstrument, cloud_compile: CloudCompile, slot_num: int):
        """Initialize with Moku device connection.
        
        Note: The connection is kept open for the lifetime of the app.
        This allows fast set_control calls without reconnection overhead.
        """
        super().__init__()
        self.moku = moku_device  # Persistent connection - kept open
        self.cc = cloud_compile  # Persistent CloudCompile instance - kept open
        self.slot_num = slot_num
        self.current_value = 0
        self.pending_value = 0  # Value waiting to be applied
        self._updating = False  # Flag to prevent recursive updates
        self._update_queue = queue.Queue()  # Queue for thread-safe UI updates

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
                    max=32767,  # 0x7FFF (half of 16-bit range)
                    step=1,
                    value=0,
                    id="control-slider"
                ),
                Horizontal(
                    Label("Power (%): ", id="percent-label"),
                    Input(
                        value="0.0",
                        placeholder="0.0 - 100.0",
                        id="percent-input",
                        type="number"
                    ),
                ),
                Button("Apply", id="apply-button", variant="primary"),
                Static("", id="status"),
            )
        )
        yield Footer()

    def _percent_to_register(self, percent: float) -> int:
        """Convert percentage (0-100) to register value (0-32767)."""
        return int((percent / 100.0) * 32767)
    
    def _register_to_percent(self, register_value: int) -> float:
        """Convert register value (0-32767) to percentage (0-100)."""
        return (register_value / 32767.0) * 100.0
    
    def _update_display(self, register_value: int) -> None:
        """Update all displays with the given register value."""
        if self._updating:
            return  # Prevent recursive updates
        
        self._updating = True
        try:
            # Clamp to max value (32767)
            register_value = max(0, min(32767, register_value))
            self.pending_value = register_value
            percent = self._register_to_percent(register_value)
            
            # Update value display
            self.query_one("#value-display", Static).update(str(register_value))
            
            # Update slider (programmatic updates shouldn't trigger events)
            slider = self.query_one("#control-slider", Slider)
            slider.value = register_value
            
            # Update percentage input
            percent_input = self.query_one("#percent-input", Input)
            percent_input.value = f"{percent:.2f}"
        finally:
            self._updating = False
    
    def on_mount(self) -> None:
        """Called when app starts."""
        self.title = "Moku Control10 Slider"
        # Set up periodic queue processing
        self.set_interval(0.1, self._process_update_queue)
        
        # Try to read current Control10 value
        try:
            current = self.cc.get_control(10)
            if current is not None:
                self.current_value = current & 0xFFFF  # Mask to 16 bits
                # Clamp to max value (32767)
                if self.current_value > 32767:
                    self.current_value = 32767
                self._update_display(self.current_value)
                self.query_one("#status", Static).update(f"Read current value: {self.current_value} ({self._register_to_percent(self.current_value):.2f}%)")
        except Exception as e:
            self.query_one("#status", Static).update(f"Could not read Control10: {e}")

    def on_slider_changed(self, event: Slider.Changed) -> None:
        """Handle slider value changes (update display, but don't apply yet)."""
        if self._updating:
            return  # Ignore events triggered by programmatic updates
        
        value = int(event.value)
        self._update_display(value)
        percent = self._register_to_percent(value)
        self.query_one("#status", Static).update(f"Pending: {value} ({percent:.2f}%) - Click Apply to set")
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle percentage input changes."""
        if self._updating:
            return  # Ignore events triggered by programmatic updates
        
        if event.input.id == "percent-input":
            try:
                percent_str = event.value.strip()
                if percent_str:
                    percent = float(percent_str)
                    # Clamp to 0-100 range
                    percent = max(0.0, min(100.0, percent))
                    register_value = self._percent_to_register(percent)
                    self._update_display(register_value)
                    self.query_one("#status", Static).update(f"Pending: {register_value} ({percent:.2f}%) - Click Apply to set")
            except ValueError:
                # Invalid input, ignore
                pass
    
    def _apply_control_value(self, value: int) -> None:
        """Apply control value in background thread and update UI via queue."""
        import time
        start_time = time.time()
        
        # Put initial status update in queue (thread-safe)
        self._update_queue.put(("status", f"Sending {value} to device..."))
        
        try:
            # This is the blocking network call - runs in background thread
            # The connection is kept open, so this should be relatively fast
            self.cc.set_control(10, value)
            
            elapsed = time.time() - start_time
            self.current_value = value
            percent = self._register_to_percent(value)
            
            # Put success update in queue with timing info
            if elapsed > 1.0:
                self._update_queue.put(("success", f"✓ Control10 set to {value} ({percent:.2f}%) - took {elapsed:.1f}s"))
            else:
                self._update_queue.put(("success", f"✓ Control10 set to {value} ({percent:.2f}%)"))
        except Exception as e:
            elapsed = time.time() - start_time
            # Put error update in queue
            self._update_queue.put(("error", f"✗ Error setting Control10: {e} (after {elapsed:.1f}s)"))
    
    def _process_update_queue(self) -> None:
        """Process updates from the background thread queue."""
        try:
            while True:
                update_type, message = self._update_queue.get_nowait()
                if update_type == "status":
                    self.query_one("#status", Static).update(message)
                elif update_type == "success":
                    self.query_one("#status", Static).update(message)
                    self.query_one("#apply-button", Button).disabled = False
                elif update_type == "error":
                    self.query_one("#status", Static).update(message)
                    self.query_one("#apply-button", Button).disabled = False
        except queue.Empty:
            pass
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "apply-button":
            # Optimistic UI update - show the value immediately
            # This makes the UI feel more responsive
            value = self.pending_value
            percent = self._register_to_percent(value)
            self.query_one("#status", Static).update(f"Applying {value} ({percent:.2f}%)...")
            
            # Disable button while applying
            button = self.query_one("#apply-button", Button)
            button.disabled = True
            
            # Run the blocking network call in a background thread
            thread = threading.Thread(
                target=self._apply_control_value,
                args=(value,),
                daemon=True
            )
            thread.start()

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
                logger.success(f"Connected to {platform_id_map[pid]} at {device_ip}")
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
        logger.success(f"Connected to {platform_name} at {device_ip}")
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


def handle_arg_parsing():
    """Parse command line arguments and configure logging."""
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

  # Upload bitstream and control
  python control_slider.py 192.168.1.100 --bitstream ./my_bitstream.tar

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
    parser.add_argument(
        '--bitstream',
        type=Path,
        help='Path to bitstream file (.tar) to upload to CloudCompile'
    )
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging for Moku library'
    )
    
    args = parser.parse_args()
    
    # Enable Moku debug logging if requested
    if args.debug:
        moku_logging.enable_debug_logging()
        logger.info("Moku debug logging enabled")
    
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
    
    return args, platform_id


def main():
    args, platform_id = handle_arg_parsing()
    
    # Connect to device
    logger.info(f"Connecting to {args.device_ip}...")
    try:
        moku = connect_to_device(args.device_ip, platform_id, force=args.force)
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        sys.exit(1)
    
    try:
        # Find CloudCompile slot
        if args.slot:
            slot_num = args.slot
            # Verify slot exists
            instruments = moku.get_instruments() or []
            if slot_num < 1 or slot_num > len(instruments):
                logger.error(f"Slot {slot_num} does not exist (device has {len(instruments)} slot(s))")
                sys.exit(1)
            
            # If bitstream is provided, we can deploy to this slot even if it's not CloudCompile
            if args.bitstream:
                instrument_name = instruments[slot_num - 1] if slot_num <= len(instruments) else None
                if instrument_name and instrument_name.strip() and instrument_name.strip() != 'CloudCompile':
                    logger.warning(f"Slot {slot_num} contains '{instrument_name}'. Will deploy CloudCompile with bitstream.")
            else:
                # Without bitstream, verify it's actually CloudCompile
                instrument_name = instruments[slot_num - 1]
                if not instrument_name or instrument_name.strip() != 'CloudCompile':
                    logger.error(f"Slot {slot_num} contains '{instrument_name}', not CloudCompile. Use --bitstream to deploy.")
                    sys.exit(1)
        else:
            # Auto-detect CloudCompile slot
            slot_num = find_cloudcompile_slot(moku)
            if slot_num is None:
                if args.bitstream:
                    # If bitstream provided but no CloudCompile found, default to slot 1
                    slot_num = 1
                    logger.info(f"No CloudCompile found. Will deploy to slot {slot_num} with bitstream.")
                else:
                    logger.error("No CloudCompile instrument found. Please specify --slot or provide --bitstream")
                    sys.exit(1)
            else:
                logger.info(f"Found CloudCompile in slot {slot_num}")
        
        # Resolve bitstream path if provided
        bitstream_path = None
        if args.bitstream:
            bitstream_path = args.bitstream
            # Resolve relative paths
            if not bitstream_path.is_absolute():
                bitstream_path = PROJECT_ROOT / bitstream_path
            if not bitstream_path.exists():
                logger.error(f"Bitstream file not found: {bitstream_path}")
                sys.exit(1)
            logger.info(f"Using bitstream: {bitstream_path.name}")
        
        # Get CloudCompile instance
        logger.info(f"Accessing CloudCompile in slot {slot_num}...")
        try:
            cc = get_cloudcompile_instance(moku, slot_num, bitstream_path)
            if bitstream_path:
                logger.success("CloudCompile instance ready (bitstream uploaded)")
            else:
                logger.success("CloudCompile instance ready")
        except Exception as e:
            logger.error(f"Failed to get CloudCompile instance: {e}")
            sys.exit(1)
        
        # Run the slider app
        logger.info("\nStarting slider control...")
        logger.info("Use the slider to control Control10 register.")
        logger.info("Press Ctrl+C or Q to exit.\n")
        
        app = ControlSliderApp(moku, cc, slot_num)
        app.run()
        
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.debug("Exception details:", exc_info=True)
        sys.exit(1)
    finally:
        # Disconnect
        try:
            logger.debug("Disconnecting from device...")
            moku.relinquish_ownership()
            logger.success("Disconnected from device")
        except Exception as e:
            logger.debug(f"Error during disconnect: {e}")


if __name__ == "__main__":
    main()

