import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select, or_
from app.database.connection import get_session_local
from app.models import Book

CATEGORIES_DEF = {
    "Fiction": {
        "tags": ["fiction", "literary", "novel", "classics"],
        "keywords": ["novel", "story", "stories", "fiction"]
    },
    "Mystery & Thriller": {
        "tags": ["mystery", "detective", "thriller", "suspense", "crime", "investigation", "horror"],
        "keywords": ["mystery", "detective", "thriller", "suspense", "murder", "crime", "investigation", "horror", "sherlock", "poirot", "conspiracy"]
    },
    "Sci-Fi & Fantasy": {
        "tags": ["science fiction", "fantasy", "space", "magic", "dystopian", "futuristic", "cyberpunk", "alien"],
        "keywords": ["science fiction", "sci-fi", "fantasy", "space", "magic", "dystopia", "dystopian", "alien", "galaxy", "future", "futuristic", "wizard", "cyberpunk", "robot"]
    },
    "Biography & Memoir": {
        "tags": ["biography", "autobiography", "memoir"],
        "keywords": ["biography", "autobiography", "memoir", "life of", "diaries", "memoirs"]
    },
    "History & Politics": {
        "tags": ["history", "political", "war", "civilization"],
        "keywords": ["history", "historical", "war", "politics", "revolution", "empire", "century", "ancient"]
    },
    "Philosophy & Psychology": {
        "tags": ["philosophy", "psychology", "mind", "ethics", "spirit"],
        "keywords": ["philosophy", "philosophical", "psychology", "psychological", "mind", "ethics", "existential", "consciousness", "psychoanalysis"]
    },
    "Science & Nature": {
        "tags": ["science", "nature", "physics", "biology", "astronomy", "technology", "environment", "mathematics", "medical", "health"],
        "keywords": ["science", "scientific", "nature", "physics", "biology", "astronomy", "universe", "evolution", "dna", "quantum", "earth", "climate", "environment"]
    },
    "Children & Young Adult": {
        "tags": ["juvenile", "children", "young adult"],
        "keywords": ["children", "young adult", "juvenile", "teen", "kids", "fairy tale", "school"]
    },
    "Comics & Graphic Novels": {
        "tags": ["comics", "graphic novel", "manga"],
        "keywords": ["comics", "comic", "graphic novel", "manga", "calvin and hobbes", "superhero", "cartoon"]
    },
    "Drama & Poetry": {
        "tags": ["drama", "poetry", "performing arts", "play"],
        "keywords": ["drama", "poetry", "poem", "poems", "play", "plays", "theater", "theatre", "tragedy"]
    },
    "Business & Economics": {
        "tags": ["business", "economics", "finance", "social science"],
        "keywords": ["business", "economics", "economy", "finance", "money", "management", "market", "capitalism", "leadership"]
    },
    "Self-Help & Lifestyle": {
        "tags": ["self-help", "health", "fitness", "family", "relationships", "travel", "humor"],
        "keywords": ["self-help", "lifestyle", "habit", "success", "wellness", "relationship", "travel", "humor", "happiness"]
    },
    "Religion & Spirituality": {
        "tags": ["religion", "theology", "faith", "spirituality"],
        "keywords": ["religion", "religious", "spiritual", "spirituality", "god", "faith", "theology", "bible", "christian", "buddhist", "islam", "prayer"]
    }
}

db = get_session_local()()
for cat_name, defs in CATEGORIES_DEF.items():
    conds = []
    for tag in defs["tags"]:
        conds.append(Book.categories.ilike(f"%{tag}%"))
    for kw in defs["keywords"]:
        conds.append(Book.title.ilike(f"%{kw}%"))
        conds.append(Book.description.ilike(f"%{kw}%"))

    stmt = select(Book).where(or_(*conds))
    books = db.scalars(stmt).all()
    print(f"Category '{cat_name}': {len(books)} books matched. First 2:")
    for b in books[:2]:
        print(f"   - {b.title} (Cat: {b.categories})")

db.close()
