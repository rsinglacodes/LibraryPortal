'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api, getStoredUser } from '../../services/api';
import { Book, User } from '../../types';
import BookCard from '../../components/BookCard';
import BookDetailModal from '../../components/BookDetailModal';
import { Sparkles, Star, Search, BookOpen, MessageCircle, RefreshCw, User as UserIcon } from 'lucide-react';

export default function RecommendationsPage() {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [recommendations, setRecommendations] = useState<Book[]>([]);
  const [signals, setSignals] = useState<{
    total_ratings: number;
    total_explored: number;
    total_searches: number;
    total_chats: number;
    active_profile: boolean;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedBook, setSelectedBook] = useState<Book | null>(null);

  const fetchRecommendationsAndSignals = async () => {
    try {
      setLoading(true);
      const [recRes, sigRes] = await Promise.allSettled([
        api.getRecommendations(12),
        api.getUserSignals(),
      ]);

      if (recRes.status === 'fulfilled') {
        setRecommendations(recRes.value);
      } else {
        setRecommendations([]);
      }

      if (sigRes.status === 'fulfilled') {
        setSignals(sigRes.value);
      }
    } catch (err) {
      console.error('Failed to fetch recommendations', err);
      setRecommendations([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const handleAuthChange = () => {
      const currentUser = getStoredUser();
      setUser(currentUser);
      setRecommendations([]);
      if (currentUser) {
        fetchRecommendationsAndSignals();
      } else {
        setLoading(false);
      }
    };

    handleAuthChange();
    window.addEventListener('library_portal_auth_change', handleAuthChange);
    return () => window.removeEventListener('library_portal_auth_change', handleAuthChange);
  }, []);

  const handleAskChatbot = (book: Book) => {
    router.push(`/chat?prompt=${encodeURIComponent(`Tell me why the recommendation model suggested "${book.title}" for me and analyze its themes.`)}`);
  };

  if (!user && !loading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] text-center p-8 portal-card max-w-lg mx-auto my-8 rounded-2xl">
        <UserIcon size={40} className="mb-4 text-navy" />
        <h2 className="text-2xl font-serif font-bold text-navy mb-2">Student Authentication Required</h2>
        <p className="text-xs text-ink-light max-w-md mb-6 leading-relaxed">
          Sign in with your university student roll number to calculate your personalized recommendations synthesized from your searches, chats, explored books, and ratings.
        </p>
        <Link
          href="/login"
          className="px-6 py-2.5 rounded-xl text-xs font-semibold bg-navy hover:bg-navy-light text-cream transition-colors shadow-sm"
        >
          Sign In with Student Roll Number →
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Banner */}
      <div className="portal-card p-6 rounded-2xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border border-parchment bg-gradient-to-r from-cream to-cream-light">
        <h1 className="text-2xl font-serif font-bold text-navy">Recommended for You</h1>
        <button
          onClick={fetchRecommendationsAndSignals}
          disabled={loading}
          className="px-4 py-2 text-xs font-semibold text-cream bg-navy hover:bg-navy-light rounded-xl transition-colors disabled:opacity-50 flex items-center gap-1.5 shrink-0 shadow-sm"
        >
          <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
          <span>{loading ? 'Recalculating...' : 'Recalculate'}</span>
        </button>
      </div>

      {/* Grid */}
      {loading ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-64 rounded-2xl bg-parchment-light/60 animate-pulse border border-parchment" />
          ))}
        </div>
      ) : recommendations.length > 0 ? (
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {recommendations.map((book) => (
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
          <p className="text-ink-muted text-sm">No recommendation predictions available yet for this user profile.</p>
        </div>
      )}

      {/* Book Detail Modal */}
      <BookDetailModal
        book={selectedBook}
        onClose={() => setSelectedBook(null)}
        onRatingUpdated={fetchRecommendationsAndSignals}
      />
    </div>
  );
}
