'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { getStoredUser } from '../services/api';
import { User } from '../types';
import { Building2, BookOpen, Sparkles, MessageCircle, GraduationCap } from 'lucide-react';

export default function Home() {
  const router = useRouter();
  const [search, setSearch] = useState('');
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const u = getStoredUser();
    setUser(u);
    if (u?.is_admin) {
      router.push('/admin');
    }
  }, []);

  const handleAction = (destination: string) => {
    const u = getStoredUser();
    if (!u) {
      router.push(`/login?redirect=${encodeURIComponent(destination)}`);
    } else if (u.is_admin) {
      router.push('/admin');
    } else {
      router.push(destination);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!search.trim()) return;
    const dest = `/books?q=${encodeURIComponent(search.trim())}`;
    handleAction(dest);
  };

  return (
    <div className="space-y-10 py-6 max-w-5xl mx-auto">
      {/* Hero Section */}
      <section className="text-center py-10 px-4">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gold/10 border border-gold/30 text-navy font-semibold text-xs mb-4">
          <Building2 size={14} className="text-gold" /> University Central Library Portal
        </div>
        <h1 className="text-3xl sm:text-4xl font-serif font-extrabold text-navy tracking-tight">
          Welcome to the University Library
        </h1>
        <p className="text-sm sm:text-base text-ink-light max-w-2xl mx-auto mt-3 leading-relaxed">
          Access over 2,400 catalog titles, personalized collaborative recommendations, interactive live book loan tracking, and real-time inventory AI assistance.
        </p>

        {/* Search Bar */}
        <form onSubmit={handleSearch} className="mt-6 max-w-xl mx-auto flex gap-2">
          <input
            type="text"
            placeholder="Search books by title, author, category, or keyword..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="flex-1 px-4 py-3 text-sm rounded-xl bg-cream-light border border-parchment text-ink placeholder-ink-muted focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold transition-all shadow-sm"
          />
          <button
            type="submit"
            className="px-6 py-3 text-xs font-semibold uppercase tracking-wider rounded-xl bg-navy hover:bg-navy-light text-cream transition-colors shadow-md"
          >
            Search
          </button>
        </form>
      </section>

      {/* Feature Navigation Cards */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-5">
        {/* Card 1: Books Catalog */}
        <div
          onClick={() => handleAction('/books')}
          className="portal-card p-6 flex flex-col justify-between group cursor-pointer hover:border-gold transition-all"
        >
          <div>
            <div className="mb-4 text-navy">
              <BookOpen size={28} className="group-hover:text-gold transition-colors" />
            </div>
            <h2 className="text-lg font-serif font-bold text-navy group-hover:text-gold transition-colors">
              Library Catalog
            </h2>
            <p className="text-xs text-ink-light mt-2 leading-relaxed">
              Explore 2,400+ digitized catalog entries with real-time stock availability, category filtering, and student ratings.
            </p>
          </div>
          <span className="text-xs font-semibold text-gold mt-4 block">
            Browse Catalog →
          </span>
        </div>

        {/* Card 2: AI Recommendations */}
        <div
          onClick={() => handleAction('/recommendations')}
          className="portal-card p-6 flex flex-col justify-between group cursor-pointer hover:border-gold transition-all"
        >
          <div>
            <div className="mb-4 text-navy">
              <Sparkles size={28} className="group-hover:text-gold transition-colors" />
            </div>
            <h2 className="text-lg font-serif font-bold text-navy group-hover:text-gold transition-colors">
              Personalized Recommendations
            </h2>
            <p className="text-xs text-ink-light mt-2 leading-relaxed">
              Candidate books generated via User-Based Collaborative Filtering, strictly verified against available library copies.
            </p>
          </div>
          <span className="text-xs font-semibold text-gold mt-4 block">
            View Recommendations →
          </span>
        </div>

        {/* Card 3: AI Chatbot */}
        <div
          onClick={() => handleAction('/chat')}
          className="portal-card p-6 flex flex-col justify-between group cursor-pointer hover:border-gold transition-all"
        >
          <div>
            <div className="mb-4 text-navy">
              <MessageCircle size={28} className="group-hover:text-gold transition-colors" />
            </div>
            <h2 className="text-lg font-serif font-bold text-navy group-hover:text-gold transition-colors">
              AI Book Assistant
            </h2>
            <p className="text-xs text-ink-light mt-2 leading-relaxed">
              Ask natural language questions about plots, themes, or request mood-based suggestions with live inventory verification and persistent session history.
            </p>
          </div>
          <span className="text-xs font-semibold text-gold mt-4 block">
            Ask Assistant →
          </span>
        </div>
      </section>

      {/* Info Banner */}
      {!user && (
        <section className="portal-card p-6 flex flex-col sm:flex-row items-center justify-between gap-4 border-parchment bg-parchment-light/50">
          <div>
            <h3 className="text-sm font-bold text-navy flex items-center gap-2">
              <GraduationCap size={18} className="text-navy" /> Sign In to Access Portal Features
            </h3>
            <p className="text-xs text-ink-light mt-1">
              Please sign in with your student roll number or administrator credentials to borrow books, view persistent chats, and manage borrows.
            </p>
          </div>
          <Link
            href="/login"
            className="px-5 py-2.5 text-xs font-semibold rounded-xl bg-navy hover:bg-navy-light text-cream whitespace-nowrap transition-colors shadow-md"
          >
            Sign In / Register →
          </Link>
        </section>
      )}
    </div>
  );
}
