// database.js - DuckDB WASM integration and data querying
// Extracted from scripts.js to demonstrate modular architecture

// Initialize DuckDB WASM
export async function initializeDuckDB() {
    console.log('Initializing DuckDB WASM...');

    // Wait for duckdb module to be available
    let retries = 20;
    while (retries > 0 && typeof window.duckdb === 'undefined') {
        await new Promise(resolve => setTimeout(resolve, 100));
        retries--;
    }

    if (typeof window.duckdb === 'undefined') {
        throw new Error('DuckDB WASM module not loaded. Make sure the ES module import completed.');
    }

    const duckdb = window.duckdb;
    console.log('DuckDB module loaded');

    // Create worker and database instance using createWorker helper
    const logger = new duckdb.ConsoleLogger(duckdb.LogLevel.WARNING);
    const bundles = duckdb.getJsDelivrBundles();
    const bundle = bundles.mvp;
    const worker = await duckdb.createWorker(bundle.mainWorker);
    const db = new duckdb.AsyncDuckDB(logger, worker);
    await db.instantiate(bundle.mainModule);
    const connection = await db.connect();

    console.log('DuckDB initialized successfully');

    // Load the rental sales database
    console.log('Loading rental sales database...');
    const response = await fetch('./data/rental_sales.db');
    if (!response.ok) {
        throw new Error(`Failed to fetch rental_sales.db: ${response.status} ${response.statusText}`);
    }

    const dbBuffer = await response.arrayBuffer();
    await db.registerFileBuffer('rental_sales.db', new Uint8Array(dbBuffer));
    await connection.query('ATTACH \\'rental_sales.db\\' AS rental_sales;');

    // Test the connection
    const testResult = await connection.query('SELECT COUNT(*) as total_records FROM rental_sales.rental_sales;');
    const recordCount = testResult.toArray()[0].total_records;
    console.log(`Successfully connected to rental sales database with ${recordCount} records`);

    // Make globally available
    window.duckdbConnection = connection;
    window.duckdbDatabase = db;

    // Dispatch event to signal DuckDB is ready
    window.dispatchEvent(new CustomEvent('duckdbReady', {
        detail: { connection, database: db, recordCount }
    }));

    return { connection, database: db };
}

// Function to query rental data from DuckDB for LGAs, SA2s, or suburbs
export async function queryRentalData(geospatialType, geospatialId, dataType = 'rent') {
    if (!window.duckdbConnection) {
        throw new Error('DuckDB connection not available. Database must be initialized first.');
    }

    // Sanitize inputs to prevent SQL injection
    const validGeospatialTypes = ['LGA', 'SA2', 'SUBURB', 'SUBURB_BY_POSTCODE'];
    const validDataTypes = ['rent', 'sales'];

    if (!validGeospatialTypes.includes(geospatialType)) {
        throw new Error(`Invalid geospatial type: ${geospatialType}`);
    }
    if (!validDataTypes.includes(dataType)) {
        throw new Error(`Invalid data type: ${dataType}`);
    }

    console.log(`Querying ${dataType} data for ${geospatialType}: ${geospatialId}`);

    // Build query based on geospatial type and query strategy
    const query = buildQuerySQL(geospatialType, geospatialId, dataType);

    const result = await window.duckdbConnection.query(query);
    const rows = result.toArray();

    console.log(`Found ${rows.length} records for ${geospatialType} ${geospatialId}`);

    return processQueryResults(rows, geospatialType, geospatialId, dataType);
}

// Helper function to build SQL queries based on geospatial type
function buildQuerySQL(geospatialType, geospatialId, dataType) {
    const baseQuery = `
        SELECT
            time_bucket,
            time_bucket_type,
            AVG(value) as avg_value,
            year,
            quarter,
            dwelling_type,
            bedrooms,
            COUNT(*) as record_count
        FROM rental_sales.rental_sales
        WHERE value_type = '${dataType}'
            AND value IS NOT NULL`;

    let whereClause = '';

    if (geospatialType === 'LGA') {
        whereClause = `AND geospatial_type = 'LGA' AND geospatial_id = '${geospatialId}'`;
    } else if (geospatialType === 'SUBURB_BY_POSTCODE') {
        whereClause = `AND geospatial_type = 'SUBURB' AND postcode = '${geospatialId}'`;
    } else if (geospatialType === 'SUBURB') {
        whereClause = `AND geospatial_type = 'SUBURB' AND geospatial_id = '${geospatialId}'`;
    } else {
        throw new Error(`Unsupported geospatial type: ${geospatialType}`);
    }

    return `${baseQuery} ${whereClause}
        GROUP BY time_bucket, time_bucket_type, year, quarter, dwelling_type, bedrooms
        ORDER BY year, quarter, time_bucket;`;
}

// Helper function to process query results into chart-ready format
function processQueryResults(rows, geospatialType, geospatialId, dataType) {
    // Helper function to safely convert BigInt/number values
    const safeNumber = (value) => {
        if (typeof value === 'bigint') {
            return Number(value);
        }
        return value;
    };

    // Get unique dwelling types, bedroom counts, and time periods
    const dwellingTypes = [...new Set(rows.map(row => row.dwelling_type))];
    const bedroomCounts = [...new Set(rows.map(row => safeNumber(row.bedrooms)))].filter(b => b !== null && b !== undefined);

    // Create series combinations: dwelling_type + bedroom count
    const seriesKeys = ['All Properties']; // Add "All Properties" series first

    // Add specific series based on available data
    if (bedroomCounts.length > 0) {
        dwellingTypes.forEach(dwellingType => {
            bedroomCounts.forEach(bedrooms => {
                if (bedrooms && bedrooms > 0) {
                    seriesKeys.push(`${bedrooms}br-${dwellingType}`);
                }
            });
        });
    } else {
        dwellingTypes.forEach(dwellingType => {
            if (dwellingType !== 'All') {
                seriesKeys.push(dwellingType);
            }
        });
    }

    const uniqueDates = [...new Set(rows.map(row => {
        const year = safeNumber(row.year);
        const quarter = safeNumber(row.quarter);
        let dateLabel;

        if (row.time_bucket_type === 'quarterly') {
            const monthByQuarter = { 1: '03', 2: '06', 3: '09', 4: '12' };
            dateLabel = `${year}-${monthByQuarter[quarter]}`;
        } else if (row.time_bucket_type === 'annually') {
            dateLabel = `${year}`;
        } else {
            dateLabel = row.time_bucket;
        }
        return dateLabel;
    }))].sort();

    // Transform results into multi-series format
    const data = {
        dates: uniqueDates,
        series: {},
        metadata: {
            geospatialType,
            geospatialId,
            recordCount: rows.length,
            dwellingTypes,
            bedroomCounts,
            seriesKeys,
            yearRange: rows.length > 0 ? {
                start: Math.min(...rows.map(row => safeNumber(row.year))),
                end: Math.max(...rows.map(row => safeNumber(row.year)))
            } : null
        }
    };

    // Initialize series for each combination
    seriesKeys.forEach(seriesKey => {
        data.series[seriesKey] = new Array(uniqueDates.length).fill(null);
    });

    // Process the data to fill series arrays
    return fillSeriesData(data, rows, uniqueDates, bedroomCounts);
}

// Helper function to fill series data arrays
function fillSeriesData(data, rows, uniqueDates, bedroomCounts) {
    // Create a map of date to index for efficient lookup
    const dateIndexMap = {};
    uniqueDates.forEach((date, index) => {
        dateIndexMap[date] = index;
    });

    const safeNumber = (value) => {
        if (typeof value === 'bigint') {
            return Number(value);
        }
        return value;
    };

    // Fill in the data for each series
    rows.forEach(row => {
        const year = safeNumber(row.year);
        const quarter = safeNumber(row.quarter);
        const avgValue = safeNumber(row.avg_value);
        const dwellingType = row.dwelling_type;
        const bedrooms = safeNumber(row.bedrooms);

        let dateLabel;
        if (row.time_bucket_type === 'quarterly') {
            const monthByQuarter = { 1: '03', 2: '06', 3: '09', 4: '12' };
            dateLabel = `${year}-${monthByQuarter[quarter]}`;
        } else if (row.time_bucket_type === 'annually') {
            dateLabel = `${year}`;
        } else {
            dateLabel = row.time_bucket;
        }

        const dateIndex = dateIndexMap[dateLabel];
        if (dateIndex !== undefined && avgValue !== null && avgValue !== undefined) {
            if (bedroomCounts.length > 0) {
                if (bedrooms && bedrooms > 0) {
                    const specificSeriesKey = `${bedrooms}br-${dwellingType}`;
                    if (data.series[specificSeriesKey]) {
                        data.series[specificSeriesKey][dateIndex] = Math.round(avgValue);
                    }
                }
            } else {
                if (dwellingType !== 'All' && data.series[dwellingType]) {
                    data.series[dwellingType][dateIndex] = Math.round(avgValue);
                }
            }
        }
    });

    // Calculate "All Properties" aggregated values
    uniqueDates.forEach((date, dateIndex) => {
        const rowsForDate = rows.filter(row => {
            const year = safeNumber(row.year);
            const quarter = safeNumber(row.quarter);
            let rowDateLabel;

            if (row.time_bucket_type === 'quarterly') {
                const monthByQuarter = { 1: '03', 2: '06', 3: '09', 4: '12' };
                rowDateLabel = `${year}-${monthByQuarter[quarter]}`;
            } else if (row.time_bucket_type === 'annually') {
                rowDateLabel = `${year}`;
            } else {
                rowDateLabel = row.time_bucket;
            }
            return rowDateLabel === date;
        });

        if (rowsForDate.length > 0) {
            let totalValue = 0;
            let totalRecords = 0;

            rowsForDate.forEach(row => {
                const avgValue = safeNumber(row.avg_value);
                const recordCount = safeNumber(row.record_count) || 1;

                if (avgValue !== null && avgValue !== undefined) {
                    totalValue += avgValue * recordCount;
                    totalRecords += recordCount;
                }
            });

            if (totalRecords > 0) {
                data.series['All Properties'][dateIndex] = Math.round(totalValue / totalRecords);
            }
        }
    });

    return data;
}