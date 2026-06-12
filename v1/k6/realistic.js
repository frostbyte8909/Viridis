import http from 'k6/http';
import { sleep, check } from 'k6';

export const options = {
  discardResponseBodies: true,
  scenarios: {
    // A natural ramp-up of normal users
    normal_traffic: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '20s', target: 200 }, // Commute/morning rush
        { duration: '40s', target: 200 }, // Sustained peak usage
        { duration: '20s', target: 0 },   // Evening taper
      ],
      exec: 'normal',
    },
    // A single IP trying to scrape or brute-force the API constantly
    brute_forcer: {
      executor: 'constant-vus',
      vus: 10,
      duration: '1m20s',
      exec: 'brute',
    },
    // A botnet that sleeps and then spikes traffic suddenly
    sneaky_spiker: {
      executor: 'constant-vus',
      vus: 30,
      duration: '1m20s',
      exec: 'spike',
    }
  },
  thresholds: {
    // For realistic traffic, 95% of responses should be sub 200ms
    http_req_duration: ['p(95)<200']
  }
};

const URL = 'http://localhost:8000/v1/admit';

export function normal() {
  // Simulate a pool of 1,000 distinct normal users randomly browsing
  const userId = (__VU * 10000) + __ITER;
  const ip = `192.168.10.${(userId % 254) + 1}`;
  const token = `viridis_user_${userId}`;
  
  const res = http.post(URL, JSON.stringify({ endpoint_path: '/api/v1/resource', method: 'GET', client_ip: ip }), { 
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` } 
  });
  
  // Normal users should get HTTP 200s
  check(res, { 'normal users get 200 OK': (r) => r.status === 200 });
  
  // Realistic "human" think time: pause for 1 to 3 seconds before clicking the next link
  sleep((__ITER % 3) + 1);
}

export function brute() {
  // Same IP and Token firing repeatedly
  const res = http.post(URL, JSON.stringify({ endpoint_path: '/api/v1/login', method: 'POST', client_ip: '10.0.0.1' }), { 
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_brute_123' } 
  });
  
  // Expect these to get blocked by the Rate Limiter eventually
  check(res, { 'brute gets 429 blocked': (r) => r.status === 429 });
  
  // Bot speeds (100ms)
  sleep(0.1); 
}

export function spike() {
  // Same IP and Token spiking occasionally
  const res = http.post(URL, JSON.stringify({ endpoint_path: '/api/v1/search', method: 'GET', client_ip: '10.0.0.2' }), { 
      headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_spike_123' } 
  });
  
  // Sneaky bots pause for 3 seconds to avoid detection, then fire a burst
  sleep(3); 
}
