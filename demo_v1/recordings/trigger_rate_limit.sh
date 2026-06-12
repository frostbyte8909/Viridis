#!/bin/bash
# test rate limiter threshold

echo "testing rate limit cutoff for viridis_qCe6iXsyw1M..."
echo "---"

for i in {1..15}; do
  curl -s -X POST http://localhost:8000/v1/admit \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer viridis_qCe6iXsyw1M7DcCsDaZ8a4H5jAfEsDs4bxViVh5wtzE" \
    -d '{"endpoint_path": "/api/v1/demo", "method": "GET", "client_ip": "10.0.0.99"}'
  echo ""
  sleep 0.2
done

echo "---"
echo "done."
