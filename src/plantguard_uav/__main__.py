"""Command-line entry point for the PlantGuard UAV API process."""

import sys

import uvicorn

from plantguard_uav.config import load_settings
from plantguard_uav.errors import PlantGuardError
from plantguard_uav.main import create_app


def main() -> int:
    """Load configuration and run the API until the operator stops it."""
    try:
        settings = load_settings()
        app = create_app(settings)
    except PlantGuardError as exc:
        print(f"{exc.error_code}: {exc.public_message}", file=sys.stderr)
        return 2

    uvicorn.run(
        app,
        host=settings.api.host,
        port=settings.api.port,
        log_level=settings.log_level.value.lower(),
        log_config=None,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
