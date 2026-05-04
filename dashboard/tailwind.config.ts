import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        teal: {
          primary: "#1ED4C2",
          secondary: "#5CD4C8",
          deep: "#1A4A45",
          mid: "#1CCAB8",
        },
        // Surface tokens map to a slate-based palette to match coverage-map.
        ink: "#0F172A", // slate-900
        muted: "#64748B", // slate-500
        line: "#E2E8F0", // slate-200
        bg: "#F8FAFC", // slate-50
        card: "#FFFFFF",
        coh: {
          0: "#E0F7F4",
          1: "#9DE5DC",
          2: "#5CD4C8",
          3: "#1ED4C2",
          4: "#1A4A45",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      maxWidth: { page: "1400px" },
      boxShadow: { card: "0 1px 2px rgba(15, 23, 42, 0.04)" },
    },
  },
  plugins: [],
};
export default config;
