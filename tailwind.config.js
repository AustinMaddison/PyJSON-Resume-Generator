/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./resumes/**/*.html"
  ],
  theme: {
    extend: {
      fontFamily: {
        'helvetica': ['"Helvetica Now Variable"', 'Helvetica', 'Arial', 'sans-serif']
      }
    }
  },
  plugins: []
}