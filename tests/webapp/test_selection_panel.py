"""
Tests for the selection panel and chart positioning.
"""
import pytest
from playwright.sync_api import Page, expect
import time


def test_selection_panel_hidden_initially(page: Page):
    """Test that the selection panel is hidden when no items are selected."""
    panel = page.locator("#selection-panel")
    expect(panel).to_be_hidden()

    # Check height is 0
    height = panel.evaluate("el => el.style.height")
    assert height == "0" or height == "0px"


def test_lga_selection_shows_panel(page: Page):
    """Test that selecting LGA polygons shows the selection panel."""
    # Wait for page to fully load
    page.wait_for_timeout(5000)

    # Check that selectedItems is available
    has_selected_items = page.evaluate("() => typeof window.selectedItems !== 'undefined'")

    if not has_selected_items:
        pytest.skip("selectedItems not available on this page")

    # Simulate LGA selection via JavaScript
    success = page.evaluate("""
        () => {
            try {
                // Wait for LGA data to be loaded
                const layers = window.deckgl?.props?.layers || [];
                const lgaLayer = layers.find(l => l.id === 'lga-boundaries');

                if (lgaLayer && lgaLayer.props && lgaLayer.props.data && lgaLayer.props.data.features) {
                    const features = lgaLayer.props.data.features;
                    if (features.length >= 2) {
                        // Clear any existing selections
                        if (window.selectedItems && window.selectedItems.clear) {
                            window.selectedItems.clear();
                        }

                        // Select two LGAs
                        const lga1 = features[0];
                        const lga2 = features[1];

                        if (window.selectedItems && window.selectedItems.set) {
                            window.selectedItems.set('lga-' + lga1.properties.LGA_NAME24, {
                                type: 'lga',
                                object: lga1,
                                properties: lga1.properties,
                                geometry: lga1.geometry
                            });

                            window.selectedItems.set('lga-' + lga2.properties.LGA_NAME24, {
                                type: 'lga',
                                object: lga2,
                                properties: lga2.properties,
                                geometry: lga2.geometry
                            });

                            // Update the display
                            if (window.updateSelectionDisplay) {
                                window.updateSelectionDisplay();
                            }
                            return true;
                        }
                    }
                }
                return false;
            } catch(e) {
                console.error('Error in test:', e);
                return false;
            }
        }
    """)

    # Wait for panel animation
    page.wait_for_timeout(500)

    # Check that panel is visible
    panel = page.locator("#selection-panel")
    expect(panel).to_be_visible()

    # Check height is 33vh
    height = panel.evaluate("el => el.style.height")
    assert height == "33vh", f"Panel height should be 33vh, got {height}"


def test_chart_visible_without_scroll(page: Page):
    """Test that charts in selection panel use proper 2/3 and 1/3 column layout."""
    # Wait for page to fully load
    page.wait_for_timeout(5000)

    # Check that handleItemClick is available (use this instead of selectedItems)
    has_handler = page.evaluate("() => typeof handleItemClick !== 'undefined'")
    if not has_handler:
        pytest.skip("handleItemClick not available on this page")

    # Simulate single LGA selection
    success = page.evaluate("""
        () => {
            try {
                const layers = window.deckgl?.props?.layers || [];
                const lgaLayer = layers.find(l => l.id === 'lga-boundaries');

                if (lgaLayer && lgaLayer.props && lgaLayer.props.data && lgaLayer.props.data.features) {
                    const features = lgaLayer.props.data.features;
                    if (features.length >= 1) {
                        const lga = features[0];
                        if (typeof handleItemClick !== 'undefined') {
                            handleItemClick(lga, lgaLayer);
                            return true;
                        }
                    }
                }
                return false;
            } catch(e) {
                console.error('Error in test:', e);
                return false;
            }
        }
    """)

    # Wait for panel to render
    page.wait_for_timeout(2000)

    # Check that the panel is visible
    panel = page.locator("#selection-panel")
    expect(panel).to_be_visible()

    # Check for two-column layout structure
    flex_containers = page.locator("#selection-content div[style*='display: flex']")

    if flex_containers.count() > 0:
        # Check for the 2/3 and 1/3 flex layout
        chart_column = page.locator("div[style*='flex: 2']").first
        data_column = page.locator("div[style*='flex: 1']").first

        expect(chart_column).to_be_visible()
        expect(data_column).to_be_visible()

        # Check that both columns are within the panel bounds
        chart_in_bounds = chart_column.evaluate("""
            (element) => {
                const rect = element.getBoundingClientRect();
                const panel = document.getElementById('selection-panel');
                const panelRect = panel.getBoundingClientRect();
                return rect.top >= panelRect.top && rect.bottom <= panelRect.bottom;
            }
        """)

        data_in_bounds = data_column.evaluate("""
            (element) => {
                const rect = element.getBoundingClientRect();
                const panel = document.getElementById('selection-panel');
                const panelRect = panel.getBoundingClientRect();
                return rect.top >= panelRect.top && rect.bottom <= panelRect.bottom;
            }
        """)

        assert chart_in_bounds, "Chart column should be visible within panel bounds"
        assert data_in_bounds, "Data column should be visible within panel bounds"


def test_two_lga_charts_side_by_side(page: Page):
    """Test that selecting two LGAs displays charts side by side."""
    # Wait for page to fully load
    page.wait_for_timeout(5000)

    # Check that selectedItems is available
    has_selected_items = page.evaluate("() => typeof window.selectedItems !== 'undefined'")
    if not has_selected_items:
        pytest.skip("selectedItems not available on this page")

    # Simulate two LGA selection
    success = page.evaluate("""
        () => {
            try {
                const layers = window.deckgl?.props?.layers || [];
                const lgaLayer = layers.find(l => l.id === 'lga-boundaries');

                if (lgaLayer && lgaLayer.props && lgaLayer.props.data && lgaLayer.props.data.features) {
                    const features = lgaLayer.props.data.features;
                    if (features.length >= 2) {
                        if (window.selectedItems && window.selectedItems.clear) {
                            window.selectedItems.clear();
                        }

                        const lga1 = features[0];
                        const lga2 = features[1];

                        if (window.selectedItems && window.selectedItems.set) {
                            window.selectedItems.set('lga-' + lga1.properties.LGA_NAME24, {
                                type: 'lga',
                                object: lga1,
                                properties: lga1.properties,
                                geometry: lga1.geometry
                            });

                            window.selectedItems.set('lga-' + lga2.properties.LGA_NAME24, {
                                type: 'lga',
                                object: lga2,
                                properties: lga2.properties,
                                geometry: lga2.geometry
                            });

                            if (window.updateSelectionDisplay) {
                                window.updateSelectionDisplay();
                            }
                            return true;
                        }
                    }
                }
                return false;
            } catch(e) {
                console.error('Error in test:', e);
                return false;
            }
        }
    """)

    # Wait for charts to render
    page.wait_for_timeout(2000)

    # Check for side-by-side layout
    flex_container = page.locator("#selection-content > div").first()
    display_style = flex_container.evaluate("el => window.getComputedStyle(el).display")
    assert display_style == "flex", "Should use flex layout for side-by-side display"

    # Check that we have 2 chart containers
    chart_containers = page.locator("div[id^='chart-']")
    assert chart_containers.count() == 2, "Should have exactly 2 charts"

    # Check both charts are visible without scrolling
    for i in range(2):
        chart = chart_containers.nth(i)
        is_visible = chart.evaluate("""
            (element) => {
                const rect = element.getBoundingClientRect();
                const panel = document.getElementById('selection-panel');
                const panelRect = panel.getBoundingClientRect();
                return rect.top >= panelRect.top && rect.bottom <= panelRect.bottom;
            }
        """)
        assert is_visible, f"Chart {i+1} should be visible without scrolling"


def test_close_button_clears_selection(page: Page):
    """Test that the close button clears the selection and hides the panel."""
    # Wait for page to fully load
    page.wait_for_timeout(5000)

    # Check that selectedItems is available
    has_selected_items = page.evaluate("() => typeof window.selectedItems !== 'undefined'")
    if not has_selected_items:
        pytest.skip("selectedItems not available on this page")

    # Select an LGA first
    success = page.evaluate("""
        () => {
            try {
                const layers = window.deckgl?.props?.layers || [];
                const lgaLayer = layers.find(l => l.id === 'lga-boundaries');

                if (lgaLayer && lgaLayer.props && lgaLayer.props.data && lgaLayer.props.data.features) {
                    const features = lgaLayer.props.data.features;
                    if (features.length >= 1) {
                        if (window.selectedItems && window.selectedItems.clear) {
                            window.selectedItems.clear();
                        }
                        const lga = features[0];
                        if (window.selectedItems && window.selectedItems.set) {
                            window.selectedItems.set('lga-' + lga.properties.LGA_NAME24, {
                                type: 'lga',
                                object: lga,
                                properties: lga.properties,
                                geometry: lga.geometry
                            });
                            if (window.updateSelectionDisplay) {
                                window.updateSelectionDisplay();
                            }
                            return true;
                        }
                    }
                }
                return false;
            } catch(e) {
                console.error('Error in test:', e);
                return false;
            }
        }
    """)

    # Wait for panel to show
    page.wait_for_timeout(500)

    # Click close button
    close_button = page.locator("#close-selection-panel")
    close_button.click()

    # Wait for animation
    page.wait_for_timeout(500)

    # Check panel is hidden
    panel = page.locator("#selection-panel")
    height = panel.evaluate("el => el.style.height")
    assert height == "0" or height == "0px", "Panel should be hidden after close"

    # Check selections are cleared
    selection_count = page.evaluate("() => window.selectedItems.size")
    assert selection_count == 0, "Selections should be cleared"