import importlib
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import engine, Base

logger = logging.getLogger("uvicorn")


def load_enabled_modules(app: FastAPI) -> list[str]:
    """
    Mounts ONLY the exact routers listed in settings.ENABLED_MODULES.
    """
    active_modules = settings.active_modules_list
    mounted_modules: list[str] = []
    logger.info(f"🚀 Configured Active Modules: {active_modules}")

    # ---> FIXED HERE: Always register BOTH User and RefreshToken models <---
    # Because User has a relationship("RefreshToken"), both model files must be
    # registered in SQLAlchemy Base, even when their routers aren't mounted!
    importlib.import_module("app.modules.users.models")
    importlib.import_module("app.modules.auth.models")

    for module_name in active_modules:
        try:
            importlib.import_module(f"app.modules.{module_name}.models")

            router_module = importlib.import_module(f"app.modules.{module_name}.router")
            if hasattr(router_module, "router"):
                app.include_router(router_module.router, prefix=settings.API_V1_STR)
                mounted_modules.append(module_name)
                logger.info(f"✅ Mounted module: {settings.API_V1_STR}/{module_name}")
        except ModuleNotFoundError:
            logger.warning(f"⚠️ Module '{module_name}' not created yet. Skipping.")
        except Exception as e:
            logger.error(f"❌ Error loading module '{module_name}': {e}")

    return mounted_modules


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    if "jokes" in MOUNTED_MODULES:
        from app.modules.jokes.seed_loader import sync_jokes_json_to_db_and_cache
        await sync_jokes_json_to_db_and_cache(target_count=settings.JOKES_DEFAULT_COUNT)

    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    swagger_ui_parameters={
        "syntaxHighlight": False,
        "docExpansion": "list",
        "defaultModelsExpandDepth": -1,
    },
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MOUNTED_MODULES = load_enabled_modules(app)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "configured_modules": settings.active_modules_list,
        "mounted_modules": MOUNTED_MODULES,
    }

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "docs_url": "/docs",
        "health_url": "/health",
        "mounted_modules": MOUNTED_MODULES,
    }