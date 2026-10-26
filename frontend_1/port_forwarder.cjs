const http = require('http');

const server = http.createServer((req, res) => {
  const target = `http://localhost:5173${req.url || ''}`;
  res.writeHead(302, { Location: target });
  res.end(`Redirecting to ${target}`);
});

server.listen(5174, '0.0.0.0', () => {
  console.log('Port forwarder running on 5174 -> redirecting to 5173');
});
