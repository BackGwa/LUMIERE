from contextlib import asynccontextmanager
from fastapi import FastAPI
import uvicorn

from src.api.routes import router
from src.utils.logger import get_logger, start_log_archiving
from src.utils.config import config, ConfigError
import sys

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("LUMIERE API server has been activated.")
    start_log_archiving()
    yield
    logger.info("LUMIERE API server has been deactivated.")

def create_app() -> FastAPI:
    app = FastAPI(
        title="LUMIERE API",
        version="1.0.0",
        lifespan=lifespan
    )
    app.include_router(router, prefix="/api")
    return app

def start_server():
    try:
        app = create_app()
        host = config.get_server_host()
        port = config.get_server_port()
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )
    except ConfigError as e:
        sys.exit(1)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        sys.exit(0)