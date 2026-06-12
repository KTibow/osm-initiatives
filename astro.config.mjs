// @ts-check
import { defineConfig, envField } from 'astro/config';
import svelte from '@astrojs/svelte';

export default defineConfig({
  base: process.env.GITHUB_ACTIONS ? '/osm-initiatives/' : '/',
  integrations: [svelte()],
  env: {
    schema: {
      GITHUB_TOKEN: envField.string({ context: "server", access: "secret", optional: true }),
    },
  },
});
