import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  discardResponseBodies: true,
  scenarios: {
    normal_traffic: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '15s', target: 5000 },
        { duration: '30s', target: 5000 },
        { duration: '15s', target: 0 },
      ],
      exec: 'normal',
    },
    brute_forcer: {
      executor: 'constant-vus',
      vus: 15000,
      duration: '60s',
      exec: 'brute',
    },
    sneaky_spiker: {
      executor: 'constant-vus',
      vus: 5000,
      duration: '60s',
      exec: 'spike',
    },
    concurrency_hog: {
      executor: 'constant-vus',
      vus: 5000,
      duration: '60s',
      exec: 'hog',
    },
  },
};

const URL = 'http://localhost:8000/v1/admit';

export function normal() {
  http.post(URL, JSON.stringify({ endpoint_path: '/api/v1/normal', method: 'GET', client_ip: '192.168.1.1' }), { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_dummykey123' } });
  sleep(1);
}

export function brute() {
  http.post(URL, JSON.stringify({ endpoint_path: '/api/v1/brute', method: 'GET', client_ip: '10.0.0.1' }), { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_brute123' } });
  sleep(1); 
}

export function spike() {
  http.post(URL, JSON.stringify({ endpoint_path: '/api/v1/spike', method: 'GET', client_ip: '10.0.0.2' }), { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_spike123' } });
  sleep(5); 
}

export function hog() {
  http.post(URL, JSON.stringify({ endpoint_path: '/api/v1/hog', method: 'GET', client_ip: '10.0.0.3' }), { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_hog123' } });
  sleep(2);
}
