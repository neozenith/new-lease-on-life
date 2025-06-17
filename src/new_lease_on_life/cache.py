# Standard Library
from pathlib import Path
from typing import Any, Optional

# Third Party
import duckdb


class DuckDBCache:
    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._init_cache()

    def _init_cache(self):
        with duckdb.connect(self.db_path) as con:
            # Table for locations (address is the primary key)
            con.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    address TEXT PRIMARY KEY,
                    lat DOUBLE,
                    lng DOUBLE
                )
            ''')
            # Table for routes (uses address text for origin and destination)
            con.execute('''
                CREATE TABLE IF NOT EXISTS routes (
                    origin_address TEXT,
                    destination_address TEXT,
                    travel_mode TEXT,
                    distance_meters INTEGER,
                    duration TEXT,
                    geojson TEXT,
                    PRIMARY KEY (origin_address, destination_address, travel_mode),
                    FOREIGN KEY(origin_address) REFERENCES locations(address),
                    FOREIGN KEY(destination_address) REFERENCES locations(address)
                )
            ''')

    def get_connection(self):
        return duckdb.connect(self.db_path)

    def get_or_create_location(self, address: str, lat: Optional[float] = None, lng: Optional[float] = None) -> str:
        with self.get_connection() as con:
            row = con.execute("SELECT address FROM locations WHERE address = ?", [address]).fetchone()
            if row:
                return row[0]
            # Insert new location
            con.execute(
                "INSERT INTO locations (address, lat, lng) VALUES (?, ?, ?)",
                [address, lat, lng]
            )
            return address

    def get_location(self, address: str) -> Optional[dict]:
        with self.get_connection() as con:
            row = con.execute("SELECT address, lat, lng FROM locations WHERE address = ?", [address]).fetchone()
            if row:
                return {"address": row[0], "lat": row[1], "lng": row[2]}
            return None

    def set_location_latlng(self, address: str, lat: float, lng: float):
        with self.get_connection() as con:
            con.execute("INSERT OR REPLACE INTO locations (address, lat, lng) VALUES (?, ?, ?)", [address, lat, lng])

    def get_route(self, origin_address: str, destination_address: str, travel_mode: str) -> Optional[tuple[Any, Any, Any]]:
        with self.get_connection() as con:
            res = con.execute(
                "SELECT distance_meters, duration, geojson FROM routes WHERE origin_address=? AND destination_address=? AND travel_mode=?",
                [origin_address, destination_address, travel_mode]
            ).fetchone()
            return res

    def set_route(self, origin_address: str, destination_address: str, travel_mode: str, distance: Any, duration: Any, geojson: str):
        with self.get_connection() as con:
            con.execute(
                "INSERT OR REPLACE INTO routes (origin_address, destination_address, travel_mode, distance_meters, duration, geojson) VALUES (?, ?, ?, ?, ?, ?)",
                [origin_address, destination_address, travel_mode, distance, duration, geojson]
            )

    def query_routes(
        self,
        origin_address: Optional[str] = None,
        destination_address: Optional[str] = None,
        travel_mode: Optional[str] = None,
    ) -> list[dict]:
        query = "SELECT * FROM routes WHERE 1=1"
        params = []
        if origin_address:
            query += " AND origin_address = ?"
            params.append(origin_address)
        if destination_address:
            query += " AND destination_address = ?"
            params.append(destination_address)
        if travel_mode:
            query += " AND travel_mode = ?"
            params.append(travel_mode)
        with self.get_connection() as con:
            rows = con.execute(query, params).fetchall()
            columns = [desc[0] for desc in con.description]
            return [dict(zip(columns, row)) for row in rows]
