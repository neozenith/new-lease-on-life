#!/usr/bin/env python3
"""
Convert rental sales CSV data to DuckDB database format.

This script converts the consolidated rental and sales data CSV into a DuckDB database
for efficient client-side querying using DuckDB WASM in the browser.

Usage:
    uv run scripts/convert_rental_sales_to_duckdb.py [--input INPUT] [--output OUTPUT]

Requirements:
    - duckdb: Database engine
    - pandas: Data processing (optional, DuckDB can handle CSV directly)
"""

import argparse
import sys
from pathlib import Path
import duckdb

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def create_rental_sales_database(input_csv: Path, output_db: Path) -> None:
    """Convert rental sales CSV to DuckDB database.

    Args:
        input_csv: Path to the input CSV file
        output_db: Path to the output DuckDB database file
    """
    print(f"Converting {input_csv} to DuckDB database {output_db}")

    # Ensure output directory exists
    output_db.parent.mkdir(parents=True, exist_ok=True)

    # Remove existing database if it exists
    if output_db.exists():
        output_db.unlink()
        print(f"Removed existing database: {output_db}")

    # Connect to DuckDB
    conn = duckdb.connect(str(output_db))

    try:
        # Check if input file exists
        if not input_csv.exists():
            raise FileNotFoundError(f"Input CSV file not found: {input_csv}")

        # Get file size for progress reporting
        file_size_mb = input_csv.stat().st_size / (1024 * 1024)
        print(f"Processing {file_size_mb:.1f}MB CSV file...")

        # Create the rental_sales table directly from CSV
        # DuckDB can efficiently read CSV files and infer schema
        create_table_sql = f"""
        CREATE TABLE rental_sales AS
        SELECT
            CASE
                WHEN value = '-' THEN NULL
                WHEN value LIKE '%*' THEN CAST(REPLACE(value, '*', '') AS DOUBLE)
                ELSE CAST(value AS DOUBLE)
            END as value,
            time_bucket,
            time_bucket_type,
            value_type,
            dwelling_type,
            bedrooms,
            geospatial_type,
            geospatial_id,
            postcode,
            -- Add computed columns for better querying, handling different time formats
            CASE
                WHEN time_bucket_type = 'quarterly' THEN EXTRACT(YEAR FROM STRPTIME(time_bucket, '%Y-%m'))
                WHEN time_bucket_type = 'annually' THEN CAST(time_bucket AS INTEGER)
                ELSE NULL
            END as year,
            CASE
                WHEN time_bucket_type = 'quarterly' THEN EXTRACT(QUARTER FROM STRPTIME(time_bucket, '%Y-%m'))
                ELSE NULL
            END as quarter,
            CASE
                WHEN time_bucket_type = 'quarterly' THEN STRPTIME(time_bucket, '%Y-%m')
                WHEN time_bucket_type = 'annually' THEN STRPTIME(time_bucket || '-01-01', '%Y-%m-%d')
                ELSE NULL
            END as time_bucket_date
        FROM read_csv_auto('{input_csv}', header=true);
        """

        conn.execute(create_table_sql)

        # Get table statistics
        row_count = conn.execute("SELECT COUNT(*) FROM rental_sales").fetchone()[0]
        print(f"Created rental_sales table with {row_count:,} rows")

        # Create indexes for better query performance
        print("Creating indexes for optimized querying...")
        indexes = [
            "CREATE INDEX idx_geospatial_type ON rental_sales(geospatial_type);",
            "CREATE INDEX idx_geospatial_id ON rental_sales(geospatial_id);",
            "CREATE INDEX idx_value_type ON rental_sales(value_type);",
            "CREATE INDEX idx_dwelling_type ON rental_sales(dwelling_type);",
            "CREATE INDEX idx_year ON rental_sales(year);",
            "CREATE INDEX idx_postcode ON rental_sales(postcode);",
            "CREATE INDEX idx_compound ON rental_sales(geospatial_type, geospatial_id, value_type);"
        ]

        for idx_sql in indexes:
            conn.execute(idx_sql)

        # Create a summary table for quick stats
        conn.execute("""
        CREATE TABLE rental_sales_summary AS
        SELECT
            geospatial_type,
            COUNT(DISTINCT geospatial_id) as unique_areas,
            COUNT(DISTINCT value_type) as value_types,
            COUNT(DISTINCT dwelling_type) as dwelling_types,
            MIN(year) as earliest_year,
            MAX(year) as latest_year,
            COUNT(*) as total_records
        FROM rental_sales
        GROUP BY geospatial_type;
        """)

        # Display summary information
        print("\nDatabase Summary:")
        summary_results = conn.execute("SELECT * FROM rental_sales_summary ORDER BY geospatial_type").fetchall()
        for row in summary_results:
            geospatial_type, unique_areas, value_types, dwelling_types, earliest_year, latest_year, total_records = row
            print(f"  {geospatial_type}: {unique_areas:,} areas, {value_types} value types, "
                  f"{dwelling_types} dwelling types, {earliest_year}-{latest_year}, {total_records:,} records")

        # Test a sample query to verify data integrity
        test_query = """
        SELECT geospatial_type, geospatial_id, AVG(value) as avg_value, COUNT(*) as records
        FROM rental_sales
        WHERE value_type = 'rent' AND year >= 2020
        GROUP BY geospatial_type, geospatial_id
        ORDER BY avg_value DESC
        LIMIT 5
        """

        print("\nSample query - Top 5 areas by average rent (2020+):")
        test_results = conn.execute(test_query).fetchall()
        for row in test_results:
            geospatial_type, geospatial_id, avg_value, records = row
            print(f"  {geospatial_type} {geospatial_id}: ${avg_value:.0f}/week ({records} records)")

        # Get database file size
        db_size_mb = output_db.stat().st_size / (1024 * 1024)
        compression_ratio = file_size_mb / db_size_mb if db_size_mb > 0 else 0

        print(f"\nConversion complete!")
        print(f"  Input CSV: {file_size_mb:.1f}MB")
        print(f"  Output DB: {db_size_mb:.1f}MB")
        print(f"  Compression: {compression_ratio:.1f}x")
        print(f"  Database saved to: {output_db}")

    except Exception as e:
        print(f"Error during database creation: {e}")
        # Clean up partial database on error
        if output_db.exists():
            output_db.unlink()
        raise
    finally:
        conn.close()

def main():
    parser = argparse.ArgumentParser(
        description="Convert rental sales CSV to DuckDB database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run scripts/convert_rental_sales_to_duckdb.py
  uv run scripts/convert_rental_sales_to_duckdb.py --input data/custom.csv --output sites/webapp/data/custom.db
        """
    )

    parser.add_argument(
        '--input',
        type=Path,
        default=PROJECT_ROOT / 'data' / 'processed' / 'rental_sales' / 'csv_processed' / 'all_rental_sales_data.csv',
        help='Input CSV file path (default: data/processed/rental_sales/csv_processed/all_rental_sales_data.csv)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=PROJECT_ROOT / 'sites' / 'webapp' / 'data' / 'rental_sales.db',
        help='Output DuckDB database file path (default: sites/webapp/data/rental_sales.db)'
    )

    args = parser.parse_args()

    try:
        create_rental_sales_database(args.input, args.output)
    except Exception as e:
        print(f"Failed to create database: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()