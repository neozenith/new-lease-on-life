# TODO

## Features and Bugs

- Extract Sales and Rental historical data from excel files into parquet / csv
- Link Rental/Sales data with appropriate geoshapes (Suburb and LGA) with appropriate `time_bucket` field
- Animate the Deck.GL visualisation with the historical rental and sales data
- Add a paired visualisation of a line chart showing the rental and sales data over time highlighting  
    current timebucket shown in the Deck.gl component
- All cross filtering by selecting a geoshape or a line in the line chart to filter the underlying data.
- Test a deck.gl component loading geojson parquet from a URL. Hypotheses: I do not need an API server, just well laid out data chunks from statically hosted endpoints.
- Implement DuckDB caching and integration?

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
