/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        solar: {
          orange: '#FF6B35',
          gold: '#F7931E',
          green: '#2D5016',
          'green-deep': '#0A4D3C',
          blue: '#4A90E2',
        }
      }
    },
  },
  plugins: [],
}
