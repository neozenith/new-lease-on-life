# Isochrone Visualization Tool - Claude Code Configuration

## Project Overview

**Project Type**: Python Geospatial Analysis & Visualization Tool  
**Framework**: Python with Panel/Holoviz + PyDeck (DeckGL.js)  
**Primary Domain**: Geospatial data processing and transportation analysis  

This project provides tools for geocoding addresses and calculating isochrones using the GraphHopper API. It processes public transport data, creates spatial visualizations, and provides an interactive web interface for exploring transportation accessibility.

## Current Architecture

**Core Components**:
- **Data Pipeline**: Extract → Transform → Load (ETL) for geospatial data
- **API Integration**: GraphHopper geocoding and isochrone services
- **File Storage**: GeoJSON and GeoParquet files for geospatial data
- **Visualization**: Panel/Holoviz web app with PyDeck serving DeckGL.js
- **Build System**: Makefile-driven workflow for data processing pipeline

**Data Flow**:

```text
Postcodes + Transport Stops → Isochrone API → GeoJSON/GeoParquet Files → PyDeck/DeckGL → Panel Frontend
```

**⚠️ Current Implementation Notes**:
- **DuckDB Integration**: Configured in dependencies but NOT currently implemented in data processing
- **Data Storage**: Currently using direct file I/O with GeoJSON and GeoParquet formats
- **Visualization**: PyDeck loads files directly and serves DeckGL.js through HoloViz Panel
- **No Database Layer**: All geospatial queries happen at file level, not through spatial database

## Development Environment

**Python Version**: 3.12+  
**Package Manager**: `uv` (with inline script metadata)  
**Code Quality**: `ruff` for formatting and linting  

**Dependencies**:
- **Core**: `duckdb`, `duckdb-extensions`, `duckdb-extension-spatial` *(not yet implemented)*
- **Geospatial**: `geopandas`, `shapely`, `pyogrio`, `fiona`
- **Visualization**: `panel`, `pydeck`, `holoviews`, `bokeh`
- **API**: `requests`, `python-dotenv`
- **Development**: `pytest`, `ruff`

## Commands & Scripts

**Build Commands**:

```bash
make all              # Complete data pipeline + start viewer
make aux_data         # Process postcodes and transport stops
make scrape_isochrones # Fetch isochrone data from API
make fix_geojson      # Clean and validate geojson files
make consolidate_isochrones # Merge isochrone data
make migrate_geojson_geoparquet # Convert to efficient format
make rentals          # Process real estate data
```

**Development Commands**:

```bash
make fix              # Format and lint code with ruff
uv run <script.py>    # Run individual scripts with dependencies
```

**Key Scripts**:
- `isochrone_viewer.py` - Interactive web visualization
- `batch_isochrones_for_stops.py` - API data fetching
- `extract_postcode_polygons.py` - Postcode boundary processing
- `process_realestate_candidates.py` - Real estate data analysis

## Configuration

**Environment Variables** (`.env`):

Read `.env.sample` for latest defintions of environment variables that should be available.

```sh
GRAPHHOPPER_API_KEY=your_graphhopper_api_key_here

# Google Maps API key - required for map visualization and geocoding and commuting directions and times
# Sign up at https://developers.google.com/maps/get-started and get a free API key
# Note: VITE_GOOGLE_MAPS_API_KEY is used for the frontend
# and GOOGLE_MAPS_API_KEY is used for the backend
# Both should be the same key for simplicity
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here
VITE_GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# Mapbox API token - required for map visualization and isochrones
# Sign up at https://www.mapbox.com/ and get a free API token
MAPBOX_API_TOKEN=your_mapbox_api_token_here
```

**Project Settings**:
- Line length: 100 characters
- Python target: 3.12
- Quote style: double quotes
- Indent: spaces

## Testing & Quality

**Linting**: `ruff` with comprehensive rule set (E, F, B, I, N, UP, S, BLE, A, C4, T10, ICN)  
**Formatting**: `ruff format` with consistent style  
**Testing**: `pytest` framework (configured in dev dependencies)

## Data Sources

**Primary APIs**:
- GraphHopper Geocoding API
- GraphHopper Isochrone API

**Victorian Government Open Data**:
- Public transport stops and routes
- Postcode boundaries  
- Property and demographic data (property sales reports)
- Urban planning datasets

## Production Concerns & Architecture Questions

**Current Limitations**:
- File-based data serving (not scalable for production)
- No spatial database queries (missing DuckDB implementation)
- Direct file loading into frontend (no API layer)
- No caching strategy for geospatial computations
- Single-user local application (not multi-user ready)

**Architecture Analysis Needed**:
1. **Geospatial API Design**: How to effectively serve large geospatial datasets via REST/GraphQL API
2. **Database Integration**: Complete DuckDB spatial extension implementation vs alternatives
3. **Caching Strategy**: Spatial query caching, tile caching, isochrone result caching
4. **Frontend/Backend Separation**: API-first architecture for scalability
5. **Performance Optimization**: Spatial indexing, query optimization, data chunking
6. **Deployment Strategy**: Local vs cloud deployment, containerization, scaling

## Claude Code Integration Notes

**Recommended Personas**:  
- `--persona-analyzer` for data architecture analysis
- `--persona-architect` for production architecture planning
- `--persona-performance` for geospatial optimization
- `--persona-backend` for API design and database integration
- `--persona-frontend` for visualization improvements

**Common Operations**:
- Geospatial data processing and analysis
- API integration and error handling
- Interactive visualization development
- Performance optimization for large datasets
- Production architecture planning

**Development Workflow**:
1. Use `make fix` for code formatting before commits
2. Test individual scripts with `uv run <script.py>`
3. Use complete pipeline with `make all`
4. Monitor API usage and caching for efficiency

**Priority Analysis Areas**:
- Database integration strategy (DuckDB vs PostGIS vs alternatives)
- API architecture for geospatial data serving
- Frontend/backend decoupling for production deployment
- Performance optimization for large Victorian property datasets

## Future Work & Technical Exploration



**Other Technical Explorations**:
- Integration with Victorian property data for enhanced analysis
- Vector tile serving for efficient data delivery
- Progressive web app capabilities for offline usage
- Real-time isochrone calculation vs pre-computed results

