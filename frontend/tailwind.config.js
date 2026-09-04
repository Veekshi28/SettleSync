/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--color-bg)",
        surface: "var(--color-surface)",
        "surface-2": "var(--color-surface-2)",
        border: "var(--color-border)",
        "border-2": "var(--color-border-2)",
        "text-1": "var(--color-text-1)",
        "text-2": "var(--color-text-2)",
        "text-3": "var(--color-text-3)",
        emerald: "var(--color-emerald)",
        "emerald-dim": "var(--color-emerald-dim)",
        amber: "var(--color-amber)",
        "amber-dim": "var(--color-amber-dim)",
        rose: "var(--color-rose)",
        "rose-dim": "var(--color-rose-dim)",
        blue: "var(--color-blue)",
        "blue-dim": "var(--color-blue-dim)",
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
}
