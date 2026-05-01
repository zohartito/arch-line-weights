/** @type {import('tailwindcss').Config} */
export default {
  // Scan all Svelte + TS source so Tailwind's JIT can purge unused classes
  // from the production build. We deliberately exclude `.svelte-kit/` —
  // that's the build output, scanning it doubles work.
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      // The drop-zone "hover/dragover" highlight uses a custom color
      // matched to the architecture-drawing aesthetic — slightly warm
      // gray, not the default Tailwind cool slate.
      colors: {
        ink: {
          900: '#0f0f0f',
          700: '#262626',
          500: '#4a4a4a',
          300: '#a3a3a3',
          100: '#ededed'
        }
      }
    }
  },
  plugins: []
};
