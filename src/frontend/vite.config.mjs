import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    host: true,
    allowedHosts: ['localhost', 'arvo.notkaramel.dev'],
  }
});