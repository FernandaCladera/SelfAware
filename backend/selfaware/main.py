"""Thin entry point. The canonical run is the factory form:

    uv run uvicorn selfaware.api.app:create_app --factory --port 8000

(`make dev-backend` / `make demo-mock`). This module exists so
`python -m selfaware.main` also works when someone inevitably tries it.
"""

import uvicorn


def main() -> None:
    uvicorn.run("selfaware.api.app:create_app", factory=True, host="127.0.0.1", port=8000)


if __name__ == "__main__":
    main()
