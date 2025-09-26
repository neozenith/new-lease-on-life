// main.js - Application initialization and coordination
// Demonstrates how the modular structure would work together

// Import modules
import { initializeDuckDB } from './database.js';
import { COLORS, GEOLOCATION_CONFIG, resolveColorReference, hexToRgbA, getCommuteFillColor } from './utils.js';
import { handleItemClick, clearAllSelections } from './selection.js';

// Import external libraries (these would be loaded via script tags or ES modules in production)
// const {DeckGL, GeoJsonLayer, ScatterplotLayer} = deck;

// Global application state
let layerConfig = null;
let colors = {};

// Application initialization
async function initializeApplication() {
    console.log('Initializing DeckGL transport analysis viewer...');

    try {
        // Initialize database connection
        await initializeDuckDB();

        // Initialize deck.gl visualization
        initializeDeckGL();

        // Load layer configuration
        await loadLayerConfiguration();

        // Initialize UI controls
        initializeUIControls();

        console.log('Application initialized successfully');
    } catch (error) {
        console.error('Failed to initialize application:', error);
        // Show user-friendly error message
        showInitializationError(error);
    }
}

// Initialize deck.gl with configuration
function initializeDeckGL() {
    // Make deckgl globally accessible for the GPS location feature
    window.deckgl = new DeckGL({
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
        getTooltip: getTooltipContent,

        // Handle hover events - tooltip display is handled by getTooltip
        onHover: () => {
            // Hover handling is managed by deck.gl internally
        },

        // Handle click events for selection
        onClick: ({object, layer}) => {
            if (!object) {
                // Clicked on empty space - clear all selections
                clearAllSelections();
                return;
            }

            handleItemClick(object, layer);
        }
    });
}

// Tooltip configuration function
function getTooltipContent({object}) {
    if (!object) return null;

    // For ScatterplotLayer, the object IS the data point
    // For GeoJsonLayer, we need to check properties
    const props = object.properties || object || {};

    // Build tooltip content
    let html = '<div class="deck-tooltip">';

    // Check if this is a real estate candidate (has address property)
    if (props.address) {
        html += `<strong>${props.address}</strong><br/>`;

        // Show rent if available
        if (props.rent) {
            html += `<strong style="color: #2E7D32;">$${props.rent}/week</strong><br/>`;
        }

        // Show property features
        const features = [];
        if (props.bedrooms) features.push(`${props.bedrooms} bed`);
        if (props.bathrooms) features.push(`${props.bathrooms} bath`);
        if (props.parking) features.push(`${props.parking} car`);
        if (features.length > 0) {
            html += `${features.join(' · ')}<br/>`;
        }

        // Show walkability
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
    else if (props.POA_NAME21 && props.suburbs) {
        html += `<strong>Postcode: ${props.POA_NAME21}</strong><br/>`;
        html += `Suburbs: ${props.suburbs}<br/>`;
    }
    // Check if this is an LGA boundary
    else if (props.LGA_NAME24) {
        html += `<strong>LGA: ${props.LGA_NAME24}</strong><br/>`;
        if (props.STE_NAME21) {
            html += `State: ${props.STE_NAME21}<br/>`;
        }
        if (props.AREASQKM) {
            html += `Area: ${Number(props.AREASQKM).toFixed(1)} km²<br/>`;
        }
        if (props.LGA_CODE24) {
            html += `LGA Code: ${props.LGA_CODE24}<br/>`;
        }
    }
    // Check if this is an SA2 boundary
    else if (props.SA2_NAME21) {
        html += `<strong>SA2: ${props.SA2_NAME21}</strong><br/>`;
        if (props.STE_NAME21) {
            html += `State: ${props.STE_NAME21}<br/>`;
        }
        if (props.AREASQKM21) {
            html += `Area: ${Number(props.AREASQKM21).toFixed(1)} km²<br/>`;
        }
        if (props.SA2_CODE21) {
            html += `SA2 Code: ${props.SA2_CODE21}<br/>`;
        }
    }
    // Add stop name if available (for isochrones and PTV stops)
    else if (props.stop_name || props.STOP_NAME) {
        html += `<strong>${props.stop_name || props.STOP_NAME}</strong><br/>`;
        if (props.stop_id || props.STOP_ID) {
            html += `Stop ID: ${props.stop_id || props.STOP_ID}<br/>`;
        }
        if (props.mode || props.MODE) {
            html += `Mode: ${props.mode || props.MODE}<br/>`;
        }
        // Add transit metadata for stops
        if (props.transit_time_minutes !== undefined) {
            html += `Transit time: ${props.transit_time_minutes.toFixed(1)} min<br/>`;
        }
        if (props.transit_distance_km !== undefined) {
            html += `Transit distance: ${props.transit_distance_km.toFixed(2)} km<br/>`;
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
}

// Load layer configuration and create layers
async function loadLayerConfiguration() {
    try {
        const response = await fetch('./layers_config.json');
        const config = await response.json();

        layerConfig = config;
        const layers = createLayersFromConfig(config);
        window.deckgl.setProps({ layers });

        console.log('Layer configuration loaded successfully');
        console.log(`Loaded ${layers.length} layers from config`);
    } catch (error) {
        console.error('Error loading layer configuration:', error);
        // Could load default layers here if needed
    }
}

// Function to create layers from configuration
function createLayersFromConfig(config) {
    if (!config || !config.layers) return [];

    colors = config.colors || {};

    return config.layers.map(layerConfig => {
        // Resolve color references
        const processedConfig = {...layerConfig};
        const layerType = layerConfig.type || 'GeoJsonLayer';

        // Handle different layer types
        if (layerType === 'GeoJsonLayer' && processedConfig.id === 'real-estate-candidates') {
            // Special handling for real estate candidates layer
            if (typeof processedConfig.data === 'string' && processedConfig.data.endsWith('.geojson')) {
                // Load GeoJSON and convert to points array
                fetch(processedConfig.data)
                    .then(response => response.json())
                    .then(geojson => {
                        const expanded_features = geojson.features.map(feature => ({
                            ...feature.properties,
                            coordinates: feature.geometry.coordinates,
                            geometry: feature.geometry
                        }));

                        // Update the layer with processed data
                        const updatedConfig = {...processedConfig};
                        updatedConfig.data = expanded_features;

                        // Handle color extraction from property
                        if (updatedConfig.getFillColor === 'ptv_walkability_colour') {
                            updatedConfig.getFillColor = d => {
                                const hex = d.ptv_walkability_colour;
                                return hexToRgbA(hex) || COLORS.DEFAULT_FILL;
                            };
                        }

                        // Create new GeoJsonLayer with updated data
                        const newLayer = new GeoJsonLayer(updatedConfig);
                        // Update the deck with the new layer
                        const currentLayers = window.deckgl.props.layers || [];
                        const filteredLayers = currentLayers.filter(l => l.id !== updatedConfig.id);
                        window.deckgl.setProps({ layers: [...filteredLayers, newLayer] });
                    });

                // Return placeholder layer while loading
                return new GeoJsonLayer({
                    ...processedConfig,
                    data: []
                });
            }
        }

        // Standard color resolution for other properties
        ['getFillColor', 'getLineColor', 'highlightColor'].forEach(prop => {
            if (processedConfig[prop]) {
                processedConfig[prop] = resolveColorReference(processedConfig[prop], colors);
            }
        });

        // Remove the type property as it's not needed by deck.gl
        delete processedConfig.type;

        return new GeoJsonLayer(processedConfig);
    });
}

// Initialize UI controls and event handlers
function initializeUIControls() {
    // Handle close button for selection panel
    const closeBtn = document.getElementById('close-selection-panel');
    if (closeBtn) {
        closeBtn.addEventListener('click', () => {
            clearAllSelections();
        });
    }

    // Initialize other UI components
    initializeLayerControls();
    initializeLocationControls();
}

// Initialize layer visibility controls
function initializeLayerControls() {
    // This would handle the layer toggle functionality
    // Implementation would be similar to the existing populateLayerToggles function
    console.log('Layer controls initialized');
}

// Initialize GPS location controls
function initializeLocationControls() {
    // This would handle the location functionality
    // Implementation would use GEOLOCATION_CONFIG and COLORS constants
    console.log('Location controls initialized');
}

// Show initialization error to user
function showInitializationError(error) {
    const container = document.getElementById('container');
    if (container) {
        container.innerHTML = `
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background: #f5f5f5;
                color: #333;
                font-family: Arial, sans-serif;
            ">
                <div style="text-align: center; max-width: 500px; padding: 20px;">
                    <h2 style="color: #d32f2f;">Application Failed to Load</h2>
                    <p>There was an error initializing the visualization:</p>
                    <p style="color: #666; font-family: monospace; background: #fff; padding: 10px; border-radius: 4px;">
                        ${error.message}
                    </p>
                    <p>Please refresh the page to try again.</p>
                </div>
            </div>
        `;
    }
}

// Start the application when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApplication);
} else {
    initializeApplication();
}

// Handle loading errors
window.addEventListener('error', (e) => {
    console.error('Application error:', e);
});

// Export for potential external use
export {
    initializeApplication,
    createLayersFromConfig,
    getTooltipContent
};