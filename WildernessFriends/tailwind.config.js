/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        forest: {
          DEFAULT: "#1B3A2D",
          light: "#2D5A45",
          dark: "#0F2218",
        },
        earth: {
          DEFAULT: "#8B6914",
          light: "#B8941A",
          dark: "#6B5010",
        },
        primary: "#0F1A14",
        secondary: "#1A2E22",
        text: {
          primary: "#ffffff",
          secondary: "#D4E8DA",
          muted: "#7A9B88",
          accent: "#8BB174",
        },
        success: "#4CAF50",
        error: "#E53935",
        warning: "#FF9800",
        info: "#29B6F6",
      },
    },
  },
  plugins: [],
};
