from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse

from app.core.database import get_db
from app.modules.jokes.schemas import (
    JokeResponse,
    JokeCreateRequest,
    PaginatedJokesResponse,
    CategorySummary,
)
from app.modules.jokes.controller import JokesController

router = APIRouter(prefix="/jokes", tags=["Jokes API"])


@router.get(
    "",
    response_model=PaginatedJokesResponse,
    summary="Get jokes with taste filters & pagination (Limit up to 1,000)",
)
async def list_jokes(
    category: Optional[str] = Query(
        None,
        description="Filter by taste: funny, dark, adult, programming, dad_joke, pun, savage",
    ),
    joke_type: Optional[str] = Query(None, description="single or twopart"),
    safe_mode: Optional[bool] = Query(
        None, description="Set true to exclude dark and 18+ adult jokes"
    ),
    is_dark: Optional[bool] = Query(None, description="Filter specifically for dark humor"),
    is_adult: Optional[bool] = Query(None, description="Filter specifically for 18+ adult jokes"),
    search: Optional[str] = Query(None, description="Search keyword in setup or punchline"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(
        20,
        ge=1,
        le=1000,
        description="Jokes per page (Max 1000. Tip: Use limit <= 100 in Swagger UI to keep UI snappy)",
    ),
):
    data = await JokesController.list_jokes(
        category, joke_type, safe_mode, is_dark, is_adult, search, page, limit
    )
    return JSONResponse(content=data)

@router.get(
    "/random",
    summary="Get 1 random joke (or up to 500 random jokes) filtered by taste",
)
async def get_random_joke(
    category: Optional[str] = Query(
        None, description="funny, dark, adult, programming, dad_joke, pun, savage"
    ),
    joke_type: Optional[str] = Query(None, description="single or twopart"),
    safe_mode: Optional[bool] = Query(None, description="Exclude dark/adult jokes"),
    count: int = Query(1, ge=1, le=500, description="How many random jokes to fetch"),
):
    return await JokesController.get_random_jokes(category, joke_type, safe_mode, count)


@router.get(
    "/categories",
    response_model=list[CategorySummary],
    summary="List all joke taste categories and total counts",
)
async def get_categories():
    return await JokesController.get_categories_summary()


@router.get(
    "/{joke_id}",
    response_model=JokeResponse,
    summary="Get a specific joke by numeric ID (1 to 2000+) in 0.1ms",
)
async def get_joke_by_id(joke_id: int):
    return await JokesController.get_joke_by_id(joke_id)


@router.post(
    "",
    response_model=JokeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new joke to PostgreSQL and RAM cache",
)
async def create_joke(
    data: JokeCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    return await JokesController.create_joke(data, db)