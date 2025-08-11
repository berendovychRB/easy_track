"""
Main entry point for EasySize Bot application.
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from easy_track import bot


def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            (
                logging.FileHandler("logs/bot.log")
                if Path("logs").exists()
                else logging.NullHandler()
            ),
        ],
    )


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        sys.exit(1)
