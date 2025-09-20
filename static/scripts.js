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
                        updatedConfig.data = expanded_features; // Set the results of loading the datafile to the processed features

                        // Handle color extraction from property
                        if (updatedConfig.getFillColor === 'ptv_walkability_colour') {
                            updatedConfig.getFillColor = d => { // Sets this property to a function that extracts color from each data point
                                const hex = d.ptv_walkability_colour;
                                return hexToRgbA(hex) || [255, 255, 255, 255];
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
                processedConfig[prop] = resolveColorReference(processedConfig, processedConfig[prop], colors);
            }
        });

        // Remove the type property as it's not needed by deck.gl
        delete processedConfig.type;

        
        return new GeoJsonLayer(processedConfig);
        
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
        else if (props.POA_NAME21 && props.suburbs) {
            html += `<strong>Postcode: ${props.POA_NAME21}</strong><br/>`;
            html += `Suburbs: ${props.suburbs}<br/>`;
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
        window.deckgl.setProps({ layers });
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

// GPS Location functionality
let userLocationLayer = null;
let userLocationCoords = null;
let isFirstLocation = true;

// Function to add user location to map
function addUserLocation(longitude, latitude, centerOnLocation = false) {
    // Store the coordinates
    userLocationCoords = { longitude, latitude };

    // Create a ScatterplotLayer for the user's location
    const locationLayer = new ScatterplotLayer({
        id: 'user-location',
        data: [{
            position: [longitude, latitude],
            name: 'Your Location'
        }],
        getPosition: d => d.position,
        getRadius: 8,
        getFillColor: [255, 0, 0, 255], // Red color
        getLineColor: [255, 255, 255, 255], // White outline
        lineWidthMinPixels: 2,
        pickable: true,
        radiusMinPixels: 6,
        radiusMaxPixels: 20,
        filled: true,
        stroked: true
    });

    // Get current layers and filter out any existing user location layer
    const currentLayers = window.deckgl.props.layers || [];
    const filteredLayers = currentLayers.filter(l => l.id !== 'user-location');

    // Add the new location layer
    userLocationLayer = locationLayer;
    window.deckgl.setProps({
        layers: [...filteredLayers, locationLayer]
    });

    // Only center on first location or if explicitly requested
    if (centerOnLocation) {
        // Simple approach: recreate deck with new initial view state
        window.deckgl.setProps({
            initialViewState: {
                longitude: longitude,
                latitude: latitude,
                zoom: 14,
                pitch: 0,
                bearing: 0,
                transitionDuration: 1000
            },
            controller: true
        });
    }
}

// Function to center map on user location
function centerOnUserLocation() {
    if (userLocationCoords) {
        const { longitude, latitude } = userLocationCoords;

        // Simple approach: recreate deck with new initial view state
        window.deckgl.setProps({
            initialViewState: {
                longitude: longitude,
                latitude: latitude,
                zoom: 14,
                pitch: 0,
                bearing: 0,
                transitionDuration: 1000
            },
            controller: true
        });
    }
}

// Function to show status message
function showLocationStatus(message, isError = false) {
    const statusElement = document.getElementById('location-status');
    statusElement.style.display = 'block';
    statusElement.textContent = message;
    statusElement.style.color = isError ? '#d32f2f' : '#2e7d32';

    // Hide status after 5 seconds
    setTimeout(() => {
        statusElement.style.display = 'none';
    }, 5000);
}

// Handle location button click
document.getElementById('get-location-btn').addEventListener('click', function() {
    const button = this;

    // Check if geolocation is available
    if (!navigator.geolocation) {
        showLocationStatus('Geolocation is not supported by your browser', true);
        return;
    }

    // Disable button and show loading state
    button.disabled = true;
    button.innerHTML = '<span style="font-size: 16px;">⏳</span><span>Getting Location...</span>';

    // Request current position
    navigator.geolocation.getCurrentPosition(
        // Success callback
        function(position) {
            const { latitude, longitude } = position.coords;

            // Add location to map - only center on first location
            addUserLocation(longitude, latitude, isFirstLocation);

            // Mark that we've gotten the first location
            if (isFirstLocation) {
                isFirstLocation = false;
            }

            // Update button state
            button.disabled = false;
            button.innerHTML = '<span style="font-size: 16px;">📍</span><span>Update Location</span>';

            // Show the center button
            const centerBtn = document.getElementById('center-location-btn');
            if (centerBtn) {
                centerBtn.style.display = 'flex';
            }

            // Show success message
            showLocationStatus(`Location found: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`, false);

            console.log('User location:', { latitude, longitude });
        },

        // Error callback
        function(error) {
            button.disabled = false;
            button.innerHTML = '<span style="font-size: 16px;">📍</span><span>Show My Location</span>';

            let errorMessage = 'Unable to get your location';
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    errorMessage = 'Location access denied. Please enable location permissions.';
                    break;
                case error.POSITION_UNAVAILABLE:
                    errorMessage = 'Location information unavailable.';
                    break;
                case error.TIMEOUT:
                    errorMessage = 'Location request timed out.';
                    break;
            }

            showLocationStatus(errorMessage, true);
            console.error('Geolocation error:', error);
        },

        // Options
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
});

// Handle center on location button click
const centerBtn = document.getElementById('center-location-btn');
if (centerBtn) {
    centerBtn.addEventListener('click', function() {
        if (userLocationCoords) {
            centerOnUserLocation();
            showLocationStatus('Centered on your location', false);
        }
    });
}