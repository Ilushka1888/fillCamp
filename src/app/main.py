from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.app.api.routes.amocrm_router import router as amocrm_router
from src.app.api.routes.user_router import router as user_router
from src.app.api.routes.game_router import router as game_router

from src.telegram.bot import create_bot_and_dispatcher, start_bot
from src.app.core.config import config
from src.app.core.logger import configure_root_logger, get_logger

from src.app.core.config import BASE_DIR, ENV_PATH


configure_root_logger()
logger = get_logger(__name__)

_bot_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _bot_task

    logger.info("Запуск CampBot Server...")
    logger.info(
        f"Читаю .env {config.amocrm_base_url}, Base = {BASE_DIR}, path = {ENV_PATH}"
    )

    bot, dp = create_bot_and_dispatcher()

    _bot_task = asyncio.create_task(start_bot(bot, dp))

    try:
        yield
    finally:
        logger.info("Остановка CampBot Server...")
        if _bot_task is not None:
            _bot_task.cancel()
            with suppress(asyncio.CancelledError):
                await _bot_task


app = FastAPI(lifespan=lifespan, title="CampBot Server")


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(amocrm_router, prefix="/api/v1")
app.include_router(user_router)
app.include_router(game_router)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    return {"status": "healthy"}


@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    logger.error(f"Необработанное исключение: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc),
        },
    )
