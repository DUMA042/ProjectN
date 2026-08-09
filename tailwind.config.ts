/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#FAFAF9",
        surface: "#FFFFFF",
        sidebar: "#FFFFFF",
        "nav-hover": "#F1F5F9",
        "text-primary": "#0F172A",
        "text-secondary": "#64748B",
        "text-muted": "#94A3B8",
        border: "#EAECF0",
        divider: "#F1F5F9",
        accent: "#0F172A",
        success: "#10B981",
        danger: "#EF4444",
        warning: "#F59E0B",
        info: "#6366F1",
        "badge-green-bg": "#D1FAE5",
        "badge-green-text": "#059669",
        "badge-red-bg": "#FEE2E2",
        "badge-red-text": "#DC2626",
        "badge-amber-bg": "#FEF3C7",
        "badge-amber-text": "#D97706",
      },
      fontFamily: {
        sans: [
          '"Plus Jakarta Sans"',
          "Inter",
          "-apple-system",
          "BlinkMacSystemFont",
          "sans-serif",
        ],
      },
      borderRadius: {
        card: "16px",
        input: "12px",
        badge: "20px",
        btn: "8px",
      },
      boxShadow: {
        card: "0px 1px 2px rgba(16, 24, 40, 0.05)",
        "card-hover": "0px 4px 12px rgba(0, 0, 0, 0.06)",
        subtle: "0px 2px 4px rgba(16, 24, 40, 0.04)",
      },
      fontSize: {
        "kpi": ["28px", { lineHeight: "36px", fontWeight: "700" }],
        "table-header": ["12px", { lineHeight: "16px", fontWeight: "500" }],
      },
    },
  },
  plugins: [],
};
