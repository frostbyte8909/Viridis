
import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  discardResponseBodies: true,
  scenarios: {
    stress: {
      executor: 'constant-vus',
      vus: 1000,
      duration: '10s',
    },
  },
};

const URL = 'http://localhost:8000/v1/admit';

export default function () {
  // Randomize IP and API Key to bypass both IP limits and API Key rate limits
  const ip = `10.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`;
  const path = `/api/v1/random/${Math.floor(Math.random() * 10000)}`;
  const token = `viridis_dummykey${Math.floor(Math.random() * 100000)}`;
  
  http.post(URL, JSON.stringify({ endpoint_path: path, method: 'GET', client_ip: ip }), { headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` } });
  
  sleep(1);
}
