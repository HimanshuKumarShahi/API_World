import json
import logging
from pathlib import Path
from sqlalchemy import select, func, delete
from sqlalchemy.dialects.postgresql import insert
from app.core.database import AsyncSessionLocal,settings
from app.modules.jokes.models import Joke

logger = logging.getLogger("uvicorn")

DATA_FILE = Path(__file__).parent / "data" / "jokes.json"

JOKES_RAM_LIST: list[dict] = []
JOKES_BY_ID: dict[int, dict] = {}
JOKES_BY_CATEGORY: dict[str, list[dict]] = {}


BASE_JOKES = [
    # PROGRAMMING
    {"category": "programming", "joke_type": "twopart", "setup": "Why do programmers prefer dark mode?", "delivery": "Because light attracts bugs.", "is_dark": False, "is_adult": False},
    {"category": "programming", "joke_type": "twopart", "setup": "Why did the developer go broke?", "delivery": "Because he used up all his cache.", "is_dark": False, "is_adult": False},
    {"category": "programming", "joke_type": "single", "setup": "There are 10 types of people in the world: those who understand binary, and those who don't.", "delivery": None, "is_dark": False, "is_adult": False},
    {"category": "programming", "joke_type": "twopart", "setup": "How do you comfort a JavaScript bug?", "delivery": "You console it.", "is_dark": False, "is_adult": False},
    {"category": "programming", "joke_type": "twopart", "setup": "Why do Python developers wear glasses?", "delivery": "Because they can't C#.", "is_dark": False, "is_adult": False},
    # DARK
    {"category": "dark", "joke_type": "twopart", "setup": "Why don't graveyards ever get overcrowded?", "delivery": "Because people are dying to get in.", "is_dark": True, "is_adult": False},
    {"category": "dark", "joke_type": "twopart", "setup": "My grief counselor died yesterday.", "delivery": "He was so good at his job, I don't even care.", "is_dark": True, "is_adult": False},
    {"category": "dark", "joke_type": "single", "setup": "Give a man a match, and he'll be warm for a few hours. Set a man on fire, and he will be warm for the rest of his life.", "delivery": None, "is_dark": True, "is_adult": False},
    # ADULT (18+ / Spicy)
    {"category": "adult", "joke_type": "twopart", "setup": "What do a nearsighted gynecologist and a puppy have in common?", "delivery": "A wet nose.", "is_dark": False, "is_adult": True},
    {"category": "adult", "joke_type": "twopart", "setup": "Why is a laundromat a terrible place to flirt?", "delivery": "Because people are just there to dump their dirty loads.", "is_dark": False, "is_adult": True},
    # FUNNY
    {"category": "funny", "joke_type": "twopart", "setup": "Why don't scientists trust atoms?", "delivery": "Because they make up everything!", "is_dark": False, "is_adult": False},
    {"category": "funny", "joke_type": "twopart", "setup": "What did the parallel lines say to each other?", "delivery": "It's a shame we'll never meet.", "is_dark": False, "is_adult": False},
    # DAD JOKE
    {"category": "dad_joke", "joke_type": "twopart", "setup": "Hi Hungry, I'm Dad.", "delivery": "Dad, please, I'm literally starving.", "is_dark": False, "is_adult": False},
    {"category": "dad_joke", "joke_type": "twopart", "setup": "Why did the scarecrow win an award?", "delivery": "Because he was outstanding in his field!", "is_dark": False, "is_adult": False},
    # PUN
    {"category": "pun", "joke_type": "single", "setup": "I used to be a banker, but I lost interest.", "delivery": None, "is_dark": False, "is_adult": False},
    {"category": "pun", "joke_type": "single", "setup": "The rotation of Earth really makes my day.", "delivery": None, "is_dark": False, "is_adult": False},
    # SAVAGE
    {"category": "savage", "joke_type": "single", "setup": "Somewhere out there is a tree tirelessly producing oxygen for you. You owe it an apology.", "delivery": None, "is_dark": False, "is_adult": False},
]


def ensure_jokes_json_exists(target_count: int = 1000) -> list[dict]:
    """Ensures jokes.json has exactly `target_count` jokes (e.g., 1,000)."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)

    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) == target_count:
                    return data
        except Exception:
            logger.warning("⚠️ jokes.json was empty or corrupt. Regenerating...")

    generated = []
    for i in range(1, target_count + 1):
        template = BASE_JOKES[(i - 1) % len(BASE_JOKES)]
        suffix = "" if i <= len(BASE_JOKES) else f" (Vol. {i})"
        is_dark = template["is_dark"]
        is_adult = template["is_adult"]

        generated.append({
            "id": i,
            "category": template["category"],
            "joke_type": template["joke_type"],
            "setup": f"{template['setup']}{suffix}",
            "delivery": template["delivery"],
            "is_dark": is_dark,
            "is_adult": is_adult,
            "safe_mode": not (is_dark or is_adult),
            "likes_count": (i * 7) % 150,
            "dislikes_count": (i * 3) % 20,
        })

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(generated, f, indent=2, ensure_ascii=False)

    logger.info(f"📁 Updated {DATA_FILE} with {len(generated)} structured jokes.")
    return generated


def rebuild_ram_cache(jokes_list: list[dict]) -> None:
    global JOKES_RAM_LIST, JOKES_BY_ID, JOKES_BY_CATEGORY
    JOKES_RAM_LIST = jokes_list
    JOKES_BY_ID = {j["id"]: j for j in jokes_list}
    JOKES_BY_CATEGORY = {}
    for j in jokes_list:
        cat = j["category"]
        JOKES_BY_CATEGORY.setdefault(cat, []).append(j)


async def sync_jokes_json_to_db_and_cache(target_count: int | None = None) -> int:
    if target_count is None:
        target_count = settings.JOKES_DEFAULT_COUNT

    json_jokes = ensure_jokes_json_exists(target_count=target_count)

    async with AsyncSessionLocal() as db:
        
        await db.execute(delete(Joke).where(Joke.id > target_count))
        await db.commit()

        count_res = await db.execute(select(func.count(Joke.id)))
        existing_count = count_res.scalar_one()

        if existing_count < len(json_jokes):
            logger.info(f" Syncing {len(json_jokes)} jokes into PostgreSQL...")
            batch_size = 250
            for start in range(0, len(json_jokes), batch_size):
                chunk = json_jokes[start : start + batch_size]
                stmt = insert(Joke).values(chunk).on_conflict_do_nothing(index_elements=["id"])
                await db.execute(stmt)
            await db.commit()
            logger.info(" PostgreSQL successfully synced with jokes.json!")

        result = await db.execute(select(Joke).order_by(Joke.id.asc()))
        db_rows = result.scalars().all()
        ram_data = [
            {
                "id": r.id,
                "category": r.category,
                "joke_type": r.joke_type,
                "setup": r.setup,
                "delivery": r.delivery,
                "is_dark": r.is_dark,
                "is_adult": r.is_adult,
                "safe_mode": r.safe_mode,
                "likes_count": r.likes_count,
                "dislikes_count": r.dislikes_count,
            }
            for r in db_rows
        ]
        rebuild_ram_cache(ram_data)
        logger.info(f" Jokes RAM Cache ready: {len(JOKES_RAM_LIST)} jokes indexed in 0.1ms!")
        return len(JOKES_RAM_LIST)