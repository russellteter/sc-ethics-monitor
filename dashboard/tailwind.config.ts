import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        slate: {
          50: "var(--slate-50)",
          100: "var(--slate-100)",
          200: "var(--slate-200)",
          300: "var(--slate-300)",
          400: "var(--slate-400)",
          500: "var(--slate-500)",
          600: "var(--slate-600)",
          700: "var(--slate-700)",
          800: "var(--slate-800)",
          900: "var(--slate-900)",
          950: "var(--slate-950)",
        },
        brand: {
          50: "var(--brand-50)",
          100: "var(--brand-100)",
          200: "var(--brand-200)",
          300: "var(--brand-300)",
          400: "var(--brand-400)",
          500: "var(--brand-500)",
          600: "var(--brand-600)",
          700: "var(--brand-700)",
          800: "var(--brand-800)",
          900: "var(--brand-900)",
        },
        dem: {
          strong: "var(--dem-strong)",
          lean: "var(--dem-lean)",
          light: "var(--dem-light)",
          tint: "var(--dem-tint)",
        },
        rep: {
          strong: "var(--rep-strong)",
          lean: "var(--rep-lean)",
          light: "var(--rep-light)",
          tint: "var(--rep-tint)",
        },

        // Legacy aliases mapped to new tokens. Kept until tasks #16/#17 restyle
        // every component; until then existing teal/ink/muted/line classes
        // continue to compile and start rendering with the brand palette.
        ink: "var(--slate-900)",
        muted: "var(--slate-500)",
        line: "var(--slate-200)",
        bg: "var(--slate-50)",
        card: "#FFFFFF",
        teal: {
          primary: "var(--brand-500)",
          secondary: "var(--brand-400)",
          deep: "var(--brand-700)",
          mid: "var(--brand-600)",
        },
        coh: {
          0: "var(--slate-100)",
          1: "var(--brand-200)",
          2: "var(--brand-400)",
          3: "var(--brand-600)",
          4: "var(--brand-800)",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "var(--font-body)", "system-ui", "sans-serif"],
        sans: ["var(--font-body)", "system-ui", "sans-serif"],
      },
      maxWidth: { page: "1400px" },
      boxShadow: {
        xs: "var(--shadow-xs)",
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
        focus: "var(--shadow-focus)",
        card: "var(--shadow-sm)",
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
        "2xl": "var(--radius-2xl)",
      },
      transitionTimingFunction: {
        "out-expo": "cubic-bezier(0.16, 1, 0.3, 1)",
        "out-back": "cubic-bezier(0.34, 1.56, 0.64, 1)",
      },
    },
  },
  plugins: [],
};

export default config;
