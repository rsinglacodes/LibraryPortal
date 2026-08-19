'use client';

import React, { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { api, setStoredToken, setStoredUser } from '../../services/api';
import { GraduationCap, Zap } from 'lucide-react';

function LoginContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectUrl = searchParams.get('redirect') || '/books';

  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login');

  // Login form
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');

  // Register form
  const [rollNumber, setRollNumber] = useState('');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const isEmail = identifier.includes('@');
      const payload = isEmail
        ? { email: identifier.trim(), password }
        : { roll_number: identifier.trim(), password };

      const res = await api.login(payload);
      setStoredToken(res.access_token);
      setStoredUser(res.user);

      if (res.user.is_admin || res.user.roll_number === 'admin') {
        router.push('/admin');
      } else {
        router.push(redirectUrl);
      }
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await api.register({
        roll_number: rollNumber.trim(),
        name: name.trim(),
        email: email.trim(),
        password: regPassword,
      });
      setStoredToken(res.access_token);
      setStoredUser(res.user);
      router.push('/books');
    } catch (err: any) {
      setError(err.message || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="flex items-center justify-center min-h-[70vh] py-8">
      <div className="w-full max-w-md portal-card p-6 sm:p-8">
        {/* Header */}
        <div className="text-center mb-6">
          <div className="flex justify-center mb-4">
            <GraduationCap size={40} className="text-navy" />
          </div>
          <h2 className="text-2xl font-serif font-bold text-navy tracking-tight">
            Student Portal
          </h2>
          <p className="text-xs text-ink-light mt-1">
            Access your library account, rate catalog books, and view recommendations
          </p>
        </div>

        {/* Tab Controls */}
        <div className="flex border-b border-parchment mb-6 text-xs font-semibold uppercase tracking-wider">
          <button
            onClick={() => {
              setActiveTab('login');
              setError(null);
            }}
            className={`flex-1 py-2.5 border-b-2 transition-colors ${
              activeTab === 'login'
                ? 'border-gold text-gold font-bold'
                : 'border-transparent text-ink-muted hover:text-navy'
            }`}
          >
            Sign In
          </button>
          <button
            onClick={() => {
              setActiveTab('register');
              setError(null);
            }}
            className={`flex-1 py-2.5 border-b-2 transition-colors ${
              activeTab === 'register'
                ? 'border-gold text-gold font-bold'
                : 'border-transparent text-ink-muted hover:text-navy'
            }`}
          >
            Register Student
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
            {error}
          </div>
        )}

        {/* Login Form */}
        {activeTab === 'login' ? (
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-navy mb-1">
                Student Roll Number or Email
              </label>
              <input
                type="text"
                required
                placeholder="e.g. 276804 or user276804@library.local"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-cream-light border border-navy/30 text-ink text-sm focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold placeholder-ink-muted shadow-sm portal-input-gold"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-navy mb-1">
                Password
              </label>
              <input
                type="password"
                required
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-cream-light border border-navy/30 text-ink text-sm focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold placeholder-ink-muted shadow-sm portal-input-gold"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-xl font-semibold text-xs uppercase tracking-wider bg-navy hover:bg-navy-light text-cream transition-colors disabled:opacity-50 mt-2 shadow-md"
            >
              {loading ? 'Signing In...' : 'Sign In'}
            </button>


          </form>
        ) : (
          /* Register Form */
          <form onSubmit={handleRegister} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-navy mb-1">
                Student Roll Number
              </label>
              <input
                type="text"
                required
                placeholder="e.g. 2026-CS-001"
                value={rollNumber}
                onChange={(e) => setRollNumber(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-cream-light border border-navy/30 text-ink text-sm focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold placeholder-ink-muted shadow-sm portal-input-gold"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-navy mb-1">
                Full Name
              </label>
              <input
                type="text"
                required
                placeholder="e.g. Eleanor Vance"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-cream-light border border-navy/30 text-ink text-sm focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold placeholder-ink-muted shadow-sm portal-input-gold"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-navy mb-1">
                University Email
              </label>
              <input
                type="email"
                required
                placeholder="student@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-cream-light border border-navy/30 text-ink text-sm focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold placeholder-ink-muted shadow-sm portal-input-gold"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-navy mb-1">
                Password
              </label>
              <input
                type="password"
                required
                minLength={8}
                placeholder="At least 8 characters"
                value={regPassword}
                onChange={(e) => setRegPassword(e.target.value)}
                className="w-full px-3.5 py-2.5 rounded-xl bg-cream-light border border-navy/30 text-ink text-sm focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold placeholder-ink-muted shadow-sm portal-input-gold"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-xl font-semibold text-xs uppercase tracking-wider bg-navy hover:bg-navy-light text-cream transition-colors disabled:opacity-50 mt-2 shadow-md"
            >
              {loading ? 'Registering...' : 'Create Student Account'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center justify-center min-h-[50vh] text-xs text-ink-muted">
          Loading Sign In...
        </div>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
