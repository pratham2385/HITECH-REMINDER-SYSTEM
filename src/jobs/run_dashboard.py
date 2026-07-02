"""CLI helper for running the local dashboard web server."""

from __future__ import annotations

from src.config.settings import load_settings
from src.db.session import init_database


def run() -> int:
    """Run the dashboard with uvicorn."""

    try:
        import uvicorn
    except ModuleNotFoundError:
        print("Missing dependency: uvicorn. Run `pip install -r requirements.txt`.")
        return 1

    settings = load_settings()
    init_database(settings)
    uvicorn.run("src.web.app:app", host="0.0.0.0", port=8000, reload=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

