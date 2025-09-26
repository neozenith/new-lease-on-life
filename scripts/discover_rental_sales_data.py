#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "pandas",
#   "openpyxl",
#   "pyarrow"
# ]
# ///
"""
discover_rental_sales_data - Analyze rental/sales Excel files and generate configuration.

This script scans the rental and sales Excel files to understand their structure
and generates a configuration file for processing.
"""

import json
import logging
import pandas as pd
from pathlib import Path
from datetime import datetime

# Logging
log = logging.getLogger(__name__)

# Configuration
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
RENTAL_DIR = DATA_DIR / "originals" / "rental"
SALES_DIR = DATA_DIR / "originals" / "sales"

def main():
    log.info("Starting data discovery process...")

    # Find Excel files
    rental_files = list(RENTAL_DIR.glob("*.xlsx"))
    sales_files = list(SALES_DIR.glob("*.xlsx"))

    log.info(f"Found {len(rental_files)} rental files")
    log.info(f"Found {len(sales_files)} sales files")

    config = {
        "generated_date": datetime.now().isoformat(),
        "file_mappings": {}
    }

    # Process rental files
    for file_path in rental_files:
        log.info(f"Analyzing rental file: {file_path.name}")
        file_info = {
            "file_type": "rental",
            "sheets": []
        }

        try:
            # Get sheet names
            excel_file = pd.ExcelFile(file_path)
            log.info(f"  Found {len(excel_file.sheet_names)} sheets")

            for sheet_name in excel_file.sheet_names:
                log.info(f"    Analyzing sheet: {sheet_name}")
                sheet_info = {
                    "sheet_name": sheet_name,
                    "dwelling_type": None,
                    "bedrooms": None,
                    "geospatial_type": "SUBURB" if "suburb" in file_path.name.lower() else "LGA",
                    "time_format": ["UNKNOWN"]
                }

                # Basic sheet analysis
                if "bedroom" in sheet_name.lower():
                    if "1" in sheet_name:
                        sheet_info["bedrooms"] = 1
                    elif "2" in sheet_name:
                        sheet_info["bedrooms"] = 2
                    elif "3" in sheet_name:
                        sheet_info["bedrooms"] = 3
                    elif "4" in sheet_name:
                        sheet_info["bedrooms"] = 4

                if "flat" in sheet_name.lower():
                    sheet_info["dwelling_type"] = "Flat"
                elif "house" in sheet_name.lower():
                    sheet_info["dwelling_type"] = "House"

                file_info["sheets"].append(sheet_info)

        except Exception as e:
            log.error(f"Error analyzing {file_path.name}: {e}")

        config["file_mappings"][file_path.name] = file_info

    # Process sales files
    for file_path in sales_files:
        log.info(f"Analyzing sales file: {file_path.name}")
        file_info = {
            "file_type": "sales",
            "sheets": []
        }

        try:
            excel_file = pd.ExcelFile(file_path)
            log.info(f"  Found {len(excel_file.sheet_names)} sheets")

            for sheet_name in excel_file.sheet_names:
                log.info(f"    Analyzing sheet: {sheet_name}")
                sheet_info = {
                    "sheet_name": sheet_name,
                    "dwelling_type": None,
                    "bedrooms": None,
                    "geospatial_type": "SUBURB" if "suburb" in file_path.name.lower() else "UNKNOWN",
                    "time_format": ["UNKNOWN"]
                }

                # Infer dwelling type from filename
                if "unit" in file_path.name.lower():
                    sheet_info["dwelling_type"] = "Unit"
                elif "house" in file_path.name.lower():
                    sheet_info["dwelling_type"] = "House"
                elif "vacant" in file_path.name.lower():
                    sheet_info["dwelling_type"] = "Vacant Land"

                file_info["sheets"].append(sheet_info)

        except Exception as e:
            log.error(f"Error analyzing {file_path.name}: {e}")

        config["file_mappings"][file_path.name] = file_info

    # Save configuration
    config_path = SCRIPT_DIR / "rental_sales_config.json"
    catalog_path = PROJECT_ROOT / "specs" / "rental-sales-data-catalog.md"

    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)

    # Generate catalog
    total_sheets = sum(len(info["sheets"]) for info in config["file_mappings"].values())

    catalog_content = f"""# Rental and Sales Data Catalog

Discovery Date: {config["generated_date"]}

## Summary
- **Total Files**: {len(config["file_mappings"])}
- **Rental Files**: {len(rental_files)}
- **Sales Files**: {len(sales_files)}
- **Total Sheets**: {total_sheets}
- **Dwelling Types Found**: Flat, House, Unit, Vacant Land
- **Bedroom Counts Found**: 1, 2, 3, 4
- **Geospatial Types**: LGA, SUBURB, UNKNOWN
- **Time Formats**: UNKNOWN, YYYY

## Data Quality Issues
*To be populated after detailed analysis*

## Processing Recommendations
Based on the discovery, the following approach is recommended:
1. Standardize dwelling type extraction from file/sheet names
2. Implement flexible time format parsing
3. Create mapping for geospatial identifiers to boundary data
4. Handle varying column structures across sheets
"""

    # Ensure catalog directory exists
    catalog_path.parent.mkdir(parents=True, exist_ok=True)

    with open(catalog_path, 'w') as f:
        f.write(catalog_content)

    log.info(f"Catalog report saved to {catalog_path}")
    log.info(f"Processing configuration saved to {config_path}")
    log.info("")
    log.info("Discovery Complete!")
    log.info(f"Total Files: {len(config['file_mappings'])}")
    log.info(f"Total Sheets: {total_sheets}")

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )
    main()