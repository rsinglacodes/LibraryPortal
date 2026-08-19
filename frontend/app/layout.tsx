import type { Metadata } from 'next';
import './globals.css';
import Navbar from '../components/Navbar';

export const metadata: Metadata = {
  title: 'University Library Portal',
  description: 'University Library Portal with personalized recommendations, live catalog search, and AI assistant.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-cream text-ink antialiased">
        <Navbar>
          <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8">
            {children}
          </main>
          <footer className="bg-parchment/60 border-t border-parchment py-5 text-center text-xs text-ink-muted mt-auto">
            <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
              <span className="font-semibold text-navy font-serif">University Library Portal</span>
              <span className="text-ink-light font-mono text-[11px]">© 2026 University Library Portal. All rights reserved.</span>
            </div>
          </footer>
        </Navbar>
      </body>
    </html>
  );
}
