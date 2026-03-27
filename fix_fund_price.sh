#!/bin/bash
set -e
BASE="http://localhost:8000"
USER=1
# FUND 持仓 id=17
curl -s -X PUT "$BASE/api/v1/portfolio/$USER/holdings/17" \
     -H "Content-Type: application/json" \
     -d '{"current_price":51.75}' | jq .
# 重新计算市值
curl -s -X POST "$BASE/api/v1/portfolio/$USER/refresh-prices" > /dev/null
echo "FUND price fixed."
