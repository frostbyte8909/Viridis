import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '10s', target: 50 },
    { duration: '40s', target: 100 },
    { duration: '10s', target: 0 },
  ],
  summaryTrendStats: ['avg', 'min', 'max', 'p(1)', 'p(95)', 'p(99)'],
  thresholds: {
    http_req_duration: ['p(95)<15'], // 95% of requests must complete below 15ms
  },
};

export default function () {
  const url = 'http://localhost:8000/v1/admit';
  
  // Replace this with a valid raw key during actual local tests
  const payload = JSON.stringify({
    endpoint_path: '/api/v1/reports',
    method: 'GET',
    client_ip: '192.168.1.1'
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer viridis_qCe6iXsyw1M7DcCsDaZ8a4H5jAfEsDs4bxViVh5wtzE',
    },
  };

  const res = http.post(url, payload, params);

  // We expect 200 or 429
  check(res, {
    'is status 200 or 429': (r) => r.status === 200 || r.status === 429,
  });

  sleep(0.1);
}
