/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: "#3e5eb9",
      },
      backgroundImage: {
        "image-login": "url('/images/bg-image-login.png')",
      },
      maxWidth: {
        "8xl": "90rem",
        "9xl": "120rem",
        "10xl": "150rem",
      },
    },
    container: {
      center: true,
      padding: {
        DEFAULT: "1rem",
        sm: "2rem", // 640px
        md: "3rem", // 768px
        lg: "3rem", // 1024px
        xl: "4rem", // 1280px
      },
    },
  },
  plugins: [],
  corePlugins: {
    preflight: true,
  },
};
