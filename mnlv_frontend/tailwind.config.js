/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        mnlv: {
          red: "#E63946",
          blue: "#1E88E5",
          dark: "#0D47A1",
        }
      }
    },
  },
  plugins: [],
}
