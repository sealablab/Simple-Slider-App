"""Simple example demonstrating textual-slider usage."""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Header, Footer, Static, Label
from textual_slider import Slider


class SliderApp(App):
    """A simple app demonstrating textual-slider."""

    CSS = """
    Screen {
        align: center middle;
    }
    
    Container {
        width: 60;
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
    """

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header(show_clock=True)
        yield Container(
            Vertical(
                Label("Textual Slider Example", id="title"),
                Static("Move the slider to see the value change", id="instructions"),
                Horizontal(
                    Label("Value: ", id="value-label"),
                    Static("0", id="value-display"),
                ),
                Slider(
                    min=0,
                    max=100,
                    step=1,
                    value=50,
                    id="main-slider"
                ),
                Static("", id="status"),
            )
        )
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts."""
        self.title = "Textual Slider Example"
        # Initialize display with initial slider value
        slider = self.query_one("#main-slider", Slider)
        self.query_one("#value-display", Static).update(str(slider.value))

    def on_slider_changed(self, event: Slider.Changed) -> None:
        """Handle slider value changes."""
        value = event.value
        self.query_one("#value-display", Static).update(str(value))
        self.query_one("#status", Static).update(f"Slider changed to: {value}")


def main():
    """Run the slider example app."""
    app = SliderApp()
    app.run()


if __name__ == "__main__":
    main()

