/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)", surface: "var(--surface)", "surface-2": "var(--surface-2)",
        ink: "var(--ink)", "text-2": "var(--text-2)", "text-3": "var(--text-3)",
        line: "var(--line)", "line-strong": "var(--line-strong)",
        gold: { DEFAULT: "var(--gold)", strong: "var(--gold-strong)", soft: "var(--gold-soft)" },
        "on-gold": "var(--on-gold)",
        accent: { DEFAULT: "var(--accent)", strong: "var(--accent-strong)", soft: "var(--accent-soft)" },
        "on-accent": "var(--on-accent)",
        pass: { DEFAULT: "var(--pass)", bg: "var(--pass-bg)" },
        review: { DEFAULT: "var(--review)", bg: "var(--review-bg)" },
        flag: { DEFAULT: "var(--flag)", bg: "var(--flag-bg)" },
      },
      fontFamily: {
        display: ["Zain", "Alexandria", "system-ui", "sans-serif"],
        sans: ["Alexandria", "system-ui", '"Segoe UI"', "sans-serif"],
      },
      fontSize: {
        "display-xl": ["3rem", { lineHeight: "1.05", fontWeight: "800" }],
        display: ["2.25rem", { lineHeight: "1.1", fontWeight: "800" }],
        h1: ["1.875rem", { lineHeight: "1.2", fontWeight: "700" }],
        h2: ["1.5rem", { lineHeight: "1.25", fontWeight: "700" }],
        h3: ["1.25rem", { lineHeight: "1.35", fontWeight: "600" }],
        title: ["1.125rem", { lineHeight: "1.4", fontWeight: "600" }],
        body: ["1rem", { lineHeight: "1.6" }],
        "body-sm": ["0.875rem", { lineHeight: "1.55" }],
        label: ["0.8125rem", { lineHeight: "1.4", fontWeight: "500" }],
        overline: ["0.6875rem", { lineHeight: "1.3", letterSpacing: "0.08em", fontWeight: "600" }],
      },
      borderRadius: { lg: "8px", xl: "12px" },
    },
  },
  plugins: [],
};
