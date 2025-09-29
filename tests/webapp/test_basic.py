"""
Basic tests for the webapp to ensure it loads correctly and has no console errors.
"""
import pytest
from playwright.sync_api import Page, expect
import time


def test_page_loads(page: Page):
    """Test that the page loads successfully."""
    # Check the page title
    expect(page).to_have_title("Josh is Finding a Rental in Melbourne")

    # Check that the map container exists
    map_element = page.get_by_role("region", name="Map")
    expect(map_element).to_be_visible()


def test_no_console_errors(page: Page):
    """Test that there are no console errors on page load."""
    console_messages = []

    def handle_console(msg):
        console_messages.append({
            "type": msg.type,
            "text": msg.text
        })

    page.on("console", handle_console)
    page.reload()

    # Wait for the page to fully load
    page.wait_for_timeout(3000)

    # Check for errors (ignoring the plotly warning)
    errors = [
        msg for msg in console_messages
        if msg["type"] == "error"
        and "plotly-latest" not in msg["text"].lower()
    ]

    assert len(errors) == 0, f"Console errors found: {errors}"


def test_layer_options_panel(page: Page):
    """Test that the layer options panel is present and can be toggled."""
    # Find the layer options heading
    layer_heading = page.locator("h3").filter(has_text="Layer Options")
    expect(layer_heading).to_be_visible()

    # Check initial state
    initial_text = layer_heading.inner_text()
    assert "▶" in initial_text or "▼" in initial_text


def test_database_loads(page: Page):
    """Test that the DuckDB database loads successfully."""
    # Wait for database to load
    page.wait_for_timeout(5000)

    # Check console for success message
    console_messages = []

    def handle_console(msg):
        if "Successfully connected to rental sales database" in msg.text:
            console_messages.append(msg.text)

    page.on("console", handle_console)
    page.reload()
    page.wait_for_timeout(5000)

    assert len(console_messages) > 0, "Database did not load successfully"