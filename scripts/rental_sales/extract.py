#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pandas",
#   "openpyxl",
#   "pyarrow",
#   "ruamel.yaml",
# ]
# ///
import argparse
import openpyxl as xl
from ruamel.yaml import YAML
from pathlib import Path
import pandas as pd
import logging
import json

log = logging.getLogger(__name__)
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR / "extract_schema_mapping.yaml"
CONFIG = YAML().load(CONFIG_FILE.read_text())
PROJECT_DIR = SCRIPT_DIR.parent.resolve()
# print(f"{json.dumps(CONFIG, indent=2)}")

def cell_range_to_indices(cell_range: str):
    """Convert an Excel cell range (e.g., 'A1:C3') to zero-based row and column indices.

    Args:
        cell_range: Excel cell range in A1 notation"""
    return xl.utils.cell.range_boundaries(cell_range)

def main(input_dir: Path, output_dir: Path, limit: int | None = None) -> None:
    """Extract rental and sales data from source files.

    Args:
        input_dir: Directory containing source files
        output_dir: Directory to save processed CSV files
        limit: Optional limit on number of files to process (for testing)
    """
    print(f"Extracting rental and sales data from {input_dir} to {output_dir.relative_to(PROJECT_DIR)}")

    configured_files = {Path(item["file"]).name: item for item in CONFIG}
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each file in the input directory
    if input_dir.is_file():
        files = [input_dir]
    else:
        files = list(input_dir.rglob("*.xlsx"))
    
    cells_processed = 0

    for file_path in files:
        print()
        print("----")
        print(f"Processing file: {file_path}")
        print("----")
        schema_map_for_file = configured_files.get(file_path.name)
        if not schema_map_for_file:
            print(f"  No schema mapping found for {file_path.name}, skipping.")
            continue

        print(f"Config for file: {schema_map_for_file}")
        workbook = xl.load_workbook(file_path, data_only=True)
        print(f"Workbook: {workbook}")
        print(f"Workbook: {list(workbook.sheetnames)}")
        configured_sheets = {item["sheet"]: item for item in schema_map_for_file["sheets"]}
        for sheet in list(workbook.sheetnames):
            sheet_config = configured_sheets.get(sheet)
            if not sheet_config:
                print(f"  No config for sheet {sheet}, skipping.")
                continue

            print(f"  Sheet: {sheet}")
            print(f"  Config: {sheet_config}")
            if "time_bucket_range" in sheet_config:
                print(f"    Time bucket range: {sheet_config['time_bucket_range']} -> {cell_range_to_indices(sheet_config['time_bucket_range'])}")
            if "geospatial_range" in sheet_config:
                print(f"    Geospatial range: {sheet_config['geospatial_range']} -> {cell_range_to_indices(sheet_config['geospatial_range'])}")
            
            # iterate across timebucket columns and geospatial rows and cross reference the corresponding value cells
            # extracting the timebucket_value, geospatial_value, statistic_type, statistic_value
            time_bucket_start_col, time_bucket_start_row, time_bucket_end_col, time_bucket_end_row = cell_range_to_indices(sheet_config["time_bucket_range"])
            geo_start_col, geo_start_row, geo_end_col, geo_end_row = cell_range_to_indices(sheet_config["geospatial_range"])
            print(f"    Time bucket columns: {time_bucket_start_col} to {time_bucket_end_col}")
            print(f"    Geospatial rows: {geo_start_row} to {geo_end_row}")
            statistics = sheet_config["statistic"]
            print(f"    Statistics: {statistics}")
            rows = []
            sheet_obj = workbook[sheet]
            for geo_row in range(geo_start_row, geo_end_row + 1):
                geo_value = sheet_obj.cell(row=geo_row, column=geo_start_col).value
                if not geo_value or geo_value in ['Group Total', 'Grand Total', 'Victoria', 'Metro', 'Non-Metro']:
                    print(f"      Row {geo_row} geospatial value is empty, skipping row.")
                    continue
                for time_col in range(time_bucket_start_col, time_bucket_end_col + 1):
                    time_value = sheet_obj.cell(row=time_bucket_start_row, column=time_col).value
                    if not time_value:
                        print(f"      Column {time_col} time bucket value is empty, skipping column.")
                        continue
                    stat_index = (time_col - time_bucket_start_col) % len(statistics)
                    stat_type = statistics[stat_index]
                    
                    stat_value = sheet_obj.cell(row=geo_row, column=time_col).value
                    if stat_value is None:
                        print(f"      Cell at row {geo_row}, column {time_col} is empty, skipping.")
                        continue
                    row = {
                        "geospatial": geo_value,
                        "time_bucket": time_value,
                        "dwelling_type": sheet_config["dwelling_type"],
                        "bedrooms": sheet_config["bedrooms"],
                        "statistic": stat_type,
                        "value": stat_value,
                    }
                    rows.append(row)
                    print(f"      Extracted row: {row}")
                    cells_processed += 1
                    if limit and cells_processed >= limit:
                        print(f"Reached processing limit of {limit} cells, stopping.")
                        break
                if limit and cells_processed >= limit:
                    break
            if limit and cells_processed >= limit:
                break
        if limit and cells_processed >= limit:
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract rental and sales data from source files.")
    parser.add_argument(
        "--input", type=Path, default=SCRIPT_DIR.parent / "data/originals/", help="Input directory containing source files."
    )
    parser.add_argument(
        "--output", type=Path, default=SCRIPT_DIR.parent / "data/processed/rental_sales/csv_processed", help="Output directory for processed CSV files."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit the number of files to process (for testing)."
    )
    args = parser.parse_args()

    main(args.input, args.output, args.limit)