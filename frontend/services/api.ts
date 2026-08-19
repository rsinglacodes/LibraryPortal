import { AuthResponse, Book, BookListResponse, User, UserRating } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const getStoredToken = (): string | null => {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('library_portal_token');
};

export const setStoredToken = (token: string | null) => {
  if (typeof window === 'undefined') return;
  if (token) {
    localStorage.setItem('library_portal_token', token);
  } else {
    localStorage.removeItem('library_portal_token');
  }
};

export const getStoredUser = (): User | null => {
  if (typeof window === 'undefined') return null;
  const userStr = localStorage.getItem('library_portal_user');
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
};

export const setStoredUser = (user: User | null) => {
  if (typeof window === 'undefined') return;
  if (user) {
    localStorage.setItem('library_portal_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('library_portal_user');
  }
  window.dispatchEvent(new Event('library_portal_auth_change'));
};

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const token = getStoredToken();

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `HTTP Error ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData && errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((e: any) => e.msg || JSON.stringify(e)).join(', ');
        }
      }
    } catch {
      // ignore json parse error
    }
    throw new Error(errorMessage);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // Auth
  login: (payload: { roll_number?: string; email?: string; password?: string }) =>
    request<AuthResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  register: (payload: { roll_number: string; name: string; email: string; password?: string }) =>
    request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getMe: () => request<User>('/auth/me'),

  // Books Catalog
  getBooks: (params: { q?: string; category?: string; page?: number; size?: number }) => {
    const query = new URLSearchParams();
    if (params.q) query.set('q', params.q);
    if (params.category) query.set('category', params.category);
    if (params.page) query.set('page', params.page.toString());
    if (params.size) query.set('size', params.size.toString());
    return request<BookListResponse>(`/books?${query.toString()}`);
  },

  getCategories: () => request<string[]>('/books/categories'),

  getBookDetail: (isbn10: string) => request<Book>(`/books/${isbn10}`),

  // Ratings & Reviews
  rateBook: (isbn10: string, rating: number, review?: string) =>
    request<any>('/ratings', {
      method: 'POST',
      body: JSON.stringify({ isbn10, rating, review: review?.trim() || undefined }),
    }),

  getBookReviews: (isbn10: string, limit = 2) =>
    request<
      Array<{
        rating_id: number;
        roll_number: string;
        user_name: string;
        rating: number;
        review?: string;
        created_at?: string;
      }>
    >(`/ratings/book/${isbn10}?limit=${limit}`),

  getMyRatings: () => request<UserRating[]>('/ratings/me'),


  // Recommendations & User Signals
  getRecommendations: (limit = 12) => request<Book[]>(`/recommendations?limit=${limit}`),

  getUserSignals: () =>
    request<{
      roll_number: string;
      total_ratings: number;
      total_explored: number;
      total_searches: number;
      total_chats: number;
      active_profile: boolean;
    }>('/recommendations/signals'),

  trackInteraction: (params: { interaction_type: string; content?: string; isbn10?: string; roll_number?: string }) =>
    request<{ status: string }>('/recommendations/track', {
      method: 'POST',
      body: JSON.stringify(params),
    }),

  // Chat
  sendChatMessage: (message: string, session_id = 'default') =>
    request<{
      response: string;
      emotion: string;
      suggested_books: any[];
    }>('/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id }),
    }),

  streamChatMessage: async (
    message: string,
    session_id = 'default',
    callbacks: {
      onToken: (token: string) => void;
      onDone: (data: { emotion: string; suggested_books: any[]; full_text: string }) => void;
      onError: (err: any) => void;
    },
    signal?: AbortSignal
  ) => {
    const token = getStoredToken();
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message, session_id }),
        signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}`);
      }

      if (!response.body) {
        throw new Error('ReadableStream not supported in response');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let donePayload: { emotion: string; suggested_books: any[]; full_text: string } | null = null;
      let accumulatedText = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const eventData = JSON.parse(trimmed.slice(6));
              if (eventData.type === 'token' && eventData.token) {
                accumulatedText += eventData.token;
                callbacks.onToken(eventData.token);
              } else if (eventData.type === 'done') {
                donePayload = {
                  emotion: eventData.emotion || 'neutral',
                  suggested_books: eventData.suggested_books || [],
                  full_text: eventData.full_text || accumulatedText,
                };
              }
            } catch (parseErr) {
              console.warn('SSE parse error:', parseErr);
            }
          }
        }
      }

      if (donePayload) {
        callbacks.onDone(donePayload);
      } else {
        callbacks.onDone({
          emotion: 'neutral',
          suggested_books: [],
          full_text: accumulatedText,
        });
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Stream aborted by user');
        return;
      }
      callbacks.onError(err);
    }
  },

  resetChatSession: (session_id = 'default') =>
    request<{
      status: string;
      session_id: string;
      message: string;
    }>('/chat/reset', {
      method: 'POST',
      body: JSON.stringify({ session_id }),
    }),

  getChatSessions: () =>
    request<
      {
        id: string;
        title: string;
        created_at: string;
        updated_at: string;
      }[]
    >('/chat/sessions'),

  getChatSessionDetail: (session_id: string) =>
    request<{
      session_id: string;
      title: string;
      messages: {
        id?: number;
        sender: 'user' | 'assistant';
        text: string;
        emotion?: string;
        suggested_books: any[];
        created_at?: string;
      }[];
    }>(`/chat/sessions/${session_id}`),

  deleteChatSession: (session_id: string) =>
    request<{ status: string; session_id: string }>(`/chat/sessions/${session_id}`, {
      method: 'DELETE',
    }),

  updateChatSessionTitle: (session_id: string, title: string) =>
    request<{ id: string; title: string }>(`/chat/sessions/${session_id}/title`, {
      method: 'PUT',
      body: JSON.stringify({ title }),
    }),

  // Student Borrows
  getMyBorrows: () => request<import('../types').BorrowRecord[]>('/borrows/my'),

  borrowBook: (isbn10: string, days = 14) =>
    request<import('../types').BorrowRecord>('/borrows/borrow', {
      method: 'POST',
      body: JSON.stringify({ isbn10, days }),
    }),

  returnMyBook: (borrow_id: number) =>
    request<import('../types').BorrowRecord>(`/borrows/return/${borrow_id}`, {
      method: 'POST',
    }),

  /**
   * Return a book with Roboflow damage inspection.
   * Sends image as multipart/form-data — backend determines fine amount.
   * The frontend NEVER sends a fine amount; it is always computed server-side.
   */
  returnMyBookWithInspection: (borrow_id: number, imageFile: File): Promise<import('../types').ReturnWithInspectionResponse> => {
    const url = `${API_BASE_URL}/borrows/return-with-inspection/${borrow_id}`;
    const token = getStoredToken();
    const formData = new FormData();
    formData.append('file', imageFile);

    return fetch(url, {
      method: 'POST',
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        // Do NOT set Content-Type — browser sets it with the correct boundary
      },
      body: formData,
    }).then(async (res) => {
      if (!res.ok) {
        let msg = `HTTP ${res.status}`;
        try { const d = await res.json(); msg = d?.detail || msg; } catch {}
        throw new Error(msg);
      }
      return res.json();
    });
  },

  getAdminDamagedReturns: () =>
    request<import('../types').BorrowRecord[]>('/admin/damaged-returns'),

  getAdminDamageSummary: () =>
    request<import('../types').DamageSummary>('/admin/damage-summary'),

  // Admin Portal API
  getAdminOverview: () => request<import('../types').AdminOverview>('/admin/overview'),

  getAdminBorrows: (params?: { status?: string; q?: string }) => {
    const query = new URLSearchParams();
    if (params?.status) query.set('status', params.status);
    if (params?.q) query.set('q', params.q);
    return request<import('../types').BorrowRecord[]>(`/admin/borrows?${query.toString()}`);
  },

  adminIssueBook: (roll_number: string, isbn10: string, days = 14) =>
    request<import('../types').BorrowRecord>('/admin/borrows/issue', {
      method: 'POST',
      body: JSON.stringify({ roll_number, isbn10, days }),
    }),

  adminReturnBook: (borrow_id: number) =>
    request<import('../types').BorrowRecord>(`/admin/borrows/${borrow_id}/return`, {
      method: 'POST',
    }),

  getAdminFinesDirectory: () => request<import('../types').UserFineSummary[]>('/admin/fines'),

  imposeFine: (payload: { roll_number: string; borrow_id?: number; amount: number; reason: string }) =>
    request<import('../types').BorrowRecord>('/admin/fines/impose', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  waiveFine: (payload: { borrow_id?: number; roll_number?: string; amount?: number; reason?: string }) =>
    request<import('../types').BorrowRecord[]>('/admin/fines/waive', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  payFine: (payload: { borrow_id?: number; roll_number?: string; amount: number }) =>
    request<import('../types').BorrowRecord[]>('/admin/fines/pay', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  getDemandAnalytics: () => request<import('../types').DemandAnalytics>('/admin/analytics/demand'),

  createBook: (payload: any) =>
    request<Book>('/admin/books', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  updateBook: (isbn10: string, payload: any) =>
    request<Book>(`/admin/books/${isbn10}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),

  deleteBook: (isbn10: string) =>
    request<{ status: string; deleted_isbn10: string }>(`/admin/books/${isbn10}`, {
      method: 'DELETE',
    }),
};

