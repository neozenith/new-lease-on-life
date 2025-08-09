# Helper Scripts Technical Debt Catalog

## High Priority

- [x] **Fix missing method implementation** - `scripts/process_realestate_candidates.py:182` calls `extract_address_from_url()` method that doesn't exist, causing runtime crashes. Add the implementation or remove the call.

## Medium Priority  

- [ ] **Standardize ArgumentParser across all scripts for consistency and automation** - Only 3/9 scripts (33%) implement ArgumentParser, creating barriers to script discoverability and breaking automated documentation generation by `index-helper-scripts` agent. **Business Impact**: Users can't discover script options with `--help`, configuration requires code editing instead of command-line arguments, and automated docs are incomplete. **Priority Implementation Order**: (1) `process_realestate_candidates.py`, `stops_by_transit_time.py` - complex scripts with extensive configuration, (2) `consolidate_isochrones.py`, `extract_postcode_polygons.py` - moderate complexity, (3) `extract_stops_within_union.py`, `migrate_geojson_geoparquet.py` - simple enhancement. **Success Metric**: 100% of scripts support `--help` with complete usage documentation.

## Low Priority

*No actionable low priority items identified*

## Analysis Summary

**Pragmatic Assessment**: Applied the frugal startup founder perspective and filtered out non-critical "debt".

**Real Problems Found**: Only 1 actual runtime failure identified out of 23+ diagnostics issues.

**False Positives Rejected**:
- Import stub warnings (geopandas, pandas, etc.) - Scripts work fine, just IDE noise
- Hardcoded API endpoints - Haven't changed in years, would take more time to "fix" than they save
- Code duplication across scripts - Each script works independently, premature abstraction would add complexity
- Missing type hints - Scripts run successfully without them, adding them is make-work
- Long functions - If they work and haven't needed changes, don't fix them

**Time Investment**: The single High priority item can be fixed in under 30 minutes by examining the code and either implementing the missing method or removing the call.

**Business Impact**: Without this fix, property analysis functionality crashes. All other "issues" are cosmetic or theoretical.

## Recommendation

**No recommendation to run `/j:refactor-helper-scripts`** - Only 1 actual problem exists, and it's a simple fix that doesn't require systematic refactoring.

The vast majority of identified "technical debt" represents working code that doesn't need to be changed. Following the pragmatic principle: "If it works, don't fix it."
