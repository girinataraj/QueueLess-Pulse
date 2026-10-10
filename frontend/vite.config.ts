import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
export default defineConfig({
  base: '/app/',
  plugins: [react(), tailwind()],
  server: { proxy: { '/api': 'http://127.0.0.1:5000', '/owner/business': 'http://127.0.0.1:5000', '/static': 'http://127.0.0.1:5000', '/sw.js': 'http://127.0.0.1:5000', '/app.webmanifest': 'http://127.0.0.1:5000' } },
  test: { environment: 'jsdom', setupFiles: './src/test/setup.ts', include: ['src/**/*.test.{ts,tsx}'] },
});
