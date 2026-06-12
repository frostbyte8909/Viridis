import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  discardResponseBodies: true,
  scenarios: {
    // Background noise: normal legitimate traffic (1,000 VUs)
    normal_traffic: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 1000 },
        { duration: '30s', target: 1000 },
        { duration: '10s', target: 0 },
      ],
      exec: 'normal',
    },
    // The Brute Forcer: Tries to blast past the sliding window quota
    brute_forcer: {
      executor: 'constant-vus',
      vus: 5000, // 5k VUs spamming constantly
      duration: '50s',
      exec: 'brute',
    },
    // The Sneaky Spiker: Sleeps, then hits with massive bursts to exhaust Token Bucket
    sneaky_spiker: {
      executor: 'per-vu-iterations',
      vus: 3000,
      iterations: 20, // Huge burst, then pause
      maxDuration: '50s',
      exec: 'spike',
    },
    // The Concurrency Hog: Simulates slow network connections taking up connection slots
    concurrency_hog: {
      executor: 'constant-vus',
      vus: 1000, // 1k VUs holding connections open
      duration: '50s',
      exec: 'hog',
    },
  },
};

const URL = 'http://localhost:8000/v1/admit';

export function normal() {
  const params = { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_dummykey123' } };
  const payload = JSON.stringify({ endpoint_path: '/api/v1/normal', method: 'GET', client_ip: '192.168.1.1' });
  http.post(URL, payload, params);
  sleep(1); // Normal user pace
}

export function brute() {
  const params = { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_brute123' } };
  const payload = JSON.stringify({ endpoint_path: '/api/v1/brute', method: 'GET', client_ip: '10.0.0.1' });
  const res = http.post(URL, payload, params);
  // Brute forcers don't sleep
}

export function spike() {
  const params = { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_spike123' } };
  const payload = JSON.stringify({ endpoint_path: '/api/v1/spike', method: 'GET', client_ip: '10.0.0.2' });
  http.post(URL, payload, params);
  // Spikers pause to regain tokens, then fire again
  sleep(5); 
}

export function hog() {
  const params = { headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_hog123' } };
  const payload = JSON.stringify({ endpoint_path: '/api/v1/hog', method: 'GET', client_ip: '10.0.0.3' });
  http.post(URL, payload, params);
  // Simulates slow connections or holding the line
  sleep(2);
}
