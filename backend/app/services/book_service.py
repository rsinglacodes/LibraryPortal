import math
import re
from typing import Sequence
from sqlalchemy import case, func, select, or_, and_
from sqlalchemy.orm import Session

from app.core.inventory import get_simulated_availability, get_expected_return_date
from app.models import Book
from app.schemas.book import BookListResponse, BookResponse

# 12 Concise, Canonical, Well-Defined Categories
CANONICAL_CATEGORIES: dict[str, dict[str, list[str]]] = {
    "Fiction & Literature": {
        "tags": ["fiction", "literary", "novel", "classics", "literature", "short stories"],
        "keywords": ["stories", "tales", "adventures"]
    },
    "Mystery & Thriller": {
        "tags": ["mystery", "detective", "thriller", "suspense", "crime", "investigation", "horror"],
        "keywords": ["mystery", "detective", "thriller", "suspense", "murder", "sherlock", "poirot", "killer", "terror"]
    },
    "Sci-Fi & Fantasy": {
        "tags": ["science fiction", "fantasy", "space", "magic", "dystopian", "futuristic", "cyberpunk", "alien"],
        "keywords": ["science fiction", "sci-fi", "fantasy", "space", "magic", "dystopia", "alien", "galaxy", "future", "wizard", "cyberpunk"]
    },
    "Biography & Memoir": {
        "tags": ["biography", "autobiography", "memoir", "biography & autobiography"],
        "keywords": ["biography", "autobiography", "memoir", "life of", "diaries"]
    },
    "History & Politics": {
        "tags": ["history", "political", "politics", "civilization", "historical", "government", "revolution", "military", "world war", "civil war", "ancient", "political science"],
        "keywords": ["history", "historical", "world war", "civil war", "revolution", "empire", "civilization"]
    },
    "Philosophy & Psychology": {
        "tags": ["philosophy", "psychology", "mind", "ethics", "spirit", "philosophical"],
        "keywords": ["philosophy", "philosophical", "psychology", "psychological", "ethics", "existential", "consciousness", "psychoanalysis"]
    },
    "Science & Nature": {
        "tags": ["science", "nature", "physics", "biology", "astronomy", "technology", "environment", "mathematics", "medical", "chemistry"],
        "keywords": ["science", "scientific", "nature", "physics", "biology", "astronomy", "universe", "evolution", "quantum", "earth", "climate"]
    },
    "Children & Young Adult": {
        "tags": ["juvenile", "children", "young adult", "juvenile fiction", "juvenile nonfiction"],
        "keywords": ["children", "young adult", "juvenile", "fairy tale"]
    },
    "Comics & Graphic Novels": {
        "tags": ["comics", "graphic novel", "manga", "cartoons", "caricatures"],
        "keywords": ["comics", "comic", "graphic novel", "manga", "calvin and hobbes", "superhero", "cartoon"]
    },
    "Drama & Poetry": {
        "tags": ["drama", "poetry", "performing arts", "play", "plays"],
        "keywords": ["drama", "poetry", "poem", "poems", "play", "plays", "theater", "theatre", "tragedy"]
    },
    "Business & Economics": {
        "tags": ["business", "economics", "finance", "business & economics", "social science"],
        "keywords": ["business", "economics", "economy", "finance", "money", "management", "market", "capitalism", "leadership"]
    },
    "Self-Help & Lifestyle": {
        "tags": ["self-help", "health & fitness", "lifestyle", "cooking", "family & relationships", "travel", "body, mind & spirit", "humor"],
        "keywords": ["self-help", "lifestyle", "habit", "wellness", "relationship", "travel", "happiness"]
    },
    "Religion & Spirituality": {
        "tags": ["religion", "theology", "faith", "spirituality", "biblical"],
        "keywords": ["religion", "religious", "spiritual", "spirituality", "theology", "bible", "christian", "buddhist", "islam", "prayer"]
    }
}

# Common query noise words & conversational chatter to strip
STOP_WORDS = {
    "some", "any", "a", "an", "the", "book", "books", "novel", "novels",
    "story", "stories", "read", "reads", "reading", "show", "me", "find",
    "search", "searching", "looking", "for", "recommend", "recommendation", "recommendations",
    "best", "top", "good", "great", "popular", "famous", "about", "in",
    "of", "with", "like", "to", "and", "or", "kind", "type", "written", "by",
    "want", "need", "please", "give", "giving", "tell", "telling", "interested",
    "interest", "one", "which", "what", "from", "sand", "i", "it", "am", "my",
    "me", "you", "they", "them", "that", "this", "these", "those", "instead",
    "rather", "exact", "actually", "just", "movie", "movies", "film", "films", "cinema",
    "love", "loving", "loves", "enjoy", "enjoys", "enjoying", "like", "likes", "liking",
    "nowadays", "today", "bit", "feel", "feeling", "suggest", "suggesting"
}

# Common typos / colloquial mapping
TYPO_SYNONYM_MAP = {
    "movei": "movie",
    "moveis": "movies",
    "movi": "movie",
    "movies": "movie",
    "cinema": "movie",
    "film": "movie",
    "films": "movie",
    "pottter": "potter",
    "potterr": "potter",
    "pottr": "potter",
    "rowling": "jk rowling",
    "horrow": "horror",
    "horror": "horror",
    "horor": "horror",
    "scary": "horror",
    "spooky": "horror",
    "creepy": "horror",
    "slasher": "horror thriller",
    "vampire": "vampire horror",
    "vampires": "vampire horror",
    "dracula": "dracula horror",
    "zombie": "zombie horror",
    "zombies": "zombie horror",
    "haunted": "haunted horror",
    "lovecraft": "lovecraft horror",
    "stephen": "stephen king horror",
    "mistery": "mystery",
    "mystry": "mystery",
    "mysteries": "mystery",
    "detective": "mystery",
    "fantacy": "fantasy",
    "fanatasy": "fantasy",
    "fantasies": "fantasy",
    "magic": "fantasy",
    "sci-fi": "science fiction",
    "scifi": "science fiction",
    "si-fi": "science fiction",
    "sifi": "science fiction",
    "space": "science fiction",
    "thriler": "thriller",
    "triller": "thriller",
    "thrillers": "thriller",
    "suspense": "thriller",
    "romnce": "romance",
    "romantics": "romance",
    "romantic": "romance",
    "adventures": "adventure",
    "advanture": "adventure",
    "biografi": "biography",
    "biographies": "biography",
    "autobiography": "biography",
    "memoir": "biography",
    "historik": "history",
    "historical": "history",
    "historicals": "history",
    "war": "history",
    "comic": "comics",
    "comics": "comics",
    "graphic": "graphic",
    "manga": "comics",
    "classic": "classics",
    "classics": "classics",
    "drama": "drama",
    "dramas": "drama",
    "poetry": "poetry",
    "poems": "poetry",
}

def clean_and_expand_query(raw_query: str) -> list[str]:
    raw_lower = raw_query.lower().strip()
    cleaned = re.sub(r"[^\w\s\-]", " ", raw_lower)
    words = cleaned.split()

    meaningful_tokens = []
    for w in words:
        w_clean = w.strip()
        if not w_clean:
            continue
        mapped = TYPO_SYNONYM_MAP.get(w_clean, w_clean)
        for part in mapped.split():
            if part not in STOP_WORDS and len(part) > 1:
                meaningful_tokens.append(part)

    if not meaningful_tokens:
        meaningful_tokens = [w for w in words if len(w) > 1] or [raw_lower]

    return list(dict.fromkeys(meaningful_tokens))

def _format_book_item(b: Book, db: Session | None = None) -> BookResponse:
    total, avail, is_avail = get_simulated_availability(b.isbn10, b.title, db=db)
    res = BookResponse.model_validate(b)
    res.total_copies = total
    res.copies_available = avail
    res.is_available = is_avail
    if not is_avail or avail == 0:
        res.expected_return_date = get_expected_return_date(b.isbn10, db=db)
    return res


def get_books(
    db: Session,
    query: str | None = None,
    category: str | None = None,
    page: int = 1,
    size: int = 20,
) -> BookListResponse:
    stmt = select(Book)
    relevance_score = None

    if query and query.strip():
        raw_q = query.strip()
        raw_lower = raw_q.lower()
        tokens = clean_and_expand_query(raw_q)

        token_conditions = []
        for t in tokens:
            pat = f"%{t}%"
            token_conditions.append(
                or_(
                    Book.title.ilike(pat),
                    Book.categories.ilike(pat),
                    Book.authors.ilike(pat),
                    Book.subtitle.ilike(pat),
                    Book.description.ilike(pat),
                    Book.isbn10.ilike(pat),
                )
            )

        raw_pat = f"%{raw_q}%"

        # Check if query matches a known canonical category
        cat_matches = []
        for cname, cdef in CANONICAL_CATEGORIES.items():
            if raw_lower in cname.lower() or any(raw_lower == t.lower() for t in cdef["tags"]):
                for tag in cdef["tags"]:
                    cat_matches.append(Book.categories.ilike(f"%{tag}%"))

        main_condition = or_(
            Book.title.ilike(raw_pat),
            Book.categories.ilike(raw_pat),
            Book.authors.ilike(raw_pat),
            Book.description.ilike(raw_pat),
            Book.isbn10.ilike(raw_pat),
            Book.subtitle.ilike(raw_pat),
            *( [or_(*cat_matches)] if cat_matches else [] ),
            *token_conditions,
        )
        stmt = stmt.where(main_condition)

        # Weighted Relevance Scoring
        relevance_parts = [
            case((Book.title.ilike(raw_q), 1000), else_=0),
            case((Book.title.ilike(f"{raw_q}%"), 500), else_=0),
            case((Book.title.ilike(raw_pat), 300), else_=0),
            case((Book.categories.ilike(raw_pat), 400), else_=0),
            case((Book.authors.ilike(raw_pat), 250), else_=0),
            case((Book.subtitle.ilike(raw_pat), 150), else_=0),
            case((Book.description.ilike(raw_pat), 20), else_=0),
        ]

        if cat_matches:
            relevance_parts.append(case((or_(*cat_matches), 450), else_=0))

        for t in tokens:
            t_pat = f"%{t}%"
            relevance_parts.extend([
                case((Book.title.ilike(t_pat), 80), else_=0),
                case((Book.categories.ilike(t_pat), 100), else_=0),
                case((Book.authors.ilike(t_pat), 60), else_=0),
                case((Book.description.ilike(t_pat), 5), else_=0),
            ])

        relevance_score = sum(relevance_parts)

    if category and category.strip():
        cat_key = category.strip()
        if cat_key in CANONICAL_CATEGORIES:
            defs = CANONICAL_CATEGORIES[cat_key]
            cat_conditions = []
            for tag in defs["tags"]:
                cat_conditions.append(Book.categories.ilike(f"%{tag}%"))
            for kw in defs.get("keywords", []):
                cat_conditions.append(Book.title.ilike(f"%{kw}%"))
            stmt = stmt.where(or_(*cat_conditions))
        else:
            cat_pattern = f"%{cat_key}%"
            stmt = stmt.where(
                or_(
                    Book.categories.ilike(cat_pattern),
                    Book.title.ilike(cat_pattern),
                )
            )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    pages = math.ceil(total / size) if size > 0 else 0
    offset = (page - 1) * size

    if relevance_score is not None:
        order_clauses = [
            relevance_score.desc(),
            Book.average_rating.desc().nullslast(),
            Book.ratings_count.desc().nullslast(),
            Book.title,
        ]
    else:
        order_clauses = [
            Book.average_rating.desc().nullslast(),
            Book.ratings_count.desc().nullslast(),
            Book.title,
        ]

    books = db.scalars(
        stmt.order_by(*order_clauses).offset(offset).limit(size)
    ).all()

    return BookListResponse(
        items=[_format_book_item(b, db) for b in books],
        total=total,
        page=page,
        size=size,
        pages=pages,
    )


def get_book_by_isbn(db: Session, isbn10: str) -> Book | None:
    return db.get(Book, isbn10.strip())

def get_unique_categories(db: Session | None = None) -> list[str]:
    return list(CANONICAL_CATEGORIES.keys())

