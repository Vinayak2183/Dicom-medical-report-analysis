"""Application entry point."""

import uvicorn

from app.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"\n  Backend API:  http://{settings.host}:{settings.port}/")
    print(f"  API docs:     http://{settings.host}:{settings.port}/docs")
    print(f"  Frontend UI:  http://localhost:3000  (run npm run dev in frontend/)\n")
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True,
    )


if __name__ == "__main__":
    main()
