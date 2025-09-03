# Helper Scripts Technical Debt Catalog

## High Priority

- [ ] **Missing method call in process_realestate_candidates.py** - `scripts/process_realestate_candidates.py:237`
  - **Issue**: Method calls `self.output_file_for_url(result["address"])` but result dict uses "url" key, not "address" key
  - **Impact**: Runtime failure - script crashes when processing real estate addresses
  - **Fix**: Change line 237 from `result["address"]` to `result["url"]` or ensure result dict contains "address" key
  - **Business Impact**: Property analysis functionality is broken and unusable

- [ ] **Assert statements in production code in extract_state_polygons.py** - `scripts/extract_state_polygons.py:130-133`
  - **Issue**: Using assert statements for validation instead of proper exception handling
  - **Impact**: Runtime failure - assertions are disabled in Python when run with -O optimization flag
  - **Fix**: Replace assert statements with proper if/raise Exception pattern for validation
  - **Business Impact**: Script could silently skip validation or crash unexpectedly in optimized environments

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

- [ ] **Unused imports and variables in extract_state_polygons.py** - `scripts/extract_state_polygons.py:27,117`
  - **Issue**: Imports pandas as pd but never uses it, unused loop variable idx
  - **Impact**: Code clutter and potential confusion, larger bundle size
  - **Fix**: Remove unused import (line 27) and use underscore for unused loop variable (line 117)
  - **Business Impact**: Low - doesn't affect functionality but reduces code cleanliness

- [ ] **Hardcoded file paths in extract_state_polygons.py** - `scripts/extract_state_polygons.py:38-39`
  - **Issue**: Hardcoded input file path and output directory
  - **Impact**: Script only works for specific file structure, not reusable
  - **Fix**: Add command line argument parsing to accept input file and output directory
  - **Business Impact**: Low - script works for its current purpose, but limits reusability

## Low Priority

*No actionable low priority items identified*

## Analysis Summary

**Pragmatic Assessment**: Applied the frugal startup founder perspective and filtered out non-critical "debt".

**Real Problems Found**: 2 actual runtime failures identified out of 10+ potential issues examined.

**False Positives Rejected**:
- Import stub warnings (geopandas, pandas, etc.) - Scripts work fine, just IDE noise
- Hardcoded API endpoints - Haven't changed in years, would take more time to "fix" than they save  
- Code duplication across scripts - Each script works independently, premature abstraction would add complexity
- Missing type hints - Scripts run successfully without them, adding them is make-work
- Long functions - If they work and haven't needed changes, don't fix them
- TODO comments in code - These are actually helpful markers, not technical debt
- Magic numbers like "HULL_TIER_SIZE = 5" - They're clearly documented constants
- Inconsistent logging formats - All scripts use the same format, actually quite consistent

**Time Investment**: The 2 High priority items can be fixed in under 45 minutes total - fixing the method call issue in process_realestate_candidates.py (15 min) and replacing assert statements with proper exception handling in extract_state_polygons.py (30 min).

**Business Impact**: Without these fixes, property analysis functionality crashes and state polygon extraction could fail in optimized Python environments. The Medium priority items affect robustness but don't cause failures in normal operation.

**Architectural Decisions That Are Fine**:
- Each script is standalone with its own imports - this is intentional for uv+PEP-723 scripts
- Scripts hardcode data paths relative to project - this is appropriate for project-specific tooling
- Mix of pandas/geopandas APIs - geospatial scripts legitimately need both
- Various CRS transformations - geospatial data requires this complexity
- File caching with timestamp checks - good pattern for expensive API operations

## Recommendation

**RECOMMENDATION: Run the /j:refactor-helper-scripts slash command to address 2 High impact items.**

While both High priority issues are relatively simple fixes (45 minutes total), they represent actual runtime failures that should be addressed:

1. Property analysis functionality is completely broken due to the method call issue
2. State polygon extraction could fail silently or crash in optimized Python environments due to assert statements

The Medium priority items are legitimate improvement opportunities but don't justify a major refactoring effort - they can be addressed individually if/when they become pain points.
