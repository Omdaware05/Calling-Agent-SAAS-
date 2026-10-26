import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

const apiProxyWithHtmlBypass = {
  target: 'http://127.0.0.1:8001',
  changeOrigin: true,
  bypass: (req: any) => {
    // If browser is requesting an HTML document (e.g. full page refresh F5 or direct URL navigation),
    // bypass the proxy and return index.html so React Router renders the UI cleanly.
    if (req.headers && req.headers.accept && req.headers.accept.includes('text/html')) {
      return '/index.html';
    }
  },
};

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/calls': apiProxyWithHtmlBypass,
      '/agents': apiProxyWithHtmlBypass,
      '/stats': apiProxyWithHtmlBypass,
      '/active-calls': apiProxyWithHtmlBypass,
      '/queue': apiProxyWithHtmlBypass,
      '/telephony': apiProxyWithHtmlBypass,
      '/voice': apiProxyWithHtmlBypass,
      '/businesses': apiProxyWithHtmlBypass,
      '/questionnaires': apiProxyWithHtmlBypass,
      '/campaigns': apiProxyWithHtmlBypass,
      '/contacts': apiProxyWithHtmlBypass,
      '/leads': apiProxyWithHtmlBypass,
      '/followups': apiProxyWithHtmlBypass,
      '/reports': apiProxyWithHtmlBypass,
      '/invoices': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
        bypass: (req: any) => {
          if (req.headers && req.headers.accept && req.headers.accept.includes('text/html') && !req.url.includes('/pdf')) {
            return '/index.html';
          }
        },
      },
    },
  },
});
