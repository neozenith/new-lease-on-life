# Standard Library
from pathlib import Path
from typing import Any

# Third Party
import duckdb


class DuckDBCache:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_cache()

    def _init_cache(self):
        con = duckdb.connect(str(self.db_path))
        con.execute("""
            CREATE TABLE IF NOT EXISTS route_cache (
                origin TEXT,
                destination TEXT,
                distance_meters INTEGER,
                duration TEXT,
                travel_mode TEXT,
                PRIMARY KEY (origin, destination, travel_mode)
            )
        """)
        con.close()

    def get_route(self, origin: str, destination: str, travel_mode: str) -> tuple | None:
        con = duckdb.connect(str(self.db_path))
        res = con.execute(
            "SELECT distance_meters, duration FROM route_cache WHERE origin=? AND destination=? AND travel_mode=?",
            [origin, destination, travel_mode],
        ).fetchone()
        con.close()
        return res

    def set_route(self, origin: str, destination: str, travel_mode: str, distance: Any, duration: Any) -> None:
        con = duckdb.connect(str(self.db_path))
        con.execute(
            """INSERT OR REPLACE INTO route_cache 
                (origin, destination, distance_meters, duration, travel_mode) 
                VALUES (?, ?, ?, ?, ?)
            """,
            [origin, destination, distance, duration, travel_mode],
        )
        con.close()
