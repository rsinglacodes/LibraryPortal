'use client';

import React, { useEffect, useState, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { api } from '../../services/api';
import { Book, BookListResponse } from '../../types';
import BookCard from '../../components/BookCard';
import BookDetailModal from '../../components/BookDetailModal';

function BooksContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const [data, setData] = useState<BookListResponse | null>(null);
  const [categories, setCategories] = useState<string[]>([]);
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('');
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);

  useEffect(() => {
    const urlQ = searchParams.get('q');
    if (urlQ) setSearch(urlQ);
    const urlCat = searchParams.get('category');
    if (urlCat) setSelectedCategory(urlCat);
  }, [searchParams]);

  const fetchBooks = async () => {
    try {
      setLoading(true);
      const res = await api.getBooks({
        q: search.trim() || undefined,
        category: selectedCategory || undefined,
        page,
        size: 20,
      });
      setData(res);
    } catch (err) {
      console.error('Failed to fetch books', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.getCategories().then(setCategories).catch(console.error);
  }, []);

  useEffect(() => {
    fetchBooks();
  }, [page, selectedCategory, search]);

  const handleAskChatbot = (book: Book) => {
    router.push(`/chat?prompt=${encodeURIComponent(`Tell me about the book "${book.title}" by ${book.authors || 'the author'} and why I should read it.`)}`);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header & Controls */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-parchment">
        <div>
          <h1 className="text-2xl font-serif font-bold text-navy tracking-tight">
            Library Catalog
          </h1>
          <p className="text-xs text-ink-light mt-1">
            {data ? `Showing ${data.items.length} of ${data.total.toLocaleString()} catalog books` : 'Loading catalog...'}
          </p>
        </div>

        {/* Search & Category Filter */}
        <div className="flex flex-wrap items-center gap-3">
          <input
            type="text"
            placeholder="Search title, author, category, or ISBN..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            className="px-3.5 py-2 text-xs rounded-xl bg-cream-light border border-parchment text-ink placeholder-ink-muted focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold shadow-sm w-56 sm:w-72 transition-colors"
          />

          <select
            value={selectedCategory}
            onChange={(e) => {
              setSelectedCategory(e.target.value);
              setPage(1);
            }}
            className="px-3 py-2 text-xs rounded-xl bg-cream-light border border-parchment text-ink focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold shadow-sm max-w-[200px] transition-colors"
          >
            <option value="">All Categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {Array.from({ length: 10 }).map((_, i) => (
            <div key={i} className="h-64 rounded-2xl bg-parchment-light/60 animate-pulse border border-parchment" />
          ))}
        </div>
      ) : data && data.items.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
          {data.items.map((book) => (
            <BookCard
              key={book.isbn10}
              book={book}
              onSelect={setSelectedBook}
              onAskChatbot={handleAskChatbot}
            />
          ))}
        </div>
      ) : (
        <div className="portal-card p-12 text-center rounded-2xl">
          <p className="text-ink-muted text-sm">No books found matching your search criteria.</p>
        </div>
      )}

      {/* Pagination */}
      {data && data.pages > 1 && (
        <div className="flex items-center justify-between pt-4 border-t border-parchment text-xs text-ink-light">
          <span>
            Page {data.page} of {data.pages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => Math.max(p - 1, 1))}
              className="px-3 py-1.5 rounded-xl bg-cream-light border border-parchment text-ink disabled:opacity-40 hover:bg-parchment-light transition-colors shadow-sm"
            >
              Previous
            </button>
            <button
              disabled={page >= data.pages}
              onClick={() => setPage((p) => Math.min(p + 1, data.pages))}
              className="px-3 py-1.5 rounded-xl bg-cream-light border border-parchment text-ink disabled:opacity-40 hover:bg-parchment-light transition-colors shadow-sm"
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Book Detail Modal */}
      <BookDetailModal
        book={selectedBook}
        onClose={() => setSelectedBook(null)}
        onRatingUpdated={fetchBooks}
      />
    </div>
  );
}

export default function BooksPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center text-ink-muted">Loading catalog...</div>}>
      <BooksContent />
    </Suspense>
  );
}
