/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        studio: {
          bg: '#0f172a',
          card: '#1e293b',
          border: '#334155',
          text: '#e2e8f0',
          muted: '#94a3b8',
        },
        kid: {
          blue: '#3b82f6',
          'blue-light': '#60a5fa',
          green: '#22c55e',
          'green-light': '#4ade80',
          orange: '#f97316',
          'orange-light': '#fb923c',
          purple: '#a855f7',
          'purple-light': '#c084fc',
          pink: '#ec4899',
          'pink-light': '#f472b6',
          yellow: '#eab308',
          'yellow-light': '#facc15',
          red: '#ef4444',
          'red-light': '#f87171',
        },
      },
      borderRadius: {
        xl: '1rem',
        '2xl': '1.5rem',
      },
      boxShadow: {
        card: '0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -2px rgba(0, 0, 0, 0.2)',
        glow: '0 0 20px rgba(59, 130, 246, 0.3)',
      },
    },
  },
  plugins: [],
};
