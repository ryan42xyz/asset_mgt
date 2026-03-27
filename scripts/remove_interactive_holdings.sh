#!/bin/bash
set -e
BASE_URL="http://localhost:8000"
USER_ID=1

echo "Deleting Interactive Brokers demo holdings..."
for id in 3 4; do
  curl -s -X DELETE "$BASE_URL/api/v1/portfolio/$USER_ID/holdings/$id" | jq .
  echo "Deleted holding id $id"
done

echo "Done" 