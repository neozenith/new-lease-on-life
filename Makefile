.PHONY: fix_geojson scrape_isochrones all consolidate_isochrones migrate_geojson_geoparquet rentals \
		aux_data isochrones state_polygons polygons_by_state fix convert_shp_files \
		postcode_polygons_subset ptv_stops_subset commuting_hulls

######### SUPPORT FILES #########
convert_shp_files:
	uv run scripts/export_shapefiles.py

postcode_polygons_subset: convert_shp_files	
	time uv run scripts/extract_postcode_polygons.py

ptv_stops_subset: postcode_polygons_subset
	time uv run scripts/extract_stops_within_union.py

commuting_hulls: ptv_stops_subset
	time uv run scripts/stops_by_transit_time.py

state_polygons: convert_shp_files
	uv run scripts/extract_state_polygons.py

polygons_by_state: state_polygons convert_shp_files
	uv run scripts/extract_boundaries_by_state.py --state 'Victoria'
	
aux_data: polygons_by_state commuting_hulls ptv_stops_subset postcode_polygons_subset

######### API FETCHING #########
scrape_isochrones:
	time uv run scripts/batch_isochrones_for_stops.py --status

rentals: 
	time uv run scripts/process_realestate_candidates.py

######### DATA TIDY UP #########
fix_geojson: scrape_isochrones
	uv run scripts/fix_geojson.py data/isochrone_cache/ -o data/geojson_fixed/

# create the data/isochrones_concatenated/**/*.geojson
consolidate_isochrones: fix_geojson
	time uv run scripts/consolidate_isochrones.py

migrate_geojson_geoparquet: consolidate_isochrones
	time uv run scripts/migrate_geojson_geoparquet.py

isochrones: aux_data consolidate_isochrones

all: aux_data migrate_geojson_geoparquet rentals
# This will run all the steps to prepare the data for the isochrone viewer
	uv run isochrone_viewer.py

fix:
	uvx rumdl check . --fix
	uv run ruff format . --respect-gitignore
	uv run ruff check --respect-gitignore --fix-only .
	uv run ruff check --respect-gitignore --statistics .