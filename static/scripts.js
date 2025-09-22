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
    },

    // Handle hover events (simplified - removed highlight logic that was causing errors)
    onHover: ({object, x, y}) => {
        // Hover handling is managed by deck.gl internally
        // Tooltip display is handled by getTooltip
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

// Selection Management System
const selectedItems = new Map(); // Map to store selected items by type
const maxSelectionsByType = {
    'real-estate-candidates': 2,
    'postcodes': 2,  // Now supports up to 2 selections
    'ptv-stops-tram': 1,
    'ptv-stops-train': 1
};

// Get item type from layer ID
function getItemType(layer) {
    const layerId = layer.id;

    // Check for real estate candidates
    if (layerId === 'real-estate-candidates') {
        return 'real-estate-candidates';
    }

    // Check for postcodes (matching the actual layer ID from config)
    if (layerId === 'postcodes-with-trams-trains' ||
        layerId === 'selected_postcodes' || layerId === 'unioned_postcodes' ||
        layerId === 'postcodes-selected' || layerId === 'postcodes-unioned') {
        return 'postcodes';
    }

    // Check for tram stops
    if (layerId === 'ptv-stops-tram') {
        return 'ptv-stops-tram';
    }

    // Check for train stops
    if (layerId === 'ptv-stops-train') {
        return 'ptv-stops-train';
    }

    return null; // Not a selectable type
}

// Generate unique ID for an item
function getItemId(object, layer) {
    const props = object.properties || object;
    const type = getItemType(layer);

    if (type === 'real-estate-candidates' && props.address) {
        return `${type}-${props.address}`;
    } else if (type === 'postcodes' && props.POA_NAME21) {
        return `${type}-${props.POA_NAME21}`;
    } else if ((type === 'ptv-stops-tram' || type === 'ptv-stops-train') && props.stop_name) {
        return `${type}-${props.stop_id || props.stop_name}`;
    }

    // Fallback to coordinates if available
    if (object.geometry && object.geometry.coordinates) {
        const coords = object.geometry.coordinates;
        return `${type}-${coords[0]}-${coords[1]}`;
    }

    return `${type}-${Date.now()}`; // Last resort
}

// Handle item click
function handleItemClick(object, layer) {
    const type = getItemType(layer);

    if (!type) {
        return; // Not a selectable layer
    }

    const itemId = getItemId(object, layer);
    const currentTypeSelections = Array.from(selectedItems.values()).filter(item => item.type === type);

    // Check if this exact item is already selected
    if (selectedItems.has(itemId)) {
        // Toggle off - remove this item
        selectedItems.delete(itemId);
    } else {
        // Check if clicking on a different type - clear all selections
        const hasOtherTypes = Array.from(selectedItems.values()).some(item => item.type !== type);
        if (hasOtherTypes) {
            clearAllSelections();
        }

        // Check max selections for this type
        const maxForType = maxSelectionsByType[type] || 999;

        if (currentTypeSelections.length >= maxForType) {
            // Remove oldest selection of this type
            const oldestKey = Array.from(selectedItems.keys()).find(key =>
                selectedItems.get(key).type === type
            );
            if (oldestKey) {
                selectedItems.delete(oldestKey);
            }
        }

        // Add new selection
        selectedItems.set(itemId, {
            type: type,
            object: object,
            layer: layer,
            properties: object.properties || object
        });
    }

    updateSelectionDisplay();
    updateLayerHighlights();
}

// Clear all selections
function clearAllSelections() {
    selectedItems.clear();
    updateSelectionDisplay();
    updateLayerHighlights();
}

// Update the selection panel display
function updateSelectionDisplay() {
    const panel = document.getElementById('selection-panel');
    const content = document.getElementById('selection-content');

    if (selectedItems.size === 0) {
        // Hide panel
        panel.style.height = '0';
        content.innerHTML = '';
        return;
    }

    // Show panel - take up bottom third of screen
    panel.style.height = '33vh';

    // Build content HTML
    let html = '';
    const itemsByType = new Map();

    // Group items by type
    selectedItems.forEach((item, id) => {
        if (!itemsByType.has(item.type)) {
            itemsByType.set(item.type, []);
        }
        itemsByType.get(item.type).push(item);
    });

    // Display items grouped by type
    itemsByType.forEach((items, type) => {
        const typeLabel = {
            'real-estate-candidates': 'Real Estate Properties',
            'postcodes': 'Postcodes',
            'ptv-stops-tram': 'Tram Stops',
            'ptv-stops-train': 'Train Stations'
        }[type] || type;

        html += `<div style="margin-bottom: 20px;">`;
        html += `<h4 style="margin: 0 0 12px 0; color: #333; font-size: 14px; font-weight: bold;">${typeLabel}</h4>`;

        items.forEach((item, index) => {
            const props = item.properties;
            html += `<div style="margin-bottom: 12px; padding: 12px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #007AFF;">`;

            if (type === 'real-estate-candidates') {
                html += `<strong>${props.address}</strong><br/>`;
                if (props.ptv_walkable_5min !== undefined) {
                    html += `5-min walkable: ${props.ptv_walkable_5min ? 'Yes ✓' : 'No ✗'}<br/>`;
                }
                if (props.ptv_walkable_15min !== undefined) {
                    html += `15-min walkable: ${props.ptv_walkable_15min ? 'Yes ✓' : 'No ✗'}<br/>`;
                }
            } else if (type === 'postcodes') {
                html += `<strong>Postcode: ${props.POA_NAME21}</strong><br/>`;
                if (props.suburbs) {
                    html += `Suburbs: ${props.suburbs}<br/>`;
                }
            } else if (type === 'ptv-stops-tram' || type === 'ptv-stops-train') {
                html += `<strong>${props.stop_name || props.STOP_NAME}</strong><br/>`;
                if (props.stop_id || props.STOP_ID) {
                    html += `Stop ID: ${props.stop_id || props.STOP_ID}<br/>`;
                }
                // Display transit time and distance metadata
                if (props.transit_time_minutes !== undefined) {
                    html += `Transit time to Southern Cross: ${props.transit_time_minutes.toFixed(1)} minutes<br/>`;
                }
                if (props.transit_distance_km !== undefined) {
                    html += `Transit distance: ${props.transit_distance_km.toFixed(2)} km<br/>`;
                }
                if (props.routes || props.ROUTES) {
                    html += `Routes: ${props.routes || props.ROUTES}<br/>`;
                }
            }

            html += `</div>`;
        });

        html += `</div>`;
    });

    content.innerHTML = html;
}

// Update layer highlights to show selected items
function updateLayerHighlights() {
    const layers = window.deckgl.props.layers || [];
    const selectedIds = new Set();

    // Collect IDs of selected items
    selectedItems.forEach((item, id) => {
        const props = item.properties;
        if (props.address) selectedIds.add(props.address);
        if (props.POA_NAME21) selectedIds.add(props.POA_NAME21);
        if (props.stop_id) selectedIds.add(props.stop_id);
        if (props.STOP_ID) selectedIds.add(props.STOP_ID);
        if (props.stop_name) selectedIds.add(props.stop_name);
        if (props.STOP_NAME) selectedIds.add(props.STOP_NAME);
    });

    // Update layers with selection highlighting
    const updatedLayers = layers.map(layer => {
        // For now, we'll rely on visual feedback from the selection panel
        // Future enhancement: add visual highlighting on the map
        return layer;
    });

    window.deckgl.setProps({ layers: updatedLayers });
}

// Handle close button for selection panel
document.addEventListener('DOMContentLoaded', function() {
    const closeBtn = document.getElementById('close-selection-panel');
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            clearAllSelections();
        });
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

// Function to attach location event listeners
function attachLocationEventListeners() {
    const getLocationBtn = document.getElementById('get-location-btn');
    const centerLocationBtn = document.getElementById('center-location-btn');

    if (getLocationBtn) {
        getLocationBtn.addEventListener('click', handleGetLocation);
    }

    if (centerLocationBtn) {
        centerLocationBtn.addEventListener('click', handleCenterLocation);
    }
}

// Handle location button click
function handleGetLocation() {
    const button = document.getElementById('get-location-btn');

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
}

// Handle center on location button click
function handleCenterLocation() {
    if (userLocationCoords) {
        centerOnUserLocation();
        showLocationStatus('Centered on your location', false);
    }
}

// Layer management functionality
const layerVisibility = {};
const layerDisplayNames = {
    'commute-tier-hulls-train': 'Train Commute Zones',
    'commute-tier-hulls-tram': 'Tram Commute Zones',
    'isochrones-5min': '5-minute Walking',
    'isochrones-15min': '15-minute Walking',
    'postcodes-with-trams-trains': 'Serviced Postcodes',
    'ptv-lines-tram': 'Tram Lines',
    'ptv-lines-train': 'Train Lines',
    'ptv-stops-tram': 'Tram Stops',
    'ptv-stops-train': 'Train Stops',
    'real-estate-candidates': 'Property Candidates'
};

// Function to populate layer toggles
function populateLayerToggles() {
    const layersSection = document.getElementById('layers-section');
    if (!layersSection || !window.deckgl) return;

    // Clear existing content
    layersSection.innerHTML = '';

    // Get all layers except user location
    const layers = window.deckgl.props.layers || [];
    const layersToShow = layers.filter(l => l.id !== 'user-location');

    // Create toggle for each layer
    layersToShow.forEach(layer => {
        // Initialize visibility state if not set
        if (layerVisibility[layer.id] === undefined) {
            layerVisibility[layer.id] = layer.props.visible !== false;
        }

        const layerItem = document.createElement('div');
        layerItem.className = 'layer-item';

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.id = `layer-toggle-${layer.id}`;
        checkbox.checked = layerVisibility[layer.id];

        const label = document.createElement('label');
        label.htmlFor = `layer-toggle-${layer.id}`;
        label.textContent = layerDisplayNames[layer.id] || layer.id;

        // Add event listener to toggle layer visibility
        checkbox.addEventListener('change', function() {
            toggleLayerVisibility(layer.id, checkbox.checked);
        });

        layerItem.appendChild(checkbox);
        layerItem.appendChild(label);
        layersSection.appendChild(layerItem);
    });

    // Create and append location control section
    const locationControl = document.createElement('div');
    locationControl.id = 'location-control';
    locationControl.style.cssText = 'margin-top: 12px; padding-top: 12px; border-top: 1px solid #e0e0e0;';

    // Create "Show My Location" button
    const getLocationBtn = document.createElement('button');
    getLocationBtn.id = 'get-location-btn';
    getLocationBtn.style.cssText = `
        padding: 10px 16px;
        background: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        display: flex;
        align-items: center;
        gap: 8px;
        width: 100%;
        justify-content: center;
    `;
    getLocationBtn.innerHTML = '<span style="font-size: 16px;">📍</span><span>Show My Location</span>';

    // Create "Center on Location" button
    const centerLocationBtn = document.createElement('button');
    centerLocationBtn.id = 'center-location-btn';
    centerLocationBtn.style.cssText = `
        margin-top: 8px;
        padding: 10px 16px;
        background: #f5f5f5;
        border: 1px solid #ddd;
        border-radius: 4px;
        cursor: pointer;
        font-size: 14px;
        display: none;
        align-items: center;
        gap: 8px;
        width: 100%;
        justify-content: center;
    `;
    centerLocationBtn.innerHTML = '<span style="font-size: 16px;">🎯</span><span>Center on Location</span>';

    // Create location status div
    const locationStatus = document.createElement('div');
    locationStatus.id = 'location-status';
    locationStatus.style.cssText = `
        margin-top: 8px;
        padding: 8px 12px;
        background: #f9f9f9;
        border-radius: 4px;
        border: 1px solid #e0e0e0;
        font-size: 12px;
        display: none;
    `;

    // Append elements to location control
    locationControl.appendChild(getLocationBtn);
    locationControl.appendChild(centerLocationBtn);
    locationControl.appendChild(locationStatus);

    // Append location control to layers section
    layersSection.appendChild(locationControl);

    // Re-attach event listeners for location buttons
    attachLocationEventListeners();
}

// Function to toggle layer visibility
function toggleLayerVisibility(layerId, visible) {
    layerVisibility[layerId] = visible;

    // Get current layers
    const layers = window.deckgl.props.layers || [];

    // Update the specific layer's visibility
    const updatedLayers = layers.map(layer => {
        if (layer.id === layerId) {
            // Instead of recreating the layer, just update its visibility property
            // This preserves all the original data and properties
            layer.props.visible = visible;
            // Force a re-render by creating a shallow clone
            return layer.clone({
                visible: visible
            });
        }
        return layer;
    });

    // Update deck with modified layers
    window.deckgl.setProps({ layers: updatedLayers });
}

// Handle expand/collapse of layers section
const infoHeader = document.getElementById('info-header');
const layersSection = document.getElementById('layers-section');
const expandIcon = document.getElementById('expand-icon');

if (infoHeader && layersSection && expandIcon) {
    infoHeader.addEventListener('click', function() {
        layersSection.classList.toggle('expanded');
        expandIcon.classList.toggle('expanded');

        // Populate layer toggles when first expanded
        if (layersSection.classList.contains('expanded')) {
            populateLayerToggles();
        }
    });
}

// Attach location event listeners initially
attachLocationEventListeners();

// Update layer toggles when layers change
const originalSetProps = window.deckgl.setProps.bind(window.deckgl);
window.deckgl.setProps = function(props) {
    const result = originalSetProps(props);

    // If layers changed and the section is expanded, update toggles
    if (props.layers && layersSection && layersSection.classList.contains('expanded')) {
        setTimeout(populateLayerToggles, 100); // Small delay to ensure layers are updated
    }

    return result;
};