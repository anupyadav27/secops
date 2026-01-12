# Jenkins Setup for SecOps Scanner

This folder contains everything needed to run Jenkins locally with the SecOps vulnerability scanner.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Local System                            │
│                                                             │
│  ┌────────────────┐                  ┌──────────────────┐  │
│  │   Jenkins      │                  │  Scanner API     │  │
│  │  (Port 8080)   │◄────────────────►│  (Port 8000)     │  │
│  │                │   HTTP Requests  │  (Docker)        │  │
│  └────────┬───────┘                  └────────┬─────────┘  │
│           │                                   │            │
│           │                                   │            │
│  ┌────────▼────────────────────────────────┬──▼─────────┐  │
│  │         Shared Folders (Volumes)        │            │  │
│  │  ┌──────────────┐    ┌──────────────┐  │            │  │
│  │  │ scan_input/  │    │ scan_output/ │  │            │  │
│  │  │ (Git repos)  │    │ (Results)    │  │            │  │
│  │  └──────────────┘    └──────────────┘  │            │  │
│  └────────────────────────────────────────┘            │  │
└─────────────────────────────────────────────────────────────┘
```

## Workflow

1. **Jenkins clones** git repo → `scanner_engine/scan_input/{project_name}/`
2. **Jenkins calls** Scanner API → `POST /scan` with `project_name`
3. **Scanner scans** code from → `scan_input/{project_name}/`
4. **Scanner saves** results → `scan_output/{project_name}/scan_results_latest.json`
5. **Jenkins reads** results from → `scan_output/{project_name}/`
6. **Jenkins archives** results and reports

---

## Quick Start

### Option A: Jenkins on Host (Recommended for Mac/Linux)

#### Step 1: Start Scanner API
```bash
cd /Users/apple/Desktop/secops/scanner_engine
docker-compose up -d

# Verify it's running
curl http://localhost:8000/health
```

#### Step 2: Install Jenkins
```bash
# macOS
brew install jenkins-lts

# Start Jenkins
brew services start jenkins-lts

# Access Jenkins at: http://localhost:8080
```

#### Step 3: Get Initial Admin Password
```bash
cat /Users/Shared/Jenkins/Home/secrets/initialAdminPassword
```

#### Step 4: Configure Jenkins
1. Open http://localhost:8080
2. Enter initial admin password
3. Install suggested plugins
4. Create admin user

#### Step 5: Install Required Plugins
Go to: **Manage Jenkins** → **Manage Plugins** → **Available**

Install:
- Pipeline
- Git plugin
- JQ Plugin (or install jq on Jenkins host)

#### Step 6: Create Pipeline Job
1. **New Item** → Enter name → **Pipeline**
2. Under **Pipeline** section:
   - Definition: **Pipeline script from SCM**
   - SCM: **Git**
   - Repository URL: Your git repo URL
   - Script Path: `jenkins_setup/Jenkinsfile`
3. **Save**

#### Step 7: Update Jenkinsfile
Edit `Jenkinsfile` line 4-5:
```groovy
SCANNER_API_URL = 'http://localhost:8000'  // For Jenkins on host
```

#### Step 8: Run Pipeline
Click **Build Now**

---

### Option B: Jenkins in Docker

#### Step 1: Start Both Services
```bash
# Start Scanner API
cd /Users/apple/Desktop/secops/scanner_engine
docker-compose up -d

# Start Jenkins
cd /Users/apple/Desktop/secops/jenkins_setup
docker-compose -f docker-compose.jenkins.yml up -d
```

#### Step 2: Get Jenkins Password
```bash
docker exec jenkins-local cat /var/jenkins_home/secrets/initialAdminPassword
```

#### Step 3: Configure Jenkins
1. Open http://localhost:8080
2. Enter password from Step 2
3. Install suggested plugins
4. Create admin user

#### Step 4: Install System Tools in Jenkins Container
```bash
docker exec -u root jenkins-local bash -c "
  apt-get update && 
  apt-get install -y jq curl git
"
```

#### Step 5: Create Pipeline Job
Same as Option A, Step 6

#### Step 6: Update Jenkinsfile
Keep this line in `Jenkinsfile`:
```groovy
SCANNER_API_URL = 'http://host.docker.internal:8000'  // For Jenkins in Docker
```

---

## Testing the Setup

### 1. Test Scanner API
```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "input_folder": "/app/scan_input",
  "output_folder": "/app/scan_output",
  "supported_languages": ["python", "terraform"]
}
```

### 2. Manual Test Scan
```bash
# Clone a test repo to input folder
cd /Users/apple/Desktop/secops/scanner_engine/scan_input
git clone https://github.com/your-repo/test-project.git

# Trigger scan
curl -X POST http://localhost:8000/scan \
     -H "Content-Type: application/json" \
     -d '{
       "project_name": "test-project",
       "save_results": true,
       "fail_on_findings": false
     }' | jq '.'

# Check results
cat /Users/apple/Desktop/secops/scanner_engine/scan_output/test-project/scan_results_latest.json | jq '.summary'
```

### 3. Run Jenkins Pipeline
1. Go to your pipeline job
2. Click **Build Now**
3. Click on build number → **Console Output**
4. Watch the pipeline execute

---

## Folder Structure

```
secops/
├── scanner_engine/
│   ├── api_server.py              # Scanner API
│   ├── scan_local.py              # Core scanning logic
│   ├── scanner_plugin.py          # Language detection
│   ├── Dockerfile                 # Scanner container
│   ├── docker-compose.yml         # Scanner deployment
│   ├── scan_input/                # ← Jenkins clones repos here
│   │   └── {project_name}/        # Each project in separate folder
│   └── scan_output/               # ← Scanner saves results here
│       └── {project_name}/
│           ├── scan_results_latest.json
│           └── scan_results_TIMESTAMP.json
│
└── jenkins_setup/
    ├── Jenkinsfile                # Pipeline definition
    ├── docker-compose.jenkins.yml # Optional: Jenkins in Docker
    └── README.md                  # This file
```

---

## Jenkinsfile Explained

The pipeline has these stages:

### 1. Health Check
Verifies Scanner API is running before proceeding.

### 2. Checkout Code
- Cleans previous scan input
- Clones git repo to `scan_input/{project_name}/`

### 3. Security Scan
- Calls Scanner API with project name
- Scanner scans the code
- Results saved to `scan_output/{project_name}/`

### 4. Analyze Results
- Reads results from output folder
- Extracts summary (files scanned, findings, errors)
- Marks build as UNSTABLE if findings > threshold

### 5. Generate Report
- Creates human-readable report
- Includes summary and findings details

### Post Actions
- Archives results (JSON + text report)
- Cleans up (optional)

---

## Customization

### Change Fail Threshold

Edit `Jenkinsfile` line ~95:
```groovy
if [ "\$TOTAL_FINDINGS" -gt "10" ]; then  // Change 10 to your threshold
    currentBuild.result = 'UNSTABLE'
fi
```

### Fail Build on Any Findings

In Scanner API call (line ~57):
```groovy
"fail_on_findings": true  // Will return HTTP 422 if findings found
```

### Add Email Notifications

Add to `post` section:
```groovy
post {
    unstable {
        emailext (
            subject: "Security Findings in ${PROJECT_NAME}",
            body: readFile('security_report.txt'),
            to: 'team@example.com'
        )
    }
}
```

### Scan Specific Branch

Add parameters:
```groovy
parameters {
    string(name: 'BRANCH', defaultValue: 'main', description: 'Branch to scan')
}

// In Checkout stage:
checkout([
    $class: 'GitSCM',
    branches: [[name: params.BRANCH]],
    ...
])
```

---

## Troubleshooting

### Scanner API not accessible from Jenkins

**If Jenkins on host:**
- Use `http://localhost:8000`
- Check scanner is running: `docker ps | grep scanner`

**If Jenkins in Docker:**
- Use `http://host.docker.internal:8000` (Mac/Windows)
- Or use `http://172.17.0.1:8000` (Linux)

### Permission errors on scan_input/scan_output

```bash
# Fix permissions
chmod -R 777 /Users/apple/Desktop/secops/scanner_engine/scan_input
chmod -R 777 /Users/apple/Desktop/secops/scanner_engine/scan_output
```

### jq command not found

**Jenkins on host:**
```bash
brew install jq  # macOS
apt install jq   # Ubuntu
```

**Jenkins in Docker:**
```bash
docker exec -u root jenkins-local apt-get update
docker exec -u root jenkins-local apt-get install -y jq
```

### Results not saved

Check Scanner API logs:
```bash
docker logs secops-scanner
```

Check folder permissions:
```bash
ls -la /Users/apple/Desktop/secops/scanner_engine/scan_output/
```

### Build marked as UNSTABLE

This is expected if vulnerabilities found. Adjust threshold in Jenkinsfile or fix the vulnerabilities.

---

## Production Deployment

For production, consider:

1. **Authentication**: Add API keys to Scanner API
2. **HTTPS**: Use reverse proxy (nginx) with SSL
3. **Secrets**: Use Jenkins credentials for API keys
4. **Resource Limits**: Add resource limits to docker-compose
5. **Monitoring**: Add Prometheus/Grafana for metrics
6. **Cleanup**: Auto-delete old scan inputs (save space)

Example cleanup stage:
```groovy
stage('Cleanup Old Scans') {
    steps {
        sh '''
            # Delete scan inputs older than 7 days
            find ${SCANNER_INPUT} -type d -mtime +7 -exec rm -rf {} +
            
            # Keep only last 10 scan results per project
            cd ${SCANNER_OUTPUT}/${PROJECT_NAME}
            ls -t scan_results_*.json | tail -n +11 | xargs rm -f
        '''
    }
}
```

---

## Support

Issues? Check:
1. Scanner API health: `curl http://localhost:8000/health`
2. Scanner logs: `docker logs secops-scanner`
3. Jenkins logs: Jenkins UI → Manage Jenkins → System Log
4. Folder permissions: `ls -la scanner_engine/scan_*`

For help: Review the API docs at http://localhost:8000/docs

