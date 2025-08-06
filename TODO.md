# TODO

## Features and Bugs

### Rental and Sales Data

Read the scripts/CLAUDE.md and create as many helper scripts as need be.

Create a new python script under `scripts/` that will extract the data out of `data/originals/rental/*.xslx` and `data/originals/sales/*.xslx` and save the results into their respective folders under `data/originals_converted/`.
These excel files contain the median renta

I want all the data consolidated into one file in csv in tall format (not wide format), where there is a column for:

- `value` is a floating point value for the respective median value we are extracting
- `count` if it is available is the associated count of records used to determine the median for that time_bucket
- the `time_bucket` eg formatted like YYYY, YYYY-QQ, YYYY-MM
- `value_type` this is either `sales` or `rent`
- the dwelling type (House, Unit, Vacant Land, Flat). This might be in the file name or the name of the excel worksheets.
- the number of bedrooms. This might be in the file name or the name of the excel worksheets. IMPORTANT make sure you find these values.
- `geospatial_type` - this should be `SUBURB` or `LGA` or `POSTCODE`. 
- the `geospatial_id` eg this could be a postcode, suburb name or an LGA. 
    - Look under `data/originals_converted/boundaries/LGA_2024_AUST_GDA2020/` for LGA data
    - Look under `data/originals_converted/boundaries/SA2_2021_AUST_SHP_GDA2020/` for Suburb data
    - Look under `data/originals_converted/boundaries/POA_2021_AUST_GDA2020_SHP/` for Postcode data
    - Leverage `geopandas` (and `pyarrow`) to explore the geojson or geoparquet (extension `.parquet`) to cross check and validate the suburb and LGA from the excel.

IMPORTANT ALL `value`s from all excel files should be extracted into this one CSV or split into a `consolidated_sales.csv` and `consolidated_rentals.csv` if need be.

Once this CSV file is created create a GeoJSON file where every record gets their corresponding polygon.

Ensure the output files are valid CSV and GeoJSON.


### Load Static Layers

I am migrating away from `isochrone_viewer.py` to `webapp/app.py`. I want to add dynamic controlled GeoJSON Layers which depending on a toggle control they are visible or not and this will be irrespective of the "Play" status of the existing animation code. In a separate task we will add the time animated data.

### Animate Deck.GL

- Animate the Deck.GL visualisation with the historical rental and sales data

### Paired Visualisations

- Add a paired visualisation of a line chart showing the rental and sales data over time highlighting  
    current timebucket shown in the Deck.gl component
- All cross filtering by selecting a geoshape or a line in the line chart to filter the underlying data.

### Deck.gl loading from a static URL

- Test a deck.gl component loading geojson parquet from a URL. Hypotheses: I do not need an API server, just well laid out data chunks from statically hosted endpoints.

### DuckDB

Replace local file caching with DuckDB or leverage DuckDB as a server to read the local parquet files and wrap a FastAPI around it to server the data urls to Deck.gl webapp

## More interesting datasets

List of some extra datasets To explore

- https://discover.data.vic.gov.au/dataset/block-level-energy-consumption-modelled-on-building-attributes-2011-baseline
- https://discover.data.vic.gov.au/dataset/street-names
- https://discover.data.vic.gov.au/dataset/public-barbecues
- https://discover.data.vic.gov.au/dataset/cafe-restaurant-bistro-seats
- https://discover.data.vic.gov.au/dataset/residential-dwellings
- https://discover.data.vic.gov.au/dataset/live-music-venues
- https://discover.data.vic.gov.au/dataset/trees-with-species-and-dimensions-urban-forest
- https://discover.data.vic.gov.au/dataset/childcare-centres
- https://discover.data.vic.gov.au/dataset/playgrounds
- https://discover.data.vic.gov.au/dataset/block-level-energy-consumption-modelled-on-building-attributes-2026-projection-business-as-usua
- https://discover.data.vic.gov.au/dataset/street-lights-with-emitted-lux-level-council-owned-lights-only
- https://discover.data.vic.gov.au/dataset/street-addresses
- https://discover.data.vic.gov.au/dataset/bar-tavern-pub-patron-capacity
- https://discover.data.vic.gov.au/dataset/outdoor-artworks
- https://discover.data.vic.gov.au/dataset/landmarks-and-places-of-interest-including-schools-theatres-health-services-sports-facilities-p
- https://discover.data.vic.gov.au/dataset/public-open-space-400m-walkable-catchment
- https://discover.data.vic.gov.au/dataset/open-space

- https://discover.data.vic.gov.au/dataset/fus-land-use

- https://discover.data.vic.gov.au/dataset/?sort=score+desc%2C+metadata_modified+desc&q=&organization=crime-statistics-agency&groups=&res_format=
- https://discover.data.vic.gov.au/dataset/government-dates-api-data
- https://discover.data.vic.gov.au/dataset/popular-baby-names
- https://discover.data.vic.gov.au/dataset/local-government-performance-reporting
- https://discover.data.vic.gov.au/dataset/school-locations-2021
- https://discover.data.vic.gov.au/dataset/victorian-government-school-zones-2026

- https://discover.data.vic.gov.au/dataset/rental-report-quarterly-quarterly-median-rents-by-lga
- https://discover.data.vic.gov.au/dataset/rental-report-quarterly-moving-annual-rents-by-suburb
- https://discover.data.vic.gov.au/dataset/rental-report-quarterly-data-tables
- https://discover.data.vic.gov.au/dataset/rental-report-quarterly-affordable-lettings-by-lga

- https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-yearly-summary
- https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-house-by-suburb
- https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-unit-by-suburb
- https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-vacant-land-by-suburb
- https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-unit-by-suburb-time-series
- https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-house-by-suburb-time-series
- https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-median-vacant-land-by-suburb-time-series
- https://discover.data.vic.gov.au/dataset/victorian-property-sales-report-time-series

- https://discover.data.vic.gov.au/dataset/vpa-precinct-boundaries

- https://discover.data.vic.gov.au/dataset/vif2023-lga-population-household-dwelling-projections-to-2036
- https://discover.data.vic.gov.au/dataset/vif2023-lga-population-age-sex-projections-to-2036

- https://discover.data.vic.gov.au/dataset/vicmap-property
- https://discover.data.vic.gov.au/dataset/vicmap-hydro
- https://discover.data.vic.gov.au/dataset/vicmap-planning
- https://discover.data.vic.gov.au/dataset/vicmap-address

- https://discover.data.vic.gov.au/dataset/vicmap-elevation-rest-api
- https://discover.data.vic.gov.au/dataset/vicmap-property-parcel-polygon
- https://discover.data.vic.gov.au/dataset/vicmap-property-property-polygon
- https://discover.data.vic.gov.au/dataset/vicmap-property-property-table
- https://discover.data.vic.gov.au/dataset/vicmap-elevation-1-5-contours-relief
