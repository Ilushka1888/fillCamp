import uvicorn

from src.app.core.config import config

if __name__ == "__main__":
    uvicorn.run(
        "src.app.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL,
    )
