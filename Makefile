run-distances:
	uv run src/new_lease_on_life/maps/distance.py candidate_rentals.yaml destinations.yaml

fix:
	uv run ruff format src/
	uv run isort src/
	uv run ruff check --fix src/