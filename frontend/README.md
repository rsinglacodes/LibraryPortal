# LibraryPortal — Frontend

Next.js 14 frontend for the University Library Portal.

## Tech Stack

- Next.js 14 (App Router)
- TypeScript
- React
- Tailwind CSS

## Getting Started

1. Copy the environment file:

   ```bash
   cp .env.local.example .env.local
   ```

2. Install dependencies:

   ```bash
   npm install
   ```

3. Run the development server:

   ```bash
   npm run dev
   ```

4. Open [http://localhost:3000](http://localhost:3000).

## Architecture

The frontend communicates with the FastAPI backend via HTTP/REST. It does **not** connect directly to Neon PostgreSQL.
