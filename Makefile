.PHONY: fix_geojson scrape_isochrones all consolidate_isochrones migrate_geojson_geoparquet rentals aux_data

######### SUPPORT FILES #########
aux_data:
#	uv run export_shapefiles.py
	uv run extract_postcode_polygons.py
	uv run extract_stops_within_union.py
	uv run stops_by_transit_time.py

######### API FETCHING #########
scrape_isochrones:
	uv run batch_isochrones_for_stops.py --status

rentals: 
	uv run process_realestate_candidates.py

######### DATA TIDY UP #########
fix_geojson: scrape_isochrones
	uv run fix_geojson.py data/geojson/foot/ -o data/geojson_fixed/foot/
	uv run fix_geojson.py data/geojson/bike/ -o data/geojson_fixed/bike/
	uv run fix_geojson.py data/geojson/car/ -o data/geojson_fixed/car/


# create the data/isochrones_concatenated/**/*.geojson
consolidate_isochrones: fix_geojson
	uv run consolidate_isochrones.py

migrate_geojson_geoparquet: consolidate_isochrones
	uv run migrate_geojson_geoparquet.py


all: aux_data migrate_geojson_geoparquet rentals
# This will run all the steps to prepare the data for the isochrone viewer
	uv run isochrone_viewer.py