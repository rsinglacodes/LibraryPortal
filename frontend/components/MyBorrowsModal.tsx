'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Camera, Upload, AlertTriangle, BookOpen } from 'lucide-react';
import { api } from '../services/api';
import { BorrowRecord, ReturnWithInspectionResponse } from '../types';

// Allowed image MIME types for book condition upload
const ALLOWED_IMG_TYPES = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'];

interface MyBorrowsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onBookReturned?: () => void;
}

export default function MyBorrowsModal({ isOpen, onClose, onBookReturned }: MyBorrowsModalProps) {
  const [borrows, setBorrows] = useState<BorrowRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  // ── Image-upload step (Step 1) ──────────────────────────────────────────
  const [imgModal, setImgModal] = useState<{
    isOpen: boolean;
    record: BorrowRecord | null;
    file: File | null;
    previewUrl: string | null;
    error: string | null;
    checking: boolean;
  }>({
    isOpen: false, record: null, file: null, previewUrl: null, error: null, checking: false,
  });
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Inspection result + Rating step (Step 2) ────────────────────────────
  const [returnModal, setReturnModal] = useState<{
    isOpen: boolean;
    record: BorrowRecord | null;
    inspectionResult: ReturnWithInspectionResponse | null;
    rating: number;
    review: string;
    submitting: boolean;
  }>({
    isOpen: false,
    record: null,
    inspectionResult: null,
    rating: 5,
    review: '',
    submitting: false,
  });

  const fetchMyBorrows = async () => {
    setLoading(true);
    try {
      const data = await api.getMyBorrows();
      setBorrows(data);
    } catch (err: any) {
      console.error('Failed to load my borrows:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchMyBorrows();
      setMsg(null);
    }
  }, [isOpen]);

  // Cleanup preview URL on unmount
  useEffect(() => {
    return () => { if (imgModal.previewUrl) URL.revokeObjectURL(imgModal.previewUrl); };
  }, [imgModal.previewUrl]);

  // Step 1: Open image upload modal
  const openReturnModal = (record: BorrowRecord) => {
    if (imgModal.previewUrl) URL.revokeObjectURL(imgModal.previewUrl);
    setImgModal({ isOpen: true, record, file: null, previewUrl: null, error: null, checking: false });
  };

  const closeImgModal = () => {
    if (imgModal.previewUrl) URL.revokeObjectURL(imgModal.previewUrl);
    setImgModal({ isOpen: false, record: null, file: null, previewUrl: null, error: null, checking: false });
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0] ?? null;
    if (!file) return;
    if (!ALLOWED_IMG_TYPES.includes(file.type.toLowerCase())) {
      setImgModal((p) => ({ ...p, error: 'Invalid file type. Use JPG, PNG, or WEBP.', file: null, previewUrl: null }));
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setImgModal((p) => ({ ...p, error: 'Image too large. Max 10 MB.', file: null, previewUrl: null }));
      return;
    }
    if (imgModal.previewUrl) URL.revokeObjectURL(imgModal.previewUrl);
    const url = URL.createObjectURL(file);
    setImgModal((p) => ({ ...p, file, previewUrl: url, error: null }));
  };

  // Step 2: Send to backend (Roboflow inspection + return)
  const handleCheckCondition = async () => {
    if (!imgModal.file || !imgModal.record) {
      setImgModal((p) => ({ ...p, error: 'Please upload a book image first.' }));
      return;
    }
    setImgModal((p) => ({ ...p, checking: true, error: null }));
    try {
      const result = await api.returnMyBookWithInspection(imgModal.record.id, imgModal.file);
      // Close img modal, open rating modal with result
      if (imgModal.previewUrl) URL.revokeObjectURL(imgModal.previewUrl);
      setImgModal({ isOpen: false, record: null, file: null, previewUrl: null, error: null, checking: false });
      setReturnModal({ isOpen: true, record: imgModal.record, inspectionResult: result, rating: 5, review: '', submitting: false });
    } catch (err: any) {
      setImgModal((p) => ({ ...p, checking: false, error: err.message || 'Could not check condition. Try again.' }));
    }
  };

  // Step 3: Submit optional rating after return-with-inspection is done
  const handleConfirmReturn = async (includeRating: boolean) => {
    if (!returnModal.record || !returnModal.inspectionResult) return;
    const { isbn10, book_title } = returnModal.record;
    const result = returnModal.inspectionResult;

    setReturnModal((prev) => ({ ...prev, submitting: true }));
    setMsg(null);

    if (includeRating && isbn10) {
      try {
        await api.rateBook(isbn10, returnModal.rating, returnModal.review.trim() || undefined);
      } catch (rErr: any) {
        console.warn('Rating note:', rErr);
      }
    }

    setReturnModal({ isOpen: false, record: null, inspectionResult: null, rating: 5, review: '', submitting: false });

    let successMsg = `✓ "${book_title}" returned successfully!`;
    if (result.damage_detected) {
      successMsg += ` Damage detected — ₹${result.fine_applied.toFixed(2)} Late Fine applied.`;
    } else {
      successMsg += ' No damage detected. ✓';
    }
    if (includeRating) successMsg += ' Thank you for your review.';

    setMsg({ text: successMsg, type: 'success' });
    fetchMyBorrows();
    if (onBookReturned) onBookReturned();
  };

  if (!isOpen) return null;

  const totalFinesRemaining = borrows.reduce((acc, b) => acc + (b.fine_remaining || 0), 0);
  const activeBorrows = borrows.filter((b) => b.status === 'active' || b.status === 'overdue');

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-navy-950/70 backdrop-blur-sm animate-in fade-in duration-150">
      <div className="portal-modal-card w-full max-w-3xl max-h-[85vh] flex flex-col overflow-auto relative">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-parchment bg-cream">
          <div className="flex items-center gap-2.5">
            <BookOpen className="w-5 h-5 text-navy"/>
            <div>
              <h2 className="text-sm font-bold text-ink mt-3 mb-1.5 flex items-center gap-1.5">My Borrowed Books & Late Fines</h2>
              <p className="text-xs text-ink-light">View active borrows, due dates, and pending late fine balances.</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-ink-muted hover:text-navy rounded-lg hover:bg-parchment transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Status Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 p-4 bg-cream-light border-b border-parchment text-xs">
          <div className="portal-stat-card p-2.5">
            <span className="text-ink-muted block text-[11px]">Active Borrows</span>
            <span className="text-base font-bold text-ink mt-3.5 mb-2 flex items-center gap-1.5">{activeBorrows.length}</span>
          </div>
          <div className="portal-stat-card p-2.5">
            <span className="text-ink-muted block text-[11px]">Total Borrows Ever</span>
            <span className="text-base font-bold text-navy">{borrows.length}</span>
          </div>
          <div className="portal-stat-card p-2.5 col-span-2 sm:col-span-1">
            <span className="text-ink-muted block text-[11px]">Outstanding Late Fines</span>
            <span className={`text-base font-bold ${totalFinesRemaining > 0 ? 'portal-stat-gold' : 'text-emerald-700'}`}>
              ₹{totalFinesRemaining.toFixed(2)}
            </span>
          </div>
        </div>

        {/* Message Banner */}
        {msg && (
          <div
            className={`mx-4 mt-3 p-3 rounded-xl text-xs flex items-center justify-between ${
              msg.type === 'success'
                ? 'bg-emerald-50 border border-emerald-300 text-emerald-800'
                : 'bg-red-50 border border-red-200 text-red-700'
            }`}
          >
            <span>My Borrows & Late Fines</span>
            <button onClick={() => setMsg(null)} className="text-xs opacity-70 hover:opacity-100">
              ✕
            </button>
          </div>
        )}

        {/* Body List */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3 custom-scrollbar">
          {loading ? (
            <div className="py-12 text-center text-xs text-ink-muted">Loading loan records...</div>
          ) : borrows.length === 0 ? (
            <div className="py-12 text-center text-xs text-ink-muted">
              <BookOpen className="w-8 h-8 text-navy opacity-40"/>
              You have not borrowed any books yet. Browse the catalog to borrow titles!
            </div>
          ) : (
            borrows.map((b) => {
              const isOverdue = b.status === 'overdue';
              const isReturned = b.status === 'returned';

              return (
                <div
                  key={b.id}
                  className="portal-stat-card p-3.5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 hover:border-gold transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-14 bg-parchment rounded overflow-hidden shrink-0 border border-parchment flex items-center justify-center">
                      {b.book_thumbnail ? (
                        <img src={b.book_thumbnail} alt={b.book_title} className="w-full h-full object-cover" />
                      ) : (
                        <BookOpen className="w-5 h-5 text-navy"/>
                      )}
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-sm font-semibold text-navy truncate">{b.book_title}</h4>
                      <p className="text-xs text-ink-muted truncate">{b.book_authors || 'Unknown Author'}</p>
                      <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-ink-light">
                        <span>Borrowed: {new Date(b.borrowed_at).toLocaleDateString()}</span>
                        <span>•</span>
                        <span>Due: {new Date(b.due_date).toLocaleDateString()}</span>
                        {isReturned && (
                          <>
                            <span>•</span>
                            <span className="text-emerald-700 font-medium">Returned</span>
                          </>
                        )}
                        {isOverdue && (
                          <>
                            <span>•</span>
                            <span className="text-red-700 font-bold">Overdue (₹10 base + ₹10/day)</span>
                          </>
                        )}
                      </div>
                    </div>
                  </div>

                  <div className="flex items-center justify-between sm:justify-end w-full sm:w-auto gap-3 pt-2 sm:pt-0 border-t sm:border-t-0 border-parchment shrink-0">
                    {/* Fine badge */}
                    {b.fine_remaining > 0 ? (
                      <div className="text-right">
                        <span className="text-[10px] uppercase font-semibold text-red-600 block">Late Fine Pending</span>
                        <span className="text-xs font-bold portal-stat-gold font-mono">₹{b.fine_remaining.toFixed(2)}</span>
                      </div>
                    ) : (
                      <span className="text-[11px] text-emerald-700 font-medium hidden sm:inline">No Late Fine</span>
                    )}

                    {/* Return Action */}
                    {!isReturned && (
                      <button
                        onClick={() => openReturnModal(b)}
                        className="portal-btn-primary px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-sm"
                      >
                        Return Book
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-parchment bg-cream text-right">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-parchment hover:bg-parchment-light text-navy transition-colors border border-parchment"
          >
            Close
          </button>
        </div>

        {/* ── STEP 1: Image Upload Modal ──────────────────────────────── */}
        {imgModal.isOpen && imgModal.record && (
          <div className="absolute inset-0 z-50 bg-navy-950/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150">
            <div className="portal-modal-card w-full max-w-md p-6 space-y-4">
              {/* Header */}
              <div className="flex items-center justify-between border-b border-navy pb-3">
                  <div className="flex items-center gap-2">
                    <Camera className="w-5 h-5 text-navy"/>
                    <h3 className="text-base font-bold text-navy">Return Book — Upload Image</h3>
                  </div>
                  {!imgModal.checking && (
                    <button onClick={closeImgModal} className="text-ink-muted hover:text-navy text-sm">✕</button>
                  )}
                </div>

              {/* Book info */}
              <div className="space-y-0.5">
                <p className="text-xs text-gold font-medium">Returning:</p>
                  <p className="text-sm font-semibold text-navy">{imgModal.record.book_title}</p>
                  <p className="text-[11px] text-ink-muted">{imgModal.record.book_authors || 'Unknown Author'}</p>
              </div>

              {/* Instruction */}
              <div className="bg-gold/10 border-l-4 border-gold rounded-xl p-3 text-xs text-navy">
                  Please upload a clear photo of the physical book. Our AI will check its condition before completing the return.
                </div>

              {/* Upload area */}
              {!imgModal.checking ? (
                <div className="space-y-2">
                  <label className="block text-xs font-medium text-navy">Book Image</label>
                  <div
                    className="border-2 border-dashed border-navy hover:border-gold rounded-xl p-4 flex flex-col items-center gap-2 cursor-pointer transition-colors bg-cream-light"
                    onClick={() => fileInputRef.current?.click()}
                  >
                    {imgModal.previewUrl ? (
                      <img src={imgModal.previewUrl} alt="Book" className="max-h-36 rounded-lg object-contain" />
                    ) : (
                      <>
                        <Upload className="w-8 h-8 text-navy opacity-30"/>
                        <span className="text-xs text-ink-muted">Click to choose an image</span>
                        <span className="text-[11px] text-ink-muted">JPG, PNG, WEBP · max 10 MB</span>
                      </>
                    )}
                  </div>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept="image/jpeg,image/jpg,image/png,image/webp"
                    className="hidden"
                    onChange={handleFileChange}
                  />
                  {imgModal.file && (
                    <p className="text-[11px] text-emerald-700">
                      ✓ {imgModal.file.name} ({(imgModal.file.size / 1024).toFixed(0)} KB) — ready
                    </p>
                  )}
                  {imgModal.error && (
                    <p className="text-[11px] text-red-700">{imgModal.error}</p>
                  )}
                </div>
              ) : (
                <div className="flex flex-col items-center gap-3 py-4">
                  <div className="w-10 h-10 border-4 border-navy border-t-transparent rounded-full animate-spin" />
                  <p className="text-xs text-ink-muted">Analysing book condition with AI...</p>
                </div>
              )}

              {/* Buttons */}
              {!imgModal.checking && (
                <div className="flex gap-2 pt-1">
                  <button
                     onClick={closeImgModal}
                     className="flex-1 portal-btn-secondary"
                   >
                     Cancel
                   </button>
                  <button
                    onClick={handleCheckCondition}
                    disabled={!imgModal.file}
                    className="flex-1 px-4 py-2 rounded-xl text-xs font-bold portal-btn-primary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    Check Condition
                  </button>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ── STEP 2: Inspection Result + Rating Modal ────────────────── */}
        {returnModal.isOpen && returnModal.record && returnModal.inspectionResult && (
          <div className="absolute inset-0 z-50 bg-navy-950/75 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-150">
            <div className="portal-modal-card w-full max-w-md p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-parchment pb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5 text-navy"/>
                    <h3 className="text-base font-bold text-navy">Book Condition & Review</h3>
                </div>
              </div>

              <div className="space-y-0.5">
                <p className="text-xs text-ink-muted">Returning:</p>
                <p className="text-sm font-semibold text-navy">{returnModal.record.book_title}</p>
                <p className="text-[11px] text-ink-muted">{returnModal.record.book_authors || 'Unknown Author'}</p>
              </div>

              {/* Condition Result */}
              {returnModal.inspectionResult.condition === 'damaged' ? (
                <div className="bg-red-50 border border-red-200 rounded-xl p-3.5 text-center space-y-1.5">
                  <p className="text-sm font-extrabold text-red-700 uppercase tracking-wider">DAMAGED</p>
                  <p className="text-xs text-red-700">Damage was detected in the uploaded book image.</p>
                  {returnModal.inspectionResult.damage_types && (
                    <p className="text-[11px] text-red-600">Detected: {returnModal.inspectionResult.damage_types}</p>
                  )}
                  <div className="mt-1 inline-block px-3 py-1.5 bg-red-100 rounded-lg">
                    <span className="text-xs font-bold text-red-800">Fine Applied: ₹{returnModal.inspectionResult.fine_applied.toFixed(2)}</span>
                  </div>
                </div>
              ) : (
                <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-center space-y-1">
                  <p className="text-lg font-extrabold text-ink mt-4 mb-2.5">GOOD CONDITION</p>
                  <p className="text-xs text-emerald-700">No significant damage was detected. No fine applied.</p>
                </div>
              )}

              {/* Rating Selector */}
              <div className="space-y-1.5 bg-cream p-3.5 rounded-xl border border-parchment">
                <label className="block text-xs font-medium text-navy">
                  How would you rate this book? (1–5 Stars)
                </label>
                <select
                  value={returnModal.rating}
                  onChange={(e) => setReturnModal({ ...returnModal, rating: Number(e.target.value) })}
                  className="w-full bg-cream-light text-navy font-bold text-xs rounded-lg px-3 py-2 border border-navy/30 focus:outline-none focus:border-gold font-mono portal-input-gold"
                >
                  <option value={5}>5 ★★★★★ (Masterpiece / Highly Recommended)</option>
                  <option value={4}>4 ★★★★☆ (Great Read)</option>
                  <option value={3}>3 ★★★☆☆ (Good / Average)</option>
                  <option value={2}>2 ★★☆☆☆ (Below Average)</option>
                  <option value={1}>1 ★☆☆☆☆ (Poor / Disliked)</option>
                </select>
                <label className="block text-xs font-medium text-navy pt-2">Write a review (optional):</label>
                <textarea
                  placeholder="Share your thoughts on this book for other students..."
                  value={returnModal.review}
                  onChange={(e) => setReturnModal({ ...returnModal, review: e.target.value })}
                  rows={3}
                  maxLength={500}
                  className="portal-modal-input w-full px-3 py-2 text-xs"
                />
                <div className="text-right text-[10px] text-ink-muted">{returnModal.review.length}/500</div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row items-center justify-end gap-2 pt-1">
                <button
                  type="button"
                  onClick={() => handleConfirmReturn(false)}
                  disabled={returnModal.submitting}
                  className="w-full sm:w-auto px-4 py-2 rounded-xl text-xs font-medium bg-parchment hover:bg-parchment-light text-navy transition-colors disabled:opacity-50"
                >
                  Confirm without Review
                </button>
                <button
                  type="button"
                  onClick={() => handleConfirmReturn(true)}
                  disabled={returnModal.submitting}
                  className="portal-btn-primary w-full sm:w-auto px-5 py-2 rounded-xl text-xs font-bold disabled:opacity-50 shadow-md flex items-center justify-center gap-1.5"
                >
                  {returnModal.submitting ? 'Processing...' : '✓ Submit Review & Confirm'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
