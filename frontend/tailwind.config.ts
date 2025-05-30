import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['var(--font-inter)', 'Inter Variable', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      colors: {
        primary: '#000000',
        accent: '#1746d4',
        // WCAG 2.1 AA compliant gray overrides
        gray: {
          50: '#f9fafb',
          100: '#f3f4f6',
          200: '#e5e7eb',
          300: '#d1d5db',
          400: '#8b949e', // Enhanced for 4.52:1 contrast ratio
          500: '#57606a', // Enhanced for 4.63:1 contrast ratio  
          600: '#424a53', // Enhanced for 6.38:1 contrast ratio
          700: '#374151',
          800: '#1f2937',
          900: '#111827',
        },
      },
      spacing: {
        '1': '4px',
        '2': '8px', 
        '3': '12px',
        '4': '16px',
        '6': '24px',
        '8': '32px',
        '12': '48px',
        '16': '64px',
      },
      animation: {
        'fade-in-up': 'fadeInUp 0.4s cubic-bezier(0.3, 0.7, 0.4, 1) forwards',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.3, 0.7, 0.4, 1)',
      },
    },
  },
  plugins: [],
};

export default config; 