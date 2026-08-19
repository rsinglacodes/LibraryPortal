'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { getStoredUser, setStoredToken, setStoredUser } from '../services/api';
import { User } from '../types';
import MyBorrowsModal from './MyBorrowsModal';
import { BookOpen } from 'lucide-react';

export default function Navbar({ children }: { children?: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [myBorrowsOpen, setMyBorrowsOpen] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const updateUser = () => setUser(getStoredUser());
    updateUser();
    window.addEventListener('library_portal_auth_change', updateUser);
    return () => window.removeEventListener('library_portal_auth_change', updateUser);
  }, [pathname]);

  // Close mobile menu on route change
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  const handleLogout = () => {
    setStoredToken(null);
    setStoredUser(null);
    setUser(null);
    router.push('/login');
  };

  const studentLinks = [
    { href: '/', label: 'Home' },
    { href: '/books', label: 'Catalog' },
    { href: '/recommendations', label: 'Recommendations' },
    { href: '/chat', label: 'AI Assistant' },
  ];

  const isChat = pathname === '/chat';
  const isLogin = pathname === '/login';

  if (isLogin) {
    return (
      <div className="flex flex-col min-h-screen">
        <header className="w-full pt-12 pb-4 flex flex-col items-center justify-center gap-2">
          <Link href="/" className="flex items-center gap-3">
            <BookOpen size={40} className="text-navy" />
            <div className="font-serif font-bold text-2xl text-navy tracking-tight leading-tight">
              University Library
            </div>
          </Link>
          <p className="text-xs text-ink-muted font-medium uppercase tracking-wider mt-1">Sign in to access features</p>
        </header>
        <div className="flex-1 flex flex-col">
          {children}
        </div>
      </div>
    );
  }

  const NavLinks = () => (
    <div className="flex flex-col gap-1 w-full">
      {user?.is_admin ? (
        <Link
          href="/admin"
          className="px-4 py-2.5 rounded-lg text-sm font-semibold text-gold bg-gold/10 border-l-4 border-gold shadow-sm transition-all"
        >
          ⚡ Admin Console
        </Link>
      ) : user ? (
        studentLinks.map((link) => {
          const isActive = pathname === link.href;
          return (
            <Link
              key={link.href}
              href={link.href}
              className={`px-4 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                isActive
                  ? 'bg-gold/10 text-gold border-l-4 border-gold pl-5 shadow-sm'
                  : 'text-cream/70 hover:text-cream hover:bg-navy-light hover:pl-5 border-l-4 border-transparent'
              }`}
            >
              {link.label}
            </Link>
          );
        })
      ) : (
        <div className="px-4 py-2 text-xs text-cream/50 italic">
          Sign in to access features
        </div>
      )}

      {user && !user.is_admin && (
        <button
          onClick={() => setMyBorrowsOpen(true)}
          className="mt-4 px-4 py-2.5 w-full text-left rounded-lg text-sm font-medium text-cream/70 hover:text-cream hover:bg-navy-light transition-all duration-200 border-l-4 border-transparent hover:pl-5 flex items-center gap-2"
        >
          <BookOpen className="w-5 h-5 text-navy" />
          <span>My Borrows & Late Fines</span>
        </button>
      )}
    </div>
  );

  const Brand = () => (
    <Link href={user?.is_admin ? "/admin" : "/"} className="flex items-center gap-3">
      <span className="text-2xl">{user?.is_admin ? '🏛️' : '📚'}</span>
      <div>
        <div className="font-serif font-bold text-lg text-cream tracking-tight leading-tight">
          {user?.is_admin ? 'LibraryAdmin' : 'University Library'}
        </div>
        {user?.is_admin && (
          <span className="text-[10px] font-bold uppercase tracking-wider text-gold">
            Librarian Console
          </span>
        )}
      </div>
    </Link>
  );

  const UserBlock = () => (
    <div className="border-t border-navy-light pt-4 w-full">
      {user ? (
        <div className="flex flex-col gap-3">
          <div>
            <span className="block text-sm font-semibold text-cream">{user.name}</span>
            <span className="block text-xs text-gold font-mono">
              {user.is_admin ? 'ID: admin' : `Roll: ${user.roll_number}`}
            </span>
          </div>
          <button
            onClick={handleLogout}
            className="w-full py-2 text-xs font-medium text-cream/70 hover:text-cream bg-navy-dark hover:bg-navy-light rounded-lg transition-colors border border-navy-light text-center"
          >
            Sign Out
          </button>
        </div>
      ) : (
        <Link
          href="/login"
          className="block w-full py-2.5 text-sm font-semibold rounded-lg bg-gold text-navy hover:bg-gold-light transition-colors text-center shadow-sm"
        >
          Sign In
        </Link>
      )}
    </div>
  );

  return (
    <>
      {isChat ? (
        /* ── Slim Top Bar for Chat Page ── */
        <div className="flex flex-col min-h-screen">
          <header className="sticky top-0 z-40 w-full bg-navy/95 backdrop-blur-md border-b border-navy-dark">
            <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
              <Brand />
              <div className="flex items-center gap-4">
                <Link href="/" className="text-sm font-medium text-cream/70 hover:text-gold transition-colors">
                  ← Back to Portal
                </Link>
              </div>
            </div>
          </header>
          <div className="flex-1 flex flex-col">
            {children}
          </div>
        </div>
      ) : (
        /* ── Standard Sidebar Layout ── */
        <div className="flex min-h-screen">
          {/* Mobile Header & Hamburger */}
          <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-navy border-b border-navy-light z-40 flex items-center justify-between px-4">
            <Brand />
            <button
              onClick={() => setMobileOpen(true)}
              className="p-2 text-cream hover:bg-navy-light rounded-lg transition-colors"
            >
              ☰
            </button>
          </div>

          {/* Mobile Slide-out Drawer */}
          {mobileOpen && (
            <div className="md:hidden fixed inset-0 z-50 flex">
              <div
                className="fixed inset-0 bg-navy-950/60 backdrop-blur-sm"
                onClick={() => setMobileOpen(false)}
              />
              <aside className="relative w-[260px] bg-navy h-full flex flex-col p-6 shadow-2xl animate-in slide-in-from-left duration-200">
                <button
                  onClick={() => setMobileOpen(false)}
                  className="absolute top-4 right-4 text-cream/70 hover:text-cream text-lg"
                >
                  ✕
                </button>
                <div className="mb-10 mt-2">
                  <Brand />
                </div>
                <div className="flex-1">
                  <NavLinks />
                </div>
                <UserBlock />
              </aside>
            </div>
          )}

          {/* Desktop Sidebar */}
          <aside className="hidden md:flex flex-col w-[260px] fixed inset-y-0 left-0 bg-navy shadow-xl z-30 p-6 border-r border-navy-dark">
            <div className="mb-10">
              <Brand />
            </div>
            <div className="flex-1 w-full">
              <NavLinks />
            </div>
            <UserBlock />
          </aside>

          {/* Main Content Area */}
          <div className="flex-1 md:ml-[260px] flex flex-col min-w-0 pt-16 md:pt-0">
            {children}
          </div>
        </div>
      )}

      {/* Student Borrows Modal */}
      {!user?.is_admin && (
        <MyBorrowsModal
          isOpen={myBorrowsOpen}
          onClose={() => setMyBorrowsOpen(false)}
        />
      )}
    </>
  );
}
