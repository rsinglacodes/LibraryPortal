'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { api, getStoredUser } from '../../services/api';
import {
  AdminOverview,
  Book,
  BookDemandItem,
  BorrowRecord,
  DamageSummary,
  DemandAnalytics,
  User,
  UserFineSummary,
} from '../../types';

export default function AdminPage() {
  const router = useRouter();
  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [activeTab, setActiveTab] = useState<'borrows' | 'demand' | 'books' | 'damaged' | 'users'>('borrows');

  // Data states
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [borrows, setBorrows] = useState<BorrowRecord[]>([]);
  const [borrowFilter, setBorrowFilter] = useState<string>('all');
  const [borrowSearch, setBorrowSearch] = useState<string>('');
  const [demandData, setDemandData] = useState<DemandAnalytics | null>(null);
  const [books, setBooks] = useState<Book[]>([]);
  const [booksSearch, setBooksSearch] = useState<string>('');
  const [booksTotal, setBooksTotal] = useState<number>(0);
  const [booksPage, setBooksPage] = useState<number>(1);
  const [userFines, setUserFines] = useState<UserFineSummary[]>([]);
  const [expandedUserRoll, setExpandedUserRoll] = useState<string | null>(null);

  const [loading, setLoading] = useState(true);
  const [bannerMsg, setBannerMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // Damaged returns
  const [damagedReturns, setDamagedReturns] = useState<BorrowRecord[]>([]);
  const [damageSummary, setDamageSummary] = useState<DamageSummary | null>(null);


  // Modals
  const [imposeModal, setImposeModal] = useState<{
    isOpen: boolean;
    rollNumber: string;
    borrowId?: number;
    amount: string;
    reason: string;
  }>({ isOpen: false, rollNumber: '', amount: '10.00', reason: 'Overdue fine (manual adjustment)' });

  const [waiveModal, setWaiveModal] = useState<{
    isOpen: boolean;
    borrowId?: number;
    rollNumber?: string;
    amount: string;
    reason: string;
  }>({ isOpen: false, amount: '', reason: 'Waived by librarian' });

  const [issueModal, setIssueModal] = useState<{
    isOpen: boolean;
    rollNumber: string;
    isbn10: string;
    days: number;
  }>({ isOpen: false, rollNumber: '', isbn10: '', days: 14 });

  const [bookModal, setBookModal] = useState<{
    isOpen: boolean;
    isEdit: boolean;
    isbn10: string;
    isbn13: string;
    title: string;
    authors: string;
    categories: string;
    publisher: string;
    publishedYear: string;
    numPages: string;
    totalCopies: number;
    description: string;
    thumbnail: string;
  }>({
    isOpen: false,
    isEdit: false,
    isbn10: '',
    isbn13: '',
    title: '',
    authors: '',
    categories: 'Fiction & Literature',
    publisher: '',
    publishedYear: '2024',
    numPages: '300',
    totalCopies: 5,
    description: '',
    thumbnail: '',
  });
  const [bookModalError, setBookModalError] = useState<string>('');

  // Auth verification
  useEffect(() => {
    const u = getStoredUser();
    setCurrentUser(u);
    if (u && u.is_admin) {
      fetchAllData();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchOverview = async () => {
    try {
      const data = await api.getAdminOverview();
      setOverview(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchBorrows = async () => {
    try {
      const statusParam = borrowFilter === 'all' ? undefined : borrowFilter;
      const data = await api.getAdminBorrows({ status: statusParam, q: borrowSearch });
      setBorrows(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDemand = async () => {
    try {
      const data = await api.getDemandAnalytics();
      setDemandData(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchBooks = async () => {
    try {
      const res = await api.getBooks({ q: booksSearch, page: booksPage, size: 15 });
      setBooks(res.items);
      setBooksTotal(res.total);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchUserFines = async () => {
    try {
      const data = await api.getAdminFinesDirectory();
      setUserFines(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchDamagedReturns = async () => {
    try {
      const [items, summary] = await Promise.all([
        api.getAdminDamagedReturns(),
        api.getAdminDamageSummary(),
      ]);
      setDamagedReturns(items);
      setDamageSummary(summary);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchAllData = async () => {
    setLoading(true);
    await Promise.all([fetchOverview(), fetchBorrows(), fetchDemand(), fetchBooks(), fetchUserFines(), fetchDamagedReturns()]);
    setLoading(false);
  };

  useEffect(() => {
    if (currentUser?.is_admin) {
      fetchBorrows();
    }
  }, [borrowFilter, borrowSearch]);

  useEffect(() => {
    if (currentUser?.is_admin) {
      fetchBooks();
    }
  }, [booksSearch, booksPage]);

  // Handlers
  const handleReturnBook = async (borrowId: number) => {
    try {
      const res = await api.adminReturnBook(borrowId);
      setBannerMsg({
        text: res.fine_amount > 0 && res.fine_status === 'imposed'
          ? `Book returned! Overdue fine of $${res.fine_amount.toFixed(2)} applied.`
          : 'Book marked as returned successfully.',
        type: 'success',
      });
      fetchOverview();
      fetchBorrows();
      fetchDemand();
    } catch (err: any) {
      setBannerMsg({ text: err.message || 'Failed to return book', type: 'error' });
    }
  };

  const handleIssueSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.adminIssueBook(issueModal.rollNumber, issueModal.isbn10, Number(issueModal.days) || 14);
      setBannerMsg({ text: 'Book loan successfully issued to student!', type: 'success' });
      setIssueModal({ isOpen: false, rollNumber: '', isbn10: '', days: 14 });
      fetchOverview();
      fetchBorrows();
      fetchDemand();
    } catch (err: any) {
      setBannerMsg({ text: err.message || 'Failed to issue book', type: 'error' });
    }
  };

  const handleImposeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amt = parseFloat(imposeModal.amount);
    if (isNaN(amt) || amt <= 0) {
      setBannerMsg({ text: 'Please enter a valid fine amount', type: 'error' });
      return;
    }
    try {
      await api.imposeFine({
        roll_number: imposeModal.rollNumber,
        borrow_id: imposeModal.borrowId,
        amount: amt,
        reason: imposeModal.reason,
      });
      setBannerMsg({ text: `Fine of $${amt.toFixed(2)} imposed successfully!`, type: 'success' });
      setImposeModal({ isOpen: false, rollNumber: '', amount: '10.00', reason: 'Overdue fine (manual adjustment)' });

      fetchOverview();
      fetchBorrows();
      fetchUserFines();
    } catch (err: any) {
      setBannerMsg({ text: err.message || 'Failed to impose fine', type: 'error' });
    }
  };

  const handleWaiveSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amt = waiveModal.amount.trim() ? parseFloat(waiveModal.amount) : undefined;
    try {
      await api.waiveFine({
        borrow_id: waiveModal.borrowId,
        roll_number: waiveModal.rollNumber,
        amount: amt,
        reason: waiveModal.reason,
      });
      setBannerMsg({ text: 'Fine waived / cleared successfully!', type: 'success' });
      setWaiveModal({ isOpen: false, amount: '', reason: 'Waived by librarian' });
      fetchOverview();
      fetchBorrows();
      fetchUserFines();
    } catch (err: any) {
      setBannerMsg({ text: err.message || 'Failed to waive fine', type: 'error' });
    }
  };

  const handleBookSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBookModalError('');
    try {
      if (bookModal.isEdit) {
        await api.updateBook(bookModal.isbn10, {
          title: bookModal.title,
          authors: bookModal.authors,
          categories: bookModal.categories,
          publisher: bookModal.publisher,
          published_year: bookModal.publishedYear ? parseInt(bookModal.publishedYear) : null,
          num_pages: bookModal.numPages ? parseInt(bookModal.numPages) : null,
          total_copies: Number(bookModal.totalCopies) || 5,
          description: bookModal.description,
          thumbnail: bookModal.thumbnail,
        });
        setBannerMsg({ text: `Book "${bookModal.title}" updated successfully!`, type: 'success' });
      } else {
        await api.createBook({
          isbn10: bookModal.isbn10,
          isbn13: bookModal.isbn13 || undefined,
          title: bookModal.title,
          authors: bookModal.authors,
          categories: bookModal.categories,
          publisher: bookModal.publisher,
          published_year: bookModal.publishedYear ? parseInt(bookModal.publishedYear) : null,
          num_pages: bookModal.numPages ? parseInt(bookModal.numPages) : null,
          total_copies: Number(bookModal.totalCopies) || 5,
          description: bookModal.description,
          thumbnail: bookModal.thumbnail,
        });
        setBannerMsg({ text: `New book "${bookModal.title}" added to catalog!`, type: 'success' });
      }
      setBookModal({ ...bookModal, isOpen: false });
      setBookModalError('');
      fetchOverview();
      fetchBooks();
      fetchDemand();
    } catch (err: any) {
      const msg = err?.response?.data?.detail
        ? (Array.isArray(err.response.data.detail)
            ? err.response.data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(' | ')
            : String(err.response.data.detail))
        : err?.message || 'Failed to save book. Please check your inputs and try again.';
      setBookModalError(msg);
    }
  };

  const handleDeleteBook = async (isbn10: string, title: string) => {
    if (!window.confirm(`Are you sure you want to remove "${title}" from the catalog?`)) return;
    try {
      await api.deleteBook(isbn10);
      setBannerMsg({ text: `Book "${title}" removed from catalog.`, type: 'success' });
      fetchOverview();
      fetchBooks();
      fetchDemand();
    } catch (err: any) {
      setBannerMsg({ text: err.message || 'Failed to delete book', type: 'error' });
    }
  };

  // Access denied view if not admin
  if (!loading && (!currentUser || !currentUser.is_admin)) {
    return (
      <div className="max-w-md mx-auto my-16 p-8 portal-stat-card text-center space-y-4">
        <span className="text-4xl block">🔒</span>
        <h2 className="text-xl font-bold text-navy">Administrator Access Required</h2>
        <p className="text-xs text-ink-light leading-relaxed">
          You must be signed in with an Administrator account to view and manage the library portal, fines, restocking analytics, and books.
        </p>
        <div className="pt-2">
          <Link
            href="/login"
            className="inline-block px-5 py-2 portal-btn-primary rounded-xl text-xs font-semibold shadow-md"
          >
            Sign In with Admin Credentials
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-parchment pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-2xl">⚡</span>
            <h1 className="text-2xl sm:text-3xl font-extrabold text-navy tracking-tight">
              Librarian & Admin Portal
            </h1>
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-gold/10 text-gold border border-gold/30">
              Admin Mode
            </span>
          </div>
          <p className="text-xs text-ink-light mt-1">
            Track student borrows, impose & waive late fines, analyze top demanding restocking priorities, and manage books.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setIssueModal({ isOpen: true, rollNumber: '', isbn10: '', days: 14 })}
            className="portal-btn-primary px-3.5 py-2 text-xs font-semibold rounded-xl shadow-sm flex items-center gap-1.5"
          >
            <span>+</span> Issue Book
          </button>
          <button
            onClick={() =>
              setBookModal({
                isOpen: true,
                isEdit: false,
                isbn10: '',
                isbn13: '',
                title: '',
                authors: '',
                categories: 'Fiction & Literature',
                publisher: '',
                publishedYear: '2024',
                numPages: '300',
                totalCopies: 5,
                description: '',
                thumbnail: '',
              })
            }
            className="portal-btn-secondary px-3.5 py-2 text-xs font-semibold rounded-xl shadow-sm flex items-center gap-1.5"
          >
            <span>+</span> Add Book
          </button>
        </div>
      </div>

      {/* Banner notification */}
      {bannerMsg && (
        <div
          className={`p-3.5 rounded-xl text-xs flex items-center justify-between shadow-md ${
            bannerMsg.type === 'success'
              ? 'bg-emerald-50 border border-emerald-200 text-emerald-800'
              : 'bg-red-50 border border-red-200 text-red-700'
          }`}
        >
          <span>{bannerMsg.text}</span>
          <button onClick={() => setBannerMsg(null)} className="text-xs opacity-70 hover:opacity-100">
            ✕
          </button>
        </div>
      )}

      {/* Overview Stat Cards */}
      {overview && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3.5">
          <div className="portal-stat-card p-4">
            <div className="text-ink-muted text-xs font-medium">Active Book Borrows</div>
            <div className="text-2xl font-bold text-navy mt-1">{overview.active_borrows}</div>
            <span className="text-[11px] text-ink-muted mt-0.5 block">Currently with students</span>
          </div>

          <div className="portal-stat-card p-4">
            <div className="text-ink-muted text-xs font-medium">Overdue Returns</div>
            <div className="text-2xl portal-stat-gold mt-1">{overview.overdue_borrows}</div>
            <span className="text-[11px] text-ink-muted mt-0.5 block">Past due date</span>
          </div>

          <div className="portal-stat-card p-4">
            <div className="text-ink-muted text-xs font-medium">Total Late Fines Imposed</div>
            <div className="text-2xl portal-stat-gold mt-1">₹{overview.total_fines_imposed.toFixed(2)}</div>
            <span className="text-[11px] text-ink-muted mt-0.5 block">All time fines</span>
          </div>

          <div className="portal-stat-card p-4">
            <div className="text-ink-muted text-xs font-medium">Outstanding Late Fines</div>
            <div className="text-2xl portal-stat-gold mt-1">₹{overview.total_fines_remaining.toFixed(2)}</div>
            <span className="text-[11px] text-ink-muted mt-0.5 block">Pending payment</span>
          </div>


          <div className="portal-stat-card p-4 col-span-2 sm:col-span-1">
            <div className="text-ink-muted text-xs font-medium">Catalog Volume</div>
            <div className="text-2xl font-bold text-navy mt-1">{overview.total_books}</div>
            <span className="text-[11px] text-ink-muted mt-0.5 block">Distinct book titles</span>
          </div>
        </div>
      )}

      {/* Tabs Navigation */}
      <div className="flex border-b border-parchment gap-2 overflow-x-auto pb-1">
        {[
          { id: 'borrows', label: '📋 Borrow & Late Fine Tracking', count: borrows.length },
          { id: 'demand', label: '📊 Restocking & Demand Analytics' },
          { id: 'books', label: '📚 Book Management', count: booksTotal },
          { id: 'users', label: '👥 Registered Users', count: userFines.length },
          { id: 'damaged', label: '🔍 Damaged Returns', count: damagedReturns.length },
        ].map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`px-4 py-2.5 rounded-xl text-xs font-semibold transition-all whitespace-nowrap flex items-center gap-1.5 ${
                isActive
                  ? 'bg-navy text-cream shadow-md'
                  : 'text-ink-muted hover:text-navy hover:bg-parchment/60'
              }`}
            >
              <span>{tab.label}</span>
              {tab.count !== undefined && (
                <span className={`px-1.5 py-0.2 rounded-full text-[10px] ${isActive ? 'bg-gold/20 text-gold' : 'bg-parchment text-ink-muted'}`}>
                  {tab.count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Tab 1: Borrows & Late Fines */}
      {activeTab === 'borrows' && (
        <div className="space-y-4">
          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-cream-light p-3 rounded-2xl border border-parchment">
            <div className="flex items-center gap-2 overflow-x-auto">
              {['all', 'active', 'overdue', 'returned', 'fines'].map((statusKey) => (
                <button
                  key={statusKey}
                  onClick={() => setBorrowFilter(statusKey)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                    borrowFilter === statusKey
                      ? 'bg-navy text-cream font-semibold'
                      : 'text-ink-muted hover:text-navy hover:bg-parchment'
                  }`}
                >
                  {statusKey === 'fines' ? 'Has Late Fine' : statusKey}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-2">
              <input
                type="text"
                placeholder="Search roll, student, title, ISBN..."
                value={borrowSearch}
                onChange={(e) => setBorrowSearch(e.target.value)}
                className="px-3.5 py-1.5 text-xs rounded-xl bg-cream border border-navy/30 text-ink placeholder-ink-muted focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold w-full sm:w-64 portal-input-gold"
              />
            </div>
          </div>

          {/* Table */}
          <div className="portal-table-wrap">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="portal-table-head">
                  <tr>
                    <th className="p-3.5">Student / Roll</th>
                    <th className="p-3.5">Book Title</th>
                    <th className="p-3.5">Dates</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Late Fines (Imposed / Remaining)</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-parchment">
                  {borrows.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-ink-muted">
                        No borrow transactions matching the selected filter.
                      </td>
                    </tr>
                  ) : (
                    borrows.map((b) => (
                      <tr key={b.id} className="portal-table-row-hover">
                        <td className="p-3.5">
                          <span className="font-semibold text-navy block">{b.user_name}</span>
                          <span className="text-ink-muted font-mono text-[11px]">Roll: {b.roll_number}</span>
                        </td>
                        <td className="p-3.5 max-w-xs">
                          <span className="font-medium text-navy block truncate">{b.book_title}</span>
                          <span className="text-ink-muted text-[11px] font-mono">ISBN: {b.isbn10}</span>
                        </td>
                        <td className="p-3.5 text-[11px] text-ink">
                          <div>Borrowed: {new Date(b.borrowed_at).toLocaleDateString()}</div>
                          <div>Due: {new Date(b.due_date).toLocaleDateString()}</div>
                          {b.returned_at && (
                            <div className="text-emerald-700">Ret: {new Date(b.returned_at).toLocaleDateString()}</div>
                          )}
                        </td>
                        <td className="p-3.5">
                          {b.status === 'active' && (
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-navy/10 text-navy border border-navy/20">
                              Active
                            </span>
                          )}
                          {b.status === 'overdue' && (
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-red-100 text-red-700 border border-red-200 animate-pulse">
                              Overdue
                            </span>
                          )}
                          {b.status === 'returned' && (
                            <span className="px-2 py-0.5 rounded-md text-[10px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-200">
                              Returned
                            </span>
                          )}
                        </td>
                        <td className="p-3.5">
                          {b.fine_amount > 0 ? (
                            <div>
                              <div className="flex items-center gap-1.5">
                                <span className="text-ink-muted">Total: ₹{b.fine_amount.toFixed(2)}</span>
                                <span className="portal-stat-gold font-bold">
                                  | Rem: ₹{b.fine_remaining.toFixed(2)}
                                </span>
                              </div>
                              {b.fine_reason && (
                                <span className="text-[10px] text-ink-muted block truncate max-w-xs">
                                  {b.fine_reason}
                                </span>
                              )}
                            </div>
                          ) : (
                            <span className="text-emerald-700 font-mono text-[11px]">None</span>
                          )}
                        </td>

                        <td className="p-3.5 text-right space-x-1.5">
                          {b.status !== 'returned' && (
                            <button
                              onClick={() => handleReturnBook(b.id)}
                              className="portal-btn-primary px-2.5 py-1 text-[11px] font-semibold rounded-lg"
                            >
                              Return
                            </button>
                          )}

                          <button
                            onClick={() =>
                              setImposeModal({
                                isOpen: true,
                                rollNumber: b.roll_number,
                                borrowId: b.id,
                                amount: '5.00',
                                reason: 'Overdue fine (manual adjustment)',
                              })
                            }
                            className="portal-btn-gold-outline px-2.5 py-1 text-[11px] font-semibold rounded-lg"
                          >
                            + Late Fine
                          </button>

                          {b.fine_remaining > 0 && (
                            <button
                              onClick={() =>
                                setWaiveModal({
                                  isOpen: true,
                                  borrowId: b.id,
                                  rollNumber: b.roll_number,
                                  amount: '',
                                  reason: 'Waived by librarian',
                                })
                              }
                              className="portal-btn-secondary px-2.5 py-1 text-[11px] font-semibold rounded-lg"
                            >
                              Waive Late Fine
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: Demand & Restocking Analytics */}
      {activeTab === 'demand' && demandData && (
        <div className="space-y-8">
          {/* Top 10 Most Demanding Books */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-bold text-navy flex items-center gap-2">
                  <span>🔥</span> Top 10 Most Demanding Books (Restock Priorities)
                </h3>
                <p className="text-xs text-ink-light">
                  Books with the highest borrow volumes, searches, views, and low stock status requiring immediate replenishment.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
              {demandData.top_demanding.map((b, idx) => {
                const isUrgent = b.restock_status === 'URGENT_RESTOCK';
                const isLow = b.restock_status === 'LOW_STOCK';

                return (
                  <div
                    key={b.isbn10}
                    className={`bg-cream-light border rounded-2xl p-4 flex gap-4 items-start shadow-sm transition-all ${
                      isUrgent
                        ? 'border-red-200'
                        : isLow
                        ? 'border-gold/30'
                        : 'border-parchment'
                    }`}
                  >
                    <div className="w-16 h-22 bg-parchment rounded-lg overflow-hidden shrink-0 border border-parchment flex items-center justify-center">
                      {b.thumbnail ? (
                        <img src={b.thumbnail} alt={b.title} className="w-full h-full object-cover" />
                      ) : (
                        <span className="text-xl">📖</span>
                      )}
                    </div>

                    <div className="min-w-0 flex-1 space-y-1.5">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <span className="text-[10px] font-bold font-mono text-gold uppercase">
                            #{idx + 1} Demand Rank
                          </span>
                          <h4 className="text-sm font-bold text-navy truncate">{b.title}</h4>
                          <p className="text-xs text-ink-muted truncate">{b.authors || 'Unknown Author'}</p>
                        </div>

                        {/* Restock Priority Badge */}
                        {isUrgent && (
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-extrabold uppercase tracking-wider bg-red-100 text-red-700 border border-red-200 shrink-0">
                            🚨 Urgent
                          </span>
                        )}
                        {isLow && (
                          <span className="px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider bg-gold/10 text-gold border border-gold/30 shrink-0">
                            ⚠️ Low Stock
                          </span>
                        )}
                        {!isUrgent && !isLow && (
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-100 text-emerald-700 border border-emerald-200 shrink-0">
                            ✓ Optimal
                          </span>
                        )}
                      </div>

                      {/* Metrics */}
                      <div className="grid grid-cols-3 gap-2 text-[11px] pt-1 border-t border-parchment">
                        <div>
                          <span className="text-ink-muted block text-[10px]">Borrows</span>
                          <span className="font-bold text-navy">{b.borrow_count}</span>
                        </div>
                        <div>
                          <span className="text-ink-muted block text-[10px]">Search Signals</span>
                          <span className="font-bold text-gold">{b.search_interaction_count}</span>
                        </div>
                        <div>
                          <span className="text-ink-muted block text-[10px]">Available / Total</span>
                          <span className={`font-bold ${b.copies_available === 0 ? 'text-red-600' : 'text-emerald-700'}`}>
                            {b.copies_available} / {b.total_copies}
                          </span>
                        </div>
                      </div>

                      {b.recommended_restock_qty > 0 && (
                        <div className="text-[11px] text-gold-dark bg-gold/5 px-2.5 py-1 rounded-lg border border-gold/20 flex items-center justify-between">
                          <span>Recommended Restock:</span>
                          <span className="font-bold font-mono">+{b.recommended_restock_qty}</span>
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Top 10 Least Demanding Books */}
          <div className="space-y-3 pt-4 border-t border-parchment">
            <div>
              <h3 className="text-lg font-bold text-navy flex items-center gap-2">
                <span>📉</span> Top 10 Least Demanding Books (Dormant Inventory)
              </h3>
              <p className="text-xs text-ink-light">
                Books with zero or minimal borrows and searches. The librarian can pause reorders or spotlight these titles in recommendations.
              </p>
            </div>

            <div className="portal-table-wrap">
              <table className="w-full text-left text-xs">
                <thead className="portal-table-head">
                  <tr>
                    <th className="p-3.5">Rank</th>
                    <th className="p-3.5">Book Title</th>
                    <th className="p-3.5">Category</th>
                    <th className="p-3.5">Borrows</th>
                    <th className="p-3.5">Search Volume</th>
                    <th className="p-3.5">Current Stock</th>
                    <th className="p-3.5 text-right">Librarian Advice</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-parchment">
                  {demandData.least_demanding.map((b, idx) => (
                    <tr key={b.isbn10} className="portal-table-row-hover">
                      <td className="p-3.5 font-mono text-ink-muted">#{idx + 1}</td>
                      <td className="p-3.5 font-medium text-navy max-w-xs truncate">
                        {b.title}
                        <span className="text-[10px] text-ink-muted block font-mono">ISBN: {b.isbn10}</span>
                      </td>
                      <td className="p-3.5 text-ink-light">{b.categories || 'General'}</td>
                      <td className="p-3.5 font-bold text-navy">{b.borrow_count}</td>
                      <td className="p-3.5 text-ink-light">{b.search_interaction_count}</td>
                      <td className="p-3.5 text-emerald-700 font-mono">{b.copies_available} / {b.total_copies} available</td>
                      <td className="p-3.5 text-right text-[11px] portal-stat-gold font-medium">
                        {b.borrow_count === 0 ? 'Pause reorders / Promote' : 'Adequate supply'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 3: Book Management (CRUD) */}
      {activeTab === 'books' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between gap-3 bg-cream-light p-3 rounded-2xl border border-parchment">
            <input
              type="text"
              placeholder="Search catalog books by title, author, ISBN..."
              value={booksSearch}
              onChange={(e) => {
                setBooksSearch(e.target.value);
                setBooksPage(1);
              }}
              className="px-3.5 py-1.5 text-xs rounded-xl bg-cream border border-navy/30 text-ink placeholder-ink-muted focus:outline-none focus:border-gold focus:ring-1 focus:ring-gold w-full sm:w-80 portal-input-gold"
            />
            <span className="text-xs text-ink-muted hidden sm:inline">Total: {booksTotal} books</span>
          </div>

          <div className="portal-table-wrap">
            <table className="w-full text-left text-xs">
              <thead className="portal-table-head">
                <tr>
                  <th className="p-3.5">Cover</th>
                  <th className="p-3.5">Title & Author</th>
                  <th className="p-3.5">ISBN</th>
                  <th className="p-3.5">Category</th>
                  <th className="p-3.5">Stock & Availability</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-parchment">
                {books.map((b) => {
                  const avail = b.copies_available !== undefined ? b.copies_available : (b.total_copies || 5);
                  const total = b.total_copies || 5;
                  const isOut = avail <= 0 || b.is_available === false;
                  return (
                    <tr key={b.isbn10} className="portal-table-row-hover">
                      <td className="p-3.5 w-12">
                        <div className="w-10 h-14 bg-parchment rounded overflow-hidden border border-parchment flex items-center justify-center">
                          {b.thumbnail ? (
                            <img src={b.thumbnail} alt={b.title} className="w-full h-full object-cover" />
                          ) : (
                            <span className="text-xs">📖</span>
                          )}
                        </div>
                      </td>
                      <td className="p-3.5 max-w-sm">
                        <span className="font-semibold text-navy block truncate">{b.title}</span>
                        <span className="text-ink-muted text-[11px] block truncate">{b.authors || 'Unknown Author'}</span>
                      </td>
                      <td className="p-3.5 font-mono text-ink-muted">{b.isbn10}</td>
                      <td className="p-3.5 text-ink">{b.categories || 'General'}</td>
                      <td className="p-3.5 font-mono text-xs">
                        <div className="flex flex-col gap-0.5">
                          <span className={`font-bold ${isOut ? 'text-red-600' : 'text-emerald-700'}`}>
                            {avail} / {total} Available
                          </span>
                          {isOut ? (
                            <span className="text-[10px] text-red-600 font-semibold uppercase tracking-wider">Out of Stock</span>
                          ) : (
                            <span className="text-[10px] text-ink-muted font-sans">
                              {total - avail} checked out
                            </span>
                          )}
                        </div>
                      </td>
                    <td className="p-3.5 text-right space-x-2">
                      <button
                        onClick={() =>
                          setBookModal({
                            isOpen: true,
                            isEdit: true,
                            isbn10: b.isbn10,
                            isbn13: b.isbn13 || '',
                            title: b.title,
                            authors: b.authors || '',
                            categories: b.categories || 'Fiction & Literature',
                            publisher: b.publisher || '',
                            publishedYear: b.published_year ? String(b.published_year) : '',
                            numPages: b.num_pages ? String(b.num_pages) : '',
                            totalCopies: b.total_copies || 5,
                            description: b.description || '',
                            thumbnail: b.thumbnail || '',
                          })
                        }
                        className="portal-btn-primary px-2.5 py-1 text-[11px] font-semibold rounded-lg"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteBook(b.isbn10, b.title)}
                        className="px-2.5 py-1 text-[11px] font-semibold bg-red-50 hover:bg-red-100 text-red-700 rounded-lg transition-colors border border-red-200"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                );
              })}

              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between text-xs text-ink-muted pt-2">
            <span>
              Page {booksPage} of {Math.ceil(booksTotal / 15) || 1}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setBooksPage((p) => Math.max(1, p - 1))}
                disabled={booksPage === 1}
                className="px-3 py-1.5 rounded-lg portal-stat-card border border-parchment disabled:opacity-40 text-ink portal-table-row-hover"
              >
                Previous
              </button>
              <button
                onClick={() => setBooksPage((p) => p + 1)}
                disabled={booksPage * 15 >= booksTotal}
                className="px-3 py-1.5 rounded-lg portal-stat-card border border-parchment disabled:opacity-40 text-ink portal-table-row-hover"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Registered Users & Borrow History */}
      {activeTab === 'users' && (
        <div className="space-y-4">
          <div className="portal-stat-card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-navy flex items-center gap-2">
                <span>👥</span> Registered Students Directory & Borrowing Records
              </h3>
              <p className="text-xs text-ink-light mt-0.5">
                Total Registered Users: <strong className="text-gold">{overview?.total_users || userFines.length}</strong>. Click any student to inspect all books they borrowed, quantities, borrow dates, return dates, and fine status.
              </p>
            </div>
          </div>

          <div className="portal-table-wrap">
            <div className="divide-y divide-parchment">
              {userFines.length === 0 ? (
                <div className="p-8 text-center text-xs text-ink-muted">
                  No registered users found.
                </div>
              ) : (
                userFines.map((u) => {
                  const isExpanded = expandedUserRoll === u.roll_number;
                  return (
                    <div key={u.roll_number} className="transition-colors">
                      {/* User Summary Row */}
                      <div
                        onClick={() => setExpandedUserRoll(isExpanded ? null : u.roll_number)}
                        className={`p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 cursor-pointer portal-table-row-hover ${
                          isExpanded ? 'bg-gold/5 border-l-4 border-gold' : ''
                        }`}
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-9 h-9 rounded-xl bg-navy/10 border border-navy/20 flex items-center justify-center text-navy font-bold text-sm shrink-0">
                            {u.name ? u.name.charAt(0).toUpperCase() : 'U'}
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-bold text-sm text-navy truncate">{u.name}</span>
                              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cream text-gold border border-gold/30">
                                {u.roll_number}
                              </span>
                            </div>
                            <span className="text-xs text-ink-light truncate block mt-0.5">{u.email}</span>
                          </div>
                        </div>

                        <div className="flex items-center gap-4 sm:gap-6 text-xs w-full sm:w-auto justify-between sm:justify-end">
                          <div className="text-center">
                            <span className="text-[10px] text-ink-muted block uppercase tracking-wider">Active Borrows</span>
                            <span className="font-bold text-navy text-sm">{u.active_borrows_count}</span>
                          </div>

                          <div className="text-center">
                            <span className="text-[10px] text-ink-muted block uppercase tracking-wider">Total Borrows</span>
                            <span className="font-bold text-ink text-sm">{u.total_borrows_count}</span>
                          </div>

                          <div className="text-center">
                            <span className="text-[10px] text-ink-muted block uppercase tracking-wider">Outstanding Late Fine</span>
                            <span className={`font-bold font-mono text-sm ${u.total_fines_remaining > 0 ? 'portal-stat-gold' : 'text-emerald-700'}`}>
                              ₹{u.total_fines_remaining.toFixed(2)}
                            </span>
                          </div>


                          <div className="flex items-center gap-1.5 shrink-0">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setImposeModal({
                                  isOpen: true,
                                  rollNumber: u.roll_number,
                                  amount: '5.00',
                                  reason: 'Manual fine',
                                });
                              }}
                              className="portal-btn-gold-outline px-2.5 py-1 text-[11px] font-semibold rounded-lg"
                            >
                              + Late Fine
                            </button>

                            {u.total_fines_remaining > 0 && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setWaiveModal({
                                    isOpen: true,
                                    rollNumber: u.roll_number,
                                    amount: '',
                                    reason: 'Waived by librarian',
                                  });
                                }}
                                className="portal-btn-secondary px-2.5 py-1 text-[11px] font-semibold rounded-lg"
                              >
                                Waive
                              </button>
                            )}

                            <span className="text-ink-muted text-xs ml-1">
                              {isExpanded ? '▲' : '▼'}
                            </span>
                          </div>
                        </div>
                      </div>

                      {/* Expanded Detailed Loan Records */}
                      {isExpanded && (
                        <div className="bg-cream p-4 border-t border-parchment space-y-3">
                          <div className="text-xs font-semibold text-ink-muted uppercase tracking-wider flex items-center justify-between">
                            <span>📚 Borrowed Books History for {u.name} ({u.loans?.length || 0} records)</span>
                            <span className="text-[11px] text-ink-muted lowercase font-normal">showing all quantities & dates</span>
                          </div>

                          {!u.loans || u.loans.length === 0 ? (
                            <div className="p-4 bg-cream-light rounded-xl text-center text-xs text-ink-muted border border-parchment">
                              This student has not borrowed any books yet.
                            </div>
                          ) : (
                            <div className="overflow-x-auto rounded-xl border border-parchment bg-cream-light">
                              <table className="w-full text-left text-xs">
                                <thead className="portal-table-head">
                                  <tr>
                                    <th className="p-3">Book Title & ISBN</th>
                                    <th className="p-3">Qty</th>
                                    <th className="p-3">Borrow Date</th>
                                    <th className="p-3">Due Date</th>
                                    <th className="p-3">Return Date</th>
                                    <th className="p-3">Status</th>
                                    <th className="p-3">Late Fine Imposed</th>
                                    <th className="p-3">Remaining Late Fine</th>
                                    <th className="p-3 text-right">Actions</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-parchment">
                                  {u.loans.map((loan) => (
                                    <tr key={loan.borrow_id} className="portal-table-row-hover">
                                      <td className="p-3 max-w-xs">
                                        <span className="font-semibold text-navy block truncate">{loan.book_title}</span>
                                        <span className="text-[10px] text-ink-muted font-mono">ISBN: {loan.isbn10}</span>
                                      </td>
                                      <td className="p-3 font-mono font-bold text-navy">{loan.quantity}</td>
                                      <td className="p-3 text-ink text-[11px]">
                                        {new Date(loan.borrowed_at).toLocaleDateString()}
                                      </td>
                                      <td className="p-3 text-ink text-[11px]">
                                        {new Date(loan.due_date).toLocaleDateString()}
                                      </td>
                                      <td className="p-3 text-[11px]">
                                        {loan.returned_at ? (
                                          <span className="text-emerald-700 font-medium">
                                            {new Date(loan.returned_at).toLocaleDateString()}
                                          </span>
                                        ) : (
                                          <span className="text-gold font-mono">Not returned</span>
                                        )}
                                      </td>
                                      <td className="p-3">
                                        {loan.status === 'active' && (
                                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-navy/10 text-navy border border-navy/20">
                                            Active
                                          </span>
                                        )}
                                        {loan.status === 'overdue' && (
                                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-red-100 text-red-700 border border-red-200 animate-pulse">
                                            Overdue
                                          </span>
                                        )}
                                        {loan.status === 'returned' && (
                                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-700 border border-emerald-200">
                                            Returned
                                          </span>
                                        )}
                                      </td>
                                      <td className="p-3 font-mono text-ink">
                                        ₹{loan.fine_amount.toFixed(2)}
                                      </td>
                                      <td className="p-3 font-mono font-bold">
                                        <span className={loan.fine_remaining > 0 ? 'portal-stat-gold' : 'text-emerald-700'}>
                                          ₹{loan.fine_remaining.toFixed(2)}
                                        </span>
                                      </td>
                                      <td className="p-3 text-right space-x-1">
                                        {loan.status !== 'returned' && (
                                          <button
                                            onClick={() => handleReturnBook(loan.borrow_id)}
                                            className="portal-btn-primary px-2 py-1 text-[10px] font-semibold rounded"
                                          >
                                            Return
                                          </button>
                                        )}
                                        <button
                                          onClick={() =>
                                            setImposeModal({
                                              isOpen: true,
                                              rollNumber: u.roll_number,
                                              borrowId: loan.borrow_id,
                                              amount: '5.00',
                                              reason: `Fine for ${loan.book_title}`,
                                            })
                                          }
                                          className="portal-btn-gold-outline px-2 py-1 text-[10px] font-semibold rounded"
                                        >
                                          Late Fine
                                        </button>
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      )}


      {/* Tab 5: Damaged Returns */}
      {activeTab === 'damaged' && (
        <div className="space-y-4">
          {/* Header & Summary Cards */}
          <div className="portal-stat-card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div>
              <h3 className="text-base font-bold text-navy flex items-center gap-2">
                <span>🔍</span> Damaged Book Returns
              </h3>
              <p className="text-xs text-ink-light mt-0.5">
                All book returns where damage was detected via AI inspection. A ₹100 fine is automatically applied for each damaged return.
              </p>
            </div>
            <button
              onClick={fetchDamagedReturns}
              className="portal-btn-primary px-3.5 py-2 text-xs font-semibold rounded-xl"
            >
              ↻ Refresh
            </button>
          </div>

          {/* Summary Cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="portal-stat-card p-4">
              <div className="text-ink-muted text-xs font-medium">Damaged Books Returned</div>
              <div className="text-2xl portal-stat-gold mt-1">{damageSummary?.damaged_count ?? damagedReturns.length}</div>
              <span className="text-[11px] text-ink-muted mt-0.5 block">Total damaged returns</span>
            </div>
            <div className="portal-stat-card p-4">
              <div className="text-ink-muted text-xs font-medium">Total Damage Fines</div>
              <div className="text-2xl portal-stat-gold mt-1">₹{(damageSummary?.total_damage_fines ?? 0).toFixed(2)}</div>
              <span className="text-[11px] text-ink-muted mt-0.5 block">From ₹100 per damaged return</span>
            </div>
          </div>

          {/* Damaged Returns Table */}
          <div className="portal-table-wrap">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="portal-table-head">
                  <tr>
                    <th className="p-3.5">Student / Roll</th>
                    <th className="p-3.5">Book</th>
                    <th className="p-3.5">Return Date</th>
                    <th className="p-3.5">Damage Types</th>
                    <th className="p-3.5">Fine Applied</th>
                    <th className="p-3.5 text-right">Image</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-parchment">
                  {damagedReturns.length === 0 ? (
                    <tr>
                      <td colSpan={6} className="p-8 text-center text-ink-muted">
                        <span className="block text-2xl mb-1 opacity-40">✅</span>
                        No damaged book returns found.
                      </td>
                    </tr>
                  ) : (
                    damagedReturns.map((r) => (
                      <tr key={r.id} className="portal-table-row-hover">
                        <td className="p-3.5">
                          <span className="font-semibold text-navy block">{r.user_name}</span>
                          <span className="text-ink-muted font-mono text-[11px]">Roll: {r.roll_number}</span>
                        </td>
                        <td className="p-3.5">
                          <span className="text-navy font-medium block truncate max-w-[180px]">{r.book_title}</span>
                          <span className="text-ink-muted text-[11px] font-mono">{r.isbn10}</span>
                        </td>
                        <td className="p-3.5 text-ink whitespace-nowrap">
                          {r.returned_at ? new Date(r.returned_at).toLocaleDateString() : '—'}
                        </td>
                        <td className="p-3.5">
                          {r.damage_types ? (
                            <div className="flex flex-wrap gap-1">
                              {r.damage_types.split(',').map((t, i) => (
                                <span key={i} className="px-2 py-0.5 rounded-full bg-red-50 border border-red-200 text-red-700 text-[10px] font-medium capitalize">
                                  {t.trim()}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span className="text-ink-muted">Detected</span>
                          )}
                        </td>
                        <td className="p-3.5">
                          <span className="portal-stat-gold font-bold">₹{r.fine_amount.toFixed(2)}</span>
                        </td>
                        <td className="p-3.5 text-right">
                          {r.damage_image ? (
                            <button
                              onClick={() => {
                                const win = window.open('', '_blank');
                                if (win) {
                                  win.document.write(`<html><body style="margin:0;background:#111;display:flex;align-items:center;justify-content:center;min-height:100vh"><img src="data:image/jpeg;base64,${r.damage_image}" style="max-width:100%;max-height:100vh;object-fit:contain"/></body></html>`);
                                }
                              }}
                              className="portal-btn-primary px-2.5 py-1 rounded-lg text-[11px] font-medium"
                            >
                              View
                            </button>
                          ) : (
                            <span className="text-ink-muted text-[11px]">N/A</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}


      {/* Impose Fine Modal */}
      {imposeModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm">
          <div className="portal-modal-card w-full max-w-md p-6 space-y-4">
            <h3 className="text-base font-bold text-navy flex items-center gap-2">
              <span>⚖️</span> Impose Late Fine on Student
            </h3>
            <form onSubmit={handleImposeSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-navy font-medium mb-1">Student Roll Number</label>
                <input
                  type="text"
                  value={imposeModal.rollNumber}
                  onChange={(e) => setImposeModal({ ...imposeModal, rollNumber: e.target.value })}
                  required
                  className="portal-modal-input w-full px-3 py-2 font-mono"
                />
              </div>

              <div>
                <label className="block text-navy font-medium mb-1">Fine Amount ($)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  value={imposeModal.amount}
                  onChange={(e) => setImposeModal({ ...imposeModal, amount: e.target.value })}
                  required
                  className="portal-modal-input w-full px-3 py-2 font-mono"
                />
              </div>

              <div>
                <label className="block text-navy font-medium mb-1">Reason</label>
                <input
                  type="text"
                  value={imposeModal.reason}
                  onChange={(e) => setImposeModal({ ...imposeModal, reason: e.target.value })}
                  required
                  placeholder="e.g. 5 days overdue, lost book, late return"
                  className="portal-modal-input w-full px-3 py-2"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setImposeModal({ ...imposeModal, isOpen: false })}
                  className="px-4 py-2 rounded-xl bg-parchment text-ink hover:bg-parchment-light border border-parchment transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="portal-btn-gold-outline px-5 py-2 rounded-xl font-semibold shadow-md"
                >
                  Impose Fine
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Waive Fine Modal */}
      {waiveModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm">
          <div className="portal-modal-card w-full max-w-md p-6 space-y-4">
            <h3 className="text-base font-bold text-navy flex items-center gap-2">
              <span>🕊️</span> Waive / Remove Fine
            </h3>
            <p className="text-xs text-ink-light">
              Clear or reduce fine balance for student {waiveModal.rollNumber ? `(${waiveModal.rollNumber})` : ''}.
            </p>
            <form onSubmit={handleWaiveSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-navy font-medium mb-1">Amount to Waive ($) (Leave blank to waive all)</label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  placeholder="All remaining fine"
                  value={waiveModal.amount}
                  onChange={(e) => setWaiveModal({ ...waiveModal, amount: e.target.value })}
                  className="portal-modal-input w-full px-3 py-2 font-mono"
                />
              </div>

              <div>
                <label className="block text-navy font-medium mb-1">Reason / Note</label>
                <input
                  type="text"
                  value={waiveModal.reason}
                  onChange={(e) => setWaiveModal({ ...waiveModal, reason: e.target.value })}
                  placeholder="e.g. Excused by librarian, payment verified"
                  className="portal-modal-input w-full px-3 py-2"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setWaiveModal({ ...waiveModal, isOpen: false })}
                  className="px-4 py-2 rounded-xl bg-parchment text-ink hover:bg-parchment-light border border-parchment transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="portal-btn-secondary px-5 py-2 rounded-xl font-semibold shadow-md"
                >
                  Waive Fine
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Issue Book Modal */}
      {issueModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm">
          <div className="portal-modal-card w-full max-w-md p-6 space-y-4">
            <h3 className="text-base font-bold text-navy flex items-center gap-2">
              <span>📖</span> Issue Book Borrow
            </h3>
            <form onSubmit={handleIssueSubmit} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-navy font-medium mb-1">Student Roll Number</label>
                <input
                  type="text"
                  value={issueModal.rollNumber}
                  onChange={(e) => setIssueModal({ ...issueModal, rollNumber: e.target.value })}
                  required
                  placeholder="e.g. 2410993251"
                  className="portal-modal-input w-full px-3 py-2 font-mono"
                />
              </div>

              <div>
                <label className="block text-navy font-medium mb-1">Book ISBN10</label>
                <input
                  type="text"
                  value={issueModal.isbn10}
                  onChange={(e) => setIssueModal({ ...issueModal, isbn10: e.target.value })}
                  required
                  placeholder="e.g. 0439708184"
                  className="portal-modal-input w-full px-3 py-2 font-mono"
                />
              </div>

              <div>
                <label className="block text-navy font-medium mb-1">Borrow Duration (Days)</label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  value={issueModal.days}
                  onChange={(e) => setIssueModal({ ...issueModal, days: parseInt(e.target.value) || 14 })}
                  className="portal-modal-input w-full px-3 py-2 font-mono"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => setIssueModal({ ...issueModal, isOpen: false })}
                  className="px-4 py-2 rounded-xl bg-parchment text-ink hover:bg-parchment-light border border-parchment transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="portal-btn-primary px-5 py-2 rounded-xl font-semibold shadow-md"
                >
                  Issue Borrow
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Add / Edit Book Modal */}
      {bookModal.isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm">
          <div className="portal-modal-card w-full max-w-xl p-6 space-y-4 max-h-[90vh] overflow-y-auto custom-scrollbar">
            <h3 className="text-base font-bold text-navy flex items-center gap-2">
              <span>{bookModal.isEdit ? '✏️' : '📚'}</span>
              <span>{bookModal.isEdit ? 'Edit Book Details' : 'Add New Book to Catalog'}</span>
            </h3>

            <form onSubmit={handleBookSubmit} className="space-y-3 text-xs">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-navy font-medium mb-1">ISBN10 (Primary Key)</label>
                  <input
                    type="text"
                    value={bookModal.isbn10}
                    disabled={bookModal.isEdit}
                    onChange={(e) => setBookModal({ ...bookModal, isbn10: e.target.value })}
                    required
                    placeholder="e.g. 0451185978"
                    minLength={1}
                    className="portal-modal-input w-full px-3 py-2 font-mono disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-navy font-medium mb-1">ISBN13 (Optional)</label>
                  <input
                    type="text"
                    value={bookModal.isbn13}
                    onChange={(e) => setBookModal({ ...bookModal, isbn13: e.target.value })}
                    className="portal-modal-input w-full px-3 py-2 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-navy font-medium mb-1">Book Title</label>
                <input
                  type="text"
                  value={bookModal.title}
                  onChange={(e) => setBookModal({ ...bookModal, title: e.target.value })}
                  required
                  className="portal-modal-input w-full px-3 py-2"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-navy font-medium mb-1">Author(s)</label>
                  <input
                    type="text"
                    value={bookModal.authors}
                    onChange={(e) => setBookModal({ ...bookModal, authors: e.target.value })}
                    required
                    className="portal-modal-input w-full px-3 py-2"
                  />
                </div>

                <div>
                  <label className="block text-navy font-medium mb-1">Category</label>
                  <input
                    type="text"
                    value={bookModal.categories}
                    onChange={(e) => setBookModal({ ...bookModal, categories: e.target.value })}
                    required
                    className="portal-modal-input w-full px-3 py-2"
                  />
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="block text-navy font-medium mb-1">Published Year</label>
                  <input
                    type="number"
                    value={bookModal.publishedYear}
                    onChange={(e) => setBookModal({ ...bookModal, publishedYear: e.target.value })}
                    className="portal-modal-input w-full px-3 py-2 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-navy font-medium mb-1">Num Pages</label>
                  <input
                    type="number"
                    value={bookModal.numPages}
                    onChange={(e) => setBookModal({ ...bookModal, numPages: e.target.value })}
                    className="portal-modal-input w-full px-3 py-2 font-mono"
                  />
                </div>

                <div>
                  <label className="block text-navy font-medium mb-1">Total Copies</label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={bookModal.totalCopies}
                    onChange={(e) => setBookModal({ ...bookModal, totalCopies: parseInt(e.target.value) || 5 })}
                    required
                    className="portal-modal-input w-full px-3 py-2 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-navy font-medium mb-1">Cover Thumbnail Image URL</label>
                <input
                  type="url"
                  value={bookModal.thumbnail}
                  onChange={(e) => setBookModal({ ...bookModal, thumbnail: e.target.value })}
                  placeholder="https://..."
                  className="portal-modal-input w-full px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-navy font-medium mb-1">Description / Synopsis</label>
                <textarea
                  rows={3}
                  value={bookModal.description}
                  onChange={(e) => setBookModal({ ...bookModal, description: e.target.value })}
                  className="portal-modal-input w-full px-3 py-2 custom-scrollbar"
                />
              </div>

              {/* Inline error alert */}
              {bookModalError && (
                <div className="flex items-start gap-2 px-4 py-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs">
                  <span className="mt-0.5 text-red-600">⚠️</span>
                  <span>{bookModalError}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-2 pt-3">
                <button
                  type="button"
                  onClick={() => { setBookModal({ ...bookModal, isOpen: false }); setBookModalError(''); }}
                  className="px-4 py-2 rounded-xl bg-parchment text-ink hover:bg-parchment-light border border-parchment transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="portal-btn-primary px-5 py-2 rounded-xl font-semibold shadow-md"
                >
                  {bookModal.isEdit ? 'Update Book' : 'Add to Catalog'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
