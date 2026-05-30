"""Legacy entry point — delegates to app package."""

from app.main import app

if __name__ == "__main__":
    from run import main
    main()
