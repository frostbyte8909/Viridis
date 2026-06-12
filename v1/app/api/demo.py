import asyncio
import re
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class LoadTestConfig(BaseModel):
    normal_users: int = 200
    scrapers: int = 10
    spikers: int = 30
    duration_seconds: int = 60

@router.post("/run-test")
async def run_load_test(config: LoadTestConfig):
    # Dynamically generate the k6 script
    k6_script = f"""
import http from 'k6/http';
import {{ sleep, check }} from 'k6';

export const options = {{
  discardResponseBodies: true,
  scenarios: {{
    normal_traffic: {{
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        {{ duration: '{max(1, config.duration_seconds // 3)}s', target: {config.normal_users} }},
        {{ duration: '{max(1, config.duration_seconds // 3)}s', target: {config.normal_users} }},
        {{ duration: '{max(1, config.duration_seconds // 3)}s', target: 0 }},
      ],
      exec: 'normal',
    }},
    brute_forcer: {{
      executor: 'constant-vus',
      vus: {config.scrapers},
      duration: '{config.duration_seconds}s',
      exec: 'brute',
    }},
    sneaky_spiker: {{
      executor: 'constant-vus',
      vus: {config.spikers},
      duration: '{config.duration_seconds}s',
      exec: 'spike',
    }}
  }}
}};

const URL = 'http://localhost:8000/v1/admit';

export function normal() {{
  const userId = Math.floor(Math.random() * 1000);
  const ip = `192.168.10.${{userId % 255}}`;
  const token = `viridis_user_${{userId}}`;
  
  const res = http.post(URL, JSON.stringify({{ endpoint_path: '/api/v1/resource', method: 'GET', client_ip: ip }}), {{ 
      headers: {{ 'Content-Type': 'application/json', 'Authorization': `Bearer ${{token}}` }} 
  }});
  check(res, {{ 'normal users get 200 OK': (r) => r.status === 200 }});
  sleep(Math.random() * 2 + 1);
}}

export function brute() {{
  const res = http.post(URL, JSON.stringify({{ endpoint_path: '/api/v1/login', method: 'POST', client_ip: '10.0.0.1' }}), {{ 
      headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_brute_123' }} 
  }});
  check(res, {{ 'brute gets 429 blocked': (r) => r.status === 429 }});
  sleep(0.1); 
}}

export function spike() {{
  const res = http.post(URL, JSON.stringify({{ endpoint_path: '/api/v1/search', method: 'GET', client_ip: '10.0.0.2' }}), {{ 
      headers: {{ 'Content-Type': 'application/json', 'Authorization': 'Bearer viridis_spike_123' }} 
  }});
  sleep(3); 
}}
"""

    temp_file = "temp_dashboard_k6.js"
    with open(temp_file, "w") as f:
        f.write(k6_script)

    try:
        # Run k6 asynchronously so we don't block the FastAPI event loop
        # The Docker command must be run this way to allow traffic to actually hit the API
        cmd = f"docker run --rm --network host -i grafana/k6 run - < {temp_file}"
        
        process = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        stdout, stderr = await process.communicate()
        output = stdout.decode() + stderr.decode()

        # Regex parse metrics
        p95_match = re.search(r'http_req_duration\.*:\s*avg=[^\s]+\s+min=[^\s]+\s+med=[^\s]+\s+max=[^\s]+\s+p\(90\)=[^\s]+\s+p\(95\)=([^\s]+)', output)
        total_reqs_match = re.search(r'http_reqs\.*:\s*([0-9]+)', output)
        failures_match = re.search(r'checks_failed\.*:\s*([0-9.]+)%', output)
        
        p95 = p95_match.group(1) if p95_match else "N/A"
        total_reqs = int(total_reqs_match.group(1)) if total_reqs_match else 0
        failures = failures_match.group(1) if failures_match else "0.00"

        return {
            "status": "success",
            "metrics": {
                "p95_latency": p95,
                "total_requests": total_reqs,
                "failure_rate_percent": failures,
                "raw_summary": output[-1500:] # Returning the end of the log just in case the frontend wants to display the raw text
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)
