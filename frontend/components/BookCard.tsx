'use client';

import React from 'react';
import { Book } from '../types';
import { BookOpen, MessageCircle } from 'lucide-react';

interface BookCardProps {
  book: Book;
  onSelect: (book: Book) => void;
  onAskChatbot?: (book: Book) => void;
}

function formatExpectedDate(dateStr?: string | null): string {
  if (!dateStr) return 'Soon';
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return dateStr;
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
  } catch {
    return dateStr;
  }
}

export default function BookCard({ book, onSelect, onAskChatbot }: BookCardProps) {
  const handleAsk = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onAskChatbot) {
      onAskChatbot(book);
    } else {
      window.location.href = `/chat?prompt=${encodeURIComponent(`Tell me about the book "${book.title}" by ${book.authors || 'the author'} and why I should read it.`)}`;
    }
  };

  return (
    <div
      onClick={() => onSelect(book)}
      className="portal-card p-3.5 flex flex-col justify-between cursor-pointer group rounded-2xl hover:shadow-md hover:-translate-y-1 transition-all duration-300 animate-in fade-in zoom-in-95 duration-500"
    >
      <div>
        {/* Cover */}
        <div className="w-full h-48 rounded-xl overflow-hidden bg-cream border border-parchment mb-3 relative flex items-center justify-center">
          {book.thumbnail ? (
            <img
              src={book.thumbnail}
              alt={book.title}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
          ) : (
            <div className="text-center p-3 text-ink-muted flex flex-col items-center">
              <BookOpen size={28} className="mb-2 opacity-50" />
              <span className="text-[11px] font-medium uppercase tracking-wider">No Cover</span>
            </div>
          )}

          {/* Rating */}
          {book.average_rating && (
            <div className="absolute top-2 right-2 px-2 py-0.5 text-xs font-bold text-navy bg-gold/90 backdrop-blur-sm rounded border border-gold shadow-sm">
              ★ {book.average_rating.toFixed(1)}
            </div>
          )}
        </div>

        {/* Category Tag */}
        {book.categories && (
          <span className="inline-block px-2 py-0.5 text-[10px] font-bold tracking-wider uppercase text-navy bg-gold/15 rounded mb-1.5 truncate max-w-full">
            {book.categories.split(',')[0]}
          </span>
        )}

        {/* Title */}
        <h3 className="font-serif font-bold text-navy text-sm line-clamp-2 group-hover:text-gold transition-colors leading-tight">
          {book.title}
        </h3>

        {/* Author */}
        <p className="text-xs text-ink-light line-clamp-1 mt-1 mb-3">
          {book.authors || 'Unknown Author'}
        </p>
      </div>

      {/* Footer Info */}
      <div className="pt-2 border-t border-parchment flex items-center justify-between text-xs">
        {book.is_available ? (
          <span className="text-gold font-mono font-bold text-[11px]">
            ✓ Available ({book.copies_available || 1})
          </span>
        ) : (
          <div className="flex flex-col gap-0.5">
            <span className="text-red-700 font-mono font-medium text-[11px] flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-red-600 animate-pulse"></span>
              Checked Out
            </span>
            {book.expected_return_date && (
              <span className="text-[10px] text-orange-700 font-semibold tracking-tight">
                Back: {formatExpectedDate(book.expected_return_date)}
              </span>
            )}
          </div>
        )}

        <button
          onClick={handleAsk}
          className="text-xs text-navy hover:text-gold font-bold flex items-center gap-1 transition-colors"
        >
          <MessageCircle size={12} />
          <span>Ask AI</span>
        </button>
      </div>
    </div>
  );
}
