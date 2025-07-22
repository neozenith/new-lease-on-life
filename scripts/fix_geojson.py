#!/usr/bin/env python
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "geopandas",
#   "pyarrow",
#   "shapely",
#   "requests",
# ]
# ///
"""
Convert non-standard GeoJSON format to standard FeatureCollection format.

This script fixes GeoJSON files that have a "polygons" array instead of the
standard "features" array in a FeatureCollection.

Can process single files or recursively iterate through directories.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import geopandas as gpd

from utils import dirty, load_stops, normalise_name, PTV_TRANSPORT_MODES, OUTPUT_BASE, TRANSPORT_MODES, MAPBOX_PROFILE_MAPPING

SCRIPT_DIR = Path(__file__).parent.resolve()


def fix_geojson(
    stops: gpd.GeoDataFrame, input_file: Path, output_file: Path | None = None, name=None
):
    """
    Fix a non-standard GeoJSON file by converting it to a proper FeatureCollection.

    Args:
        input_file (str): Path to the input GeoJSON file
        output_file (str, optional): Path to save the fixed GeoJSON file. If None, overwrites the input.
        name (str, optional): Name for the FeatureCollection. If None, uses the filename.

    Returns:
        bool: True if successful, False otherwise
    """
    # Determine output path
    if output_file is None:
        output_file = input_file

    # compare mtime of input and output file
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not dirty(output_path, input_path):
        print(f"SKIP: Output file {output_file} is newer than input file {input_file}. Skipping processing.")
        return True

    isochrone_mode = input_path.parts[2]
    stop_id = input_path.stem.split("_")[1]
    name_prefix_length = len(input_path.stem.split("_")[0]) + len(input_path.stem.split("_")[1]) + 2
    normalised_stop_name = input_path.stem[name_prefix_length:]
    stop = stops[stops["STOP_ID"] == stop_id]

    _props = {
        "isochrone_mode": isochrone_mode,
        "STOP_ID": stop_id,
        "normalised_stop_name": normalised_stop_name,
    }
    if stop.shape[0] > 0:
        stop = stop.iloc[0]

        if normalise_name(stop.STOP_NAME) != normalised_stop_name:
            print(
                f"!!!!!!!!!!!!!!!!Warning: Normalised stop name {normalised_stop_name} does not match stop.STOP_NAME {stop.STOP_NAME}"
            )
            print(f"""
                {isochrone_mode=}
                {stop_id=}
                {normalised_stop_name=}
            """)
            print(f"""
                {stop.name=}
                {stop.geometry=}
                {stop.MODE=}
                {stop.STOP_NAME=}
                {stop.STOP_ID=}
            """)
        _props["STOP_NAME"] = stop.STOP_NAME
        _props["MODE"] = stop.MODE
    else:
        print(
            f"Warning: No stop found for STOP_ID {stop_id} in {input_file}. Using default properties."
        )

    try:
        # Read the input file
        # if input_path.name != "isochrone_vic:rail:STL_stawell_railway_station.geojson":
        #     return True

        data = json.loads(input_path.read_text(encoding="utf-8"))
        name = input_path.stem

        # Create the proper FeatureCollection structure
        feature_collection = {
            "type": "FeatureCollection",
            "name": name,
            "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}},
            "features": [],
        }

        # Check if the original structure has a "polygons" array
        if "polygons" in data:
            # Copy features from polygons array
            feature_collection["features"] = data["polygons"]
            for feature in feature_collection["features"]:
                # Ensure each feature has the required properties
                if "properties" not in feature:
                    feature["properties"] = {}
                # Add or update properties with isochrone info
                feature["properties"].update(_props)

                if "bucket" in feature["properties"]:
                    # Convert bucket to integer if it's a string
                    feature["properties"]["contour_time_minutes"] = (
                        int(feature["properties"]["bucket"]) * 5 + 5
                    )

            # Copy any additional metadata
            if "info" in data:
                feature_collection["info"] = data["info"]
        elif "features" in data:
            # If already in standard format, just copy features
            feature_collection["features"] = data["features"]
            for feature in feature_collection["features"]:
                # Ensure each feature has the required properties
                if "properties" not in feature:
                    feature["properties"] = {}
                # Add or update properties with isochrone info
                key_to_drop = [
                    "fill-opacity",
                    "fillColor",
                    "opacity",
                    "fill",
                    "fillOpacity",
                    "color",
                ]
                for key in key_to_drop:
                    if key in feature["properties"]:
                        del feature["properties"][key]

                if "contour" in feature["properties"]:
                    feature["properties"]["contour_time_minutes"] = int(
                        feature["properties"]["contour"]
                    )
                feature["properties"].update(_props)

            # MapBox doesn't include metadata in the features, so we add it here
            feature_collection["info"] = {
                "copyrights": ["MapBox IsoChrone API", "OpenStreetMap contributors"],
                "collected": input_path.stat().st_mtime,
                "source": "MapBox IsoChrone API",
            }
        else:
            print(f"Warning: No 'polygons' array found in {input_file}")
            return False

        output_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        output_path.write_text(json.dumps(feature_collection, indent=2))

        # print(f"Successfully converted {input_file} to standard GeoJSON format")
        # print(f"Saved to {output_file}")
        return True

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in {input_file}: {e}")
        return False
    except Exception as e:
        print(f"Error processing {input_file}: {e}")
        return False


def validate_geojson(file_path):
    """
    Basic validation of GeoJSON file.

    Args:
        file_path (str): Path to GeoJSON file to validate

    Returns:
        tuple: (is_valid, message)
    """
    try:
        # Read the file
        file_path = Path(file_path)
        data = json.loads(file_path.read_text(encoding="utf-8"))

        # Check for required properties
        if "type" not in data:
            return False, "Missing 'type' property at root level"

        if data["type"] == "FeatureCollection":
            if "features" not in data:
                return False, "FeatureCollection missing 'features' array"

            # Check each feature
            for i, feature in enumerate(data["features"]):
                if "type" not in feature:
                    return False, f"Feature {i} missing 'type' property"

                if "geometry" not in feature:
                    return False, f"Feature {i} missing 'geometry' property"

                if "properties" not in feature:
                    return False, f"Feature {i} missing 'properties' property"

                if "type" not in feature["geometry"]:
                    return False, f"Feature {i} geometry missing 'type' property"

                if "coordinates" not in feature["geometry"]:
                    return False, f"Feature {i} geometry missing 'coordinates' property"

        return True, "GeoJSON appears to be valid"

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"
    except Exception as e:
        return False, f"Error validating GeoJSON: {e}"


def process_directory(stops: gpd.GeoDataFrame, input_dir: Path, output_dir: Path, validate=False):
    """
    Process all GeoJSON files in a directory recursively.

    Args:
        input_dir (str): Input directory containing GeoJSON files
        output_dir (str): Output directory to save fixed GeoJSON files
        validate (bool): Whether to validate the output files

    Returns:
        tuple: (total_files, successful_files)
    """
    input_path = input_dir
    output_path = output_dir

    if not input_path.is_dir():
        print(f"Error: {input_dir} is not a directory")
        return 0, 0

    total_files = 0
    successful_files = 0
    cached_files = 0

    # Find all GeoJSON files in the directory and its subdirectories
    for geojson_file in input_path.glob("**/*.geojson"):
        total_files += 1

        # Determine the relative path from the input directory
        rel_path = geojson_file.relative_to(input_path)

        # Create the corresponding output path
        out_file = output_path / rel_path

        # Ensure the output directory exists
        out_file.parent.mkdir(parents=True, exist_ok=True)
        if out_file.exists():
            cached_files += 1
            print(f"Skipping {geojson_file} as it already exists at {out_file}")
            continue

        success = fix_geojson(stops, geojson_file, out_file)

        if success:
            successful_files += 1
            if validate:
                valid, message = validate_geojson(str(out_file))
                if valid:
                    print(f"  Validation: {message}")
                else:
                    print(f"  Validation failed: {message}")

    return total_files, successful_files, cached_files


def main():
    parser = argparse.ArgumentParser(description="Fix non-standard GeoJSON files")
    parser.add_argument("input", help="Input GeoJSON file or directory to fix")
    parser.add_argument(
        "-o", "--output", help="Output file path or directory (default: overwrite input)"
    )
    parser.add_argument(
        "-n", "--name", help="Name for the FeatureCollection (only used for single file)"
    )
    parser.add_argument(
        "-v", "--validate", action="store_true", help="Validate the GeoJSON file after fixing"
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Process directories recursively (implied if input is a directory)",
    )

    args = parser.parse_args()

    input_path = Path(args.input)

    stops = load_stops(PTV_TRANSPORT_MODES)
    # Check if input is a directory
    if input_path.is_dir(): 
        if args.output is None:
            print("Error: When processing a directory, you must specify an output directory")
            return 1

        print(f"Processing directory {args.input} recursively...")
        total, successful, cached_files = process_directory(
            stops, Path(args.input), Path(args.output), args.validate
        )
        print(f"Processed {successful}/{total} files successfully")
        if cached_files > 0:
            print(f"Skipped {cached_files} files that were already cached")
        return 0 if successful == total and total > 0 else 1

    # Process single file
    else:
        success = fix_geojson(stops, Path(args.input), Path(args.output), args.name)

        # Validate the output if requested
        if success and args.validate:
            output_file = args.output if args.output else args.input
            valid, message = validate_geojson(output_file)
            if valid:
                print(f"Validation: {message}")
            else:
                print(f"Validation failed: {message}")

        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
