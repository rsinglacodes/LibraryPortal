export interface Book {
  isbn10: string;
  isbn13?: string | null;
  title: string;
  subtitle?: string | null;
  authors?: string | null;
  categories?: string | null;
  thumbnail?: string | null;
  description?: string | null;
  publisher?: string | null;
  published_year?: number | null;
  average_rating?: number | null;
  num_pages?: number | null;
  ratings_count?: number | null;
  total_copies?: number;
  copies_available?: number;
  is_available?: boolean;
  expected_return_date?: string | null;
}

export interface BookListResponse {
  items: Book[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

export interface User {
  roll_number: string;
  name: string;
  email: string;
  is_admin?: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface UserRating {
  roll_number: string;
  isbn10: string;
  rating: number;
}

export interface ChatMessage {
  id?: number;
  sender: 'user' | 'assistant';
  text: string;
  emotion?: string;
  suggestedBooks?: Book[];
  created_at?: string;
}

export interface ChatSessionMeta {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface BorrowRecord {
  id: number;
  roll_number: string;
  user_name: string;
  user_email: string;
  isbn10: string;
  book_title: string;
  book_authors?: string | null;
  book_thumbnail?: string | null;
  borrowed_at: string;
  due_date: string;
  returned_at?: string | null;
  status: 'active' | 'returned' | 'overdue';
  fine_amount: number;
  fine_paid: number;
  fine_waived: number;
  fine_remaining: number;
  fine_reason?: string | null;
  fine_status: 'none' | 'imposed' | 'paid' | 'waived' | 'partial';
  // Damage detection fields (populated on return-with-inspection)
  damage_detected?: boolean;
  damage_types?: string | null;
  damage_image?: string | null;
}

export interface AdminOverview {
  total_users: number;
  total_books: number;
  active_borrows: number;
  overdue_borrows: number;
  total_fines_imposed: number;
  total_fines_paid: number;
  total_fines_waived: number;
  total_fines_remaining: number;
}

export interface UserLoanItem {
  borrow_id: number;
  isbn10: string;
  book_title: string;
  book_authors?: string | null;
  book_thumbnail?: string | null;
  quantity: number;
  borrowed_at: string;
  due_date: string;
  returned_at?: string | null;
  status: 'active' | 'returned' | 'overdue';
  fine_amount: number;
  fine_paid: number;
  fine_waived: number;
  fine_remaining: number;
  fine_reason?: string | null;
}

export interface UserFineSummary {
  roll_number: string;
  name: string;
  email: string;
  active_borrows_count: number;
  total_borrows_count: number;
  total_fines_imposed: number;
  total_fines_paid: number;
  total_fines_waived: number;
  total_fines_remaining: number;
  loans?: UserLoanItem[];
}

export interface BookDemandItem {
  isbn10: string;
  title: string;
  authors?: string | null;
  categories?: string | null;
  thumbnail?: string | null;
  average_rating?: number | null;
  ratings_count?: number | null;
  total_copies: number;
  copies_available: number;
  borrow_count: number;
  search_interaction_count: number;
  unmet_demand_count?: number;
  demand_score: number;
  restock_status: 'URGENT_RESTOCK' | 'LOW_STOCK' | 'OPTIMAL' | 'LOW_DEMAND' | 'OVERSTOCKED';
  recommended_restock_qty: number;
}

export interface DemandAnalytics {
  top_demanding: BookDemandItem[];
  least_demanding: BookDemandItem[];
}

// ── Damage-detection types ────────────────────────────────────────────────────

export interface ReturnWithInspectionResponse {
  borrow_record: BorrowRecord;
  condition: 'good' | 'damaged';
  damage_detected: boolean;
  damage_types?: string | null;
  fine_applied: number;
}

export interface DamageSummary {
  damaged_count: number;
  total_damage_fines: number;
}
