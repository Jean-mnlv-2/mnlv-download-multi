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
          red: {
            DEFAULT: "#FF3B30",
            light: "#FFEBEE",
            dark: "#D32F2F"
          },
          blue: {
            DEFAULT: "#007AFF",
            light: "#E3F2FD",
            dark: "#0056B3"
          },
          slate: {
            50: "#F5F5F7",
            100: "#E8E8ED",
            200: "#D2D2D7",
            800: "#1D1D1F",
            900: "#121214",
            950: "#000000"
          }
        }
      },
      fontFamily: {
        sans: ['SF Pro Display', 'Inter', 'system-ui', 'sans-serif'],
        display: ['SF Pro Display', 'Outfit', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '18px',
        '3xl': '24px',
        '4xl': '32px',
      },
      boxShadow: {
        'pro': '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
        'pro-hover': '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)',
        'pro-blue': '0 10px 15px -3px rgba(0, 122, 255, 0.2), 0 4px 6px -2px rgba(0, 122, 255, 0.1)',
      }
    },
  },
  plugins: [],
}
