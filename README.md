# new-lease-on-life
Silly little side project helping me find a rental

## Create Google Maps API Key

https://console.cloud.google.com/apis/credentials

- Create a new Google Developer Project
- Create an API Key
- Its weird and dumb but each Google API you wish to use. Like explicit opt-in

```sh
# For VS Code
code --add-mcp '{"name":"playwright","command":"npx","args":["@playwright/mcp@latest"]}'
```

## Quick Start

### 1. Install dependencies
- Backend: `uv pip install fastapi uvicorn duckdb`
- Frontend: `cd frontend && npm install`

### 2. Run the backend (serves API and built frontend)
```
uvicorn main:app --reload
```

### 3. Run the frontend (development mode)
```
cd frontend
npm run dev
```

### 4. Build the frontend for production
```
cd frontend
npm run build
```

### 5. API
- `GET /api/routes` — Returns all cached routes from DuckDB

### 6. Serving the frontend
- The backend serves the built frontend from `frontend/dist` at the root URL (`/`).

## Development Notes
- DuckDB cache is stored at the repo root as `distance_cache.duckdb`.
- Edit `.github/copilot-instructions.md` for Copilot guidance.