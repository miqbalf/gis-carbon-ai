#!/usr/bin/env node

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');
const app = express();
const PORT = 3000;

// Proxy for FastAPI tile service
app.use('/tiles', createProxyMiddleware({
  target: 'http://fastapi:8000',
  changeOrigin: true,
  pathRewrite: {
    '^/tiles': '/tiles'
  },
  onError: (err, req, res) => {
    console.error('Proxy error:', err);
    // Return a transparent PNG tile on error
    const transparentPNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64');
    res.set('Content-Type', 'image/png');
    res.send(transparentPNG);
  }
}));

app.listen(PORT, '0.0.0.0', () => {
  console.log(`Tile proxy server running on port ${PORT}`);
});
