// selection.js - Selection management system
// Extracted from scripts.js to demonstrate modular architecture

import { MAX_SELECTIONS_BY_TYPE, TYPE_LABELS } from './utils.js';

// Selection state
export const selectedItems = new Map(); // Map to store selected items by type
const maxSelectionsByType = MAX_SELECTIONS_BY_TYPE;

// Get item type from layer ID
export function getItemType(layer) {
    const layerId = layer.id;

    // Check for real estate candidates
    if (layerId === 'real-estate-candidates') {
        return 'real-estate-candidates';
    }

    // Check for LGA boundaries
    if (layerId === 'lga-boundaries') {
        return 'lga';
    }

    // Check for SA2 boundaries
    if (layerId === 'suburbs-sa2') {
        return 'sa2';
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
export function getItemId(object, layer) {
    const props = object.properties || object;
    const type = getItemType(layer);

    if (type === 'real-estate-candidates' && props.address) {
        return `${type}-${props.address}`;
    } else if (type === 'lga' && props.LGA_NAME24) {
        return `${type}-${props.LGA_NAME24}`;
    } else if (type === 'sa2' && props.SA2_NAME21) {
        return `${type}-${props.SA2_NAME21}`;
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
export function handleItemClick(object, layer) {
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
export function clearAllSelections() {
    selectedItems.clear();
    updateSelectionDisplay();
    updateLayerHighlights();
}

// Update the selection panel display
export function updateSelectionDisplay() {
    const panel = document.getElementById('selection-panel');
    const content = document.getElementById('selection-content');

    if (!panel || !content) return;

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
    selectedItems.forEach((item, _id) => {
        if (!itemsByType.has(item.type)) {
            itemsByType.set(item.type, []);
        }
        itemsByType.get(item.type).push(item);
    });

    // Check if we have exactly 2 items for side-by-side display
    const totalItems = Array.from(selectedItems.values());
    if (totalItems.length === 2) {
        html += `<div style="display: flex; gap: 16px; height: 100%;">`;

        totalItems.forEach((item, index) => {
            const props = item.properties;
            const type = item.type;

            html += `<div style="flex: 1; padding: 12px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #007AFF;">`;

            // For postcodes, LGAs, and SA2s, include charts when there are 1-2 selected
            const shouldIncludeChart = (type === 'postcodes' || type === 'lga' || type === 'sa2') && (totalItems.length === 1 || totalItems.length === 2);
            let chartContainerId = null;
            if (shouldIncludeChart) {
                const identifier = type === 'postcodes' ? props.POA_NAME21 :
                                  type === 'sa2' ? props.SA2_NAME21 : props.LGA_NAME24;
                chartContainerId = `chart-${type}-${identifier}-${index}`;
            }

            html += generateItemContent(type, props, shouldIncludeChart, chartContainerId);

            html += `</div>`;
        });

        html += `</div>`;
    } else if (totalItems.length === 1 && (totalItems[0].type === 'postcodes' || totalItems[0].type === 'lga' || totalItems[0].type === 'sa2')) {
        // Special case for single postcode, LGA, or SA2 selection - show chart
        const item = totalItems[0];
        const props = item.properties;
        const type = item.type;

        html += `<div style="padding: 12px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #007AFF;">`;

        const identifier = type === 'postcodes' ? props.POA_NAME21 :
                          type === 'sa2' ? props.SA2_NAME21 : props.LGA_NAME24;
        const chartContainerId = `chart-${type}-${identifier}-single`;
        html += generateItemContent(type, props, true, chartContainerId);

        html += `</div>`;
    } else {
        // Original display logic for non-2 item cases
        itemsByType.forEach((items, type) => {
            const typeLabel = TYPE_LABELS[type] || type;

            html += `<div style="margin-bottom: 20px;">`;
            html += `<h4 style="margin: 0 0 12px 0; color: #333; font-size: 14px; font-weight: bold;">${typeLabel}s</h4>`;

            items.forEach((item, _index) => {
                const props = item.properties;
                html += `<div style="margin-bottom: 12px; padding: 12px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #007AFF;">`;

                // Use the helper function to generate item content
                html += generateItemContent(type, props);

                html += `</div>`;
            });

            html += `</div>`;
        });
    }

    content.innerHTML = html;
}

// Helper function to generate content for a single item
export function generateItemContent(type, props, includeChart = false, chartContainerId = null) {
    let content = '';

    const typeLabel = TYPE_LABELS[type] || type;

    content += `<h4 style="margin: 0 0 8px 0; color: #333; font-size: 14px; font-weight: bold;">${typeLabel}</h4>`;

    if (type === 'real-estate-candidates') {
        content += `<strong>${props.address}</strong><br/>`;

        // Display rental details if available
        if (props.rent) {
            content += `<strong style="color: #2E7D32;">$${props.rent}/week</strong><br/>`;
        }

        // Display property features if available
        const features = [];
        if (props.bedrooms) features.push(`${props.bedrooms} bed`);
        if (props.bathrooms) features.push(`${props.bathrooms} bath`);
        if (props.parking) features.push(`${props.parking} car`);
        if (features.length > 0) {
            content += `${features.join(' · ')}<br/>`;
        }

        // Display walkability
        if (props.ptv_walkable_5min !== undefined) {
            content += `5-min walkable: ${props.ptv_walkable_5min ? 'Yes ✓' : 'No ✗'}<br/>`;
        }
        if (props.ptv_walkable_15min !== undefined) {
            content += `15-min walkable: ${props.ptv_walkable_15min ? 'Yes ✓' : 'No ✗'}<br/>`;
        }

        // Add link if available
        if (props.link) {
            content += `<a href="${props.link}" target="_blank" style="color: #1976D2; text-decoration: none; font-size: 12px;">View on realestate.com.au →</a><br/>`;
        }
    } else if (type === 'postcodes') {
        content += `<strong>Postcode: ${props.POA_NAME21}</strong><br/>`;
        if (props.suburbs) {
            content += `Suburbs: ${props.suburbs}<br/>`;
        }

        // Add chart for postcode if requested
        if (includeChart && chartContainerId) {
            content += `<div id="${chartContainerId}" style="margin-top: 12px; height: 250px; width: 100%;"></div>`;
            // Chart creation would be handled by the charts module
        }
    } else if (type === 'lga') {
        content += `<strong>LGA: ${props.LGA_NAME24}</strong><br/>`;
        if (props.STE_NAME21) {
            content += `State: ${props.STE_NAME21}<br/>`;
        }
        if (props.AREASQKM) {
            content += `Area: ${Number(props.AREASQKM).toFixed(1)} km²<br/>`;
        }
        if (props.LGA_CODE24) {
            content += `Code: ${props.LGA_CODE24}<br/>`;
        }

        // Add chart for LGA if requested
        if (includeChart && chartContainerId) {
            content += `<div id="${chartContainerId}" style="margin-top: 12px; height: 250px; width: 100%;"></div>`;
            // Chart creation would be handled by the charts module
        }
    } else if (type === 'sa2') {
        content += `<strong>SA2: ${props.SA2_NAME21}</strong><br/>`;
        if (props.STE_NAME21) {
            content += `State: ${props.STE_NAME21}<br/>`;
        }
        if (props.AREASQKM21) {
            content += `Area: ${Number(props.AREASQKM21).toFixed(1)} km²<br/>`;
        }
        if (props.SA2_CODE21) {
            content += `Code: ${props.SA2_CODE21}<br/>`;
        }
        if (props.SA3_NAME21) {
            content += `SA3: ${props.SA3_NAME21}<br/>`;
        }
        if (props.SA4_NAME21) {
            content += `SA4: ${props.SA4_NAME21}<br/>`;
        }

        // Add chart for SA2 if requested
        if (includeChart && chartContainerId) {
            content += `<div id="${chartContainerId}" style="margin-top: 12px; height: 250px; width: 100%;"></div>`;
            // Chart creation would be handled by the charts module
        }
    } else if (type === 'ptv-stops-tram' || type === 'ptv-stops-train') {
        content += `<strong>${props.stop_name || props.STOP_NAME}</strong><br/>`;
        if (props.stop_id || props.STOP_ID) {
            content += `Stop ID: ${props.stop_id || props.STOP_ID}<br/>`;
        }
        // Display transit time and distance metadata
        if (props.transit_time_minutes !== undefined) {
            content += `Transit time to Southern Cross: ${props.transit_time_minutes.toFixed(1)} minutes<br/>`;
        }
        if (props.transit_distance_km !== undefined) {
            content += `Transit distance: ${props.transit_distance_km.toFixed(2)} km<br/>`;
        }
        if (props.routes || props.ROUTES) {
            content += `Routes: ${props.routes || props.ROUTES}<br/>`;
        }
    }

    return content;
}

// Update layer highlights to show selected items
export function updateLayerHighlights() {
    // This would integrate with the main deck.gl instance
    // For now, this is a placeholder that would need to access window.deckgl

    if (typeof window !== 'undefined' && window.deckgl) {
        const layers = window.deckgl.props.layers || [];
        const selectedIds = new Set();

        // Collect IDs of selected items
        selectedItems.forEach((item, _id) => {
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
}