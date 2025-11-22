/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'workday-bg': '#f5f5f5',
        'workday-panel': '#ffffff',
        'workday-text': '#1a1a1a',
        'workday-muted': '#6b7280',
        'workday-border': '#e5e7eb',
      },
      fontFamily: {
        serif: ['serif'],
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}
