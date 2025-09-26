-- Template for LGA boundary queries
-- Replace {{lga_name}} with actual LGA name

SELECT
    year,
    quarter,
    dwelling_type,
    bedrooms,
    AVG(value) as avg_value,
    COUNT(*) as record_count
FROM rental_sales
WHERE geospatial_type = 'LGA'
AND geospatial_id = '{{lga_name}}'
AND value IS NOT NULL
GROUP BY year, quarter, dwelling_type, bedrooms
ORDER BY year, quarter, dwelling_type, bedrooms;