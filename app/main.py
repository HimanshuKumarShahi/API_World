import importlib
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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

    # Always register the core User model metadata so ForeignKeys (user_id)
    # in auth, banking, or jokes never fail, WITHOUT mounting the users router!

    importlib.import_module("app.modules.users.models")

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
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

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