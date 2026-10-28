import random
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.modules.jokes.models import Joke
from app.modules.jokes.schemas import (
    JokeCreateRequest,
    PaginatedJokesResponse,
    CategorySummary,
)
import app.modules.jokes.seed_loader as cache


class JokesController:

    @staticmethod
    async def ensure_loaded() -> None:
        if not cache.JOKES_RAM_LIST:
            await cache.sync_jokes_json_to_db_and_cache()

    @staticmethod
    def _filter_ram_jokes(
        category: Optional[str] = None,
        joke_type: Optional[str] = None,
        safe_mode: Optional[bool] = None,
        is_dark: Optional[bool] = None,
        is_adult: Optional[bool] = None,
        search: Optional[str] = None,
    ) -> list[dict]:
        """0.1ms in-memory filtering with smart Swagger boolean handling."""
        if category and "," not in category:
            cat_clean = category.strip().lower()
            pool = cache.JOKES_BY_CATEGORY.get(cat_clean, [])
        elif category:
            cats = {c.strip().lower() for c in category.split(",") if c.strip()}
            pool = [j for j in cache.JOKES_RAM_LIST if j["category"] in cats]
        else:
            pool = cache.JOKES_RAM_LIST

        if joke_type and joke_type.strip().lower() in ("single", "twopart"):
            pool = [j for j in pool if j["joke_type"] == joke_type.strip().lower()]

        
        if is_dark is True and is_adult is True:
            
            pool = [j for j in pool if j["is_dark"] or j["is_adult"]]
        elif is_dark is True:
            pool = [j for j in pool if j["is_dark"] is True]
        elif is_adult is True:
            pool = [j for j in pool if j["is_adult"] is True]
        elif safe_mode is True:
           
            pool = [j for j in pool if j["safe_mode"] is True]
        else:
            if is_dark is False:
                pool = [j for j in pool if j["is_dark"] is False]
            if is_adult is False:
                pool = [j for j in pool if j["is_adult"] is False]

       
        if search and search.strip():
            q = search.strip().lower()
            pool = [
                j for j in pool
                if q in j["setup"].lower()
                or (j["delivery"] and q in j["delivery"].lower())
            ]

        return pool

    @staticmethod
    async def list_jokes(
        category: Optional[str],
        joke_type: Optional[str],
        safe_mode: Optional[bool],
        is_dark: Optional[bool],
        is_adult: Optional[bool],
        search: Optional[str],
        page: int,
        limit: int,
    ) -> PaginatedJokesResponse:
        await JokesController.ensure_loaded()
        filtered = JokesController._filter_ram_jokes(
            category, joke_type, safe_mode, is_dark, is_adult, search
        )
        total = len(filtered)
        start = (page - 1) * limit
        end = start + limit
        sliced = filtered[start:end]

        return PaginatedJokesResponse(
            total_available=total,
            returned_count=len(sliced),
            page=page,
            limit=limit,
            execution_mode="RAM_CACHE_0.1MS + POSTGRES_BACKED",
            items=sliced,
        )

    @staticmethod
    async def get_random_jokes(
        category: Optional[str],
        joke_type: Optional[str],
        safe_mode: Optional[bool],
        count: int,
    ) -> list[dict] | dict:
        await JokesController.ensure_loaded()
        pool = JokesController._filter_ram_jokes(
            category=category, joke_type=joke_type, safe_mode=safe_mode
        )
        if not pool:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No jokes found matching those taste filters.",
            )

        if count == 1:
            return random.choice(pool)

        sample_size = min(count, len(pool))
        return random.sample(pool, sample_size)

    @staticmethod
    async def get_joke_by_id(joke_id: int) -> dict:
        await JokesController.ensure_loaded()
        joke = cache.JOKES_BY_ID.get(joke_id)
        if not joke:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Joke with ID #{joke_id} not found",
            )
        return joke

    @staticmethod
    async def get_categories_summary() -> list[CategorySummary]:
        await JokesController.ensure_loaded()
        return [
            CategorySummary(category=cat, count=len(items))
            for cat, items in cache.JOKES_BY_CATEGORY.items()
        ]

    @staticmethod
    async def create_joke(data: JokeCreateRequest, db: AsyncSession) -> dict:
        await JokesController.ensure_loaded()
        is_dark = data.is_dark or (data.category.value == "dark")
        is_adult = data.is_adult or (data.category.value == "adult")
        safe_mode = not (is_dark or is_adult)

        new_joke = Joke(
            category=data.category.value,
            joke_type=data.joke_type.value,
            setup=data.setup,
            delivery=data.delivery if data.joke_type.value == "twopart" else None,
            is_dark=is_dark,
            is_adult=is_adult,
            safe_mode=safe_mode,
        )
        db.add(new_joke)
        await db.commit()
        await db.refresh(new_joke)

        joke_dict = {
            "id": new_joke.id,
            "category": new_joke.category,
            "joke_type": new_joke.joke_type,
            "setup": new_joke.setup,
            "delivery": new_joke.delivery,
            "is_dark": new_joke.is_dark,
            "is_adult": new_joke.is_adult,
            "safe_mode": new_joke.safe_mode,
            "likes_count": new_joke.likes_count,
            "dislikes_count": new_joke.dislikes_count,
        }
        cache.JOKES_RAM_LIST.append(joke_dict)
        cache.JOKES_BY_ID[new_joke.id] = joke_dict
        cache.JOKES_BY_CATEGORY.setdefault(new_joke.category, []).append(joke_dict)
        return joke_dict