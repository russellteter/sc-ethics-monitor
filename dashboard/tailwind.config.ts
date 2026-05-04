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
        ink: "#1F1F23",
        muted: "#6B7280",
        line: "#E5E7EB",
        bg: "#F8F8F8",
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
        display: ["Syne", "system-ui", "sans-serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      maxWidth: { page: "1400px" },
      boxShadow: { card: "0 1px 2px rgba(15, 23, 42, 0.04)" },
    },
  },
  plugins: [],
};
export default config;
