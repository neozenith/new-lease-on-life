# Modular JavaScript Architecture

This directory demonstrates how the monolithic `scripts.js` file could be organized into focused, maintainable modules.

## Module Overview

### 🗂️ **utils.js** - Pure Utility Functions
- **Constants**: Application-wide constants (colors, limits, configurations)
- **Color Functions**: `hexToRgbA()`, `resolveColorReference()`, color mapping
- **Helper Functions**: `safeNumber()`, `showLocationStatus()`, chart styling
- **Pure Functions**: No side effects, easy to test

### 🔗 **database.js** - DuckDB Integration
- **Connection Management**: `initializeDuckDB()`, database setup
- **Data Querying**: `queryRentalData()` with input validation
- **SQL Generation**: Dynamic query building for different geospatial types
- **Result Processing**: Transform raw data into chart-ready format

### 🎯 **selection.js** - Selection Management System
- **State Management**: `selectedItems` Map, selection limits
- **Event Handling**: `handleItemClick()`, `clearAllSelections()`
- **UI Generation**: `generateItemContent()`, selection panel updates
- **Type Detection**: Layer ID to item type mapping

### 🎮 **main.js** - Application Orchestration
- **Initialization**: Coordinate all modules and external libraries
- **DeckGL Setup**: Map configuration, event handlers, tooltips
- **Layer Management**: Config loading, layer creation from JSON
- **Error Handling**: Graceful degradation and user feedback

## Benefits of This Architecture

### 📦 **Separation of Concerns**
- **Database logic** separated from UI logic
- **Utility functions** isolated for reusability
- **Selection management** as independent system
- **Main app** focuses on coordination only

### 🧪 **Testability**
- **Pure functions** in utils.js are easily unit tested
- **Database module** can be tested with mock connections
- **Selection logic** can be tested independently
- **Modular design** enables isolated testing

### 🔄 **Maintainability**
- **Single Responsibility**: Each module has one clear purpose
- **Smaller Files**: 200-400 lines vs 1600+ line monolith
- **Clear Dependencies**: Import/export makes relationships explicit
- **Easier Navigation**: Find functionality by module purpose

### 🚀 **Performance**
- **Tree Shaking**: Unused functions can be eliminated
- **Code Splitting**: Modules can be loaded on demand
- **Caching**: Browser can cache unchanged modules
- **Parallel Loading**: Multiple modules can load simultaneously

## File Structure Comparison

### Before (Monolithic)
```
scripts.js (1600+ lines)
├── DuckDB integration
├── Utility functions
├── Layer management
├── Color handling
├── Selection system
├── Chart creation
├── GPS functionality
├── UI management
└── Application setup
```

### After (Modular)
```
modules/
├── utils.js (150 lines) - Pure utilities & constants
├── database.js (300 lines) - DuckDB integration & queries
├── selection.js (250 lines) - Selection management system
├── main.js (200 lines) - App initialization & coordination
└── [potential additional modules]
    ├── charts.js - Plotly.js chart creation
    ├── location.js - GPS functionality
    ├── layers.js - Layer creation & management
    └── ui.js - UI controls & interactions
```

## Usage Example

### HTML Integration
```html
<!DOCTYPE html>
<html>
<head>
    <!-- External dependencies -->
    <script src="https://unpkg.com/deck.gl@latest/dist.min.js"></script>
    <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
</head>
<body>
    <div id="container"></div>

    <!-- Main application -->
    <script type="module" src="modules/main.js"></script>
</body>
</html>
```

### Module Imports
```javascript
// In main.js
import { initializeDuckDB, queryRentalData } from './database.js';
import { COLORS, hexToRgbA, showLocationStatus } from './utils.js';
import { handleItemClick, clearAllSelections } from './selection.js';

// Use imported functions
await initializeDuckDB();
const data = await queryRentalData('LGA', 'Melbourne', 'rent');
showLocationStatus('Database connected', false);
```

## Migration Strategy

### Phase 1: Extract Constants & Utils
1. Move constants to `utils.js`
2. Extract pure functions
3. Update imports in main file

### Phase 2: Extract Major Subsystems
1. Move database logic to `database.js`
2. Extract selection system to `selection.js`
3. Test integration

### Phase 3: Complete Modularization
1. Create remaining modules (charts, location, layers, ui)
2. Minimize main.js to coordination only
3. Add comprehensive testing

### Phase 4: Optimization
1. Implement code splitting
2. Add lazy loading for non-critical modules
3. Optimize bundle sizes

## Next Steps

1. **Test the Modular Structure**: Verify all functionality works with imports
2. **Add Missing Modules**: Extract charts, location, layers, and UI modules
3. **Implement Testing**: Add unit tests for each module
4. **Bundle Optimization**: Use webpack/vite for production builds
5. **Documentation**: Add JSDoc comments and API documentation

## Development Guidelines

- **Keep modules focused**: Each should have a single, clear responsibility
- **Minimize dependencies**: Reduce coupling between modules
- **Use pure functions**: Where possible, avoid side effects
- **Document interfaces**: Clear import/export documentation
- **Test independently**: Each module should be testable in isolation