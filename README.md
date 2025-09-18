# New Lease On Life 🏘️

Silly little GIS project to help me narrow down finding a rental suitable for me as I am moving to Melbourne.

## Features

- Geocode addresses from a YAML file using the Google Maps API
- Calculate "Commuting Contours"
- Calculate isochrones for different transport modes (foot, car, bike) and time limits
- Visualize isochrones using DeckGL.JS

## Requirements

- Python 3.12 or higher
- MapBox API key
- Google Maps API Key
- `uv` installed (for dependency management)

## License

[MIT License](LICENSE)

## Acknowledgements

This project uses the API for geocoding and isochrone calculation.

- [MapBox Isochrone](https://docs.mapbox.com/api/navigation/isochrone/)

It also makes use of Google Directions API

- [Google Maps Directions API (Legacy)](https://developers.google.com/maps/documentation/directions)

Thanks to Victoria Government:

- [Public Transport Lines and Stops (GeoJSON)](https://discover.data.vic.gov.au/dataset/public-transport-lines-and-stops)

Thanks to Australian Bureau of Statistics:

- [Postcode Polygon Boundaries (SHP Files)](https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files)

Also thanks to GeoPandas for the easy assist manipulating all of these geospatial files

- [GeoPandas](https://geopandas.org/en/stable/)

