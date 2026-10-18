"""CLI entry point: `pulsewatch` or `python -m pulsewatch`."""

from __future__ import annotations

import logging

import uvicorn

from pulsewatch.api import create_app
from pulsewatch.config import Settings


def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings()
    uvicorn.run(create_app(settings), host=settings.host, port=settings.port)


if __name__ == "__main__":
    run()
