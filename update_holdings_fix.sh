#!/bin/bash
set -e
BASE_URL="http://localhost:8000"
UID=1

echo "Delete Tiger demo RSP & NVDA (25 shares)..."
for id in 5 6; do
  curl -s -X DELETE "$BASE_URL/api/v1/portfolio/$UID/holdings/$id" | jq .
  echo "deleted $id"
done

echo "Update NVDA (14) broker -> HuaShengTong (id 16)"
curl -s -X PUT "$BASE_URL/api/v1/portfolio/$UID/holdings/16" \
  -H "Content-Type: application/json" \
  -d '{"broker_name":"HuaShengTong"}' | jq .

echo "Update FUND current price 51.75 and broker Tiger (id 17)"
curl -s -X PUT "$BASE_URL/api/v1/portfolio/$UID/holdings/17" \
  -H "Content-Type: application/json" \
  -d '{"current_price":51.75,"broker_name":"Tiger Brokers"}' | jq .

echo "recalculate market value"
# refresh prices to recalc
curl -s -X POST "$BASE_URL/api/v1/portfolio/$UID/refresh-prices" | jq 'length'

echo Done 