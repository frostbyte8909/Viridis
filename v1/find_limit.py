import subprocess
import re
import sys

k6_template = """
import http from 'k6/http';
import { sleep } from 'k6';

export const options = {
  discardResponseBodies: true,
  scenarios: {
    stress: {
      executor: 'constant-vus',
      vus: __VUS__,
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
"""

def run_test(vus):
    with open('temp_k6.js', 'w') as f:
        f.write(k6_template.replace('__VUS__', str(vus)))
    
    print(f"Testing {vus} VUs...", flush=True)
    result = subprocess.run(
        "docker run --rm --network host --ulimit nofile=65535:65535 -i grafana/k6 run - < temp_k6.js",
        shell=True,
        capture_output=True,
        text=True
    )
    
    output = result.stdout + result.stderr
    
    if "cannot assign requested address" in output or "connection reset by peer" in output or "socket: too many open files" in output:
        print(f"-> FATAL: Docker network bridge collapsed at {vus} VUs.", flush=True)
        return False
        
    match = re.search(r'http_req_failed\.+:?\s*([0-9\.]+)%', output)
    if match:
        fail_rate = float(match.group(1))
        if fail_rate > 2.0:  # Allow 2% threshold
            print(f"-> FAILED: HTTP Error rate hit {fail_rate}% at {vus} VUs.", flush=True)
            return False
            
    print(f"-> SUCCESS: Handled {vus} VUs cleanly.", flush=True)
    return True

def main():
    max_successful = 0
    for vus in range(1000, 31000, 1000):
        success = run_test(vus)
        if not success:
            print(f"\n[!] LIMIT FOUND: The framework broke at {vus} VUs.")
            print(f"[*] Absolute maximum stable capacity: {max_successful} VUs.")
            sys.exit(0)
        max_successful = vus

if __name__ == "__main__":
    main()
