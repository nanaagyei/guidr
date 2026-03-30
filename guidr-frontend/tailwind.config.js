/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Refined color palette - Warm academic aesthetic
        background: "#FFFFFF", // Clean white base
        card: "#FFFFFF",
        cardAlt: "#FFFCF9", // Warmer card variant
        // Sidebar uses a light surface so the green Guidr logo stays legible
        sidebar: "#F8F6F3",
        sidebarHover: "#E8E4DE",

        // Primary colors - Deep charcoal/black for Hume-style
        primary: "#1C2127", // Deep charcoal black
        primaryHover: "#2D3640",
        primaryLight: "#F5F5F5", // Light primary tint
        primaryMuted: "#9099A4",

        // Accent colors - Warm peach/coral
        accent: "#E8B4A0", // Warm peach accent
        accentHover: "#D9A08C",
        accentLight: "#FFF5ED",

        // Secondary - Sage teal (for specific elements)
        secondary: "#4A7C74",
        secondaryHover: "#3D6860",
        secondaryLight: "#E8F0EE",

        // Text colors
        text: "#1C2127",
        textSecondary: "#5D6470",
        textMuted: "#9099A4",

        // UI colors
        border: "#E8E4DE",
        borderHover: "#D4CEC5",
        muted: "#F7F7F7",
        mutedAlt: "#F2F2F2",

        // Status colors
        success: "#4A9D6E",
        successLight: "#E8F5ED",
        warning: "#D4A34E",
        warningLight: "#FDF6E8",
        error: "#C75B5B",
        errorLight: "#FBEAEA",
        info: "#5B8DC7",
        infoLight: "#EAF2FB",

        // Tier colors for recommendations
        dream: "#7B68A8",
        dreamLight: "#F3F0F9",
        reach: "#C75B5B",
        reachLight: "#FBEAEA",
        target: "#4A9D6E",
        targetLight: "#E8F5ED",
        safety: "#5B8DC7",
        safetyLight: "#EAF2FB",

        // Landing page pastel cards (Hume-style)
        landingLavender: "#EDE4FF", // Soft purple
        landingPeach: "#FFECD9", // Soft peach/orange
        landingCream: "#FFF8E7", // Soft cream/yellow
        landingMint: "#E4F5F0", // Soft mint
        landingPink: "#FFE4EC", // Soft pink
        landingGray: "#F5F5F5", // Neutral gray

        // Hero gradient colors
        heroPeach: "#FFD4C4", // Hero gradient start
        heroPeachLight: "#FFF0E8", // Hero gradient end
        heroGreen: "#D4E8D9", // Hero gradient start (light green)
        heroGreenLight: "#E8F5EC", // Hero gradient end
      },
      fontFamily: {
        sans: ['Söhne', 'Outfit', 'system-ui', '-apple-system', 'sans-serif'],
        display: ['Fraunces', 'Georgia', 'serif'],
        mono: ['Söhne Mono', 'JetBrains Mono', 'monospace'],
      },
      letterSpacing: {
        'widest-plus': '0.15em',
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
      },
      boxShadow: {
        'soft': '0 2px 15px -3px rgba(28, 33, 39, 0.04), 0 4px 6px -4px rgba(28, 33, 39, 0.02)',
        'soft-lg': '0 10px 40px -15px rgba(28, 33, 39, 0.08), 0 4px 15px -8px rgba(28, 33, 39, 0.04)',
        'inner-soft': 'inset 0 2px 4px 0 rgba(28, 33, 39, 0.03)',
        'glow': '0 0 20px rgba(74, 124, 116, 0.15)',
        'glow-accent': '0 0 20px rgba(201, 168, 124, 0.2)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'gradient-warm': 'linear-gradient(135deg, #F8F6F3 0%, #FBF5ED 100%)',
        'gradient-card': 'linear-gradient(180deg, #FFFFFF 0%, #FFFCF9 100%)',
        'gradient-hero': 'linear-gradient(180deg, #FFD4C4 0%, #FFECD9 50%, #FFF5ED 100%)',
        'gradient-hero-peach': 'linear-gradient(180deg, #FFD4C4 0%, #FFE8DC 40%, #FFF0E8 70%, #FFFFFF 100%)',
        'gradient-hero-green': 'linear-gradient(180deg, #D4E8D9 0%, #E8F5EC 40%, #F0F9F2 70%, #FFFFFF 100%)',
        'gradient-cta': 'linear-gradient(180deg, #FFE4EC 0%, #EDE4FF 50%, #E4F5F0 100%)',
        'mesh-pattern': `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%234A7C74' fill-opacity='0.03'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
      },
      borderRadius: {
        '2xl': '1rem',
        '3xl': '1.5rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.5s ease-out forwards',
        'slide-up': 'slideUp 0.5s ease-out forwards',
        'slide-down': 'slideDown 0.3s ease-out forwards',
        'shimmer': 'shimmer 2s infinite linear',
        'pulse-soft': 'pulseSoft 2s infinite',
        'float': 'float 3s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        slideUp: {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        slideDown: {
          '0%': { opacity: '0', transform: 'translateY(-10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseSoft: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.7' },
        },
        float: {
          '0%, 100%': { transform: 'translateY(0)' },
          '50%': { transform: 'translateY(-5px)' },
        },
      },
      transitionTimingFunction: {
        'bounce-soft': 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
    },
  },
  plugins: [],
}
