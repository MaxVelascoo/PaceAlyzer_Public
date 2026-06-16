/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./src/app/**/*.{js,ts,jsx,tsx}",
    "./src/components/**/*.{js,ts,jsx,tsx}",
    "./src/pages/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            p: { textAlign: 'left' },
            li: { textAlign: 'left' },
          },
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],

};
