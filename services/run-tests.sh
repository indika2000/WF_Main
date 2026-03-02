#!/usr/bin/env bash
#
# Unified test runner for all WildernessFriends backend services.
# Runs tests inside Docker containers via docker-compose exec.
#
# Usage:
#   ./run-tests.sh                    # Run all tests
#   ./run-tests.sh --unit             # Unit tests only
#   ./run-tests.sh --integration      # Integration tests only
#   ./run-tests.sh --coverage         # All tests with coverage
#   ./run-tests.sh --service commerce # Single service only
#   ./run-tests.sh --service gateway  # Node gateway only

set -euo pipefail

# --- Parse flags ---
UNIT=false
INTEGRATION=false
COVERAGE=false
SERVICE=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --unit)        UNIT=true; shift ;;
    --integration) INTEGRATION=true; shift ;;
    --coverage)    COVERAGE=true; shift ;;
    --service)     SERVICE="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--unit] [--integration] [--coverage] [--service <name>]"
      echo ""
      echo "Services: permissions, llm-service, image-service, commerce, gateway"
      exit 0
      ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

# --- Config ---
PYTHON_SERVICES=("permissions" "llm-service" "image-service" "commerce")
RESULTS=()
FAILURES=0

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

run_python_tests() {
  local svc=$1
  local pytest_args="-v --tb=short"

  if $UNIT && ! $INTEGRATION; then
    pytest_args="$pytest_args tests/unit/"
  elif $INTEGRATION && ! $UNIT; then
    pytest_args="$pytest_args tests/integration/"
  else
    pytest_args="$pytest_args tests/"
  fi

  if $COVERAGE; then
    pytest_args="$pytest_args --cov=app --cov-report=term-missing"
  fi

  echo -e "\n${YELLOW}=== Testing $svc ===${NC}"
  if docker-compose exec -T "$svc" pytest $pytest_args; then
    RESULTS+=("${GREEN}PASS${NC}  $svc")
  else
    RESULTS+=("${RED}FAIL${NC}  $svc")
    FAILURES=$((FAILURES + 1))
  fi
}

run_node_tests() {
  echo -e "\n${YELLOW}=== Testing gateway ===${NC}"

  local npm_cmd="test"
  if $UNIT && ! $INTEGRATION; then
    npm_cmd="test:unit"
  elif $INTEGRATION && ! $UNIT; then
    npm_cmd="test:integration"
  fi

  if docker-compose exec -T gateway npm run "$npm_cmd"; then
    RESULTS+=("${GREEN}PASS${NC}  gateway")
  else
    RESULTS+=("${RED}FAIL${NC}  gateway")
    FAILURES=$((FAILURES + 1))
  fi
}

# --- Run tests ---
echo -e "${YELLOW}WildernessFriends Test Suite${NC}"
echo "================================"

if [[ -n "$SERVICE" ]]; then
  # Single service mode
  if [[ "$SERVICE" == "gateway" ]]; then
    run_node_tests
  else
    run_python_tests "$SERVICE"
  fi
else
  # All services
  for svc in "${PYTHON_SERVICES[@]}"; do
    run_python_tests "$svc"
  done
  run_node_tests
fi

# --- Summary ---
echo ""
echo "================================"
echo -e "${YELLOW}RESULTS${NC}"
echo "================================"
for r in "${RESULTS[@]}"; do
  echo -e "  $r"
done
echo "================================"

if [[ $FAILURES -gt 0 ]]; then
  echo -e "${RED}$FAILURES service(s) failed${NC}"
  exit 1
else
  echo -e "${GREEN}All tests passed!${NC}"
  exit 0
fi
