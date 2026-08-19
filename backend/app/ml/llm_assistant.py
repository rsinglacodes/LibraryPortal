from __future__ import annotations

import os
import re
import json
from typing import Any, Dict, List, Set, Tuple
from sqlalchemy import select, or_, and_, desc
from sqlalchemy.orm import Session

try:
    from groq import Groq, BadRequestError, RateLimitError, APIError
except ImportError:
    Groq = None
    BadRequestError = Exception
    RateLimitError = Exception
    APIError = Exception

from app.core.config import get_settings
from app.core.inventory import get_simulated_availability, get_expected_return_date
from app.models import Book
from app.services.book_service import clean_and_expand_query

# Backward compatibility aliases
_get_simulated_availability = get_simulated_availability

# --------------------------------------------------
# 1. Hard Safety Filter & Crisis Response
# --------------------------------------------------

UNSAFE_KEYWORDS = [
    "suicide", "suicidal", "self-harm", "self harm", "kill myself",
    "end my life", "want to die", "hurt myself"
]

CRISIS_MESSAGE = (
    "I'm not able to help with that. If you or someone you know is struggling, please reach out to "
    "a crisis helpline — in India, you can contact AASRA at 91-22-27546669, available 24/7. "
    "Is there something else I can help you find in the library?"
)

def contains_unsafe_request(query: str) -> bool:
    query_lower = query.lower()
    return any(keyword in query_lower for keyword in UNSAFE_KEYWORDS)

# --------------------------------------------------
# 2. Greetings & Acknowledgments
# --------------------------------------------------

GREETING_PHRASES = {
    "hi", "hello", "hey", "hlo", "helo", "hii", "hiii", "hola",
    "good morning", "good afternoon", "good evening", "good day",
    "howdy", "greetings", "sup", "yo", "namaste", "whats up", "what's up",
    "help", "start", "menu"
}

ACKNOWLEDGMENT_PHRASES = {
    "ok", "okay", "okk", "k", "got it", "thanks", "thank you", "thanks a lot",
    "cool", "nice", "alright", "sounds good", "perfect", "great", "sure", "yep"
}

GREETING_WELCOME_MESSAGE = (
    "Hello! Welcome to the University Library.\n\n"
    "I can assist you with:\n"
    "• Finding books by title, author, topic, or genre\n"
    "• Recommending books based on your mood or reading goals\n"
    "• Checking copy availability in our stacks\n"
    "• Providing book synopses, themes, and summaries\n\n"
    "What would you like to explore today?"
)

def is_greeting(query: str) -> bool:
    cleaned = re.sub(r"[^\w\s]", "", query.lower()).strip()
    if cleaned in GREETING_PHRASES:
        return True
    words = cleaned.split()
    if len(words) <= 3:
        greeting_words = {"hi", "hello", "hey", "hlo", "helo", "there", "bot", "assistant", "ai", "friend", "library", "librarian"}
        if all(w in greeting_words or w in GREETING_PHRASES for w in words):
            return True
    return False

def is_pure_acknowledgment(query: str) -> bool:
    cleaned = re.sub(r"[^\w\s]", "", query.lower()).strip()
    return cleaned in ACKNOWLEDGMENT_PHRASES

# --------------------------------------------------
# 3. Emotion Detection & Tone Guidance
# --------------------------------------------------

EMOTION_TONE_GUIDE = {
    "horror_thrill": {
        "description": "Atmospheric, suspenseful, dark, cinematic, and chilling tone suited for horror, spooky tales, horror movies, and psychological thrillers.",
        "prefix": "Step into the shadows... Here are spine-chilling horror and thriller titles from our library stacks matching your interest:"
    },
    "comfort_relief": {
        "description": "Gentle, soothing, deeply comforting, uplifting, and cozy tone. Perfect for someone tired, stressed, overwhelmed, or seeking a heartwarming escape.",
        "prefix": "I hear you — when you're feeling tired or worn out, a comforting, gentle, and uplifting book is the best remedy. Here are cozy and heartwarming reads to help you unwind:"
    },
    "frustration": {
        "description": "Attentive, empathetic, validating, respectful, and laser-focused tone. Apologizes smoothly for any previous confusion and immediately delivers exact matches for what the user is searching for without generic fluff.",
        "prefix": "I hear you clearly, and I apologize for the previous confusion! Let's get you exactly what you're searching for right now:"
    },
    "sadness": {
        "description": "Gentle, compassionate, deeply empathetic, warm, and soothing tone.",
        "prefix": "I hear you, and I know days like this can feel heavy. Here are some comforting and heartfelt books from our shelves:"
    },
    "anger": {
        "description": "Calm, patient, validating, respectful, and direct tone.",
        "prefix": "I completely understand your frustration. Let's find exactly what you're looking for right now:"
    },
    "fear": {
        "description": "Reassuring, calming, steady, and protective tone.",
        "prefix": "It's completely okay to feel anxious. Here are some grounded, calming reads from our catalog:"
    },
    "joy": {
        "description": "Energetic, enthusiastic, celebratory, and vibrant tone.",
        "prefix": "That sounds fantastic! I love that energy — here are some exhilarating reads from our collection:"
    },
    "curiosity": {
        "description": "Scholarly, insightful, intellectually stimulating, and articulate tone.",
        "prefix": "A wonderful subject to delve into! Here are stellar selections from the library collection matching your inquiry:"
    },
    "neutral": {
        "description": "Polite, helpful, concise, and academic library tone.",
        "prefix": "Here are books from our library catalog matching your request:"
    }
}

def detect_emotion(text: str) -> Tuple[str, float]:
    text_lower = text.lower()

    frustration_cues = [
        "not what i", "giving me from recommendation", "i am searching and",
        "i want the one", "not what i asked", "didn't ask for", "dont want random",
        "wrong book", "wrong recommendation", "frustrated", "annoyed", "stop recommending",
        "i told you", "i was asking for", "listen to me", "i asked about", "i am asking about",
        "instead of recommendations", "not recommendations", "give me what i searched",
        "which i am searching", "in which i am interested"
    ]
    if any(c in text_lower for c in frustration_cues):
        return "frustration", 0.95

    relief_cues = [
        "tired", "relief", "relieve", "relax", "relaxing", "exhausted", "burnout",
        "unwind", "calm me", "cozy", "comfort", "uplifting", "cheer me up", "soothing",
        "bad day", "hard day", "long day", "peaceful"
    ]
    if any(w in text_lower for w in relief_cues):
        return "comfort_relief", 0.95

    if any(w in text_lower for w in ["horror", "scary", "spooky", "creepy", "ghost", "vampire", "dracula", "stephen king", "gore", "slasher", "haunted", "dread", "terror", "nightmare", "chilling", "underworld", "lovecraft", "poe"]):
        return "horror_thrill", 0.95

    if any(w in text_lower for w in ["sad", "depressed", "unhappy", "down", "lonely", "grief", "awful", "heartbroken", "crying", "miserable"]):
        return "sadness", 0.95

    if any(w in text_lower for w in ["angry", "mad", "upset", "irritated", "furious", "hate", "terrible", "worst"]):
        return "anger", 0.90

    if any(w in text_lower for w in ["anxious", "scared", "fear", "worried", "nervous", "panic", "overwhelmed"]):
        return "fear", 0.88

    if any(w in text_lower for w in ["happy", "excited", "joy", "cheerful", "great", "awesome", "loved", "delighted", "wonderful", "amazing", "fun", "thrilled"]):
        return "joy", 0.90

    if any(w in text_lower for w in ["wonder", "curious", "recommend", "explore", "discover", "interesting", "fantasy", "mystery", "sci-fi", "philosophy", "science", "history", "movie", "cinema", "harry potter"]):
        return "curiosity", 0.85

    return "neutral", 0.70

# --------------------------------------------------
# 4. In-Memory Session Storage
# --------------------------------------------------

class SessionStore:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "history": [],
                "last_recommended": [],
                "all_recommended_titles": set(),
            }
        return self._sessions[session_id]

    def reset_session(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

session_store = SessionStore()

# --------------------------------------------------
# 5. Database Search with Smart Query Expansion
# --------------------------------------------------

HORROR_AUTHORS = {
    "stephen king", "h. p. lovecraft", "h.p. lovecraft", "howard phillips lovecraft",
    "edgar allan poe", "susan hill", "douglas clegg", "graham masterton",
    "john saul", "dean ray koontz", "dean koontz", "greg cox", "bram stoker", "mary shelley"
}

COMFORT_POSITIVE_KEYWORDS = [
    "humor", "comedy", "funny", "travel", "adventure", "uplifting", "calm",
    "peaceful", "delightful", "charming", "witty", "breezy", "cozy", "warm", "nature"
]

COMFORT_EXCLUDED_CATEGORIES = [
    "death", "grief", "tragedy", "war", "murder", "violence", "suicide", "horror"
]

def db_search_books(
    db: Session,
    query: str,
    top_k: int = 4,
    exclude_titles: Set[str] | None = None,
    only_available: bool = True,
) -> List[Dict[str, Any]]:
    """
    Search library catalog using multi-token expansion, category, author, and thematic matching.
    Only returns books strictly relevant to the query and currently available in stock.
    """
    exclude_titles = exclude_titles or set()
    cleaned_query = query.strip()
    raw_tokens = clean_and_expand_query(cleaned_query)
    
    meaningful_tokens = [t for t in raw_tokens if len(t) >= 3 or t.upper() in {"AI", "CS", "IT", "GO", "C#", "C", "R", "DB"}]
    if not meaningful_tokens and len(cleaned_query) >= 2:
        meaningful_tokens = [cleaned_query.lower()]

    if not meaningful_tokens:
        return []

    is_horror_query = any(t in ["horror", "terror", "creepy", "scary", "spooky", "vampire", "dracula", "ghost", "haunted", "slasher", "king", "lovecraft", "poe"] for t in meaningful_tokens) or \
                      any(w in cleaned_query.lower() for w in ["horror", "scary", "spooky", "creepy", "ghost", "vampire", "dracula", "stephen king", "slasher", "movie", "movies"])

    is_comfort_query = any(w in cleaned_query.lower() for w in ["tired", "relief", "relieve", "relax", "comfort", "unwind", "sooth", "calm", "cozy", "uplifting", "cheer", "exhausted", "gentle"])

    # 1. Author and Title conditions
    author_title_conds = []
    for t in meaningful_tokens:
        pat = f"%{t}%"
        author_title_conds.append(Book.authors.ilike(pat))
        author_title_conds.append(Book.title.ilike(pat))

    # 2. General matching on categories, subtitle, description
    general_conds = []
    for t in meaningful_tokens:
        pat = f"%{t}%"
        general_conds.append(Book.categories.ilike(pat))
        general_conds.append(Book.subtitle.ilike(pat))
        if len(t) >= 4:
            general_conds.append(Book.description.ilike(pat))

    if is_horror_query:
        general_conds.extend([
            Book.categories.ilike("%horror%"),
            Book.categories.ilike("%thriller%"),
            Book.description.ilike("%horror%"),
            Book.description.ilike("%scary%"),
            Book.description.ilike("%terror%"),
        ])

    if is_comfort_query:
        for kw in COMFORT_POSITIVE_KEYWORDS:
            general_conds.append(Book.categories.ilike(f"%{kw}%"))
            general_conds.append(Book.description.ilike(f"%{kw}%"))

    all_conds = author_title_conds + general_conds
    if not all_conds:
        all_conds = [Book.title.ilike(f"%{cleaned_query}%")]

    stmt = (
        select(Book)
        .where(or_(*all_conds))
        .order_by(
            Book.average_rating.desc().nullslast(),
            Book.ratings_count.desc().nullslast()
        )
        .limit(top_k * 4 + len(exclude_titles) + 15)
    )
    all_matches = db.scalars(stmt).all()

    # Fast batch fetch active loans and earliest return dates in 1 single query
    isbns = [b.isbn10 for b in all_matches if b.isbn10]
    active_counts: Dict[str, int] = {}
    due_dates: Dict[str, str] = {}
    if isbns:
        from app.models.borrow import BorrowTransaction
        from sqlalchemy import func
        batch_stmt = select(
            BorrowTransaction.isbn10,
            func.count(BorrowTransaction.id),
            func.min(BorrowTransaction.due_date)
        ).where(
            BorrowTransaction.isbn10.in_(isbns),
            BorrowTransaction.status == "active"
        ).group_by(BorrowTransaction.isbn10)
        for r_isbn, cnt, min_due in db.execute(batch_stmt):
            active_counts[r_isbn] = cnt or 0
            if min_due:
                due_dates[r_isbn] = min_due.isoformat()

    scored_matches = []
    for b in all_matches:
        if b.title in exclude_titles:
            continue
        total = b.total_copies if (b.total_copies is not None) else 5
        active = active_counts.get(b.isbn10, 0)
        avail = max(0, total - active)
        is_avail = avail > 0
        exp_date = due_dates.get(b.isbn10) if not is_avail else None

        if only_available and not is_avail:
            continue

        b_author = (b.authors or "").lower()
        b_title = (b.title or "").lower()
        b_desc = (b.description or "").lower()
        b_cat = (b.categories or "").lower()

        if is_comfort_query:
            if any(ex in b_cat for ex in COMFORT_EXCLUDED_CATEGORIES) or any(ex in b_title for ex in ["death", "dead", "grief", "dying", "murder", "suicide"]):
                continue

        score = 0
        for t in meaningful_tokens:
            t_low = t.lower()
            if t_low in b_title:
                score += 35
                if b_title.startswith(t_low) or f" {t_low} " in f" {b_title} ":
                    score += 25
            if t_low in b_author:
                score += 30
                if f" {t_low} " in f" {b_author} " or b_author.startswith(t_low):
                    score += 20
            if t_low in b_cat:
                score += 20
            if len(t_low) >= 4 and t_low in b_desc:
                score += 5

        if is_horror_query:
            if any(ha in b_author for ha in HORROR_AUTHORS):
                score += 30
            if "horror" in b_cat or "horror tales" in b_cat:
                score += 25
            if "horror" in b_desc or "terror" in b_desc or "vampire" in b_desc:
                score += 15

        if is_comfort_query:
            if any(pos in b_cat for pos in ["humor", "travel", "adventure", "self-help", "lifestyle", "nature"]):
                score += 30
            if any(pos in b_desc for pos in ["humor", "witty", "heartwarming", "uplifting", "gentle", "charming", "laugh", "nature"]):
                score += 20

        # Only accept books with genuine token match or thematic match
        if score >= 15 or is_horror_query or is_comfort_query:
            scored_matches.append((score, b, total, avail, is_avail, exp_date))

    scored_matches.sort(key=lambda x: x[0], reverse=True)

    results = []
    for _, b, total, avail, is_avail, exp_date in scored_matches:
        item = {
            "isbn10": b.isbn10,
            "title": b.title,
            "authors": b.authors or "Unknown Author",
            "categories": b.categories or "General",
            "description": b.description or "No description available in catalog.",
            "thumbnail": b.thumbnail,
            "average_rating": float(b.average_rating) if b.average_rating is not None else None,
            "published_year": b.published_year,
            "num_pages": b.num_pages,
            "total_copies": total,
            "copies_available": avail,
            "is_available": is_avail,
            "expected_return_date": exp_date,
        }
        results.append(item)
        if len(results) >= top_k:
            break

    return results

def db_get_book_description(db: Session, title: str) -> Dict[str, Any]:
    cleaned_title = title.strip()
    if not cleaned_title:
        return {"error": "No title provided"}
    stmt = select(Book).where(Book.title.ilike(f"%{cleaned_title}%")).limit(1)
    book = db.scalar(stmt)
    if not book:
        return {"error": f"Book '{title}' not found in library catalog"}

    total, avail, is_avail = get_simulated_availability(book.isbn10, book.title, db=db)
    return {
        "isbn10": book.isbn10,
        "title": book.title,
        "authors": book.authors or "Unknown Author",
        "categories": book.categories or "General",
        "description": book.description or "No description available in catalog.",
        "thumbnail": book.thumbnail,
        "average_rating": float(book.average_rating) if book.average_rating is not None else None,
        "total_copies": total,
        "copies_available": avail,
        "is_available": is_avail,
        "expected_return_date": get_expected_return_date(book.isbn10, db=db) if (not is_avail or avail == 0) else None,
    }

def db_get_multiple_availability(db: Session, titles: List[str]) -> List[Dict[str, Any]]:
    results = []
    for t in titles:
        if not t.strip():
            continue
        stmt = select(Book).where(Book.title.ilike(f"%{t.strip()}%")).limit(1)
        b = db.scalar(stmt)
        if not b:
            results.append({"title": t, "error": "Not found in library catalog", "is_available": False})
        else:
            total, avail, is_avail = get_simulated_availability(b.isbn10, b.title, db=db)
            results.append({
                "isbn10": b.isbn10,
                "title": b.title,
                "copies_available": avail,
                "total_copies": total,
                "is_available": is_avail,
                "expected_return_date": get_expected_return_date(b.isbn10, db=db) if (not is_avail or avail == 0) else None,
            })
    return results

def db_get_recent_recommendations(db: Session, session_id: str) -> List[Dict[str, Any]]:
    session = session_store.get_session(session_id)
    titles = session["last_recommended"]
    if not titles:
        return [{"error": "No books have been recommended yet in this conversation"}]

    results = []
    for t in titles:
        stmt = select(Book).where(Book.title.ilike(f"%{t.strip()}%")).limit(1)
        b = db.scalar(stmt)
        if b:
            total, avail, is_avail = get_simulated_availability(b.isbn10, b.title, db=db)
            results.append({
                "isbn10": b.isbn10,
                "title": b.title,
                "authors": b.authors or "Unknown Author",
                "categories": b.categories or "General",
                "description": b.description or "No summary available",
                "thumbnail": b.thumbnail,
                "average_rating": float(b.average_rating) if b.average_rating is not None else None,
                "total_copies": total,
                "copies_available": avail,
                "is_available": is_avail,
                "expected_return_date": get_expected_return_date(b.isbn10, db=db) if (not is_avail or avail == 0) else None,
            })
    return results

# --------------------------------------------------
# 6. Helper: Match Only Mentioned Books in Output
# --------------------------------------------------

def _is_title_mentioned_in_answer(title: str, answer: str) -> bool:
    if not title or not answer:
        return False

    clean_title = title.strip()
    title_escaped = re.escape(clean_title)
    if re.search(rf"\*\*{title_escaped}\*\*", answer, re.IGNORECASE):
        return True

    main_title = re.split(r"[:\—\-\(\[]", clean_title)[0].strip()
    if main_title and len(main_title) >= 3:
        main_escaped = re.escape(main_title)
        if re.search(rf"\*\*{main_escaped}\*\*", answer, re.IGNORECASE):
            return True
        if len(main_title) >= 4 or " " in main_title:
            if re.search(rf"\b{main_escaped}\b", answer, re.IGNORECASE):
                return True

    if len(clean_title) >= 4 or " " in clean_title:
        if re.search(rf"\b{title_escaped}\b", answer, re.IGNORECASE):
            return True

    return False

def _filter_suggested_books_to_mentioned(answer: str, candidate_books: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not candidate_books or not answer:
        return []

    matched: List[Dict[str, Any]] = []
    seen = set()

    for b in candidate_books:
        title = b.get("title", "")
        if not b.get("is_available") or (b.get("copies_available") or 0) <= 0:
            continue
        if not title or title in seen:
            continue
        if _is_title_mentioned_in_answer(title, answer):
            seen.add(title)
            matched.append(b)

    # If LLM gave a targeted response but title casing/formatting didn't match regex exactly,
    # include candidate books if length is small (<= 3) and relevant
    if not matched and len(candidate_books) <= 3 and any(k in answer.lower() for k in ["recommend", "catalog", "book", "available", "shelf", "read"]):
        for b in candidate_books:
            if b.get("is_available") and (b.get("copies_available") or 0) > 0 and b.get("title") not in seen:
                seen.add(b["title"])
                matched.append(b)

    return matched

# --------------------------------------------------
# 7. RAG LLM Assistant
# --------------------------------------------------

class LLMAssistant:
    def __init__(self):
        settings = get_settings()
        api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
        self.client = None
        if Groq and api_key:
            try:
                self.client = Groq(api_key=api_key)
            except Exception as e:
                print(f"Warning: Could not initialize Groq client: {e}")

    def _get_client(self):
        if not self.client and Groq:
            settings = get_settings()
            api_key = settings.GROQ_API_KEY or os.environ.get("GROQ_API_KEY", "")
            if api_key:
                try:
                    self.client = Groq(api_key=api_key)
                except Exception as e:
                    print(f"Groq re-init error: {e}")
        return self.client

    def process_chat(self, db: Session, user_query: str, session_id: str = "demo_user") -> Dict[str, Any]:
        session = session_store.get_session(session_id)
        user_query_clean = user_query.strip()

        # 1. Hard Safety Guardrail Check
        if contains_unsafe_request(user_query_clean):
            session["history"].append({"user": user_query_clean, "assistant": CRISIS_MESSAGE})
            return {
                "response": CRISIS_MESSAGE,
                "emotion": "fear",
                "suggested_books": [],
            }

        # 2. Greeting / Conversational Start Check
        if is_greeting(user_query_clean):
            session["history"].append({"user": user_query_clean, "assistant": GREETING_WELCOME_MESSAGE})
            return {
                "response": GREETING_WELCOME_MESSAGE,
                "emotion": "neutral",
                "suggested_books": [],
            }

        # 3. Pure Acknowledgment Check
        if is_pure_acknowledgment(user_query_clean):
            ack_msg = "You're very welcome! Let me know if you want to explore more titles, delve deeper into a plot, or search another genre!"
            session["history"].append({"user": user_query_clean, "assistant": ack_msg})
            return {
                "response": ack_msg,
                "emotion": "neutral",
                "suggested_books": [],
            }

        # 4. Emotion & Tone Detection
        emotion, confidence = detect_emotion(user_query_clean)
        
        answer = ""
        suggested_books_list: List[Dict[str, Any]] = []

        client = self._get_client()
        if client:
            try:
                answer, suggested_books_list = self._execute_rag_flow(
                    client=client,
                    db=db,
                    user_query=user_query_clean,
                    emotion=emotion,
                    confidence=confidence,
                    session=session,
                    session_id=session_id,
                )
            except Exception as e:
                print(f"Groq RAG execution error: {e}")
                answer = ""

        # 5. Local RAG Fallback
        if not answer:
            answer, suggested_books_list = self._generate_resilient_rag_response(
                db=db,
                user_query=user_query_clean,
                emotion=emotion,
                confidence=confidence,
                session=session,
                session_id=session_id,
            )

        if "<function=" in answer or "<function =" in answer:
            answer = "I've searched our library catalog for you. Here are available books matching your interest!"

        session["history"].append({"user": user_query_clean, "assistant": answer})

        return {
            "response": answer,
            "emotion": emotion,
            "suggested_books": suggested_books_list,
        }

    def _call_groq(
        self,
        client: Any,
        messages: List[Dict[str, str]],
        response_format: Any = None,
        max_tokens: int = 600,
        temperature: float = 0.3,
    ) -> str:
        candidate_models = [
            "openai/gpt-oss-120b",
            "groq/compound-mini",
            "allam-2-7b",
            "qwen/qwen3.6-27b",
        ]
        last_err = None
        for model_name in candidate_models:
            try:
                kwargs: Dict[str, Any] = {
                    "model": model_name,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                }
                if response_format:
                    kwargs["response_format"] = response_format

                res = client.chat.completions.create(**kwargs)
                content = res.choices[0].message.content or ""
                # Strip out any reasoning or thinking artifacts
                content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                if content:
                    return content
            except Exception as e:
                last_err = e
                continue
        raise last_err or RuntimeError("All Groq candidate models failed")

    def _execute_rag_flow(
        self,
        client: Any,
        db: Session,
        user_query: str,
        emotion: str,
        confidence: float,
        session: Dict[str, Any],
        session_id: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        # Fast lightweight intent classifier in Python (0 LLM overhead, avoids rate limits & minimizes latency)
        q_lower = user_query.lower().strip()
        candidate_books: List[Dict[str, Any]] = []
        tool_name = "search_books"
        tool_result: Any = None

        if any(w in q_lower for w in ["these", "this one", "first one", "second one", "which of these", "tell me more about this"]):
            res_books = db_get_recent_recommendations(db, session_id)
            tool_result = res_books
            candidate_books = [b for b in res_books if "error" not in b]
            tool_name = "get_recent_recommendations"
        elif any(q_lower.startswith(p) for p in ["what is the plot of", "tell me about the book", "summary of", "synopsis of"]):
            clean_title = re.sub(r"^(what is the plot of|tell me about the book|summary of|synopsis of)\s*", "", q_lower, flags=re.IGNORECASE).strip()
            b = db_get_book_description(db, clean_title or user_query)
            tool_result = b
            if "title" in b and "error" not in b:
                candidate_books = [b]
            tool_name = "get_book_description"
        else:
            # Direct catalog semantic/token search
            res_books = db_search_books(db, user_query, top_k=4, exclude_titles=session["all_recommended_titles"], only_available=False)
            tool_result = res_books
            candidate_books = res_books
            tool_name = "search_books"

        tone_info = EMOTION_TONE_GUIDE.get(emotion, EMOTION_TONE_GUIDE["neutral"])
        gen_system = f"""You are the official University Library AI Assistant, designed to feel intelligent, articulate, warm, and helpful like ChatGPT.

CONVERSATION & TONE GUIDELINES:
- User Emotion / Mood: **{emotion}**
- Communication Style: **{tone_info['description']}**
- Speak naturally and engagingly. Structure recommendations with clean Markdown formatting (bullet points, clear paragraphs, **bold** book titles).
- When a book is available, highlight its available copies in our live inventory.
- When a book is checked out / out of stock, clearly inform the user of its **estimated return date / expected timing** (from the Catalog Data).
- If the user asks general or academic questions, provide informative, well-rounded answers and suggest relevant reading material from our collection.
- Never make up fictitious books not present in the Catalog Data when making specific library recommendations.

Catalog Data:
{json.dumps(tool_result, indent=2, default=str)}
"""
        history_messages = []
        for t in session["history"][-3:]:
            history_messages.append({"role": "user", "content": t["user"]})
            history_messages.append({"role": "assistant", "content": t["assistant"]})

        answer = self._call_groq(
            client=client,
            messages=[
                {"role": "system", "content": gen_system},
                *history_messages,
                {"role": "user", "content": user_query}
            ],
            temperature=0.4,
            max_tokens=600,
        )
        final_suggested_books = _filter_suggested_books_to_mentioned(answer, candidate_books)

        round_titles = [b["title"] for b in final_suggested_books if "title" in b]
        if round_titles:
            session["last_recommended"] = round_titles
            session["all_recommended_titles"].update(round_titles)
        elif candidate_books and tool_name == "search_books":
            session["last_recommended"] = [b["title"] for b in candidate_books[:3]]
            session["all_recommended_titles"].update([b["title"] for b in candidate_books[:3]])

        return answer, final_suggested_books

    def stream_chat(
        self,
        db: Session,
        user_query: str,
        session_id: str = "demo_user",
    ):
        """
        Yields Server-Sent Event (SSE) formatted text chunks for real-time ChatGPT streaming,
        followed by a final JSON payload containing suggested_books, emotion, and done flag.
        """
        session = session_store.get_session(session_id)
        user_query_clean = user_query.strip()

        # Hard safety
        if contains_unsafe_request(user_query_clean):
            yield f"data: {json.dumps({'type': 'token', 'token': CRISIS_MESSAGE})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'emotion': 'fear', 'suggested_books': []})}\n\n"
            return

        # Greeting check
        if is_greeting(user_query_clean):
            yield f"data: {json.dumps({'type': 'token', 'token': GREETING_WELCOME_MESSAGE})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'emotion': 'neutral', 'suggested_books': []})}\n\n"
            return

        # Acknowledgment check
        if is_pure_acknowledgment(user_query_clean):
            ack_msg = "You're very welcome! Let me know if you want to explore more titles, delve deeper into a plot, or search another genre!"
            yield f"data: {json.dumps({'type': 'token', 'token': ack_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'emotion': 'neutral', 'suggested_books': []})}\n\n"
            return

        emotion, confidence = detect_emotion(user_query_clean)
        client = self._get_client()

        if not client:
            # Fallback to local RAG
            answer, suggested = self._generate_resilient_rag_response(
                db=db,
                user_query=user_query_clean,
                emotion=emotion,
                confidence=confidence,
                session=session,
                session_id=session_id,
            )
            yield f"data: {json.dumps({'type': 'token', 'token': answer})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'emotion': emotion, 'suggested_books': suggested})}\n\n"
            return

        # Fast candidate catalog query
        q_lower = user_query_clean.lower()
        if any(w in q_lower for w in ["these", "this one", "first one", "second one"]):
            res_books = db_get_recent_recommendations(db, session_id)
            tool_result = res_books
            candidate_books = [b for b in res_books if "error" not in b]
        elif any(q_lower.startswith(p) for p in ["what is the plot of", "tell me about the book", "summary of", "synopsis of"]):
            clean_title = re.sub(r"^(what is the plot of|tell me about the book|summary of|synopsis of)\s*", "", q_lower, flags=re.IGNORECASE).strip()
            b = db_get_book_description(db, clean_title or user_query_clean)
            tool_result = b
            candidate_books = [b] if ("title" in b and "error" not in b) else []
        else:
            res_books = db_search_books(db, user_query_clean, top_k=4, exclude_titles=session["all_recommended_titles"], only_available=False)
            tool_result = res_books
            candidate_books = res_books

        tone_info = EMOTION_TONE_GUIDE.get(emotion, EMOTION_TONE_GUIDE["neutral"])
        gen_system = f"""You are the official University Library AI Assistant, designed to feel intelligent, articulate, warm, and helpful like ChatGPT.

CONVERSATION & TONE GUIDELINES:
- User Emotion / Mood: **{emotion}**
- Communication Style: **{tone_info['description']}**
- Speak naturally and engagingly. Structure recommendations with clean Markdown formatting (bullet points, clear paragraphs, **bold** book titles).
- When a book is available, highlight its available copies in our live inventory.
- When a book is checked out / out of stock, clearly inform the user of its **estimated return date / expected timing** (from the Catalog Data).
- If the user asks general or academic questions, provide informative, well-rounded answers and suggest relevant reading material from our collection.
- Never make up fictitious books not present in the Catalog Data when making specific library recommendations.

Catalog Data:
{json.dumps(tool_result, indent=2, default=str)}
"""
        history_messages = []
        for t in session["history"][-3:]:
            history_messages.append({"role": "user", "content": t["user"]})
            history_messages.append({"role": "assistant", "content": t["assistant"]})

        candidate_models = ["openai/gpt-oss-120b", "groq/compound-mini", "allam-2-7b", "qwen/qwen3.6-27b"]
        full_response = ""
        stream_success = False

        for model_name in candidate_models:
            try:
                stream = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": gen_system},
                        *history_messages,
                        {"role": "user", "content": user_query_clean}
                    ],
                    stream=True,
                    temperature=0.4,
                    max_tokens=600,
                )
                in_think = False
                for chunk in stream:
                    delta = chunk.choices[0].delta.content or ""
                    if "<think>" in delta:
                        in_think = True
                        continue
                    if "</think>" in delta:
                        in_think = False
                        continue
                    if in_think:
                        continue
                    if delta:
                        full_response += delta
                        yield f"data: {json.dumps({'type': 'token', 'token': delta})}\n\n"
                stream_success = True
                break
            except Exception as e:
                print(f"Streaming error on {model_name}: {e}")
                continue

        if not stream_success or not full_response:
            answer, suggested = self._generate_resilient_rag_response(
                db=db,
                user_query=user_query_clean,
                emotion=emotion,
                confidence=confidence,
                session=session,
                session_id=session_id,
            )
            full_response = answer
            final_suggested = suggested
            yield f"data: {json.dumps({'type': 'token', 'token': answer})}\n\n"
        else:
            final_suggested = _filter_suggested_books_to_mentioned(full_response, candidate_books)
            round_titles = [b["title"] for b in final_suggested if "title" in b]
            if round_titles:
                session["last_recommended"] = round_titles
                session["all_recommended_titles"].update(round_titles)
            elif candidate_books:
                session["last_recommended"] = [b["title"] for b in candidate_books[:3]]
                session["all_recommended_titles"].update([b["title"] for b in candidate_books[:3]])

        session["history"].append({"user": user_query_clean, "assistant": full_response})
        yield f"data: {json.dumps({'type': 'done', 'emotion': emotion, 'suggested_books': final_suggested, 'full_text': full_response})}\n\n"

    def _generate_resilient_rag_response(
        self,
        db: Session,
        user_query: str,
        emotion: str,
        confidence: float,
        session: Dict[str, Any],
        session_id: str,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        if is_greeting(user_query):
            return GREETING_WELCOME_MESSAGE, []

        tone_info = EMOTION_TONE_GUIDE.get(emotion, EMOTION_TONE_GUIDE["neutral"])
        prefix = tone_info["prefix"]

        lower_q = user_query.lower()
        if any(w in lower_q for w in ["these", "this", "which one", "from this", "first one", "second one"]):
            recent_books = db_get_recent_recommendations(db, session_id)
            valid_recent = [b for b in recent_books if "error" not in b and b.get("is_available")]
            if valid_recent:
                best = valid_recent[0]
                desc = best.get("description", "A compelling title in our catalog.")
                avail_str = f"{best.get('copies_available', 1)} copy available"
                return (
                    f"{prefix}\n\nFrom the books we just discussed, I recommend **{best['title']}** by {best.get('authors', 'Unknown Author')}.\n\n"
                    f"**Synopsis:** {desc[:250]}...\n\n"
                    f"**Status:** {avail_str} in our library stacks.",
                    [best]
                )

        matches = db_search_books(db, user_query, top_k=3, exclude_titles=session["all_recommended_titles"], only_available=True)
        if not matches:
            return (
                "I couldn't find any books in our catalog directly matching that description. "
                "You can search by book title, author, or broad genres like Fiction, Mystery, Science Fiction, History, or Business!",
                []
            )

        round_titles = [m["title"] for m in matches]
        if round_titles:
            session["last_recommended"] = round_titles
            session["all_recommended_titles"].update(round_titles)

        book_lines = []
        for idx, b in enumerate(matches, 1):
            avail_badge = f"{b['copies_available']} copy/copies available"
            author_str = b.get("authors", "Unknown Author")
            cat_str = b.get("categories", "General")
            desc_snippet = (b.get("description") or "")[:120]
            if desc_snippet:
                desc_snippet = f"\n   • *{desc_snippet}...*"
            book_lines.append(
                f"{idx}. **{b['title']}** by *{author_str}* — `{cat_str}`\n"
                f"   • Status: **{avail_badge}** | ⭐ Rating: {b['average_rating'] or 'N/A'}"
                f"{desc_snippet}"
            )

        response_body = (
            f"{prefix}\n\n"
            + "\n\n".join(book_lines)
            + "\n\nWould you like to explore the plot or themes of any of these titles?"
        )
        return response_body, matches

llm_assistant = LLMAssistant()
