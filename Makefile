run-distances:
	uv run src/new_lease_on_life/maps/distance.py candidate_rentals.yaml destinations.yaml

fe:
	cd frontend && uv run npm run build && cd ..

run-api:
	uv run uvicorn backend.api:app --reload

fix:
	uv run ruff format src/
	uv run isort src/
	uv run ruff check --fix src/