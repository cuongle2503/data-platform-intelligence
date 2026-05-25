#!/bin/bash
# IDP System Health Check
set -e

echo "=== System Health Check at $(date) ==="
STATUS=0

check_service() {
    NAME=$1
    URL=$2
    EXPECTED_CODE=$3
    echo -n "Checking $NAME... "
    CODE=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")
    if [[ "$CODE" == "$EXPECTED_CODE" ]] || [[ "$EXPECTED_CODE" == "200" && "$CODE" == "302" ]]; then
        echo "[OK] ($CODE)"
    else
        echo "[FAIL] ($CODE)"
        STATUS=1
    fi
}

# 1. FastAPI
check_service "FastAPI" "http://localhost:8000/health" "200"

# 2. MinIO API
check_service "MinIO" "http://localhost:9000/minio/health/live" "200"

# 3. Elasticsearch
check_service "Elasticsearch" "http://localhost:9200/_cluster/health" "200"

# 4. Neo4j Browser
check_service "Neo4j" "http://localhost:7474" "200"

# 5. Airflow Webserver
check_service "Airflow" "http://localhost:8080/api/v2/monitor/health" "200"

echo "-----------------------------------"
if [ $STATUS -eq 0 ]; then
    echo "Overall Status: HEALTHY"
else
    echo "Overall Status: UNHEALTHY"
fi

exit $STATUS
