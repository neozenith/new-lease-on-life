"""Test that rental data lookup works with hyphen-delimited geospatial codes."""

import pytest
from playwright.sync_api import Page, expect


def test_page_loads(page: Page, base_url: str):
    """Test that the webapp page loads successfully."""
    page.goto(base_url)
    expect(page).to_have_title("Josh is Finding a Rental in Melbourne")


def test_suburb_code_with_hyphen_lookup(page: Page, base_url: str):
    """Test that queryRentalData works when geospatial_codes contain hyphen-delimited codes."""
    page.goto(base_url)

    # Wait for DuckDB to initialize
    page.wait_for_function("() => window.duckdbConnection !== undefined", timeout=10000)

    # Test direct query against DuckDB to verify the database structure
    # This checks if there are any records with hyphen-delimited codes
    db_check = page.evaluate("""async () => {
        const query = `
            SELECT
                geospatial_codes,
                COUNT(*) as record_count
            FROM rental_sales.rental_sales
            WHERE geospatial_type = 'suburb'
                AND geospatial_codes LIKE '%-%'
            GROUP BY geospatial_codes
            LIMIT 5
        `;
        const result = await window.duckdbConnection.query(query);
        const rows = result.toArray();
        return {
            hasHyphenatedCodes: rows.length > 0,
            examples: rows.map(r => r.geospatial_codes)
        };
    }""")

    # If there are no hyphenated codes, the test is not applicable
    if not db_check["hasHyphenatedCodes"]:
        pytest.skip("No hyphen-delimited codes found in database")

    print(f"Found hyphenated codes: {db_check['examples']}")

    # Now test that queryRentalData can handle a single code from a hyphenated group
    # Take the first hyphenated code and split it to get individual codes
    first_hyphenated = db_check["examples"][0]
    individual_codes = first_hyphenated.split("-")

    print(f"Testing individual codes from '{first_hyphenated}': {individual_codes}")

    # Test each individual code to ensure it can be looked up
    for code in individual_codes:
        result = page.evaluate(f"""async () => {{
            try {{
                const data = await queryRentalData('SUBURB', '{code}', 'rental');
                return {{
                    success: true,
                    recordCount: data.dates.length,
                    seriesCount: Object.keys(data.series).length,
                    metadata: data.metadata
                }};
            }} catch (error) {{
                return {{
                    success: false,
                    error: error.message
                }};
            }}
        }}""")

        assert result["success"], f"queryRentalData should succeed for code '{code}': {result.get('error', '')}"
        assert result["recordCount"] > 0, f"Should find records for code '{code}'"
        assert result["seriesCount"] > 0, f"Should have series data for code '{code}'"


def test_lga_code_with_hyphen_lookup(page: Page, base_url: str):
    """Test that queryRentalData works for LGA codes with hyphen-delimited geospatial_codes."""
    page.goto(base_url)

    # Wait for DuckDB to initialize
    page.wait_for_function("() => window.duckdbConnection !== undefined", timeout=10000)

    # Test direct query against DuckDB to check for hyphenated LGA codes
    db_check = page.evaluate("""async () => {
        const query = `
            SELECT
                geospatial_codes,
                COUNT(*) as record_count
            FROM rental_sales.rental_sales
            WHERE geospatial_type = 'lga'
                AND geospatial_codes LIKE '%-%'
            GROUP BY geospatial_codes
            LIMIT 5
        `;
        const result = await window.duckdbConnection.query(query);
        const rows = result.toArray();
        return {
            hasHyphenatedCodes: rows.length > 0,
            examples: rows.map(r => r.geospatial_codes)
        };
    }""")

    # If there are no hyphenated codes, the test is not applicable
    if not db_check["hasHyphenatedCodes"]:
        pytest.skip("No hyphen-delimited LGA codes found in database")

    print(f"Found hyphenated LGA codes: {db_check['examples']}")

    # Test that queryRentalData can handle individual codes from a hyphenated group
    first_hyphenated = db_check["examples"][0]
    individual_codes = first_hyphenated.split("-")

    print(f"Testing individual LGA codes from '{first_hyphenated}': {individual_codes}")

    # Test each individual code
    for code in individual_codes:
        result = page.evaluate(f"""async () => {{
            try {{
                const data = await queryRentalData('LGA', '{code}', 'rental');
                return {{
                    success: true,
                    recordCount: data.dates.length,
                    seriesCount: Object.keys(data.series).length,
                    metadata: data.metadata
                }};
            }} catch (error) {{
                return {{
                    success: false,
                    error: error.message
                }};
            }}
        }}""")

        assert result["success"], f"queryRentalData should succeed for LGA code '{code}': {result.get('error', '')}"
        assert result["recordCount"] > 0, f"Should find records for LGA code '{code}'"
        assert result["seriesCount"] > 0, f"Should have series data for LGA code '{code}'"


def test_duckdb_string_split_function(page: Page, base_url: str):
    """Test that DuckDB's string_split and list_contains functions work correctly."""
    page.goto(base_url)

    # Wait for DuckDB to initialize
    page.wait_for_function("() => window.duckdbConnection !== undefined", timeout=10000)

    # Test the string_split and list_contains functions directly
    result = page.evaluate("""async () => {
        try {
            const query = `
                SELECT
                    string_split('ABC-DEF-GHI', '-') as split_result,
                    list_contains(string_split('ABC-DEF-GHI', '-'), 'DEF') as contains_def,
                    list_contains(string_split('ABC-DEF-GHI', '-'), 'XYZ') as contains_xyz
            `;
            const queryResult = await window.duckdbConnection.query(query);
            const rows = queryResult.toArray();
            return {
                success: true,
                split_result: rows[0].split_result,
                contains_def: rows[0].contains_def,
                contains_xyz: rows[0].contains_xyz
            };
        } catch (error) {
            return {
                success: false,
                error: error.message
            };
        }
    }""")

    assert result["success"], f"DuckDB string functions should work: {result.get('error', '')}"
    assert result["split_result"] == ["ABC", "DEF", "GHI"], "string_split should split correctly"
    assert result["contains_def"] == True, "list_contains should find 'DEF'"
    assert result["contains_xyz"] == False, "list_contains should not find 'XYZ'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
