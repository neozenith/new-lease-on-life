// Destructure deck.gl components
const {DeckGL, GeoJsonLayer, ScatterplotLayer} = deck;

// Load layer configuration
let layerConfig = null;
let colors = {};

// function for string hexcode rgb to array
function hexToRgbA(hex) {
    if (hex.startsWith('#')) {
        // Handle #rgb #rrggbb and #rrggbbaa formats
        let r, g, b, a = 255; // Default is solid white
        if (hex.length === 4) {
            r = parseInt(hex[1] + hex[1], 16);
            g = parseInt(hex[2] + hex[2], 16);
            b = parseInt(hex[3] + hex[3], 16);
        } else if (hex.length === 7) {
            r = parseInt(hex.substring(1, 3), 16);
            g = parseInt(hex.substring(3, 5), 16);
            b = parseInt(hex.substring(5, 7), 16);
        } else if (hex.length === 9) {
            r = parseInt(hex.substring(1, 3), 16);
            g = parseInt(hex.substring(3, 5), 16);
            b = parseInt(hex.substring(5, 7), 16);
            a = parseInt(hex.substring(7, 9), 16);
        }
        return [r, g, b, a];
    }
    return null;
}

// Function to resolve color references in the config
function resolveColorReference(config, value, colors) {
    if (typeof value === 'string') {
        if (value.startsWith('color:')) {
            const colorKey = value.substring(6);
            return colors[colorKey] || [255, 255, 255, 255];
        } 
    }
    return value;
}

// Function to create layers from config
function createLayersFromConfig(config) {
    if (!config || !config.layers) return [];

    colors = config.colors || {};

    return config.layers.map(layerConfig => {
        // Resolve color references
        const processedConfig = {...layerConfig};
        const layerType = layerConfig.type || 'GeoJsonLayer';

        // Handle different layer types
        if (layerType === 'ScatterplotLayer') {
            // For ScatterplotLayer with GeoJSON data
            if (typeof processedConfig.data === 'string' && processedConfig.data.endsWith('.geojson')) {
                // Load GeoJSON and convert to points array
                fetch(processedConfig.data)
                    .then(response => response.json())
                    .then(geojson => {
                        const points = geojson.features.map(feature => ({
                            ...feature.properties,
                            coordinates: feature.geometry.coordinates
                        }));

                        // Update the layer with processed data
                        const updatedConfig = {...processedConfig};
                        updatedConfig.data = points;

                        // Handle color extraction from property
                        if (updatedConfig.getFillColor === 'ptv_walkability_colour') {
                            updatedConfig.getFillColor = d => {
                                const hex = d.ptv_walkability_colour;
                                return hexToRgbA(hex) || [255, 255, 255, 255];
                            };
                        }

                        // Handle position extraction
                        if (updatedConfig.getPosition === 'coordinates') {
                            updatedConfig.getPosition = d => d.coordinates;
                        }

                        const newLayer = new ScatterplotLayer(updatedConfig);
                        // Update the deck with the new layer
                        const currentLayers = deckgl.props.layers || [];
                        const filteredLayers = currentLayers.filter(l => l.id !== updatedConfig.id);
                        deckgl.setProps({ layers: [...filteredLayers, newLayer] });
                    });

                // Return placeholder layer while loading
                return new ScatterplotLayer({
                    ...processedConfig,
                    data: []
                });
            }
        }

        // Standard color resolution for other properties
        ['getFillColor', 'getLineColor', 'highlightColor'].forEach(prop => {
            if (processedConfig[prop]) {
                processedConfig[prop] = resolveColorReference(processedConfig, processedConfig[prop], colors);
            }
        });

        // Remove the type property as it's not needed by deck.gl
        delete processedConfig.type;

        // Return appropriate layer type
        if (layerType === 'ScatterplotLayer') {
            return new ScatterplotLayer(processedConfig);
        } else {
            return new GeoJsonLayer(processedConfig);
        }
    });
}

// Color scale for commute time hulls (gradient based on transit time)
const getCommuteFillColor = (minutes) => {
    // Create gradient from green (short) to red (long) based on minutes
    const normalized = Math.min(Math.max((minutes - 100) / 300, 0), 1); // Normalize 100-400 min to 0-1
    const r = Math.floor(255 * normalized);
    const g = Math.floor(255 * (1 - normalized));
    const b = 50;
    return [r, g, b, 30]; // Low opacity for overlay effect
};

// Initialize deck.gl with empty layers initially
let deckgl = new DeckGL({
    container: 'container',

    // Set initial view to Victoria, Australia
    initialViewState: {
        longitude: 144.9631,  // Melbourne coordinates
        latitude: -37.8136,
        zoom: 11,
        pitch: 0,
        bearing: 0
    },

    // Enable map controls
    controller: true,

    // Use CartoDB dark basemap
    mapStyle: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',

    // Initial empty layers - will be populated after loading config
    layers: [],

    // Tooltip configuration
    getTooltip: ({object}) => {
        if (!object) return null;

        // For ScatterplotLayer, the object IS the data point
        // For GeoJsonLayer, we need to check properties
        const props = object.properties || object || {};

        // Build tooltip content
        let html = '<div class="deck-tooltip">';

        // Check if this is a real estate candidate (has address property)
        if (props.address) {
            html += `<strong>${props.address}</strong><br/>`;
            if (props.ptv_walkable_5min !== undefined) {
                html += `5-min walkable: ${props.ptv_walkable_5min ? 'Yes' : 'No'}<br/>`;
            }
            if (props.ptv_walkable_15min !== undefined) {
                html += `15-min walkable: ${props.ptv_walkable_15min ? 'Yes' : 'No'}<br/>`;
            }
        }
        // Check if this is a commute tier hull
        else if (props.MODE && props.transit_time_minutes_nearest_tier) {
            html += `<strong>${props.MODE}</strong><br/>`;
            html += `Transit time: ${Math.round(props.transit_time_minutes_nearest_tier)} minutes<br/>`;
            html += `Stations included: ${props.point_count || props.STOP_NAME || 'N/A'}<br/>`;
        }
        // Add stop name if available (for isochrones)
        else if (props.stop_name) {
            html += `<strong>${props.stop_name}</strong><br/>`;
            if (props.stop_id) {
                html += `Stop ID: ${props.stop_id}<br/>`;
            }
            if (props.mode) {
                html += `Mode: ${props.mode}<br/>`;
            }
            if (props.time_limit) {
                html += `Time: ${props.time_limit} minutes<br/>`;
            }
        }
        // Generic isochrone info
        else {
            const timeLimit = props.time_limit || (object.source?.id === 'isochrones-5min' ? 5 : 15);
            html += `<strong>${timeLimit}-minute isochrone</strong><br/>`;
            html += `Area reachable within ${timeLimit} minutes`;
        }

        html += '</div>';

        return {html};
    },

    // Handle hover events (simplified - removed highlight logic that was causing errors)
    onHover: ({object, x, y}) => {
        // Hover handling is managed by deck.gl internally
        // Tooltip display is handled by getTooltip
    }
});

// Load the layer configuration and initialize layers
fetch('./layers_config.json')
    .then(response => response.json())
    .then(config => {
        layerConfig = config;
        const layers = createLayersFromConfig(config);
        deckgl.setProps({ layers });
        console.log('Layer configuration loaded successfully');
        console.log(`Loaded ${layers.length} layers from config`);
    })
    .catch(error => {
        console.error('Error loading layer configuration:', error);
        // Fallback - could load default layers here if needed
    });

// Log when data is loaded
console.log('DeckGL transport analysis viewer initialized');
console.log('Loading layer configuration...');

// Handle loading errors
window.addEventListener('error', (e) => {
    console.error('Error loading data:', e);
});