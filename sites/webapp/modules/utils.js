// utils.js - Pure utility functions
// Extracted from scripts.js to demonstrate modular architecture

// Application Constants (extracted from main file)
export const COMMUTE_TIME_MIN = 100;
export const COMMUTE_TIME_RANGE = 300;

export const COLORS = {
    USER_LOCATION: [255, 0, 0, 255],
    USER_LOCATION_OUTLINE: [255, 255, 255, 255],
    DEFAULT_FILL: [255, 255, 255, 255]
};

export const MAX_SELECTIONS_BY_TYPE = {
    'real-estate-candidates': 2,
    'postcodes': 2,
    'lga': 2,
    'sa2': 2,
    'ptv-stops-tram': 1,
    'ptv-stops-train': 1
};

export const GEOLOCATION_CONFIG = {
    enableHighAccuracy: true,
    timeout: 10000,
    maximumAge: 0
};

// Function to convert hex color codes to RGBA arrays
export function hexToRgbA(hex) {
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

// Function to resolve color references in configuration
export function resolveColorReference(value, colors) {
    if (typeof value === 'string') {
        if (value.startsWith('color:')) {
            const colorKey = value.substring(6);
            return colors[colorKey] || COLORS.DEFAULT_FILL;
        }
    }
    return value;
}

// Color scale for commute time hulls (gradient based on transit time)
export const getCommuteFillColor = (minutes) => {
    // Create gradient from green (short) to red (long) based on minutes
    const normalized = Math.min(Math.max((minutes - COMMUTE_TIME_MIN) / COMMUTE_TIME_RANGE, 0), 1); // Normalize 100-400 min to 0-1
    const r = Math.floor(255 * normalized);
    const g = Math.floor(255 * (1 - normalized));
    const b = 50;
    return [r, g, b, 30]; // Low opacity for overlay effect
};

// Layer display names mapping
export const LAYER_DISPLAY_NAMES = {
    'commute-tier-hulls-train': 'Train Commute Zones',
    'commute-tier-hulls-tram': 'Tram Commute Zones',
    'isochrones-5min': '5-minute Walking',
    'isochrones-15min': '15-minute Walking',
    'lga-boundaries': 'LGA Boundaries',
    'suburbs-sa2': 'SA2 Boundaries',
    'postcodes-with-trams-trains': 'Serviced Postcodes',
    'ptv-lines-tram': 'Tram Lines',
    'ptv-lines-train': 'Train Lines',
    'ptv-stops-tram': 'Tram Stops',
    'ptv-stops-train': 'Train Stops',
    'real-estate-candidates': 'Property Candidates'
};

// Type labels for different selection types
export const TYPE_LABELS = {
    'real-estate-candidates': 'Real Estate Property',
    'postcodes': 'Postcode',
    'lga': 'Local Government Area',
    'sa2': 'Statistical Area 2',
    'ptv-stops-tram': 'Tram Stop',
    'ptv-stops-train': 'Train Station'
};

// Chart color functions for different series
export function getSeriesColor(seriesKey) {
    // All Properties gets prominent blue
    if (seriesKey === 'All Properties') return '#1976D2';

    // House series use green tones
    if (seriesKey.includes('House')) {
        if (seriesKey.includes('1br')) return '#A5D6A7';
        if (seriesKey.includes('2br')) return '#81C784';
        if (seriesKey.includes('3br')) return '#4CAF50';
        if (seriesKey.includes('4br')) return '#388E3C';
        if (seriesKey.includes('5br')) return '#2E7D32';
        return '#4CAF50'; // default green
    }

    // Unit series use orange tones
    if (seriesKey.includes('Unit')) {
        if (seriesKey.includes('1br')) return '#FFCC80';
        if (seriesKey.includes('2br')) return '#FFB74D';
        if (seriesKey.includes('3br')) return '#FF9800';
        if (seriesKey.includes('4br')) return '#F57C00';
        if (seriesKey.includes('5br')) return '#E65100';
        return '#FF9800'; // default orange
    }

    // Fallback
    return '#666666';
}

export function getSeriesWidth(seriesKey) {
    return seriesKey === 'All Properties' ? 3 : 2;
}

export function getMarkerSize(seriesKey) {
    return seriesKey === 'All Properties' ? 6 : 4;
}

// Helper function to show status messages
export function showLocationStatus(message, isError = false) {
    const statusElement = document.getElementById('location-status');
    if (statusElement) {
        statusElement.style.display = 'block';
        statusElement.textContent = message;
        statusElement.style.color = isError ? '#d32f2f' : '#2e7d32';

        // Hide status after 5 seconds
        setTimeout(() => {
            statusElement.style.display = 'none';
        }, 5000);
    }
}

// Utility function for safe number conversion (handles BigInt)
export function safeNumber(value) {
    if (typeof value === 'bigint') {
        return Number(value);
    }
    return value;
}