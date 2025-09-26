-- Template for Postcode boundary queries
-- Replace {{postcode}} with actual postcode (e.g., '3142')
-- This aggregates all suburbs within the postcode

SELECT
    year,
    quarter,
    dwelling_type,
    bedrooms,
    AVG(value) as avg_value,
    COUNT(*) as record_count
FROM rental_sales
WHERE geospatial_type = 'SUBURB'
AND postcode = '{{postcode}}'
AND value IS NOT NULL
GROUP BY year, quarter, dwelling_type, bedrooms
ORDER BY year, quarter, dwelling_type, bedrooms;