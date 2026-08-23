/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        dark: {
          950: '#070a12',
          900: '#0d1322',
          800: '#151d32',
          700: '#212d4a',
        }
      }
    },
  },
  plugins: [],
}
