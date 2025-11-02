import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './styles/**/*.{css}',
  ],
  darkMode: ['class'],
  theme: {
    extend: {
      colors: {
        'text-primary': '#F3F4FA',
        'text-secondary': '#D0D3E2'
      },
      boxShadow: {
        neon: '0 0 20px rgba(143, 200, 255, 0.25)'
      },
      backdropBlur: {
        xl: '24px'
      }
    }
  },
  plugins: [
    function ({ addUtilities }) {
      const newUtilities = {
        '.glass': {
          background: 'rgba(255,255,255,0.12)',
          border: '1px solid #FFFFFF15',
          backdropFilter: 'blur(24px)',
        },
        '.neon-edge': {
          boxShadow: '0 0 0 1px #FFFFFF15, 0 0 18px rgba(197, 138, 255, 0.35)'
        }
      }
      addUtilities(newUtilities)
    }
  ]
}

export default config
