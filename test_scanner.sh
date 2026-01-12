#!/bin/bash

# Test Script for SecOps Scanner
# Tests the scanner API with sample code

set -e

API_URL="http://localhost:8000"
INPUT_DIR="scanner_engine/scan_input"
OUTPUT_DIR="scanner_engine/scan_output"
TEST_PROJECT="scanner-test"

echo "🧪 Testing SecOps Scanner..."
echo "================================================"

# Check if scanner is running
echo "1️⃣  Checking scanner health..."
if ! curl -s "${API_URL}/health" > /dev/null 2>&1; then
    echo "❌ Scanner API is not running!"
    echo "   Start it with: ./start_scanner.sh"
    exit 1
fi

echo "✅ Scanner is healthy"
curl -s "${API_URL}/health" | jq '.status, .supported_languages'

# Create test project in input folder
echo ""
echo "2️⃣  Creating test project in input folder..."
mkdir -p "${INPUT_DIR}/${TEST_PROJECT}"

# Create test Python file with vulnerabilities
cat > "${INPUT_DIR}/${TEST_PROJECT}/test.py" << 'EOF'
import os
import subprocess

# Test: Hardcoded credentials (should be detected)
API_KEY = "sk-1234567890abcdef"
PASSWORD = "admin123"

# Test: Command injection vulnerability
def run_command(user_input):
    os.system("echo " + user_input)  # Unsafe

# Test: SQL injection vulnerability  
def query_db(user_id):
    query = f"SELECT * FROM users WHERE id = {user_id}"  # Unsafe
    return query

# Test: Weak cryptography
import hashlib
def hash_password(pwd):
    return hashlib.md5(pwd.encode()).hexdigest()  # Weak
EOF

echo "✅ Created test file: ${INPUT_DIR}/${TEST_PROJECT}/test.py"

# Scan the project
echo ""
echo "3️⃣  Scanning test project via API..."
curl -s -X POST "${API_URL}/scan" \
     -H "Content-Type: application/json" \
     -d "{
         \"project_name\": \"${TEST_PROJECT}\",
         \"save_results\": true,
         \"fail_on_findings\": false
     }" > scan_response.json

echo "✅ Scan completed"

# Display results
echo ""
echo "4️⃣  Scan Results:"
echo "================================================"
jq -r '.summary | 
    "Files Scanned:  \(.files_scanned)\n" +
    "Total Findings: \(.total_findings)\n" +
    "Total Errors:   \(.total_errors)"' scan_response.json

# Show findings details
echo ""
echo "5️⃣  Findings Details:"
echo "================================================"
FINDINGS=$(jq -r '.summary.total_findings' scan_response.json)

if [ "$FINDINGS" -gt "0" ]; then
    echo "✅ Test PASSED - Vulnerabilities detected as expected!"
    jq -r '.scan_data.results[].findings[] | 
        "  • \(.rule // .message // "Unknown rule")"' scan_response.json | head -10
else
    echo "⚠️  No findings detected (unexpected for test file)"
fi

# Check output file
echo ""
echo "6️⃣  Verifying output file..."
RESULT_FILE="${OUTPUT_DIR}/${TEST_PROJECT}/scan_results_latest.json"
if [ -f "$RESULT_FILE" ]; then
    echo "✅ Results saved to: $RESULT_FILE"
    ls -lh "$RESULT_FILE"
else
    echo "❌ Result file not found: $RESULT_FILE"
fi

# Cleanup
echo ""
echo "7️⃣  Cleaning up..."
rm -rf "${INPUT_DIR}/${TEST_PROJECT}"
rm -f scan_response.json

echo ""
echo "================================================"
echo "🎉 Scanner test completed successfully!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Review scanner API docs: ${API_URL}/docs"
echo "2. Set up Jenkins: cd jenkins_setup && cat README.md"
echo "3. Run your first real scan!"
echo ""

