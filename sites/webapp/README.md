# Isochrone Visualization

Interactive map visualization showing transport accessibility isochrones in Melbourne, Victoria.

## Features

- 5 and 15-minute walking isochrones from public transport stops
- Metro train and tram network visualization
- Commute time tier hulls for different transport modes
- Real estate candidate locations with walkability indicators

## Data Layers

- **Isochrones**: 5 and 15-minute walking catchments
- **Transport Lines**: Metro train (green) and tram (orange) routes
- **Transport Stops**: Station and stop locations with commute times
- **Real Estate**: Property locations colored by walkability score

## Usage

The visualization loads automatically and displays multiple data layers. Hover over any element to see detailed information.

## Configuration

Layer settings are configured in `layers_config.json` which controls:

- Layer visibility and styling
- Color schemes for different transport modes
- Point sizes and line widths
- Interactive hover effects

## Requirements

Modern web browser with WebGL support for deck.gl rendering.
