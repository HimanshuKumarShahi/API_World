from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class JokeCategory(str, Enum):
    funny = "funny"
    dark = "dark"
    adult = "adult"
    programming = "programming"
    dad_joke = "dad_joke"
    pun = "pun"
    savage = "savage"


class JokeType(str, Enum):
    single = "single"
    twopart = "twopart"


class JokeResponse(BaseModel):
    id: int
    category: str
    joke_type: str
    setup: str
    delivery: Optional[str] = None
    is_dark: bool
    is_adult: bool
    safe_mode: bool
    likes_count: int
    dislikes_count: int

    model_config = ConfigDict(from_attributes=True)


class JokeCreateRequest(BaseModel):
    category: JokeCategory = JokeCategory.funny
    joke_type: JokeType = JokeType.twopart
    setup: str = Field(..., min_length=5, max_length=1000)
    delivery: Optional[str] = Field(None, max_length=1000)
    is_dark: bool = False
    is_adult: bool = False


class PaginatedJokesResponse(BaseModel):
    total_available: int
    returned_count: int
    page: int
    limit: int
    execution_mode: str = "RAM_CACHE_0.1MS"
    items: List[JokeResponse]


class CategorySummary(BaseModel):
    category: str
    count: int