"""Lovelight: AI bookkeeping for accounting bureaus."""


def main() -> None:
    """Serve the API and UI on http://127.0.0.1:8000 (`uv run lovelight`)."""
    import uvicorn

    uvicorn.run("lovelight.server:app", host="127.0.0.1", port=8000)
