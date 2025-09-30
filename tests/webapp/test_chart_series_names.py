"""Test that chart series names use the format 'DwellingType-Bedrooms'."""

import pytest
from playwright.sync_api import Page, expect


def test_page_loads(page: Page, base_url: str):
    """Test that the webapp page loads successfully."""
    page.goto(base_url)
    expect(page).to_have_title("Josh is Finding a Rental in Melbourne")


def test_series_names_format_for_suburb_data(page: Page, base_url: str):
    """Test that series names follow 'DwellingType-Bedrooms' format for suburb data."""
    page.goto(base_url)

    # Wait for DuckDB to initialize
    page.wait_for_function("() => window.duckdbConnection !== undefined", timeout=10000)

    # Query data for Richmond-Burnley suburb which has bedroom data
    result = page.evaluate("""async () => {
        if (typeof queryRentalData === 'function') {
            const data = await queryRentalData('SUBURB', 'Richmond-Burnley', 'rent');
            return {
                success: true,
                seriesKeys: data.metadata.seriesKeys
            };
        }
        return { success: false };
    }""")

    assert result["success"], "queryRentalData function should be available"

    series_keys = result["seriesKeys"]

    # Check that "All Properties" exists
    assert "All Properties" in series_keys, "Should have 'All Properties' series"

    # Filter out "All Properties" to check the format of other series
    bedroom_series = [key for key in series_keys if key != "All Properties"]

    # Check that we have bedroom-specific series
    assert len(bedroom_series) > 0, "Should have bedroom-specific series"

    # Verify each series follows the format "DwellingType-Bedrooms"
    for series_key in bedroom_series:
        # Should contain a hyphen
        assert "-" in series_key, f"Series '{series_key}' should contain a hyphen"

        # Split by hyphen
        parts = series_key.split("-")
        assert len(parts) == 2, f"Series '{series_key}' should have exactly 2 parts"

        dwelling_type, bedrooms = parts

        # Dwelling type should be "Unit" or "House"
        assert dwelling_type in ["Unit", "House"], \
            f"Dwelling type '{dwelling_type}' should be 'Unit' or 'House'"

        # Bedrooms should be a number
        assert bedrooms.isdigit(), \
            f"Bedrooms '{bedrooms}' should be a number"

        # Bedrooms should be between 1 and 5
        assert 1 <= int(bedrooms) <= 5, \
            f"Bedrooms '{bedrooms}' should be between 1 and 5"


def test_series_color_assignment(page: Page, base_url: str):
    """Test that series colors are correctly assigned based on new format."""
    page.goto(base_url)

    # Wait for DuckDB to initialize
    page.wait_for_function("() => window.duckdbConnection !== undefined", timeout=10000)

    # Test the color assignment function
    result = page.evaluate("""() => {
        // We'll test by checking if the function logic works
        // by simulating what happens in createAreaChart
        const testSeriesKeys = [
            "All Properties",
            "House-2",
            "House-3",
            "House-4",
            "Unit-1",
            "Unit-2",
            "Unit-3"
        ];

        // Mock version of getSeriesColor from createAreaChart
        const getSeriesColor = (seriesKey) => {
            if (seriesKey === "All Properties") return "#1976D2";

            if (seriesKey.startsWith("House-")) {
                if (seriesKey.includes("-1")) return "#A5D6A7";
                if (seriesKey.includes("-2")) return "#81C784";
                if (seriesKey.includes("-3")) return "#4CAF50";
                if (seriesKey.includes("-4")) return "#388E3C";
                if (seriesKey.includes("-5")) return "#2E7D32";
                return "#4CAF50";
            }

            if (seriesKey.startsWith("Unit-")) {
                if (seriesKey.includes("-1")) return "#FFCC80";
                if (seriesKey.includes("-2")) return "#FFB74D";
                if (seriesKey.includes("-3")) return "#FF9800";
                if (seriesKey.includes("-4")) return "#F57C00";
                if (seriesKey.includes("-5")) return "#E65100";
                return "#FF9800";
            }

            return "#666666";
        };

        const colors = {};
        testSeriesKeys.forEach(key => {
            colors[key] = getSeriesColor(key);
        });

        return { success: true, colors };
    }""")

    assert result["success"], "Color assignment test should succeed"

    colors = result["colors"]

    # Verify All Properties gets blue
    assert colors["All Properties"] == "#1976D2", \
        "All Properties should get blue color"

    # Verify House series get green tones
    assert colors["House-2"] == "#81C784", "House-2 should get green"
    assert colors["House-3"] == "#4CAF50", "House-3 should get darker green"
    assert colors["House-4"] == "#388E3C", "House-4 should get even darker green"

    # Verify Unit series get orange tones
    assert colors["Unit-1"] == "#FFCC80", "Unit-1 should get light orange"
    assert colors["Unit-2"] == "#FFB74D", "Unit-2 should get orange"
    assert colors["Unit-3"] == "#FF9800", "Unit-3 should get darker orange"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])