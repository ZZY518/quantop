import argparse

import uvicorn

from app.jobs.scheduler import create_scheduler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action="store_true", help="enable uvicorn auto reload")
    parser.add_argument("--scheduler", action="store_true", help="start APScheduler with the API process")
    args = parser.parse_args()

    scheduler = None
    if args.scheduler:
        scheduler = create_scheduler()
        scheduler.start()

    try:
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload)
    finally:
        if scheduler:
            scheduler.shutdown()


if __name__ == "__main__":
    main()
7