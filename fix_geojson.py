#!/usr/bin/env python
"""
Convert non-standard GeoJSON format to standard FeatureCollection format.

This script fixes GeoJSON files that have a "polygons" array instead of the
standard "features" array in a FeatureCollection.

Can process single files or recursively iterate through directories.
"""

import json
import sys
from pathlib import Path
import argparse
import shutil
from typing import List, Tuple

def fix_geojson(input_file, output_file=None, name=None):
    """
    Fix a non-standard GeoJSON file by converting it to a proper FeatureCollection.
    
    Args:
        input_file (str): Path to the input GeoJSON file
        output_file (str, optional): Path to save the fixed GeoJSON file. If None, overwrites the input.
        name (str, optional): Name for the FeatureCollection. If None, uses the filename.
    
    Returns:
        bool: True if successful, False otherwise
    """
    if output_file is not None:
        #compare mtime of input and output file
        input_path = Path(input_file)
        output_path = Path(output_file)
        if output_path.exists() and output_path.stat().st_mtime >= input_path.stat().st_mtime:
            # print(f"SKIP: Output file {output_file} is newer than input file {input_file}. Skipping processing.")
            return True
    
    try:
        # Read the input file
        input_filepath = Path(input_file)
        data = json.loads(input_filepath.read_text(encoding='utf-8'))
        name = input_filepath.stem
        
        # Create the proper FeatureCollection structure
        feature_collection = {
            "type": "FeatureCollection",
            "name": name,
            "crs": {
                "type": "name", 
                "properties": {
                    "name": "urn:ogc:def:crs:OGC:1.3:CRS84"
                }
            },
            "features": []
        }
        
        # Check if the original structure has a "polygons" array
        if "polygons" in data:
            # Copy features from polygons array
            feature_collection["features"] = data["polygons"]
            
            # Copy any additional metadata
            if "info" in data:
                feature_collection["info"] = data["info"]
        else:
            print(f"Warning: No 'polygons' array found in {input_file}")
            return False
        
        # Determine output path
        if output_file is None:
            output_file = input_file
        
        # Write the fixed GeoJSON to file
        output_filepath = Path(output_file)
        output_filepath.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
        output_filepath.write_text(json.dumps(feature_collection, indent=2))
        
        print(f"Successfully converted {input_file} to standard GeoJSON format")
        print(f"Saved to {output_file}")
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
        data = json.loads(file_path.read_text(encoding='utf-8'))
        
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

def process_directory(input_dir, output_dir, validate=False):
    """
    Process all GeoJSON files in a directory recursively.
    
    Args:
        input_dir (str): Input directory containing GeoJSON files
        output_dir (str): Output directory to save fixed GeoJSON files
        validate (bool): Whether to validate the output files
        
    Returns:
        tuple: (total_files, successful_files)
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    if not input_path.is_dir():
        print(f"Error: {input_dir} is not a directory")
        return 0, 0
    
    total_files = 0
    successful_files = 0
    
    # Find all GeoJSON files in the directory and its subdirectories
    for geojson_file in input_path.glob("**/*.geojson"):
        total_files += 1
        
        # Determine the relative path from the input directory
        rel_path = geojson_file.relative_to(input_path)
        
        # Create the corresponding output path
        out_file = output_path / rel_path
        
        # Ensure the output directory exists
        out_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"Processing {geojson_file}...")
        success = fix_geojson(str(geojson_file), str(out_file))
        
        if success:
            successful_files += 1
            if validate:
                valid, message = validate_geojson(str(out_file))
                if valid:
                    print(f"  Validation: {message}")
                else:
                    print(f"  Validation failed: {message}")
    
    return total_files, successful_files

def main():
    parser = argparse.ArgumentParser(description="Fix non-standard GeoJSON files")
    parser.add_argument("input", help="Input GeoJSON file or directory to fix")
    parser.add_argument("-o", "--output", help="Output file path or directory (default: overwrite input)")
    parser.add_argument("-n", "--name", help="Name for the FeatureCollection (only used for single file)")
    parser.add_argument("-v", "--validate", action="store_true", help="Validate the GeoJSON file after fixing")
    parser.add_argument("-r", "--recursive", action="store_true", help="Process directories recursively (implied if input is a directory)")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    
    # Check if input is a directory
    if input_path.is_dir():
        if args.output is None:
            print("Error: When processing a directory, you must specify an output directory")
            return 1
            
        print(f"Processing directory {args.input} recursively...")
        total, successful = process_directory(args.input, args.output, args.validate)
        print(f"Processed {successful}/{total} files successfully")
        return 0 if successful == total and total > 0 else 1
    
    # Process single file
    else:
        success = fix_geojson(args.input, args.output, args.name)
        
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
