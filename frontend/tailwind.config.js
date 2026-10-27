/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        islamic: {
          950: '#051611',
          900: '#072019',
          850: '#0a2a21',
          800: '#0f382d',
          700: '#144c3d',
          600: '#1b6451',
          500: '#22836b',
          400: '#34d399',
          300: '#6ee7b7',
          200: '#a7f3d0',
          100: '#d1fae5',
          50: '#ecfdf5',
        },
        gold: {
          600: '#b8860b',
          500: '#c59b27',
          400: '#d4af37',
          300: '#e5c158',
          200: '#f3dea2',
          100: '#fcf6e5',
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        quran: ['Amiri', '"Scheherazade New"', 'Traditional Arabic', 'serif'],
        arabic: ['Amiri', '"Scheherazade New"', 'Traditional Arabic', 'serif'],
      },
    },
  },
  plugins: [],
}
