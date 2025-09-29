.PHONY: fix_isochrone_geojson scrape_isochrones all consolidate_isochrones migrate_ptv_stops_lines_geojson_geoparquet rentals \
		aux_data isochrones state_polygons polygons_by_state fix convert_shp_files \
		postcode_polygons_subset ptv_stops_subset commuting_hulls site site_data \
		discover_rental_sales rental_sales rental_sales_duckdb clean_rental_sales

diagrams/%.png: diagrams/%.mmd
	npx -y -p @mermaid-js/mermaid-cli mmdc --input $< --output $@ -t default -b transparent -s 4

diag: $(patsubst %.mmd,%.png,$(wildcard diagrams/*.mmd))


##################################################
# CODE FORMATTING AND LINTING
##################################################

fix:
	uvx rumdl check . --fix
	uv run ruff format . --respect-gitignore
	uv run ruff check --respect-gitignore --fix-only .
	uv run ruff check --respect-gitignore --statistics .

##################################################
# AUX DATA
##################################################
convert_shp_files:
	uv run scripts/export_shapefiles.py

# Convertes the base PTV stops and lines geojson into geoparquet
ptv_lines_stops_parquet: data/public_transport_lines.parquet data/public_transport_stops.parquet
data/public_transport_lines.parquet data/public_transport_stops.parquet: data/public_transport_lines.geojson data/public_transport_stops.geojson
	time uv run scripts/migrate_geojson_geoparquet.py

postcode_polygons_subset: convert_shp_files	scripts/extract_postcode_polygons.py
	time uv run scripts/extract_postcode_polygons.py

ptv_stops_subset: postcode_polygons_subset
	time uv run scripts/extract_stops_within_union.py

# Commuting hulls and commuting times to each ptv stop which also subsets the ptv stops
commuting_hulls: ptv_stops_subset
	time uv run scripts/stops_by_transit_time.py

# Create a polygon for each state to to for other subsetting activities
state_polygons: convert_shp_files
	uv run scripts/extract_state_polygons.py

# Filter all boundary polygons to only the ones intersecting Victoria
# Eg Meshblocks, SA2, LGA, etc
polygons_by_state: state_polygons convert_shp_files
	uv run scripts/extract_boundaries_by_state.py --state 'Victoria'
	
aux_data: \
	polygons_by_state \
	commuting_hulls \
	ptv_stops_subset \
	postcode_polygons_subset \
	migrate_ptv_stops_lines_geojson_geoparquet

##################################################
# ISOCHRONES
##################################################
scrape_isochrones: data/public_transport_stops.geojson
	time uv run scripts/batch_isochrones_for_stops.py --status

# create the data/isochrones_geojson_fixed/**/*.geojson
fix_isochrone_geojson: scrape_isochrones
	uv run scripts/fix_geojson.py data/isochrone_cache/ -o data/isochrones_geojson_fixed/

# create the data/isochrones_concatenated/**/*.geojson
consolidate_isochrones: fix_isochrone_geojson
	time uv run scripts/consolidate_isochrones.py


isochrones: aux_data consolidate_isochrones


##################################################
# RENTAL/SALES DATA PROCESSING
##################################################

rentals: consolidate_isochrones
	time uv run scripts/geocode_candidates.py

rental_sales:
	uv run scripts/rental_sales/extract.py

##################################################
# MAPPING STATIC SITE DATA TO SOURCE JOBS
##################################################

data/geojson/ptv/boundaries/selected_lga_2024_aust_gda2020.geojson data/geojson/ptv/boundaries/selected_sa2_2021_aust_gda2020.geojson: postcode_polygons_subset

data/isochrones_concatenated/foot/5.geojson data/isochrones_concatenated/foot/15.geojson: fix_isochrone_geojson

data/geojson/ptv/ptv_commute_tier_hulls_metro_train.geojson data/geojson/ptv/ptv_commute_tier_hulls_metro_tram.geojson \
data/geojson/ptv/boundaries/selected_postcodes_with_trams_trains.geojson \
data/geojson/ptv/stops_with_commute_times_metro_train.geojson data/geojson/ptv/stops_with_commute_times_metro_tram.geojson: commuting_hulls

data/geojson/ptv/lines_within_union_metro_tram.geojson data/geojson/ptv/lines_within_union_metro_train.geojson: ptv_stops_subset

##################################################
# STATIC SITE DATA
##################################################
sites/webapp/data/5.geojson: data/isochrones_concatenated/foot/5.geojson
	cp $< $@
sites/webapp/data/15.geojson: data/isochrones_concatenated/foot/15.geojson
	cp $< $@

sites/webapp/data/all_candidates.geojson: data/candidate_real_estate/all_candidates.geojson
	cp $< $@

sites/webapp/data/lines_within_union_metro_tram.geojson: data/geojson/ptv/lines_within_union_metro_tram.geojson
	cp $< $@
sites/webapp/data/lines_within_union_metro_train.geojson: data/geojson/ptv/lines_within_union_metro_train.geojson
	cp $< $@
sites/webapp/data/ptv_commute_tier_hulls_metro_train.geojson: data/geojson/ptv/ptv_commute_tier_hulls_metro_train.geojson
	cp $< $@
sites/webapp/data/ptv_commute_tier_hulls_metro_tram.geojson: data/geojson/ptv/ptv_commute_tier_hulls_metro_tram.geojson
	cp $< $@
sites/webapp/data/selected_postcodes_with_trams_trains.geojson: data/geojson/ptv/boundaries/selected_postcodes_with_trams_trains.geojson
	cp $< $@
sites/webapp/data/stops_with_commute_times_metro_train.geojson: data/geojson/ptv/stops_with_commute_times_metro_train.geojson
	cp $< $@
sites/webapp/data/stops_with_commute_times_metro_tram.geojson: data/geojson/ptv/stops_with_commute_times_metro_tram.geojson
	cp $< $@
sites/webapp/data/selected_lga_2024_aust_gda2020.geojson: data/geojson/ptv/boundaries/selected_lga_2024_aust_gda2020.geojson
	cp $< $@

sites/webapp/data/selected_sa2_2021_aust_gda2020.geojson: data/geojson/ptv/boundaries/selected_sa2_2021_aust_gda2020.geojson
	cp $< $@



site_data: sites/webapp/data/5.geojson sites/webapp/data/15.geojson sites/webapp/data/all_candidates.geojson \
	sites/webapp/data/lines_within_union_metro_tram.geojson sites/webapp/data/lines_within_union_metro_train.geojson \
	sites/webapp/data/ptv_commute_tier_hulls_metro_train.geojson sites/webapp/data/ptv_commute_tier_hulls_metro_tram.geojson \
	sites/webapp/data/selected_postcodes_with_trams_trains.geojson \
	sites/webapp/data/stops_with_commute_times_metro_train.geojson sites/webapp/data/stops_with_commute_times_metro_tram.geojson \
	sites/webapp/data/selected_lga_2024_aust_gda2020.geojson sites/webapp/data/selected_sa2_2021_aust_gda2020.geojson rental_sales_duckdb


all: aux_data migrate_ptv_stops_lines_geojson_geoparquet rentals site_data