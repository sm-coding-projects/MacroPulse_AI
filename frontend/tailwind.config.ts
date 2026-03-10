import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "#0F172A",
        accent: "#3B82F6",
        surface: "#1E293B",
        muted: "#64748B",
      },
    },
  },
  plugins: [],
};

export default config;
