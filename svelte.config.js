import adapter from '@sveltejs/adapter-node';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

const config = {
  preprocess: vitePreprocess(),
  compilerOptions: {
    warningFilter: (warning) => {
      return !warning.code.startsWith('a11y');
    }
  },
  kit: {
    adapter: adapter()
  }
};

export default config;
