import type { Config } from "tailwindcss";
import plugin from "tailwindcss/plugin"; // 1. Import the plugin helper

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        hydro: { cyan: "#06B6D4", blue: "#0284C7" },
        bio: { green: "#10B981" },
        obsidian: { 950: "#020617", 900: "#0F172A" },
        status: { normal: "#10B981", drift: "#F59E0B", alert: "#FF1E3C" },
      },
      backgroundImage: {
        "hydro-gradient": "linear-gradient(135deg, #06B6D4 0%, #0284C7 100%)",
      },
      backdropBlur: { panel: "16px" },
      boxShadow: {
        "glow-normal": "0 0 12px 2px rgba(16, 185, 129, 0.55)",
        "glow-drift": "0 0 12px 2px rgba(245, 158, 11, 0.55)",
        "glow-alert": "0 0 16px 4px rgba(255, 30, 60, 0.65)",
        panel: "0 8px 32px 0 rgba(2, 6, 23, 0.45)",
      },
      keyframes: {
        pulseGlow: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.55" },
        },
      },
      animation: {
        "pulse-glow": "pulseGlow 1.8s ease-in-out infinite",
      },
    },
  },
  plugins: [
    // 2. Wrap your function inside the plugin helper
    plugin(function ({ addUtilities }) {
      addUtilities({
        ".glass-panel": {
          backgroundColor: "rgba(15, 23, 42, 0.55)",
          backdropFilter: "blur(16px)",
          WebkitBackdropFilter: "blur(16px)",
          border: "1px solid rgba(148, 163, 184, 0.12)",
        },
        ".status-dot": {
          display: "inline-block",
          width: "0.6rem",
          height: "0.6rem",
          borderRadius: "9999px",
        },
        ".status-dot-normal": {
          backgroundColor: "#10B981",
          boxShadow: "0 0 12px 2px rgba(16, 185, 129, 0.55)",
        },
        ".status-dot-drift": {
          backgroundColor: "#F59E0B",
          boxShadow: "0 0 12px 2px rgba(245, 158, 11, 0.55)",
        },
        ".status-dot-alert": {
          backgroundColor: "#FF1E3C",
          boxShadow: "0 0 16px 4px rgba(255, 30, 60, 0.65)",
        },
      });
    }),
  ],
};

export default config;
