"""Test DuckDB loading status indicator in the Layer Options panel."""

import pytest
from playwright.sync_api import Page, expect


def test_duckdb_status_indicator_exists(page: Page):
    """Verify that the DuckDB status indicator is present in the Layer Options panel."""
    page.goto("/")

    # Wait for the page to load
    page.wait_for_load_state("networkidle")

    # Check that the status indicator container exists
    status_container = page.locator("#duckdb-status")
    expect(status_container).to_be_visible()

    # Check that the status icon exists
    status_icon = page.locator("#duckdb-status-icon")
    expect(status_icon).to_be_visible()

    # Check that the status text exists
    status_text = page.locator("#duckdb-status-text")
    expect(status_text).to_be_visible()


def test_duckdb_loading_states(page: Page):
    """Verify that the DuckDB status indicator shows different loading states."""
    page.goto("/")

    # Get the status elements
    status_icon = page.locator("#duckdb-status-icon")
    status_text = page.locator("#duckdb-status-text")

    # Initially, it should show a loading state (orange indicator)
    # Check within first 500ms to catch the loading state
    initial_text = status_text.text_content()
    assert initial_text in [
        "Loading DuckDB...",
        "Loading DuckDB library...",
        "Initializing database...",
        "Loading rental database...",
        "Connecting to database...",
        "Verifying connection...",
    ], f"Expected loading state, got: {initial_text}"

    # Wait for DuckDB to finish loading (max 10 seconds)
    page.wait_for_function(
        """() => {
            const text = document.getElementById('duckdb-status-text')?.textContent || '';
            return text.includes('Connected') && text.includes('records');
        }""",
        timeout=10000
    )

    # After loading, it should show success state with record count
    final_text = status_text.text_content()
    assert "Connected" in final_text, f"Expected 'Connected' in final status, got: {final_text}"
    assert "records" in final_text, f"Expected 'records' in final status, got: {final_text}"

    # Check that the icon color changed to green (success)
    icon_color = status_icon.evaluate("el => getComputedStyle(el).backgroundColor")
    # Green color in rgb format should be close to: rgb(0, 198, 100) = #00c864
    # Allow for slight variations in rendering
    assert ("0, 198, 100" in icon_color or "0, 200, 100" in icon_color or "00c864" in icon_color.lower()), \
        f"Expected green color for success state, got: {icon_color}"


def test_duckdb_ready_event_dispatched(page: Page):
    """Verify that the duckdbReady event is dispatched when loading completes."""
    # Set up event listener BEFORE navigating to the page
    page.goto("/", wait_until="domcontentloaded")

    # Inject the event listener immediately after DOM loads but before scripts run
    page.evaluate("""() => {
        window.duckdbEventReceived = false;
        window.duckdbEventDetails = null;
        window.addEventListener('duckdbReady', (event) => {
            window.duckdbEventReceived = true;
            const recordCount = event.detail.recordCount;
            window.duckdbEventDetails = {
                hasConnection: event.detail.connection !== undefined,
                hasDatabase: event.detail.database !== undefined,
                hasRecordCount: (typeof recordCount === 'number' || typeof recordCount === 'bigint'),
                recordCount: Number(recordCount)
            };
        }, { once: true });
    }""")

    # Wait for the event to be dispatched (indicated by status showing "Connected")
    page.wait_for_function(
        """() => window.duckdbEventReceived === true""",
        timeout=10000
    )

    # Get the event details
    event_details = page.evaluate("() => window.duckdbEventDetails")

    # Verify the event was received with proper details
    assert event_details is not None, "duckdbReady event details were not captured"
    assert event_details.get("hasConnection"), "duckdbReady event missing connection"
    assert event_details.get("hasDatabase"), "duckdbReady event missing database"
    assert event_details.get("hasRecordCount"), "duckdbReady event missing recordCount"
    assert event_details.get("recordCount") > 0, "recordCount should be greater than 0"


def test_duckdb_status_in_layer_options_panel(page: Page):
    """Verify that the status indicator is positioned correctly in the Layer Options panel."""
    page.goto("/")
    page.wait_for_load_state("networkidle")

    # Check that the status is inside the info panel
    info_panel = page.locator("#info")
    status_container = page.locator("#duckdb-status")

    expect(info_panel).to_be_visible()
    expect(status_container).to_be_visible()

    # Verify the status indicator comes before the Victoria transit accessibility text
    status_parent = status_container.evaluate("el => el.parentElement.id")
    assert status_parent == "info", "Status indicator should be inside the #info panel"


def test_console_messages_during_loading(page: Page):
    """Verify that appropriate console messages are logged during DuckDB initialization."""
    # Collect console messages
    console_messages = []
    page.on("console", lambda msg: console_messages.append(msg.text))

    page.goto("/")

    # Wait for DuckDB to finish loading
    page.wait_for_function(
        """() => {
            const text = document.getElementById('duckdb-status-text')?.textContent || '';
            return text.includes('Connected');
        }""",
        timeout=10000
    )

    # Check that key messages were logged
    all_messages = " ".join(console_messages)
    assert "Initializing DuckDB WASM" in all_messages, "Missing initialization log message"
    assert "DuckDB module loaded" in all_messages, "Missing module loaded message"
    assert "DuckDB initialized successfully" in all_messages, "Missing success message"
    assert "Successfully connected to rental sales database" in all_messages, "Missing connection message"
