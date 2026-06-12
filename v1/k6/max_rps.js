import http from 'k6/http';

export const options = {
  discardResponseBodies: true,
  scenarios: {
    max_throughput: {
      executor: 'constant-vus',
      vus: 5000,
      duration: '60s',
    },
  },
};

const URL = 'http://localhost:8000/v1/admit';

export default function () {
  const payload = JSON.stringify({ endpoint_path: '/api/v1/speed', method: 'GET', client_ip: '10.0.0.99' });
  const params = { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_dummykey123' } };
  http.post(URL, payload, params);
  // Zero sleep. Absolute maximum requests per second.
}
