-- Template for SA2 boundary queries
-- Replace {{suburb_name}} with matched suburb name (e.g., 'ARMADALE')
-- Note: This uses fuzzy-matched suburb data

SELECT
    year,
    quarter,
    dwelling_type,
    bedrooms,
    AVG(value) as avg_value,
    COUNT(*) as record_count
FROM rental_sales
WHERE geospatial_type = 'SUBURB'
AND geospatial_id = '{{suburb_name}}'
AND value IS NOT NULL
GROUP BY year, quarter, dwelling_type, bedrooms
ORDER BY year, quarter, dwelling_type, bedrooms;