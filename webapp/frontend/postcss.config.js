// PostCSS pipeline: Tailwind expands utility classes, autoprefixer adds
// vendor prefixes for the targets in package.json's browserslist (default
// `last 2 versions, not dead`).
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {}
  }
};
