from __future__ import annotations

import re
from typing import Sequence, Set, Dict, List, Tuple
from collections import Counter
import numpy as np
import pandas as pd
from scipy.sparse import csr_matrix
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import Session

from app.core.inventory import get_simulated_availability
from app.models import Book, Rating, User, UserInteraction
from app.schemas.book import BookResponse
from app.services.book_service import clean_and_expand_query

def _to_book_response(b: Book, db: Session | None = None) -> BookResponse:
    total, avail, is_avail = get_simulated_availability(b.isbn10, b.title, db=db)
    res = BookResponse.model_validate(b)
    res.total_copies = total
    res.copies_available = avail
    res.is_available = is_avail
    return res


import time

_CF_CACHE: dict[str, Any] = {
    "timestamp": 0.0,
    "user2idx": {},
    "isbn2idx": {},
    "idx2isbn": {},
    "R": None,
    "R_centered": None,
    "user_means": None,
}

def _get_cf_model(db: Session, ttl: float = 300.0) -> dict[str, Any] | None:
    global _CF_CACHE
    now = time.time()
    if _CF_CACHE["R"] is not None and (now - _CF_CACHE["timestamp"]) < ttl:
        return _CF_CACHE

    stmt = select(Rating.roll_number, Rating.isbn10, Rating.rating).where(Rating.rating >= 1)
    ratings_data = db.execute(stmt).all()
    if not ratings_data:
        return None

    df = pd.DataFrame(ratings_data, columns=["user_id", "isbn10", "rating"])
    user_ids = df["user_id"].unique()
    isbns = df["isbn10"].unique()

    user2idx = {u: i for i, u in enumerate(user_ids)}
    isbn2idx = {b: i for i, b in enumerate(isbns)}
    idx2isbn = {i: b for b, i in isbn2idx.items()}

    num_users = len(user_ids)
    num_isbns = len(isbns)

    row_indices = df["user_id"].map(user2idx).values
    col_indices = df["isbn10"].map(isbn2idx).values
    data = df["rating"].values.astype(np.float64)

    R = csr_matrix((data, (row_indices, col_indices)), shape=(num_users, num_isbns)).toarray()
    R_centered = np.zeros_like(R, dtype=np.float64)
    user_means = np.zeros(num_users, dtype=np.float64)

    for u in range(num_users):
        rated_indices = R[u] > 0
        if np.any(rated_indices):
            mean_val = np.mean(R[u, rated_indices])
            user_means[u] = mean_val
            R_centered[u, rated_indices] = R[u, rated_indices] - mean_val

    _CF_CACHE = {
        "timestamp": now,
        "user2idx": user2idx,
        "isbn2idx": isbn2idx,
        "idx2isbn": idx2isbn,
        "R": R,
        "R_centered": R_centered,
        "user_means": user_means,
    }
    return _CF_CACHE


class MultiSignalRecommendationEngine:

    """
    High-Dynamic Multi-Signal Hybrid Recommendation Engine.
    Instantly and noticeably adapts recommendations across:
    1. Search History (Queries, Keywords, Target Authors & Genres)
    2. Chatbot Consultation Topics & AI-Suggested Books
    3. User Ratings (High Ratings Boosts, Low Ratings Penalties, CF Cosine Similarity)
    4. Clicked & Explored Catalog Books
    5. Contextual Thematic Top-up from Preferred Genres/Authors
    6. Strict Real-Time Library Inventory Verification
    """

    def recommend_for_user(
        self,
        db: Session,
        roll_number: str,
        top_n: int = 12,
        k_neighbors: int = 20,
    ) -> list[BookResponse]:
        book_scores: dict[str, float] = {}
        already_interacted_isbns: set[str] = set()

        fav_authors: Counter = Counter()
        fav_categories: Counter = Counter()
        disliked_authors: set[str] = set()
        disliked_categories: set[str] = set()

        # -------------------------------------------------------------
        # 1. Gather User Explicit Ratings
        # -------------------------------------------------------------
        user_ratings = db.scalars(
            select(Rating).where(Rating.roll_number == roll_number)
        ).all()

        liked_isbns = set()
        disliked_isbns = set()
        for r in user_ratings:
            already_interacted_isbns.add(r.isbn10)
            if r.rating >= 4:
                liked_isbns.add(r.isbn10)
            elif r.rating <= 2:
                disliked_isbns.add(r.isbn10)

        # -------------------------------------------------------------
        # 2. Gather User Interaction History (Searches, Chats, Views)
        # -------------------------------------------------------------
        interactions = db.scalars(
            select(UserInteraction)
            .where(UserInteraction.roll_number == roll_number)
            .order_by(desc(UserInteraction.created_at))
            .limit(50)
        ).all()

        explored_isbns: list[str] = []
        search_queries: list[str] = []
        chat_queries: list[str] = []
        chat_suggested_isbns: list[str] = []

        for inter in interactions:
            if inter.isbn10:
                if inter.interaction_type in ["view", "explore"]:
                    explored_isbns.append(inter.isbn10)
                    already_interacted_isbns.add(inter.isbn10)
                elif inter.interaction_type == "chat_suggested":
                    chat_suggested_isbns.append(inter.isbn10)

            if inter.interaction_type == "search" and inter.content:
                search_queries.append(inter.content.strip())
            elif inter.interaction_type == "chat" and inter.content:
                chat_queries.append(inter.content.strip())

        # -------------------------------------------------------------
        # 3. Collaborative Filtering Predictions (for Rated Users)
        # -------------------------------------------------------------
        if user_ratings:
            cf_predictions = self._compute_cf_predictions(db, roll_number, k_neighbors=k_neighbors)
            for isbn, score in cf_predictions:
                if isbn not in already_interacted_isbns:
                    book_scores[isbn] = book_scores.get(isbn, 0.0) + (score * 15.0)


        # -------------------------------------------------------------
        # 4. Process Liked & Disliked Rated Books
        # -------------------------------------------------------------
        if liked_isbns:
            liked_books = db.scalars(
                select(Book).where(Book.isbn10.in_(list(liked_isbns)))
            ).all()
            for b in liked_books:
                if b.authors:
                    fav_authors[b.authors.strip().lower()] += 12
                    author_matched = db.scalars(
                        select(Book.isbn10).where(Book.authors.ilike(f"%{b.authors.strip()}%")).limit(15)
                    ).all()
                    for aisbn in author_matched:
                        if aisbn not in already_interacted_isbns:
                            book_scores[aisbn] = book_scores.get(aisbn, 0.0) + 120.0

                if b.categories:
                    for cat in b.categories.split(","):
                        cat_clean = cat.strip().lower()
                        if cat_clean:
                            fav_categories[cat_clean] += 10
                            # Boost books in same category
                            cat_matched = db.scalars(
                                select(Book.isbn10).where(Book.categories.ilike(f"%{cat.strip()}%")).limit(15)
                            ).all()
                            for cisbn in cat_matched:
                                if cisbn not in already_interacted_isbns:
                                    book_scores[cisbn] = book_scores.get(cisbn, 0.0) + 70.0

        if disliked_isbns:
            disliked_books = db.scalars(
                select(Book).where(Book.isbn10.in_(list(disliked_isbns)))
            ).all()
            for b in disliked_books:
                if b.authors:
                    disliked_authors.add(b.authors.strip().lower())
                if b.categories:
                    for cat in b.categories.split(","):
                        cat_clean = cat.strip().lower()
                        if cat_clean:
                            disliked_categories.add(cat_clean)

        # -------------------------------------------------------------
        # 5. Process Explored & Chat-Suggested Books
        # -------------------------------------------------------------
        all_interested_isbns = explored_isbns[:20] + chat_suggested_isbns[:20]
        if all_interested_isbns:
            interested_books = db.scalars(
                select(Book).where(Book.isbn10.in_(all_interested_isbns))
            ).all()
            for b in interested_books:
                if b.authors:
                    fav_authors[b.authors.strip().lower()] += 6
                    # Boost related works by author
                    rel_author = db.scalars(
                        select(Book.isbn10).where(Book.authors.ilike(f"%{b.authors.strip()}%")).limit(10)
                    ).all()
                    for aisbn in rel_author:
                        if aisbn not in already_interacted_isbns:
                            book_scores[aisbn] = book_scores.get(aisbn, 0.0) + 60.0

                if b.categories:
                    for cat in b.categories.split(","):
                        cat_clean = cat.strip().lower()
                        if cat_clean:
                            fav_categories[cat_clean] += 5
                            # Boost related works in category
                            rel_cat = db.scalars(
                                select(Book.isbn10).where(Book.categories.ilike(f"%{cat.strip()}%")).limit(12)
                            ).all()
                            for cisbn in rel_cat:
                                if cisbn not in already_interacted_isbns:
                                    book_scores[cisbn] = book_scores.get(cisbn, 0.0) + 40.0

        # -------------------------------------------------------------
        # 6. Deep Search & Chat Queries Expansion (Instant Adaptation)
        # -------------------------------------------------------------
        all_text_queries = search_queries + chat_queries
        for idx, raw_query in enumerate(all_text_queries[:15]):
            recency_weight = max(1.0, 3.5 - (idx * 0.2))
            tokens = clean_and_expand_query(raw_query)
            if not tokens:
                continue

            # Prioritize matching title, author, or category (strict matching over description)
            strict_conds = []
            for t in tokens:
                pat = f"%{t}%"
                strict_conds.append(Book.title.ilike(pat))
                strict_conds.append(Book.authors.ilike(pat))
                strict_conds.append(Book.categories.ilike(pat))

            matching_books = db.scalars(
                select(Book).where(or_(*strict_conds)).limit(20)
            ).all()

            for b in matching_books:
                if b.isbn10 in already_interacted_isbns:
                    continue
                score_boost = 0.0
                b_title = (b.title or "").lower()
                b_author = (b.authors or "").lower()
                b_cat = (b.categories or "").lower()

                for t in tokens:
                    t_low = t.lower()
                    if t_low in b_title:
                        score_boost += 60.0
                    if t_low in b_author:
                        score_boost += 50.0
                    if t_low in b_cat:
                        score_boost += 40.0

                if score_boost > 0:
                    book_scores[b.isbn10] = book_scores.get(b.isbn10, 0.0) + (score_boost * recency_weight)
                    if b.authors:
                        fav_authors[b.authors.strip().lower()] += 4
                    if b.categories:
                        for cat in b.categories.split(","):
                            cat_clean = cat.strip().lower()
                            if cat_clean:
                                fav_categories[cat_clean] += 3

        # -------------------------------------------------------------
        # 7. Author & Category Affinity Expansion
        # -------------------------------------------------------------
        for author, weight in fav_authors.most_common(8):
            if author in disliked_authors:
                continue
            author_books = db.scalars(
                select(Book.isbn10).where(Book.authors.ilike(f"%{author}%")).limit(15)
            ).all()
            for isbn in author_books:
                if isbn not in already_interacted_isbns:
                    book_scores[isbn] = book_scores.get(isbn, 0.0) + (weight * 20.0)

        for cat, weight in fav_categories.most_common(8):
            if cat in disliked_categories:
                continue
            cat_books = db.scalars(
                select(Book.isbn10).where(Book.categories.ilike(f"%{cat}%")).limit(20)
            ).all()
            for isbn in cat_books:
                if isbn not in already_interacted_isbns:
                    book_scores[isbn] = book_scores.get(isbn, 0.0) + (weight * 15.0)

        # -------------------------------------------------------------
        # 8. Penalize Disliked Authors & Categories
        # -------------------------------------------------------------
        for dis_author in disliked_authors:
            dis_books = db.scalars(
                select(Book.isbn10).where(Book.authors.ilike(f"%{dis_author}%")).limit(25)
            ).all()
            for dis_isbn in dis_books:
                if dis_isbn in book_scores:
                    book_scores[dis_isbn] -= 100.0

        for dis_cat in disliked_categories:
            dis_cat_books = db.scalars(
                select(Book.isbn10).where(Book.categories.ilike(f"%{dis_cat}%")).limit(25)
            ).all()
            for dis_isbn in dis_cat_books:
                if dis_isbn in book_scores:
                    book_scores[dis_isbn] -= 80.0

        # -------------------------------------------------------------
        # 9. Verify Live Library Availability for Top Candidates
        # -------------------------------------------------------------
        sorted_candidates = sorted(book_scores.items(), key=lambda x: x[1], reverse=True)
        candidate_isbns = [isbn for isbn, score in sorted_candidates if score > 0][: top_n * 8]

        recommended_books: list[BookResponse] = []
        if candidate_isbns:
            books_map = {
                b.isbn10: b
                for b in db.scalars(select(Book).where(Book.isbn10.in_(candidate_isbns))).all()
            }
            for isbn, _ in sorted_candidates:
                if isbn in books_map:
                    book_obj = books_map[isbn]
                    _, avail, is_avail = get_simulated_availability(book_obj.isbn10, book_obj.title, db=db)
                    if is_avail and avail > 0:
                        recommended_books.append(_to_book_response(book_obj, db=db))
                        if len(recommended_books) >= top_n:
                            break

        # -------------------------------------------------------------
        # 10. Thematic Contextual Top-up / Cold-Start Fallback
        # -------------------------------------------------------------
        if len(recommended_books) < top_n:
            exclude_set = already_interacted_isbns.union({b.isbn10 for b in recommended_books})
            needed = top_n - len(recommended_books)

            # If user has a favorite category/author, top-up strictly from that preference!
            top_up_books: list[BookResponse] = []
            if fav_categories:
                for top_cat, _ in fav_categories.most_common(4):
                    genre_books = db.scalars(
                        select(Book)
                        .where(and_(
                            Book.categories.ilike(f"%{top_cat}%"),
                            Book.isbn10.not_in(list(exclude_set))
                        ))
                        .order_by(Book.average_rating.desc().nullslast(), Book.ratings_count.desc().nullslast())
                        .limit(needed * 3)
                    ).all()
                    for gb in genre_books:
                        _, g_avail, g_is_avail = get_simulated_availability(gb.isbn10, gb.title, db=db)
                        if g_is_avail and g_avail > 0:
                            top_up_books.append(_to_book_response(gb, db=db))
                            exclude_set.add(gb.isbn10)
                            if len(top_up_books) >= needed:
                                break
                    if len(top_up_books) >= needed:
                        break

            recommended_books.extend(top_up_books)

            # Diverse multi-genre fallback for cold-start (not just fiction!)
            if len(recommended_books) < top_n:
                fallback_books = self._fallback_diverse_books(
                    db, limit=top_n - len(recommended_books), exclude_isbns=exclude_set
                )
                recommended_books.extend(fallback_books)

        return recommended_books

    def _compute_cf_predictions(self, db: Session, roll_number: str, k_neighbors: int = 20) -> list[tuple[str, float]]:
        model = _get_cf_model(db)
        if not model or roll_number not in model["user2idx"]:
            return []

        user2idx = model["user2idx"]
        idx2isbn = model["idx2isbn"]
        R = model["R"]
        R_centered = model["R_centered"]
        user_means = model["user_means"]

        target_u_idx = user2idx[roll_number]
        num_isbns = len(idx2isbn)

        target_vec = R_centered[target_u_idx : target_u_idx + 1]
        sims = cosine_similarity(target_vec, R_centered)[0]
        sims[target_u_idx] = 0

        top_k_indices = np.argsort(sims)[::-1][:k_neighbors]
        top_k_sims = sims[top_k_indices]

        valid_mask = top_k_sims > 0
        if not np.any(valid_mask):
            return []

        top_k_indices = top_k_indices[valid_mask]
        top_k_sims = top_k_sims[valid_mask]
        rated_by_target = set(np.where(R[target_u_idx] > 0)[0])

        predictions = []
        for item_idx in range(num_isbns):
            if item_idx in rated_by_target:
                continue

            neighbor_ratings = R_centered[top_k_indices, item_idx]
            has_rating_mask = R[top_k_indices, item_idx] > 0
            if not np.any(has_rating_mask):
                continue

            denom = np.sum(top_k_sims[has_rating_mask])
            if denom == 0:
                continue

            predicted_rating = user_means[target_u_idx] + (
                np.sum(top_k_sims[has_rating_mask] * neighbor_ratings[has_rating_mask]) / denom
            )
            predictions.append((idx2isbn[item_idx], predicted_rating))

        return predictions

    def _fallback_diverse_books(
        self,
        db: Session,
        limit: int,
        exclude_isbns: set[str] | None = None,
    ) -> list[BookResponse]:
        """Provides balanced, high-rated titles across multiple major disciplines rather than only one genre."""
        sample_genres = [
            "History", "Science", "Philosophy", "Psychology",
            "Biography", "Mystery", "Fiction", "Business"
        ]
        results: list[BookResponse] = []
        exclude = set(exclude_isbns or set())

        # Pull top book from each genre for diversity
        for genre in sample_genres:
            stmt = (
                select(Book)
                .where(and_(
                    Book.categories.ilike(f"%{genre}%"),
                    Book.isbn10.not_in(list(exclude)),
                    Book.average_rating.is_not(None)
                ))
                .order_by(Book.average_rating.desc(), Book.ratings_count.desc())
                .limit(2)
            )
            books = db.scalars(stmt).all()
            for b in books:
                total, avail, is_avail = get_simulated_availability(b.isbn10, b.title, db=db)
                if is_avail and avail > 0:
                    results.append(_to_book_response(b, db=db))
                    exclude.add(b.isbn10)
                    if len(results) >= limit:
                        return results

        # If still needed, fill with general top rated
        if len(results) < limit:
            stmt = select(Book).where(and_(
                Book.average_rating.is_not(None),
                Book.isbn10.not_in(list(exclude))
            )).order_by(Book.average_rating.desc(), Book.ratings_count.desc()).limit((limit - len(results)) * 3)
            for b in db.scalars(stmt).all():
                total, avail, is_avail = get_simulated_availability(b.isbn10, b.title, db=db)
                if is_avail and avail > 0:
                    results.append(_to_book_response(b, db=db))
                    exclude.add(b.isbn10)
                    if len(results) >= limit:
                        break

        return results


    def _fallback_popular_books(
        self,
        db: Session,
        limit: int,
        exclude_isbns: set[str] | None = None,
    ) -> list[BookResponse]:
        return self._fallback_diverse_books(db, limit, exclude_isbns)

recommendation_engine = MultiSignalRecommendationEngine()
