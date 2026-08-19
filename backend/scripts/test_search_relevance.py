from sqlalchemy import select, func, or_, case
from app.database.connection import get_session_local
from app.models import Book

db = get_session_local()()
q = 'history'
pat = f'%{q}%'

score = (
    case((Book.title.ilike(pat), 100), else_=0) +
    case((Book.categories.ilike(pat), 80), else_=0) +
    case((Book.authors.ilike(pat), 70), else_=0) +
    case((Book.description.ilike(pat), 10), else_=0)
)

stmt = (
    select(Book, score.label('relevance'))
    .where(score > 0)
    .order_by(score.desc(), Book.average_rating.desc().nullslast(), Book.ratings_count.desc().nullslast())
    .limit(10)
)

results = db.execute(stmt).all()
print(f'Found {len(results)} books for query "{q}":')
for b, s in results:
    print(f'  [Score {s:3d}] {b.title} | Cat: {b.categories} | Author: {b.authors} | Rating: {b.average_rating}')
db.close()
