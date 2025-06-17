from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from new_lease_on_life.cache import DuckDBCache

CACHE_DB_PATH = Path(__file__).parent.parent / 'distance_cache.duckdb'
print(f"Using cache database at: {CACHE_DB_PATH}")
cache = DuckDBCache(CACHE_DB_PATH)

app = FastAPI(title="Distance Cache API")

# Allow CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/routes")
def get_routes(
    origin_address: str | None = None,
    destination_address: str | None = None,
    travel_mode: str | None = None
) -> list[dict]:
    """Query cached routes. All params optional."""
    return cache.query_routes(
        origin_address=origin_address,
        destination_address=destination_address,
        travel_mode=travel_mode
    )

@app.get("/api/locations")
def get_locations(address: str | None = None) -> list[dict]:
    """Query cached locations. Address param optional."""
    with cache.get_connection() as con:
        if address:
            rows = con.execute(
                "SELECT address, lat, lng FROM locations WHERE address = ?", [address]
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT address, lat, lng FROM locations"
            ).fetchall()
        columns = [desc[0] for desc in con.description]
        return list([dict(zip(columns, row)) for row in rows])

# Mount the built frontend (Vite/React) static assets
# This has to be mounted AFTER the API routes to avoid conflicts
# and ensure the API is accessible at /api/*
frontend_dist = Path(__file__).parent.parent / "frontend" / "dist"
app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")