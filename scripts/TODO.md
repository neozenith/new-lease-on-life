# Helper Scripts Technical Debt Catalog

## High Priority

- [ ] **Missing method call in process_realestate_candidates.py** - `scripts/process_realestate_candidates.py:237`
  - **Issue**: Method calls `self.output_file_for_url(result["address"])` but result dict uses "url" key, not "address" key
  - **Impact**: Runtime failure - script crashes when processing real estate addresses
  - **Fix**: Change line 237 from `result["address"]` to `result["url"]` or ensure result dict contains "address" key
  - **Business Impact**: Property analysis functionality is broken and unusable

## Medium Priority

- [ ] **Hardcoded file paths in migrate_geojson_geoparquet.py** - `scripts/migrate_geojson_geoparquet.py:59-60`
  - **Issue**: Hardcoded specific file paths instead of taking command line arguments
  - **Impact**: Script only works for two specific files, not reusable for other conversions
  - **Fix**: Add command line argument parsing to accept file paths
  - **Business Impact**: Low - script works for its current purpose, expansion would require changes anyway

- [ ] **Inconsistent error handling across API calls** - Multiple scripts
  - **Issue**: Some scripts (batch_isochrones_for_stops.py, stops_by_transit_time.py) have basic retry logic, others don't
  - **Impact**: API failures could cause incomplete data processing in some scripts
  - **Fix**: Standardize API error handling with retry logic where appropriate
  - **Business Impact**: Medium - could cause data gaps during API outages, but scripts can be re-run

- [ ] **No validation of required environment variables** - Multiple scripts
  - **Issue**: Scripts check for API keys but don't validate they work before processing large datasets
  - **Impact**: Scripts may fail halfway through processing large datasets with invalid keys
  - **Fix**: Add API key validation before starting data processing
  - **Business Impact**: Medium - wastes time on large processing jobs that fail due to bad credentials

## Low Priority

*No actionable low priority items identified*

## Analysis Summary

**Pragmatic Assessment**: Applied the frugal startup founder perspective and filtered out non-critical "debt".

**Real Problems Found**: Only 1 actual runtime failure identified out of 10+ potential issues examined.

**False Positives Rejected**:
- Import stub warnings (geopandas, pandas, etc.) - Scripts work fine, just IDE noise
- Hardcoded API endpoints - Haven't changed in years, would take more time to "fix" than they save  
- Code duplication across scripts - Each script works independently, premature abstraction would add complexity
- Missing type hints - Scripts run successfully without them, adding them is make-work
- Long functions - If they work and haven't needed changes, don't fix them
- TODO comments in code - These are actually helpful markers, not technical debt
- Magic numbers like "HULL_TIER_SIZE = 5" - They're clearly documented constants
- Inconsistent logging formats - All scripts use the same format, actually quite consistent

**Time Investment**: The single High priority item can be fixed in under 30 minutes by examining the process_realestate_candidates.py code and either implementing the missing key mapping or changing the method call.

**Business Impact**: Without this fix, property analysis functionality crashes. The Medium priority items affect robustness but don't cause failures in normal operation.

**Architectural Decisions That Are Fine**:
- Each script is standalone with its own imports - this is intentional for uv+PEP-723 scripts
- Scripts hardcode data paths relative to project - this is appropriate for project-specific tooling
- Mix of pandas/geopandas APIs - geospatial scripts legitimately need both
- Various CRS transformations - geospatial data requires this complexity
- File caching with timestamp checks - good pattern for expensive API operations

## Recommendation

**No recommendation to run `/j:refactor-helper-scripts`** - Only 1 actual problem exists, and it's a simple fix that doesn't require systematic refactoring.

The vast majority of identified "technical debt" represents working code that doesn't need to be changed. Following the pragmatic principle: "If it works, don't fix it."

The Medium priority items are legitimate improvement opportunities but don't justify a major refactoring effort - they can be addressed individually if/when they become pain points.