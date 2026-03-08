/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./app/**/*.{js,jsx,ts,tsx}", "./components/**/*.{js,jsx,ts,tsx}"],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        parchment: {
          DEFAULT: "#F5F0E8",
          light: "#FAF7F2",
          dark: "#E8E0D4",
        },
        bark: {
          DEFAULT: "#6B5B4F",
          light: "#8B7B6B",
          dark: "#3B2F2F",
        },
        sage: {
          DEFAULT: "#7B8F6B",
          light: "#9AAD8A",
          dark: "#5A6B4A",
        },
        // Keep old forest/earth tokens for dev-tools screens (unchanged)
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
        primary: "#FAF7F2",
        secondary: "#F5F0E8",
        text: {
          primary: "#3B2F2F",
          secondary: "#6B5B4F",
          muted: "#9A8D82",
          accent: "#5A6B4A",
        },
        success: "#6B8F5A",
        error: "#C45A4A",
        warning: "#C4944A",
        info: "#5A8FA0",
      },
    },
  },
  plugins: [],
};
