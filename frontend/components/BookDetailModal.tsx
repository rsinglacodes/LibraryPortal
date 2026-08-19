'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { Book } from '../types';
import { api, getStoredUser } from '../services/api';
import { X, BookOpen, Clock, Calendar, Bell, BellOff, MessageCircle, Star, Check } from 'lucide-react';

interface BookDetailModalProps {
  book: Book | null;
  onClose: () => void;
  onRatingUpdated?: () => void;
}

interface BookReviewItem {
  rating_id: number;
  roll_number: string;
  user_name: string;
  rating: number;
  review?: string;
  created_at?: string;
}

function formatFullExpectedDate(dateStr?: string | null): string {
  if (!dateStr) return 'Shortly';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString('en-US', { day: 'numeric', month: 'long', year: 'numeric' });
  } catch {
    return dateStr;
  }
}

export default function BookDetailModal({ book, onClose, onRatingUpdated }: BookDetailModalProps) {
  const router = useRouter();
  const [reviews, setReviews] = useState<BookReviewItem[]>([]);
  const [reviewsLoading, setReviewsLoading] = useState(false);
  const [borrowing, setBorrowing] = useState(false);
  const [borrowMessage, setBorrowMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);
  const [isNotified, setIsNotified] = useState(false);

  const fetchReviews = async (isbn: string) => {
    try {
      setReviewsLoading(true);
      const data = await api.getBookReviews(isbn, 2);
      setReviews(data || []);
    } catch (e) {
      console.warn('Could not fetch reviews:', e);
    } finally {
      setReviewsLoading(false);
    }
  };

  useEffect(() => {
    if (book) {
      const user = getStoredUser();
      api.trackInteraction({
        interaction_type: 'explore',
        isbn10: book.isbn10,
        content: book.title,
        roll_number: user ? user.roll_number : 'guest',
      }).catch(() => {});

      fetchReviews(book.isbn10);

      // Check existing notification preference
      const notifyKey = `portal_notify_${book.isbn10}`;
      setIsNotified(localStorage.getItem(notifyKey) === 'true');
    }
  }, [book?.isbn10]);

  const handleToggleNotify = () => {
    if (!book) return;
    const notifyKey = `portal_notify_${book.isbn10}`;
    if (isNotified) {
      localStorage.removeItem(notifyKey);
      setIsNotified(false);
    } else {
      localStorage.setItem(notifyKey, 'true');
      setIsNotified(true);
    }
  };


  if (!book) return null;

  const isOutOfStock = !book.is_available || (book.copies_available !== undefined && book.copies_available <= 0);

  const handleBorrowBook = async () => {
    const user = getStoredUser();
    if (!user) {
      router.push('/login');
      return;
    }

    try {
      setBorrowing(true);
      setBorrowMessage(null);
      const res = await api.borrowBook(book.isbn10);

      // Decrement copies locally
      if (book.copies_available !== undefined) {
        book.copies_available = Math.max(0, book.copies_available - 1);
        if (book.copies_available === 0) {
          book.is_available = false;
        }
      }

      setBorrowMessage({
        text: `Successfully borrowed "${book.title}"! Due date: ${new Date(res.due_date).toLocaleDateString()}. (Overdue late fee is ₹10 base + ₹10/day).`,
        type: 'success',
      });

      if (onRatingUpdated) onRatingUpdated();
    } catch (err: any) {
      setBorrowMessage({
        text: err.message || 'Failed to borrow book. It might be out of stock or already issued.',
        type: 'error',
      });
    } finally {
      setBorrowing(false);
    }
  };

  const handleDiscussInChat = () => {
    onClose();
    sessionStorage.setItem('pending_chat_prompt', `Provide a summary, key themes, and analysis of "${book.title}" by ${book.authors || 'the author'}.`);
    router.push(`/chat`);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl bg-cream-light rounded-2xl p-6 sm:p-8 shadow-2xl border border-parchment max-h-[90vh] overflow-y-auto custom-scrollbar">
        {/* Close Button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-2 text-ink-muted hover:text-navy rounded-xl bg-parchment hover:bg-parchment-light transition-colors"
        >
          <X size={18} />
        </button>

        <div className="flex flex-col sm:flex-row gap-6">
          {/* Cover */}
          <div className="w-full sm:w-44 h-60 rounded-xl overflow-hidden bg-cream border border-parchment shrink-0 flex items-center justify-center">
            {book.thumbnail ? (
              <img src={book.thumbnail} alt={book.title} className="w-full h-full object-cover" />
            ) : (
              <div className="text-center p-4 text-ink-muted flex flex-col items-center">
                <BookOpen size={36} className="mb-2 opacity-50" />
                <span className="text-xs uppercase tracking-widest font-semibold">No Cover</span>
              </div>
            )}
          </div>

          {/* Details */}
          <div className="flex-1 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2 flex-wrap">
                {book.is_available ? (
                  <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-green-100 text-emerald-800 border border-green-200/60 flex items-center gap-1">
                    <Check size={12} /> Available ({book.copies_available || 1} copies)
                  </span>
                ) : (
                  <span className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-red-50 text-red-700 border border-red-200/60 flex items-center gap-1">
                    <X size={12} /> Checked Out
                  </span>
                )}
                {book.categories && (
                  <span className="text-[11px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-gold/15 text-navy border border-gold/20">
                    {book.categories}
                  </span>
                )}
              </div>

              <h2 className="text-xl sm:text-2xl font-serif font-bold text-navy leading-snug">
                {book.title}
              </h2>
              {book.subtitle && (
                <p className="text-xs text-ink-muted italic mt-1">{book.subtitle}</p>
              )}
              <p className="text-xs font-semibold text-gold mt-1.5">
                By {book.authors || 'Unknown Author'}
              </p>

              {/* Metadata Table */}
              <div className="grid grid-cols-2 gap-2 text-xs my-4 bg-cream p-3 rounded-xl border border-parchment font-mono">
                <div>
                  <span className="text-ink-muted">ISBN-10:</span>{' '}
                  <span className="text-navy font-semibold">{book.isbn10}</span>
                </div>
                <div>
                  <span className="text-ink-muted">Published:</span>{' '}
                  <span className="text-navy font-semibold">{book.published_year || 'Unknown'}</span>
                </div>
                <div>
                  <span className="text-ink-muted">Rating:</span>{' '}
                  <span className="text-gold font-bold">
                    ★ {book.average_rating ? `${book.average_rating.toFixed(1)} / 5` : 'Unrated'}
                  </span>
                </div>
                <div>
                  <span className="text-ink-muted">Reviews:</span>{' '}
                  <span className="text-navy font-semibold">{book.ratings_count || 0} count</span>
                </div>
              </div>

              {/* Description */}
              <div className="space-y-1 mb-4">
                <h3 className="text-[10px] font-bold uppercase tracking-widest text-ink-muted mb-1.5">Description</h3>
                <p className="text-xs text-ink leading-relaxed max-h-28 overflow-y-auto pr-2">
                  {book.description || 'No description available for this book in the catalog.'}
                </p>
              </div>
            </div>

            {/* Borrow Action Banner */}
            <div className="my-3 p-4 rounded-xl bg-cream border border-parchment flex flex-col gap-3 shadow-sm">
              <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-full bg-parchment text-navy">
                    {isOutOfStock ? <Clock size={20} /> : <BookOpen size={20} />}
                  </div>
                  <div>
                    <span className="text-xs font-bold text-navy block">
                      {isOutOfStock ? 'Currently Checked Out' : 'Available for Self-Service Borrowing'}
                    </span>
                    <span className="text-[11px] text-ink-light mt-0.5 block">
                      {isOutOfStock
                        ? 'All copies of this book are currently on loan.'
                        : `14-day checkout period (${book.copies_available || 1} copies left in stacks).`}
                    </span>
                  </div>
                </div>

                {!isOutOfStock && (
                  <button
                    onClick={handleBorrowBook}
                    disabled={borrowing}
                    className="w-full sm:w-auto px-4 py-2.5 text-xs font-semibold uppercase tracking-wider rounded-xl transition-all shadow-md shrink-0 bg-navy hover:bg-navy-light text-cream cursor-pointer active:scale-95 flex items-center justify-center gap-1.5"
                  >
                    {!borrowing && <Check size={14} />}
                    {borrowing ? 'Processing..' : 'Borrow Book'}
                  </button>
                )}
              </div>

              {/* Expected Return Date & Notification Badge for Out of Stock Books */}
              {isOutOfStock && (
                <div className="pt-3 border-t border-parchment flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
                  <div className="flex items-center gap-2 text-xs text-orange-800 bg-orange-100 border border-orange-200 px-3 py-2 rounded-xl w-full sm:w-auto">
                    <Calendar size={14} />
                    <span>
                      <strong className="font-bold">Estimated Return:</strong>{' '}
                      {formatFullExpectedDate(book.expected_return_date)}
                    </span>
                  </div>

                  <button
                    onClick={handleToggleNotify}
                    className={`w-full sm:w-auto px-4 py-2 text-xs font-bold rounded-xl transition-all flex items-center justify-center gap-2 ${
                      isNotified
                        ? 'bg-gold/15 border border-gold/30 text-navy shadow-inner'
                        : 'bg-cream border border-parchment hover:bg-parchment text-navy'
                    }`}
                  >
                    {isNotified ? <Bell size={14} className="text-gold" /> : <BellOff size={14} className="text-ink-muted" />}
                    <span>{isNotified ? 'Notify Me (Active)' : 'Notify Me When Available'}</span>
                  </button>
                </div>
              )}
            </div>

            {/* Borrow Status Feedback */}
            {borrowMessage && (
              <div
                className={`p-3 rounded-xl text-xs font-bold border mb-3 flex items-center gap-2 ${
                  borrowMessage.type === 'success'
                    ? 'bg-green-100 border-green-200 text-emerald-800'
                    : 'bg-red-50 border-red-200 text-red-700'
                }`}
              >
                {borrowMessage.type === 'success' ? <Check size={14} /> : <X size={14} />}
                {borrowMessage.text}
              </div>
            )}

            {/* Discuss in AI Assistant */}
            <div className="mb-4">
              <button
                onClick={handleDiscussInChat}
                className="w-full py-2.5 rounded-xl text-xs font-bold text-navy bg-gold/80 hover:bg-gold border border-gold/90 shadow-sm flex items-center justify-center gap-2 transition-colors"
              >
                <MessageCircle size={16} />
                <span>Discuss with AI Assistant</span>
              </button>
            </div>

            {/* Rating Overview */}
            <div className="pt-4 border-t border-parchment space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-ink-muted flex items-center gap-1.5">
                  <Star size={12} className="text-gold" /> Average Rating &amp; Reviews
                </h4>
                <span className="text-gold font-mono text-sm font-extrabold flex items-center gap-1">
                  ★
                  <span>{book.average_rating ? `${Math.min(5.0, book.average_rating).toFixed(1)} / 5` : 'Unrated'}</span>
                  <span className="text-xs text-ink-muted font-sans font-normal ml-1">({book.ratings_count || 0})</span>
                </span>
              </div>
            </div>

            {/* 2 Most Recent Student Reviews */}
            <div className="mt-3 pt-3 border-t border-parchment space-y-2">
              <div className="flex items-center justify-between">
                <h4 className="text-[10px] font-bold uppercase tracking-widest text-ink-muted">
                  Recent Student Reviews ({Math.min(2, reviews.length)})
                </h4>
                <span className="text-[9px] text-ink-light uppercase tracking-wider">Submitted upon book return</span>
              </div>

              {reviewsLoading ? (
                <div className="text-xs text-ink-muted py-2">Loading reviews...</div>
              ) : reviews.length === 0 ? (
                <div className="text-xs text-ink-muted py-2 italic bg-cream p-4 rounded-xl border border-parchment text-center">
                  No student reviews yet for this book.
                </div>
              ) : (
                <div className="space-y-2">
                  {reviews.slice(0, 2).map((rev) => (
                    <div key={rev.rating_id} className="p-3.5 rounded-xl bg-cream border border-parchment text-xs shadow-sm">
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="font-bold text-navy">{rev.user_name}</span>
                        <span className="text-gold font-bold font-mono text-[11px]">
                          {'★'.repeat(Math.min(5, Math.max(1, rev.rating)))}{'☆'.repeat(Math.max(0, 5 - Math.min(5, Math.max(1, rev.rating))))} ({Math.min(5, Math.max(1, rev.rating))}/5)
                        </span>
                      </div>
                      {rev.review ? (
                        <p className="text-ink text-xs leading-relaxed">{rev.review}</p>
                      ) : (
                        <p className="text-ink-muted text-[11px] italic">Rated {Math.min(5, Math.max(1, rev.rating))}/5 stars.</p>
                      )}
                      {rev.created_at && (
                        <span className="text-[9px] uppercase tracking-wider text-ink-light block mt-2">
                          {new Date(rev.created_at).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
