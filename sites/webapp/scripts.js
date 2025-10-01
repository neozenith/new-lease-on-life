// Destructure deck.gl components
const { DeckGL, GeoJsonLayer, ScatterplotLayer } = deck;

// Load layer configuration
let layerConfig = null;
let colors = {};

// Application Constants
const COMMUTE_TIME_MIN = 100;
const COMMUTE_TIME_RANGE = 300;

const COLORS = {
  USER_LOCATION: [255, 0, 0, 255],
  USER_LOCATION_OUTLINE: [255, 255, 255, 255],
  DEFAULT_FILL: [255, 255, 255, 255],
};

const MAX_SELECTIONS_BY_TYPE = {
  "real-estate-candidates": 2,
  postcodes: 2,
  lga: 2,
  sal: 2,
  "ptv-stops-tram": 1,
  "ptv-stops-train": 1,
};

const GEOLOCATION_CONFIG = {
  enableHighAccuracy: true,
  timeout: 10000,
  maximumAge: 0,
};

// Helper function to update DuckDB status indicator
function updateDuckDBStatus(status, message) {
  const statusIcon = document.getElementById('duckdb-status-icon');
  const statusText = document.getElementById('duckdb-status-text');

  if (!statusIcon || !statusText) return;

  const statusStyles = {
    loading: { color: '#ffa500', text: message || 'Loading...' },
    error: { color: '#ff4444', text: message || 'Error loading database' },
    success: { color: '#00c864', text: message || 'Database connected' }
  };

  const style = statusStyles[status] || statusStyles.loading;
  statusIcon.style.background = style.color;
  statusText.textContent = style.text;
}

// Initialize DuckDB WASM
async function initializeDuckDB() {
  console.log("Initializing DuckDB WASM...");
  updateDuckDBStatus('loading', 'Loading DuckDB library...');

  // Wait for duckdb module to be available
  let retries = 20;
  while (retries > 0 && typeof window.duckdb === "undefined") {
    await new Promise((resolve) => setTimeout(resolve, 100));
    retries--;
  }

  if (typeof window.duckdb === "undefined") {
    updateDuckDBStatus('error', 'Failed to load DuckDB library');
    throw new Error("DuckDB WASM module not loaded. Make sure the ES module import completed.");
  }

  const duckdb = window.duckdb;
  console.log("DuckDB module loaded");
  updateDuckDBStatus('loading', 'Initializing database...');

  // Create worker and database instance using createWorker helper
  const logger = new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING);
  const bundles = duckdb.getJsDelivrBundles();
  const bundle = bundles.mvp;
  const worker = await duckdb.createWorker(bundle.mainWorker);
  const db = new duckdb.AsyncDuckDB(logger, worker);
  await db.instantiate(bundle.mainModule);
  const connection = await db.connect();

  console.log("DuckDB initialized successfully");
  updateDuckDBStatus('loading', 'Loading rental database...');

  // Load the rental sales database
  console.log("Loading rental sales database...");
  const response = await fetch("./data/rental_sales.duckdb");
  if (!response.ok) {
    updateDuckDBStatus('error', 'Failed to fetch database file');
    throw new Error(`Failed to fetch rental_sales.duckdb: ${response.status} ${response.statusText}`);
  }

  updateDuckDBStatus('loading', 'Connecting to database...');
  const dbBuffer = await response.arrayBuffer();
  await db.registerFileBuffer("rental_sales.duckdb", new Uint8Array(dbBuffer));
  await connection.query("ATTACH 'rental_sales.duckdb' AS rental_sales;");

  // Test the connection
  updateDuckDBStatus('loading', 'Verifying connection...');
  const testResult = await connection.query("SELECT COUNT(*) as total_records FROM rental_sales.rental_sales;");
  const recordCount = testResult.toArray()[0].total_records;
  console.log(`Successfully connected to rental sales database with ${recordCount} records`);

  // Make globally available
  window.duckdbConnection = connection;
  window.duckdbDatabase = db;

  // Update status to success with record count
  updateDuckDBStatus('success', `Connected (${recordCount.toLocaleString()} records)`);

  // Dispatch event to signal DuckDB is ready
  window.dispatchEvent(
    new CustomEvent("duckdbReady", {
      detail: { connection, database: db, recordCount },
    }),
  );

  return { connection, database: db };
}

// Initialize DuckDB when page loads
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => {
    initializeDuckDB().catch((error) => {
      console.error("Failed to initialize DuckDB:", error);
      updateDuckDBStatus('error', 'Database connection failed');
    });
  });
} else {
  initializeDuckDB().catch((error) => {
    console.error("Failed to initialize DuckDB:", error);
    updateDuckDBStatus('error', 'Database connection failed');
  });
}

// function for string hexcode rgb to array
function hexToRgbA(hex) {
  if (hex.startsWith("#")) {
    // Handle #rgb #rrggbb and #rrggbbaa formats
    let r,
      g,
      b,
      a = 255; // Default is solid white
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
function resolveColorReference(value, colors) {
  if (typeof value === "string") {
    if (value.startsWith("color:")) {
      const colorKey = value.substring(6);
      return colors[colorKey] || COLORS.DEFAULT_FILL;
    }
  }
  return value;
}

// Function to create layers from config
function createLayersFromConfig(config) {
  if (!config || !config.layers) return [];

  colors = config.colors || {};

  return config.layers.map((layerConfig) => {
    // Resolve color references
    const processedConfig = { ...layerConfig };
    const layerType = layerConfig.type || "GeoJsonLayer";

    // Handle different layer types
    if (layerType === "GeoJsonLayer" && processedConfig.id === "real-estate-candidates") {
      // Special handling for real estate candidates layer
      if (typeof processedConfig.data === "string" && processedConfig.data.endsWith(".geojson")) {
        // Load GeoJSON and convert to points array
        fetch(processedConfig.data)
          .then((response) => response.json())
          .then((geojson) => {
            const expanded_features = geojson.features.map((feature) => ({
              ...feature.properties,
              coordinates: feature.geometry.coordinates,
              geometry: feature.geometry,
            }));
            // Update the layer with processed data
            const updatedConfig = { ...processedConfig };
            updatedConfig.data = expanded_features; // Set the results of loading the datafile to the processed features

            // Handle color extraction from property
            if (updatedConfig.getFillColor === "ptv_walkability_colour") {
              updatedConfig.getFillColor = (d) => {
                // Sets this property to a function that extracts color from each data point
                const hex = d.ptv_walkability_colour;
                return hexToRgbA(hex) || COLORS.DEFAULT_FILL;
              };
            }

            // Create new GeoJsonLayer with updated data
            const newLayer = new GeoJsonLayer(updatedConfig);
            // Update the deck with the new layer
            const currentLayers = window.deckgl.props.layers || [];
            const filteredLayers = currentLayers.filter((l) => l.id !== updatedConfig.id);
            window.deckgl.setProps({ layers: [...filteredLayers, newLayer] });
          });

        // Return placeholder layer while loading
        return new GeoJsonLayer({
          ...processedConfig,
          data: [],
        });
      }
    }

    // Standard color resolution for other properties
    ["getFillColor", "getLineColor", "highlightColor"].forEach((prop) => {
      if (processedConfig[prop]) {
        processedConfig[prop] = resolveColorReference(processedConfig[prop], colors);
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
  const normalized = Math.min(Math.max((minutes - COMMUTE_TIME_MIN) / COMMUTE_TIME_RANGE, 0), 1); // Normalize 100-400 min to 0-1
  const r = Math.floor(255 * normalized);
  const g = Math.floor(255 * (1 - normalized));
  const b = 50;
  return [r, g, b, 30]; // Low opacity for overlay effect
};

// Initialize deck.gl with empty layers initially
// Make deckgl globally accessible for the GPS location feature
window.deckgl = new DeckGL({
  container: "container",

  // Set initial view to Victoria, Australia
  initialViewState: {
    longitude: 144.9631, // Melbourne coordinates
    latitude: -37.8136,
    zoom: 9,
    pitch: 0,
    bearing: 0,
  },

  // Enable map controls
  controller: true,

  // Use CartoDB dark basemap
  mapStyle: "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",

  // Initial empty layers - will be populated after loading config
  layers: [],

  // Tooltip configuration
  getTooltip: ({ object }) => {
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
        html += `${features.join(" · ")}<br/>`;
      }

      // Show walkability
      if (props.ptv_walkable_5min !== undefined) {
        html += `5-min walkable: ${props.ptv_walkable_5min ? "Yes" : "No"}<br/>`;
      }
      if (props.ptv_walkable_15min !== undefined) {
        html += `15-min walkable: ${props.ptv_walkable_15min ? "Yes" : "No"}<br/>`;
      }
    }
    // Check if this is a commute tier hull
    else if (props.MODE && props.transit_time_minutes_nearest_tier) {
      html += `<strong>${props.MODE}</strong><br/>`;
      html += `Transit time: ${Math.round(props.transit_time_minutes_nearest_tier)} minutes<br/>`;
      html += `Stations included: ${props.point_count || props.STOP_NAME || "N/A"}<br/>`;
    } else if (props.POA_NAME21 && props.suburbs) {
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
    // Check if this is an SAL boundary
    else if (props.SAL_NAME21) {
      html += `<strong>SAL: ${props.SAL_NAME21}</strong><br/>`;
      if (props.STE_NAME21) {
        html += `State: ${props.STE_NAME21}<br/>`;
      }
      if (props.AREASQKM21) {
        html += `Area: ${Number(props.AREASQKM21).toFixed(1)} km²<br/>`;
      }
      if (props.SAL_CODE21) {
        html += `SAL Code: ${props.SAL_CODE21}<br/>`;
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
      const timeLimit = props.time_limit || (object.source?.id === "isochrones-5min" ? 5 : 15);
      html += `<strong>${timeLimit}-minute isochrone</strong><br/>`;
      html += `Area reachable within ${timeLimit} minutes`;
    }

    html += "</div>";

    return { html };
  },

  // Handle hover events - tooltip display is handled by getTooltip
  onHover: () => {
    // Hover handling is managed by deck.gl internally
  },

  // Handle click events for selection
  onClick: ({ object, layer }) => {
    if (!object) {
      // Clicked on empty space - clear all selections
      clearAllSelections();
      return;
    }

    handleItemClick(object, layer);
  },
});

// Selection Management System
const selectedItems = new Map(); // Map to store selected items by type
const maxSelectionsByType = MAX_SELECTIONS_BY_TYPE;

// Get item type from layer ID
function getItemType(layer) {
  const layerId = layer.id;

  // Check for real estate candidates
  if (layerId === "real-estate-candidates") {
    return "real-estate-candidates";
  }

  // Check for LGA boundaries
  if (layerId === "lga-boundaries") {
    return "lga";
  }

  // Check for SAL boundaries
  if (layerId === "suburbs-sal") {
    return "sal";
  }

  // Check for postcodes (matching the actual layer ID from config)
  if (
    layerId === "postcodes-with-trams-trains" ||
    layerId === "selected_postcodes" ||
    layerId === "unioned_postcodes" ||
    layerId === "postcodes-selected" ||
    layerId === "postcodes-unioned"
  ) {
    return "postcodes";
  }

  // Check for tram stops
  if (layerId === "ptv-stops-tram") {
    return "ptv-stops-tram";
  }

  // Check for train stops
  if (layerId === "ptv-stops-train") {
    return "ptv-stops-train";
  }

  return null; // Not a selectable type
}

// Generate unique ID for an item
function getItemId(object, layer) {
  const props = object.properties || object;
  const type = getItemType(layer);

  if (type === "real-estate-candidates" && props.address) {
    return `${type}-${props.address}`;
  } else if (type === "lga" && props.LGA_NAME24) {
    return `${type}-${props.LGA_NAME24}`;
  } else if (type === "sal" && props.SAL_NAME21) {
    return `${type}-${props.SAL_NAME21}`;
  } else if (type === "postcodes" && props.POA_NAME21) {
    return `${type}-${props.POA_NAME21}`;
  } else if ((type === "ptv-stops-tram" || type === "ptv-stops-train") && props.stop_name) {
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
  const currentTypeSelections = Array.from(selectedItems.values()).filter((item) => item.type === type);

  // Check if this exact item is already selected
  if (selectedItems.has(itemId)) {
    // Toggle off - remove this item
    selectedItems.delete(itemId);
  } else {
    // Check if clicking on a different type - clear all selections
    const hasOtherTypes = Array.from(selectedItems.values()).some((item) => item.type !== type);
    if (hasOtherTypes) {
      clearAllSelections();
    }

    // Check max selections for this type
    const maxForType = maxSelectionsByType[type] || 999;

    if (currentTypeSelections.length >= maxForType) {
      // Remove oldest selection of this type
      const oldestKey = Array.from(selectedItems.keys()).find((key) => selectedItems.get(key).type === type);
      if (oldestKey) {
        selectedItems.delete(oldestKey);
      }
    }

    // Add new selection
    selectedItems.set(itemId, {
      type: type,
      object: object,
      layer: layer,
      properties: object.properties || object,
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

// Function to query rental data from DuckDB for LGAs, SALs, or suburbs
async function queryRentalData(geospatialType, geospatialId, dataType = "rent") {
  if (!window.duckdbConnection) {
    throw new Error("DuckDB connection not available. Database must be initialized first.");
  }

  // Sanitize inputs to prevent SQL injection
  const validGeospatialTypes = ["LGA", "SAL", "SUBURB"];
  const validDataTypes = ["rental", "sales"];

  if (!validGeospatialTypes.includes(geospatialType)) {
    throw new Error(`Invalid geospatial type: ${geospatialType}`);
  }
  if (!validDataTypes.includes(dataType)) {
    throw new Error(`Invalid data type: ${dataType}`);
  }

  console.log(`Querying ${dataType} data for ${geospatialType}: ${geospatialId}`);

  // Build query based on geospatial type and query strategy
  let query;
  let result;
  let rows;

  if (geospatialType === "LGA") {
    // LGA matching with hyphen-delimited code support
    // The geospatial_codes column may contain multiple codes separated by hyphens
    query = `
            SELECT
                time_bucket,
                dwelling_type,
                bedrooms,
                statistic,
                value,
                EXTRACT(YEAR FROM time_bucket) as year,
                EXTRACT(QUARTER FROM time_bucket) as quarter
            FROM rental_sales.rental_sales
            WHERE geospatial_type = 'lga'
                AND list_contains(string_split(geospatial_codes, '-'), '${geospatialId}')
                AND data_type = '${dataType}'
                AND statistic = 'median'
                AND value IS NOT NULL
            ORDER BY time_bucket, dwelling_type, bedrooms;
        `;

    result = await window.duckdbConnection.query(query);
    rows = result.toArray();
    console.log(`Found ${rows.length} records for ${geospatialType} ${geospatialId}`);
  } else if (geospatialType === "SUBURB") {
    // SUBURB matching with hyphen-delimited code support
    // The geospatial_codes column may contain multiple codes separated by hyphens
    query = `
            SELECT
                time_bucket,
                dwelling_type,
                bedrooms,
                statistic,
                value,
                EXTRACT(YEAR FROM time_bucket) as year,
                EXTRACT(QUARTER FROM time_bucket) as quarter
            FROM rental_sales.rental_sales
            WHERE geospatial_type = 'suburb'
                AND list_contains(string_split(geospatial_codes, '-'), '${geospatialId}')
                AND data_type = '${dataType}'
                AND statistic = 'median'
                AND value IS NOT NULL
            ORDER BY time_bucket, dwelling_type, bedrooms;
        `;

    result = await window.duckdbConnection.query(query);
    rows = result.toArray();
    console.log(`Found ${rows.length} records for ${geospatialType} ${geospatialId}`);

    if (rows.length === 0) {
      // Return empty result structure instead of throwing error
      return {
        dates: [],
        series: {},
        metadata: {
          geospatialType: geospatialType,
          geospatialId: geospatialId,
          dataType: dataType,
          seriesKeys: [],
        },
      };
    }
  } else {
    throw new Error(`Unsupported geospatial type: ${geospatialType}`);
  }

  // Helper function to safely convert BigInt/number values
  const safeNumber = (value) => {
    if (typeof value === "bigint") {
      return Number(value);
    }
    return value;
  };

  // Get unique dwelling types, bedroom counts, and time periods
  // Get unique combinations that actually exist in the data
  const uniqueCombinations = new Set();
  rows.forEach((row) => {
    const dwellingType = row.dwelling_type;
    const bedrooms = row.bedrooms; // Keep as string

    // Capitalize first letter of dwelling type for consistency
    const formattedDwellingType = dwellingType.charAt(0).toUpperCase() + dwellingType.slice(1);

    // Create series key: "House-2", "Unit-3", etc.
    if (bedrooms === 'all') {
      uniqueCombinations.add(formattedDwellingType); // "House", "Unit"
    } else {
      uniqueCombinations.add(`${formattedDwellingType}-${bedrooms}`);
    }
  });

  // Create series keys from unique combinations
  const seriesKeys = [];

  // Add "All Properties" series (aggregated across all dwelling types and bedrooms)
  seriesKeys.push("All Properties");

  // Add all unique combinations found in the data
  seriesKeys.push(...Array.from(uniqueCombinations).sort());

  const uniqueDates = [
    ...new Set(
      rows.map((row) => {
        const year = safeNumber(row.year);
        const quarter = safeNumber(row.quarter);
        // Use YYYY-MM format for proper chronological sorting
        const monthByQuarter = { 1: "03", 2: "06", 3: "09", 4: "12" };
        const dateLabel = `${year}-${monthByQuarter[quarter]}`;
        return dateLabel;
      }),
    ),
  ].sort();

  // Transform DuckDB results into multi-series format
  const data = {
    dates: uniqueDates,
    series: {},
    metadata: {
      geospatialType,
      geospatialId,
      recordCount: rows.length,
      seriesKeys,
      yearRange:
        rows.length > 0
          ? {
              start: Math.min(...rows.map((row) => safeNumber(row.year))),
              end: Math.max(...rows.map((row) => safeNumber(row.year))),
            }
          : null,
    },
  };

  // Initialize series for each combination
  seriesKeys.forEach((seriesKey) => {
    data.series[seriesKey] = new Array(uniqueDates.length).fill(null);
  });

  // Create a map of date to index for efficient lookup
  const dateIndexMap = {};
  uniqueDates.forEach((date, index) => {
    dateIndexMap[date] = index;
  });

  // Fill in the data for each series
  // First pass: populate specific bedroom+dwelling combinations
  rows.forEach((row) => {
    const year = safeNumber(row.year);
    const quarter = safeNumber(row.quarter);
    const value = safeNumber(row.value);
    const dwellingType = row.dwelling_type;
    const bedrooms = row.bedrooms; // Already a string

    // Use YYYY-MM format for proper chronological sorting
    const monthByQuarter = { 1: "03", 2: "06", 3: "09", 4: "12" };
    const dateLabel = `${year}-${monthByQuarter[quarter]}`;

    const dateIndex = dateIndexMap[dateLabel];
    if (dateIndex !== undefined && value !== null && value !== undefined) {
      // Capitalize first letter of dwelling type for consistency
      const formattedDwellingType = dwellingType.charAt(0).toUpperCase() + dwellingType.slice(1);

      // Create series key: "House-2", "Unit-3", etc.
      let seriesKey;
      if (bedrooms === 'all') {
        seriesKey = formattedDwellingType; // "House", "Unit"
      } else {
        seriesKey = `${formattedDwellingType}-${bedrooms}`;
      }

      // Add to the appropriate series
      if (data.series[seriesKey]) {
        data.series[seriesKey][dateIndex] = Math.round(value);
      }
    }
  });

  // Second pass: Calculate "All Properties" aggregated values
  uniqueDates.forEach((date, dateIndex) => {
    const rowsForDate = rows.filter((row) => {
      const year = safeNumber(row.year);
      const quarter = safeNumber(row.quarter);
      const monthByQuarter = { 1: "03", 2: "06", 3: "09", 4: "12" };
      const rowDateLabel = `${year}-${monthByQuarter[quarter]}`;
      return rowDateLabel === date;
    });

    if (rowsForDate.length > 0) {
      // Calculate simple average across all dwelling types and bedrooms
      let totalValue = 0;
      let count = 0;

      rowsForDate.forEach((row) => {
        const value = safeNumber(row.value);

        if (value !== null && value !== undefined) {
          totalValue += value;
          count++;
        }
      });

      if (count > 0) {
        data.series["All Properties"][dateIndex] = Math.round(totalValue / count);
      }
    }
  });

  return data;
}

// Function to setup data toggle for rental vs sales
function setupDataToggle(toggleId, chartContainerId, geospatialType, geospatialId, displayName) {
  const rentalBtn = document.getElementById(`${toggleId}-rental`);
  const salesBtn = document.getElementById(`${toggleId}-sales`);

  if (!rentalBtn || !salesBtn) {
    console.warn(`Toggle buttons not found for ${toggleId}`);
    return;
  }

  // Toggle button click handlers
  const handleToggle = (activeBtn, inactiveBtn, dataType) => {
    // Update button styles
    activeBtn.style.background = "#1976D2";
    activeBtn.style.color = "white";
    activeBtn.classList.add("active");

    inactiveBtn.style.background = "#e0e0e0";
    inactiveBtn.style.color = "#666";
    inactiveBtn.classList.remove("active");

    // Reload chart with new data type
    createAreaChart(chartContainerId, geospatialType, geospatialId, dataType, displayName);
  };

  rentalBtn.addEventListener("click", () => {
    if (!rentalBtn.classList.contains("active")) {
      handleToggle(rentalBtn, salesBtn, "rental");
    }
  });

  salesBtn.addEventListener("click", () => {
    if (!salesBtn.classList.contains("active")) {
      handleToggle(salesBtn, rentalBtn, "sales");
    }
  });
}

// Helper function to determine geospatial type from selected item
function getGeospatialTypeFromSelection(item) {
  const type = item.type;
  const props = item.properties;

  if (type === "lga" && props.LGA_CODE24) {
    // LGA uses LGA_CODE24 for matching
    return {
      geospatialType: "LGA",
      geospatialId: props.LGA_CODE24,
      displayName: props.LGA_NAME24,
      queryType: "lga",
    };
  } else if (type === "sal" && props.SAL_CODE21) {
    // SAL uses SAL_CODE21 for matching
    return {
      geospatialType: "SUBURB",
      geospatialId: props.SAL_CODE21,
      displayName: props.SAL_NAME21,
      queryType: "sal",
      originalId: props.SAL_CODE21,
      originalName: props.SAL_NAME21,
    };
  }

  return null;
}

// Function to create a Plotly chart for any geospatial area (LGA, SAL, or postcode)
async function createAreaChart(containerId, geospatialType, geospatialId, chartType = "rental", displayName = null) {
  try {
    // Query data from DuckDB
    const data = await queryRentalData(geospatialType, geospatialId, chartType);

    // Use displayName if provided, otherwise fall back to geospatialId
    const areaName = displayName || geospatialId;

    if (!data || data.dates.length === 0 || !data.series || Object.keys(data.series).length === 0) {
      console.warn(`No data available for ${geospatialType} ${geospatialId}`);

      // Show placeholder message
      setTimeout(() => {
        const element = document.getElementById(containerId);
        if (element) {
          element.innerHTML = `
                        <div style="padding: 20px; text-align: center; color: #666; font-size: 12px;">
                            <p>📊 No ${chartType} data available</p>
                            <p style="font-size: 10px; margin-top: 8px;">for ${areaName}</p>
                        </div>
                    `;
        }
      }, 100);
      return;
    }

    // Determine the appropriate label and color
    const areaTypeLabel =
      geospatialType === "LGA"
        ? "LGA"
        : geospatialType === "SUBURB"
          ? "Suburb"
          : geospatialType;

    const chartTitle =
      chartType === "rental"
        ? `${areaName} - Rental Trends`
        : `${areaName} - Sales Trends`;

    const yAxisTitle = chartType === "rental" ? "Weekly Rent ($)" : "Sales Price ($)";

    // Define colors for bedroom+dwelling combinations
    const getSeriesColor = (seriesKey) => {
      // All Properties gets prominent blue
      if (seriesKey === "All Properties") return "#1976D2";

      // House series use green tones
      if (seriesKey.startsWith("House-")) {
        if (seriesKey.includes("-1")) return "#A5D6A7";
        if (seriesKey.includes("-2")) return "#81C784";
        if (seriesKey.includes("-3")) return "#4CAF50";
        if (seriesKey.includes("-4")) return "#388E3C";
        if (seriesKey.includes("-5")) return "#2E7D32";
        return "#4CAF50"; // default green
      }

      // Unit series use orange tones
      if (seriesKey.startsWith("Unit-")) {
        if (seriesKey.includes("-1")) return "#FFCC80";
        if (seriesKey.includes("-2")) return "#FFB74D";
        if (seriesKey.includes("-3")) return "#FF9800";
        if (seriesKey.includes("-4")) return "#F57C00";
        if (seriesKey.includes("-5")) return "#E65100";
        return "#FF9800"; // default orange
      }

      // Fallback
      return "#666666";
    };

    const getSeriesWidth = (seriesKey) => {
      return seriesKey === "All Properties" ? 3 : 2;
    };

    const getMarkerSize = (seriesKey) => {
      return seriesKey === "All Properties" ? 6 : 4;
    };

    // Create traces for each bedroom+dwelling combination
    const traces = [];
    Object.keys(data.series).forEach((seriesKey) => {
      const seriesData = data.series[seriesKey];

      // Filter out null values for cleaner display
      const filteredIndices = [];
      const filteredDates = [];
      const filteredValues = [];

      seriesData.forEach((value, index) => {
        if (value !== null && value !== undefined) {
          filteredIndices.push(index);
          filteredDates.push(data.dates[index]);
          filteredValues.push(value);
        }
      });

      if (filteredValues.length > 0) {
        const trace = {
          x: filteredDates,
          y: filteredValues,
          type: "scatter",
          mode: "lines+markers",
          name: seriesKey,
          line: {
            color: getSeriesColor(seriesKey),
            width: getSeriesWidth(seriesKey),
          },
          marker: { size: getMarkerSize(seriesKey) },
        };
        traces.push(trace);
      }
    });

    const layout = {
      title: {
        text: chartTitle,
        font: { size: 14, color: "#333" },
      },
      xaxis: {
        title: "Time Period",
        tickangle: -45,
        tickfont: { size: 10 },
      },
      yaxis: {
        title: yAxisTitle,
        tickfont: { size: 10 },
      },
      margin: { l: 60, r: 20, t: 40, b: 90 },
      height: 300, // Increased height to accommodate legend with more series
      paper_bgcolor: "rgba(0,0,0,0)",
      plot_bgcolor: "rgba(0,0,0,0)",
      font: { size: 10 },
      showlegend: traces.length > 1, // Show legend if multiple series
      legend: {
        orientation: "h",
        x: 0.5,
        xanchor: "center",
        y: -0.25,
        font: { size: 8 },
        // Wrap legend items to multiple rows if needed
        traceorder: "normal",
      },
    };

    const config = {
      displayModeBar: false,
      responsive: true,
    };

    // Use setTimeout to ensure the DOM element exists
    setTimeout(() => {
      const element = document.getElementById(containerId);
      if (element) {
        Plotly.newPlot(containerId, traces, layout, config)
          .then(() => {
            // Add metadata info if available
            if (data.metadata && data.metadata.recordCount) {
              const metaInfo = document.createElement("div");
              metaInfo.style.cssText = `
                                font-size: 10px;
                                color: #888;
                                text-align: center;
                                margin-top: -8px;
                                padding: 4px;
                            `;

              const fallbackText = data.metadata.fallback ? " (fallback data)" : "";
              metaInfo.textContent = `${data.metadata.recordCount} records${fallbackText}`;

              element.appendChild(metaInfo);
            }
          })
          .catch((error) => {
            console.error("Error creating chart:", error);
            element.innerHTML = `<div style="color: red; font-size: 12px; padding: 20px; text-align: center;">Chart error: ${error.message}</div>`;
          });
      }
    }, 100);
  } catch (error) {
    console.error(`Error creating chart for ${geospatialType} ${geospatialId}:`, error);

    // Show error message
    setTimeout(() => {
      const element = document.getElementById(containerId);
      if (element) {
        element.innerHTML = `
                    <div style="padding: 20px; text-align: center; color: #d32f2f; font-size: 12px;">
                        <p>⚠️ Chart Error</p>
                        <p style="font-size: 10px; margin-top: 8px;">${error.message}</p>
                    </div>
                `;
      }
    }, 100);
  }
}

// Helper function to generate content for a single item
function generateItemContent(type, props, includeChart = false, chartContainerId = null, useSharedToggle = false) {
  let dataContent = "";
  let chartContent = "";

  const typeLabel =
    {
      "real-estate-candidates": "Real Estate Property",
      postcodes: "Postcode",
      lga: "Local Government Area",
      sal: "Suburbs and Localities (SAL)",
      "ptv-stops-tram": "Tram Stop",
      "ptv-stops-train": "Train Station",
    }[type] || type;

  dataContent += `<h4 style="margin: 0 0 8px 0; color: #333; font-size: 14px; font-weight: bold;">${typeLabel}</h4>`;

  if (type === "real-estate-candidates") {
    dataContent += `<strong>${props.address}</strong><br/>`;

    // Display rental details if available
    if (props.rent) {
      dataContent += `<strong style="color: #2E7D32;">$${props.rent}/week</strong><br/>`;
    }

    // Display property features if available
    const features = [];
    if (props.bedrooms) features.push(`${props.bedrooms} bed`);
    if (props.bathrooms) features.push(`${props.bathrooms} bath`);
    if (props.parking) features.push(`${props.parking} car`);
    if (features.length > 0) {
      dataContent += `${features.join(" · ")}<br/>`;
    }

    // Display walkability
    if (props.ptv_walkable_5min !== undefined) {
      dataContent += `5-min walkable: ${props.ptv_walkable_5min ? "Yes ✓" : "No ✗"}<br/>`;
    }
    if (props.ptv_walkable_15min !== undefined) {
      dataContent += `15-min walkable: ${props.ptv_walkable_15min ? "Yes ✓" : "No ✗"}<br/>`;
    }

    // Add link if available
    if (props.link) {
      dataContent += `<a href="${props.link}" target="_blank" style="color: #1976D2; text-decoration: none; font-size: 12px;">View on realestate.com.au →</a><br/>`;
    }
  } else if (type === "postcodes") {
    dataContent += `<strong>Postcode: ${props.POA_NAME21}</strong><br/>`;
    if (props.suburbs) {
      dataContent += `Suburbs: ${props.suburbs}<br/>`;
    }

    // Create chart content separately
    if (includeChart && chartContainerId) {
      chartContent = `<div id="${chartContainerId}" style="height: 100%; width: 100%;"></div>`;
      // Create the chart after the DOM is updated
      setTimeout(() => createAreaChart(chartContainerId, "SUBURB", props.POA_NAME21, "rent"), 200);
    }
  } else if (type === "lga") {
    dataContent += `<strong>LGA: ${props.LGA_NAME24}</strong><br/>`;
    if (props.STE_NAME21) {
      dataContent += `State: ${props.STE_NAME21}<br/>`;
    }
    if (props.AREASQKM) {
      dataContent += `Area: ${Number(props.AREASQKM).toFixed(1)} km²<br/>`;
    }
    if (props.LGA_CODE24) {
      dataContent += `Code: ${props.LGA_CODE24}<br/>`;
    }

    // Create chart content separately with data type toggle
    if (includeChart && chartContainerId) {
      if (useSharedToggle) {
        // When using shared toggle, just show the chart without individual toggle
        chartContent = `<div id="${chartContainerId}" class="shared-chart" style="height: 100%; width: 100%;" data-geo-type="LGA" data-geo-id="${props.LGA_CODE24}" data-display-name="${props.LGA_NAME24}"></div>`;
        // Create the chart after the DOM is updated
        setTimeout(() => {
          createAreaChart(chartContainerId, "LGA", props.LGA_CODE24, "rental", props.LGA_NAME24);
        }, 200);
      } else {
        // Individual toggle for single-item view
        const toggleId = `toggle-${chartContainerId}`;
        chartContent = `
          <div style="display: flex; flex-direction: column; height: 100%; gap: 8px;">
            <div style="display: flex; justify-content: center; align-items: center; gap: 8px; padding: 8px; background: #f5f5f5; border-radius: 4px;">
              <button id="${toggleId}-rental" class="data-toggle-btn active" data-chart-id="${chartContainerId}" data-type="rental" style="flex: 1; padding: 6px 12px; background: #1976D2; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 12px;">
                Rental
              </button>
              <button id="${toggleId}-sales" class="data-toggle-btn" data-chart-id="${chartContainerId}" data-type="sales" style="flex: 1; padding: 6px 12px; background: #e0e0e0; color: #666; border: none; border-radius: 3px; cursor: pointer; font-size: 12px;">
                Sales
              </button>
            </div>
            <div id="${chartContainerId}" style="flex: 1; min-height: 0;"></div>
          </div>
        `;
        // Create the chart after the DOM is updated
        setTimeout(() => {
          createAreaChart(chartContainerId, "LGA", props.LGA_CODE24, "rental", props.LGA_NAME24);
          setupDataToggle(toggleId, chartContainerId, "LGA", props.LGA_CODE24, props.LGA_NAME24);
        }, 200);
      }
    }
  } else if (type === "sal") {
    dataContent += `<strong>SAL: ${props.SAL_NAME21}</strong><br/>`;
    if (props.STE_NAME21) {
      dataContent += `State: ${props.STE_NAME21}<br/>`;
    }
    if (props.AREASQKM21) {
      dataContent += `Area: ${Number(props.AREASQKM21).toFixed(1)} km²<br/>`;
    }
    if (props.SAL_CODE21) {
      dataContent += `Code: ${props.SAL_CODE21}<br/>`;
    }
    if (props.SA3_NAME21) {
      dataContent += `SA3: ${props.SA3_NAME21}<br/>`;
    }
    if (props.SA4_NAME21) {
      dataContent += `SA4: ${props.SA4_NAME21}<br/>`;
    }

    // Create chart content separately with data type toggle
    if (includeChart && chartContainerId) {
      if (useSharedToggle) {
        // When using shared toggle, just show the chart without individual toggle
        chartContent = `<div id="${chartContainerId}" class="shared-chart" style="height: 100%; width: 100%;" data-geo-type="SUBURB" data-geo-id="${props.SAL_CODE21}" data-display-name="${props.SAL_NAME21}"></div>`;
        // Create the chart after the DOM is updated
        setTimeout(() => {
          createAreaChart(chartContainerId, "SUBURB", props.SAL_CODE21, "rental", props.SAL_NAME21);
        }, 200);
      } else {
        // Individual toggle for single-item view
        const toggleId = `toggle-${chartContainerId}`;
        chartContent = `
          <div style="display: flex; flex-direction: column; height: 100%; gap: 8px;">
            <div style="display: flex; justify-content: center; align-items: center; gap: 8px; padding: 8px; background: #f5f5f5; border-radius: 4px;">
              <button id="${toggleId}-rental" class="data-toggle-btn active" data-chart-id="${chartContainerId}" data-type="rental" style="flex: 1; padding: 6px 12px; background: #1976D2; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 12px;">
                Rental
              </button>
              <button id="${toggleId}-sales" class="data-toggle-btn" data-chart-id="${chartContainerId}" data-type="sales" style="flex: 1; padding: 6px 12px; background: #e0e0e0; color: #666; border: none; border-radius: 3px; cursor: pointer; font-size: 12px;">
                Sales
              </button>
            </div>
            <div id="${chartContainerId}" style="flex: 1; min-height: 0;"></div>
          </div>
        `;
        // Create the chart after the DOM is updated
        setTimeout(() => {
          createAreaChart(chartContainerId, "SUBURB", props.SAL_CODE21, "rental", props.SAL_NAME21);
          setupDataToggle(toggleId, chartContainerId, "SUBURB", props.SAL_CODE21, props.SAL_NAME21);
        }, 200);
      }
    }
  } else if (type === "ptv-stops-tram" || type === "ptv-stops-train") {
    dataContent += `<strong>${props.stop_name || props.STOP_NAME}</strong><br/>`;
    if (props.stop_id || props.STOP_ID) {
      dataContent += `Stop ID: ${props.stop_id || props.STOP_ID}<br/>`;
    }
    // Display transit time and distance metadata
    if (props.transit_time_minutes !== undefined) {
      dataContent += `Transit time to Southern Cross: ${props.transit_time_minutes.toFixed(1)} minutes<br/>`;
    }
    if (props.transit_distance_km !== undefined) {
      dataContent += `Transit distance: ${props.transit_distance_km.toFixed(2)} km<br/>`;
    }
    if (props.routes || props.ROUTES) {
      dataContent += `Routes: ${props.routes || props.ROUTES}<br/>`;
    }
  }

  // Return both data and chart content separately
  return { dataContent, chartContent };
}

// Update the selection panel display
function updateSelectionDisplay() {
  const panel = document.getElementById("selection-panel");
  const content = document.getElementById("selection-content");

  if (selectedItems.size === 0) {
    // Hide panel
    panel.style.height = "0";
    content.innerHTML = "";
    return;
  }

  // Show panel - take up bottom half of screen for better chart visibility
  panel.style.height = "50vh";

  // Build content HTML
  let html = "";
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
    // Check if both items support charts
    const bothHaveCharts = totalItems.every(item =>
      item.type === "postcodes" || item.type === "lga" || item.type === "sal"
    );

    // Add shared toggle at the top if both have charts
    if (bothHaveCharts) {
      html += `
        <div style="display: flex; justify-content: center; align-items: center; gap: 8px; padding: 8px; background: #f5f5f5; border-radius: 4px; margin-bottom: 12px;">
          <button id="shared-toggle-rental" class="shared-data-toggle-btn active" data-type="rental" style="flex: 1; padding: 8px 16px; background: #1976D2; color: white; border: none; border-radius: 3px; cursor: pointer; font-size: 13px; font-weight: 500;">
            Rental Data
          </button>
          <button id="shared-toggle-sales" class="shared-data-toggle-btn" data-type="sales" style="flex: 1; padding: 8px 16px; background: #e0e0e0; color: #666; border: none; border-radius: 3px; cursor: pointer; font-size: 13px; font-weight: 500;">
            Sales Data
          </button>
        </div>
      `;
    }

    html += `<div style="display: flex; gap: 16px; height: ${bothHaveCharts ? 'calc(100% - 52px)' : '100%'};">`;

    totalItems.forEach((item, index) => {
      const props = item.properties;
      const type = item.type;

      html += `<div style="flex: 1; padding: 12px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #007AFF; overflow: hidden;">`;

      // For postcodes, LGAs, and SALs, include charts when there are 1-2 selected
      const shouldIncludeChart =
        (type === "postcodes" || type === "lga" || type === "sal") &&
        (totalItems.length === 1 || totalItems.length === 2);
      let chartContainerId = null;
      if (shouldIncludeChart) {
        const identifier =
          type === "postcodes" ? props.POA_NAME21 : type === "sal" ? props.SAL_NAME21 : props.LGA_NAME24;
        chartContainerId = `chart-${type}-${identifier}-${index}`;
      }

      const { dataContent, chartContent } = generateItemContent(type, props, shouldIncludeChart, chartContainerId, bothHaveCharts);

      if (shouldIncludeChart && chartContent) {
        // Two column layout: 2/3 for chart, 1/3 for data
        html += `
                    <div style="display: flex; gap: 12px; height: 100%;">
                        <div style="flex: 2; min-width: 0;">
                            ${chartContent}
                        </div>
                        <div style="flex: 1; min-width: 0; overflow-y: auto;">
                            ${dataContent}
                        </div>
                    </div>
                `;
      } else {
        // Just data content without chart
        html += dataContent;
      }

      html += `</div>`;
    });

    html += `</div>`;
  } else if (
    totalItems.length === 1 &&
    (totalItems[0].type === "postcodes" || totalItems[0].type === "lga" || totalItems[0].type === "sal")
  ) {
    // Special case for single postcode, LGA, or SAL selection - show chart
    const item = totalItems[0];
    const props = item.properties;
    const type = item.type;

    html += `<div style="padding: 12px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #007AFF; overflow: hidden; height: 100%;">`;

    const identifier = type === "postcodes" ? props.POA_NAME21 : type === "sal" ? props.SAL_NAME21 : props.LGA_NAME24;
    const chartContainerId = `chart-${type}-${identifier}-single`;
    const { dataContent, chartContent } = generateItemContent(type, props, true, chartContainerId);

    // Two column layout: 2/3 for chart, 1/3 for data
    html += `
            <div style="display: flex; gap: 12px; height: 100%;">
                <div style="flex: 2; min-width: 0;">
                    ${chartContent}
                </div>
                <div style="flex: 1; min-width: 0; overflow-y: auto;">
                    ${dataContent}
                </div>
            </div>
        `;

    html += `</div>`;
  } else {
    // Original display logic for non-2 item cases
    itemsByType.forEach((items, type) => {
      const typeLabel =
        {
          "real-estate-candidates": "Real Estate Properties",
          postcodes: "Postcodes",
          lga: "Local Government Areas",
          sal: "Suburbs and Localities (SAL)",
          "ptv-stops-tram": "Tram Stops",
          "ptv-stops-train": "Train Stations",
        }[type] || type;

      html += `<div style="margin-bottom: 20px;">`;
      html += `<h4 style="margin: 0 0 12px 0; color: #333; font-size: 14px; font-weight: bold;">${typeLabel}</h4>`;

      items.forEach((item, _index) => {
        const props = item.properties;
        html += `<div style="margin-bottom: 12px; padding: 12px; background: #f9f9f9; border-radius: 4px; border-left: 3px solid #007AFF;">`;

        // Use the helper function to generate item content
        const { dataContent } = generateItemContent(type, props);
        html += dataContent;

        html += `</div>`;
      });

      html += `</div>`;
    });
  }

  content.innerHTML = html;

  // Setup shared toggle if it exists (for 2-item comparison)
  const sharedToggleRental = document.getElementById("shared-toggle-rental");
  const sharedToggleSales = document.getElementById("shared-toggle-sales");

  if (sharedToggleRental && sharedToggleSales) {
    const handleSharedToggle = (activeBtn, inactiveBtn, dataType) => {
      // Update button styles
      activeBtn.style.background = "#1976D2";
      activeBtn.style.color = "white";
      activeBtn.classList.add("active");

      inactiveBtn.style.background = "#e0e0e0";
      inactiveBtn.style.color = "#666";
      inactiveBtn.classList.remove("active");

      // Reload all charts with the new data type
      const sharedCharts = document.querySelectorAll(".shared-chart");
      sharedCharts.forEach(chartEl => {
        const geoType = chartEl.getAttribute("data-geo-type");
        const geoId = chartEl.getAttribute("data-geo-id");
        const displayName = chartEl.getAttribute("data-display-name");
        const chartId = chartEl.id;

        createAreaChart(chartId, geoType, geoId, dataType, displayName);
      });
    };

    sharedToggleRental.addEventListener("click", () => {
      if (!sharedToggleRental.classList.contains("active")) {
        handleSharedToggle(sharedToggleRental, sharedToggleSales, "rental");
      }
    });

    sharedToggleSales.addEventListener("click", () => {
      if (!sharedToggleSales.classList.contains("active")) {
        handleSharedToggle(sharedToggleSales, sharedToggleRental, "sales");
      }
    });
  }
}

// Update layer highlights to show selected items
function updateLayerHighlights() {
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
  const updatedLayers = layers.map((layer) => {
    // For now, we'll rely on visual feedback from the selection panel
    // Future enhancement: add visual highlighting on the map
    return layer;
  });

  window.deckgl.setProps({ layers: updatedLayers });
}

// Handle close button for selection panel
document.addEventListener("DOMContentLoaded", function () {
  const closeBtn = document.getElementById("close-selection-panel");
  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      clearAllSelections();
    });
  }
});

// Load the layer configuration and initialize layers
fetch("./layers_config.json")
  .then((response) => response.json())
  .then((config) => {
    layerConfig = config;
    const layers = createLayersFromConfig(config);
    window.deckgl.setProps({ layers });
    console.log("Layer configuration loaded successfully");
    console.log(`Loaded ${layers.length} layers from config`);
  })
  .catch((error) => {
    console.error("Error loading layer configuration:", error);
    // Fallback - could load default layers here if needed
  });

// Log when data is loaded
console.log("DeckGL transport analysis viewer initialized");
console.log("Loading layer configuration...");

// Handle loading errors
window.addEventListener("error", (e) => {
  console.error("Error loading data:", e);
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
    id: "user-location",
    data: [
      {
        position: [longitude, latitude],
        name: "Your Location",
      },
    ],
    getPosition: (d) => d.position,
    getRadius: 8,
    getFillColor: COLORS.USER_LOCATION, // Red color
    getLineColor: COLORS.USER_LOCATION_OUTLINE, // White outline
    lineWidthMinPixels: 2,
    pickable: true,
    radiusMinPixels: 6,
    radiusMaxPixels: 20,
    filled: true,
    stroked: true,
  });

  // Get current layers and filter out any existing user location layer
  const currentLayers = window.deckgl.props.layers || [];
  const filteredLayers = currentLayers.filter((l) => l.id !== "user-location");

  // Add the new location layer
  userLocationLayer = locationLayer;
  window.deckgl.setProps({
    layers: [...filteredLayers, locationLayer],
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
        transitionDuration: 1000,
      },
      controller: true,
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
        transitionDuration: 1000,
      },
      controller: true,
    });
  }
}

// Function to show status message
function showLocationStatus(message, isError = false) {
  const statusElement = document.getElementById("location-status");
  statusElement.style.display = "block";
  statusElement.textContent = message;
  statusElement.style.color = isError ? "#d32f2f" : "#2e7d32";

  // Hide status after 5 seconds
  setTimeout(() => {
    statusElement.style.display = "none";
  }, 5000);
}

// Function to attach location event listeners
function attachLocationEventListeners() {
  const getLocationBtn = document.getElementById("get-location-btn");
  const centerLocationBtn = document.getElementById("center-location-btn");

  if (getLocationBtn) {
    getLocationBtn.addEventListener("click", handleGetLocation);
  }

  if (centerLocationBtn) {
    centerLocationBtn.addEventListener("click", handleCenterLocation);
  }
}

// Handle location button click
function handleGetLocation() {
  const button = document.getElementById("get-location-btn");

  // Check if geolocation is available
  if (!navigator.geolocation) {
    showLocationStatus("Geolocation is not supported by your browser", true);
    return;
  }

  // Disable button and show loading state
  button.disabled = true;
  button.innerHTML = '<span style="font-size: 16px;">⏳</span><span>Getting Location...</span>';

  // Request current position
  navigator.geolocation.getCurrentPosition(
    // Success callback
    function (position) {
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
      const centerBtn = document.getElementById("center-location-btn");
      if (centerBtn) {
        centerBtn.style.display = "flex";
      }

      // Show success message
      showLocationStatus(`Location found: ${latitude.toFixed(4)}, ${longitude.toFixed(4)}`, false);

      console.log("User location:", { latitude, longitude });
    },

    // Error callback
    function (error) {
      button.disabled = false;
      button.innerHTML = '<span style="font-size: 16px;">📍</span><span>Show My Location</span>';

      let errorMessage = "Unable to get your location";
      switch (error.code) {
        case error.PERMISSION_DENIED:
          errorMessage = "Location access denied. Please enable location permissions.";
          break;
        case error.POSITION_UNAVAILABLE:
          errorMessage = "Location information unavailable.";
          break;
        case error.TIMEOUT:
          errorMessage = "Location request timed out.";
          break;
      }

      showLocationStatus(errorMessage, true);
      console.error("Geolocation error:", error);
    },

    // Options
    GEOLOCATION_CONFIG,
  );
}

// Handle center on location button click
function handleCenterLocation() {
  if (userLocationCoords) {
    centerOnUserLocation();
    showLocationStatus("Centered on your location", false);
  }
}

// Layer management functionality
const layerVisibility = {};
const layerDisplayNames = {
  "commute-tier-hulls-train": "Train Commute Zones",
  "commute-tier-hulls-tram": "Tram Commute Zones",
  "isochrones-5min": "5-minute Walking",
  "isochrones-15min": "15-minute Walking",
  "lga-boundaries": "LGA Boundaries",
  "suburbs-sal": "Suburbs and Localities (SAL)",
  "postcodes-with-trams-trains": "Serviced Postcodes",
  "ptv-lines-tram": "Tram Lines",
  "ptv-lines-train": "Train Lines",
  "ptv-stops-tram": "Tram Stops",
  "ptv-stops-train": "Train Stops",
  "real-estate-candidates": "Property Candidates",
};

// Function to populate layer toggles
function populateLayerToggles() {
  const layersSection = document.getElementById("layers-section");
  if (!layersSection || !window.deckgl) return;

  // Clear existing content
  layersSection.innerHTML = "";

  // Get all layers except user location
  const layers = window.deckgl.props.layers || [];
  const layersToShow = layers.filter((l) => l.id !== "user-location");

  // Create toggle for each layer
  layersToShow.forEach((layer) => {
    // Initialize visibility state if not set
    if (layerVisibility[layer.id] === undefined) {
      layerVisibility[layer.id] = layer.props.visible !== false;
    }

    const layerItem = document.createElement("div");
    layerItem.className = "layer-item";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.id = `layer-toggle-${layer.id}`;
    checkbox.checked = layerVisibility[layer.id];

    const label = document.createElement("label");
    label.htmlFor = `layer-toggle-${layer.id}`;
    label.textContent = layerDisplayNames[layer.id] || layer.id;

    // Add event listener to toggle layer visibility
    checkbox.addEventListener("change", function () {
      toggleLayerVisibility(layer.id, checkbox.checked);
    });

    layerItem.appendChild(checkbox);
    layerItem.appendChild(label);
    layersSection.appendChild(layerItem);
  });

  // Create and append location control section
  const locationControl = document.createElement("div");
  locationControl.id = "location-control";
  locationControl.style.cssText = "margin-top: 12px; padding-top: 12px; border-top: 1px solid #e0e0e0;";

  // Create "Show My Location" button
  const getLocationBtn = document.createElement("button");
  getLocationBtn.id = "get-location-btn";
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
  const centerLocationBtn = document.createElement("button");
  centerLocationBtn.id = "center-location-btn";
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
  const locationStatus = document.createElement("div");
  locationStatus.id = "location-status";
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
  const updatedLayers = layers.map((layer) => {
    if (layer.id === layerId) {
      // Instead of recreating the layer, just update its visibility property
      // This preserves all the original data and properties
      layer.props.visible = visible;
      // Force a re-render by creating a shallow clone
      return layer.clone({
        visible: visible,
      });
    }
    return layer;
  });

  // Update deck with modified layers
  window.deckgl.setProps({ layers: updatedLayers });
}

// Handle expand/collapse of layers section
const infoHeader = document.getElementById("info-header");
const layersSection = document.getElementById("layers-section");
const expandIcon = document.getElementById("expand-icon");

if (infoHeader && layersSection && expandIcon) {
  infoHeader.addEventListener("click", function () {
    layersSection.classList.toggle("expanded");
    expandIcon.classList.toggle("expanded");

    // Populate layer toggles when first expanded
    if (layersSection.classList.contains("expanded")) {
      populateLayerToggles();
    }
  });
}

// Attach location event listeners initially
attachLocationEventListeners();

// Update layer toggles when layers change
const originalSetProps = window.deckgl.setProps.bind(window.deckgl);
window.deckgl.setProps = function (props) {
  const result = originalSetProps(props);

  // If layers changed and the section is expanded, update toggles
  if (props.layers && layersSection && layersSection.classList.contains("expanded")) {
    setTimeout(populateLayerToggles, 100); // Small delay to ensure layers are updated
  }

  return result;
};
