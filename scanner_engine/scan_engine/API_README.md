# SecOps Vulnerability Scanner API

REST API for scanning Python and Terraform code for security vulnerabilities. Jenkins CI/CD ready.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r api_requirements.txt
```

### 2. Start API Server

```bash
# Development mode
python api_server.py

# Production mode with custom host/port
uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4

# Background mode
nohup uvicorn api_server:app --host 0.0.0.0 --port 8000 &
```

### 3. Verify Server is Running

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-01T...",
  "supported_languages": ["python", "terraform"]
}
```

## API Endpoints

### 1. Health Check
**GET** `/health`

Monitor API status (use in Jenkins health checks)

```bash
curl http://localhost:8000/health
```

---

### 2. Scan Single File
**POST** `/scan/file`

Upload and scan a single `.py` or `.tf` file.

```bash
curl -X POST http://localhost:8000/scan/file \
     -F "file=@/path/to/your/script.py" \
     -o results.json

# View results
cat results.json | jq '.'
```

**Response Structure:**
```json
{
  "success": true,
  "scan_type": "single_file",
  "filename": "script.py",
  "timestamp": "2025-11-01T10:30:00",
  "engine": "python",
  "input": "/tmp/tmpxxx/script.py",
  "results": [
    {
      "file": "/tmp/tmpxxx/script.py",
      "language": "python",
      "findings": [...]
    }
  ],
  "errors": []
}
```

---

### 3. Scan Zip Folder
**POST** `/scan/zip`

Upload and scan a zipped project containing multiple files.

```bash
# Create zip
zip -r myproject.zip . -x "*.git*" "__pycache__/*"

# Scan
curl -X POST http://localhost:8000/scan/zip \
     -F "zip_file=@myproject.zip" \
     -o results.json
```

---

### 4. Scan Local Path (Jenkins Workspace)
**POST** `/scan/path`

Scan a file or directory already on the server. **Best for Jenkins pipelines.**

```bash
curl -X POST http://localhost:8000/scan/path \
     -H "Content-Type: application/json" \
     -d '{
       "path": "/var/jenkins/workspace/my-project",
       "output_results": true
     }' \
     -o results.json
```

**Request Body:**
- `path` (required): Absolute or relative path to file/folder
- `output_results` (optional): If `true`, saves results to `scan_results/` folder

---

## Jenkins Integration

### Option A: Path-Based Scan (Recommended)

When API server and Jenkins are on the same machine:

```groovy
stage('Security Scan') {
    steps {
        sh '''
            curl -X POST http://localhost:8000/scan/path \
                 -H "Content-Type: application/json" \
                 -d "{\\"path\\": \\"${WORKSPACE}\\", \\"output_results\\": true}" \
                 -o scan_results.json
            
            # Check for vulnerabilities
            VULN_COUNT=$(jq '[.results[].findings | length] | add // 0' scan_results.json)
            echo "Found ${VULN_COUNT} potential issues"
            
            # Fail build if critical issues found (customize threshold)
            # if [ "$VULN_COUNT" -gt "10" ]; then exit 1; fi
        '''
    }
}
```

### Option B: Zip Upload (Remote API Server)

When API server is on a different machine:

```groovy
stage('Security Scan') {
    steps {
        sh '''
            # Create zip (exclude unnecessary files)
            zip -r code.zip . -x "*.git*" "node_modules/*" "__pycache__/*"
            
            # Upload and scan
            curl -X POST http://scanner-api.example.com:8000/scan/zip \
                 -F "zip_file=@code.zip" \
                 -o scan_results.json
            
            jq '.' scan_results.json
        '''
    }
}
```

### Full Jenkinsfile Example

See `Jenkinsfile.example` for a complete pipeline implementation with:
- Health checks
- Multiple scan strategies
- Result parsing and thresholds
- Build status integration
- Artifact archiving

---

## Response Format

All scan endpoints return:

```json
{
  "success": true,
  "scan_type": "...",
  "timestamp": "2025-11-01T10:30:00",
  "engine": "python|terraform|multi (folder)",
  "input": "/path/to/scanned/code",
  "results": [
    {
      "file": "/path/to/file.py",
      "language": "python",
      "findings": [
        {
          "rule": "hardcoded_secret",
          "severity": "HIGH",
          "line": 42,
          "message": "Hardcoded credential detected",
          "code_snippet": "..."
        }
      ]
    }
  ],
  "errors": [
    {
      "file": "/path/to/broken.py",
      "error": "Could not parse file"
    }
  ]
}
```

---

## Production Deployment

### Using systemd (Linux)

Create `/etc/systemd/system/scanner-api.service`:

```ini
[Unit]
Description=SecOps Scanner API
After=network.target

[Service]
Type=simple
User=scanner
WorkingDirectory=/opt/secops/scanner_engine
ExecStart=/usr/bin/uvicorn api_server:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable scanner-api
sudo systemctl start scanner-api
sudo systemctl status scanner-api
```

### Using Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . /app

RUN pip install -r api_requirements.txt -r requirements.txt

EXPOSE 8000

CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build and run:
```bash
docker build -t scanner-api .
docker run -d -p 8000:8000 scanner-api
```

---

## Testing the API

### Interactive Documentation

Open in browser: `http://localhost:8000/docs`

FastAPI provides auto-generated Swagger UI for testing.

### Command-Line Testing

```bash
# Test single Python file
curl -X POST http://localhost:8000/scan/file \
     -F "file=@test.py" | jq '.'

# Test Terraform folder
cd terraform_project
zip -r terraform.zip *.tf
curl -X POST http://localhost:8000/scan/zip \
     -F "zip_file=@terraform.zip" | jq '.'

# Test workspace scan
curl -X POST http://localhost:8000/scan/path \
     -H "Content-Type: application/json" \
     -d '{"path": "/path/to/code"}' | jq '.'
```

---

## Troubleshooting

### API won't start
- Check if port 8000 is already in use: `lsof -i :8000`
- Verify all dependencies installed: `pip list | grep fastapi`

### Scanner module errors
- Ensure you're in the correct directory: `scanner_engine/`
- Check `scanner_plugin.py` and scanner modules are present

### Jenkins pipeline fails
- Verify API URL is accessible from Jenkins: `curl http://api-url/health`
- Check Jenkins workspace path permissions
- Review JSON parsing - install `jq` on Jenkins node

### Empty results
- Verify file extensions (only `.py` and `.tf` supported)
- Check file encoding (UTF-8 expected)
- Review scan_local.py logs

---

## Security Considerations

1. **Path Traversal Protection**: The `/scan/path` endpoint accepts any path. In production:
   - Whitelist allowed directories
   - Validate paths against base workspace
   - Use authentication/authorization

2. **Rate Limiting**: Add rate limiting for production use

3. **Authentication**: Add API keys or OAuth for protected deployments

4. **File Size Limits**: Configure max upload size in production

Example with path restriction:
```python
ALLOWED_BASE_PATHS = ["/var/jenkins/workspace", "/opt/builds"]

def validate_path(path):
    abs_path = os.path.abspath(path)
    if not any(abs_path.startswith(base) for base in ALLOWED_BASE_PATHS):
        raise HTTPException(403, "Path not allowed")
    return abs_path
```

---

## Support

For issues or questions:
1. Check API logs
2. Review `scan_local.py` and `scanner_plugin.py`
3. Test scanners independently before using API

API version: 1.0.0

