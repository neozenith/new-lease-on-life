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

from ruamel.yaml import YAML
from pathlib import Path
import pandas as pd
import logging

log = logging.getLogger(__name__)
SCRIPT_DIR = Path(__file__).parent.resolve()
CONFIG_FILE = SCRIPT_DIR.parent / "extract_schema_mapping.yml"
CONFIG = YAML().load(CONFIG_FILE.read_text())

def main(input_dir: Path, output_dir: Path, limit: int | None = None) -> None:
    """Extract rental and sales data from source files.

    Args:
        input_dir: Directory containing source files
        output_dir: Directory to save processed CSV files
        limit: Optional limit on number of files to process (for testing)
    """
    log.info(f"Extracting rental and sales data from {input_dir} to {output_dir}")

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each file in the input directory
    files = list(input_dir.glob("*.xslx"))
    
    for file_path in files:
        log.info(f"Processing file: {file_path}")
        df = pd.read_excel(file_path, engine="openpyxl")
        

        # Apply schema mapping from config
        if "columns" in CONFIG:
            df = df.rename(columns=CONFIG["columns"])

        # Save processed CSV
        output_file = output_dir / f"{file_path.stem}_processed.csv"
        df.to_csv(output_file, index=False)
        log.info(f"Saved processed data to {output_file}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract rental and sales data from source files.")
    parser.add_argument(
        "--input", type=Path, default=SCRIPT_DIR.parent / "data/rental_sales", help="Input directory containing source files."
    )
    parser.add_argument(
        "--output", type=Path, default=SCRIPT_DIR.parent / "data/processed/rental_sales/csv_processed", help="Output directory for processed CSV files."
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Limit the number of files to process (for testing)."
    )
    args = parser.parse_args()

    main(args.input, args.output, args.limit)