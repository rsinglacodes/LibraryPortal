import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        /* ── Archival Backgrounds ─────────────────────── */
        cream:          '#F5F0E6',
        'cream-light':  '#FBF7EF',
        parchment:      '#EDE4D3',
        'parchment-light': '#F2EBD9',

        /* ── Navy Primary ────────────────────────────── */
        navy: {
          DEFAULT: '#1B2A41',
          light:   '#243450',
          dark:    '#111D2E',
          950:     '#0C1522',
        },

        /* ── Gold Accent ─────────────────────────────── */
        gold: {
          DEFAULT: '#C9A34E',
          light:   '#D4B366',
          muted:   '#A68A3E',
          50:      '#FBF5E6',
        },

        /* ── Ink (text on cream) ─────────────────────── */
        ink: {
          DEFAULT: '#2C2C2C',
          light:   '#5A5A5A',
          muted:   '#8A8275',
        },
      },
      fontFamily: {
        serif: ['Playfair Display', 'Georgia', 'Times New Roman', 'serif'],
        sans:  ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
