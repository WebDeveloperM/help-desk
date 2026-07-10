/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Industrial color palette
        navy: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        safety: {
          orange: '#f97316',
          'orange-light': '#fb923c',
          'orange-dark': '#ea580c',
          amber: '#f59e0b',
          'amber-light': '#fbbf24',
        },
        industrial: {
          steel: '#64748b',
          chrome: '#94a3b8',
          slate: '#334155',
        },
        // Custom surface colors (theme-aware)
        surface: 'hsl(var(--card))',
        surfaceHover: 'hsl(var(--muted))',
        borderLight: 'hsl(var(--border))',
        text: {
          primary: 'hsl(var(--foreground))',
          secondary: 'hsl(var(--muted-foreground))',
          tertiary: 'hsl(var(--muted-foreground))',
        },
        success: 'hsl(var(--success))',
        warning: 'hsl(var(--warning))',
        // Shadcn colors
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
      },
      fontFamily: {
        sans: [
          '"Onest Variable"',
          '-apple-system',
          'BlinkMacSystemFont',
          '"Segoe UI"',
          'Roboto',
          'sans-serif',
        ],
        display: ['"Lora Variable"', 'Georgia', '"Times New Roman"', 'serif'],
      },
      fontSize: {
        xs: '12px',
        sm: '13.5px',
        base: '15px',
        lg: '17px',
        xl: '22px',
        '2xl': '30px',
      },
      fontWeight: {
        normal: 400,
        medium: 500,
        semibold: 600,
        bold: 700,
      },
      borderRadius: {
        sm: '8px',
        md: '12px',
        lg: '16px',
        xl: '20px',
        '2xl': '26px',
      },
      boxShadow: {
        /* Atlas: soft, warm-tinted, low-contrast shadows */
        sm: '0 1px 2px rgba(45,40,30,0.05)',
        md: '0 2px 10px -2px rgba(45,40,30,0.08)',
        lg: '0 8px 28px -8px rgba(45,40,30,0.14)',
      },
    },
  },
  plugins: [],
}
