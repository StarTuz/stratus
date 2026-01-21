#!/bin/bash
# Stratus ATC - Pre-commit regression check
# Install: cp scripts/check_regression.sh .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

echo "🔍 Running Stratus ATC regression checks (Zero Python Edition)..."

# 1. Check for prohibited naming patterns
echo -n "  Checking naming consistency... "
SIMAPI_COUNT=$(grep -ri "simapi\|SimApi\|SimAPI" --include="*.rs" \
  --include="*.c" . 2>/dev/null | \
  grep -v __pycache__ | grep -v target/ | grep -v tests/ | grep -v ".git" | wc -l)

if [ "$SIMAPI_COUNT" -gt 0 ]; then
    echo -e "${RED}FAILED${NC}"
    echo "  Found $SIMAPI_COUNT occurrences of 'simAPI' in source files (should be 0)"
    echo "  Run: grep -ri 'simapi' --include='*.rs' --include='*.py' --include='*.c' . | grep -v target/"
    exit 1
fi
echo -e "${GREEN}OK${NC}"

# 2. Check for old directory references
echo -n "  Checking for old directory names... "
STRATUSAI_COUNT=$(grep -ri "StratusAI\|StratusML" --include="*.rs" \
  --include="*.c" . 2>/dev/null | \
  grep -v __pycache__ | grep -v target/ | grep -v ".git" | wc -l)

if [ "$STRATUSAI_COUNT" -gt 0 ]; then
    echo -e "${RED}FAILED${NC}"
    echo "  Found $STRATUSAI_COUNT occurrences of 'StratusAI/StratusML' in source files (should be 0)"
    exit 1
fi
echo -e "${GREEN}OK${NC}"

# 3. Rust compilation check
echo -n "  Checking Rust compilation... "
if [ -d "stratus-rs" ]; then
    cd stratus-rs
    if ! cargo check --workspace --quiet; then
        echo -e "${RED}FAILED${NC}"
        echo "  Rust code does not compile. Run 'cargo check' for details."
        exit 1
    fi
    cd ..
fi
echo -e "${GREEN}OK${NC}"

echo ""
echo -e "${GREEN}✅ All regression checks passed${NC}"
