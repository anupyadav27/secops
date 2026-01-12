# Jenkins Pipeline with Parameters - User Guide

## ✅ What Changed

The Jenkinsfile now asks for input **when you click "Build"** instead of hardcoding values!

---

## 🎯 How It Works Now

### **First Time You Run:**

1. Click **"Build Now"**
2. Pipeline runs with default values
3. Jenkins creates the parameter form

### **Second Time and After:**

1. Click **"Build with Parameters"** (appears after first run)
2. You'll see a form with these fields:

```
┌─────────────────────────────────────────────────────────┐
│  Build with Parameters                                  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  🔗 GIT_REPO_URL                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ https://github.com/your-org/your-repo.git       │   │
│  └─────────────────────────────────────────────────┘   │
│  Enter Git repository URL to scan                       │
│                                                          │
│  🌿 GIT_BRANCH                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ main ▼                                          │   │
│  └─────────────────────────────────────────────────┘   │
│  (Options: main, master, develop, staging)              │
│  Select branch to scan                                  │
│                                                          │
│  🗑️ CLEANUP_DAYS                                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 7                                               │   │
│  └─────────────────────────────────────────────────┘   │
│  Days to keep old scan folders                          │
│                                                          │
│  [  Build  ]                                            │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

3. **Fill in your values:**
   - Git URL: `https://github.com/myorg/myapp.git`
   - Branch: Select from dropdown
   - Cleanup days: Keep as 7 or change

4. Click **"Build"**

5. Jenkins downloads YOUR specified repo and scans it!

---

## 📝 Parameter Details

### 1. **GIT_REPO_URL** (Required)
- **What:** URL of the Git repository to scan
- **Default:** `https://github.com/your-org/your-repo.git`
- **Examples:**
  ```
  https://github.com/username/python-app.git
  https://gitlab.com/company/terraform-infra.git
  file:///Users/apple/Desktop/my-code
  ```

### 2. **GIT_BRANCH** (Dropdown)
- **What:** Which branch to scan
- **Options:** 
  - `main` (default)
  - `master`
  - `develop`
  - `staging`
- **Can add more:** Edit Jenkinsfile line 11-13

### 3. **CLEANUP_DAYS** (Optional)
- **What:** How many days to keep old scan folders
- **Default:** 7 days
- **Examples:** 3, 7, 14, 30

---

## 🚀 Step-by-Step: First Build

### 1. Update Your Pipeline

If you already created the pipeline, you need to run it once for parameters to appear:

1. Go to: http://localhost:8080/job/security-scanner
2. Click **"Build Now"** (just once)
3. Let it run (may fail if default URL is invalid - that's OK!)
4. After build finishes, **refresh the page**
5. You'll now see **"Build with Parameters"** instead of "Build Now"

### 2. Use Parameters

1. Click **"Build with Parameters"**
2. Enter your Git repo URL
3. Select branch
4. Click **"Build"**

---

## 📸 Visual Examples

### Example 1: Scan Public GitHub Repo

```
GIT_REPO_URL:  https://github.com/django/django.git
GIT_BRANCH:    main
CLEANUP_DAYS:  7
```

Click **Build** → Scans Django framework code!

### Example 2: Scan Private GitLab Repo

```
GIT_REPO_URL:  https://gitlab.com/mycompany/api-service.git
GIT_BRANCH:    develop
CLEANUP_DAYS:  14
```

*Note: For private repos, add credentials in Jenkins first*

### Example 3: Scan Local Folder

```
GIT_REPO_URL:  file:///Users/apple/Desktop/test-code
GIT_BRANCH:    master
CLEANUP_DAYS:  3
```

Click **Build** → Scans local folder!

---

## 🎨 Customizing Parameters

### Add More Branch Options

Edit Jenkinsfile lines 10-14:

```groovy
choice(
    name: 'GIT_BRANCH',
    choices: ['main', 'master', 'develop', 'staging', 'production', 'qa'],
    description: '🌿 Select branch to scan'
)
```

### Add Custom Branch Input

Replace the `choice` with `string`:

```groovy
string(
    name: 'GIT_BRANCH',
    defaultValue: 'main',
    description: '🌿 Enter branch name to scan'
)
```

Now you can type ANY branch name!

### Add Credential Selection

Add this parameter:

```groovy
credentials(
    name: 'GIT_CREDENTIALS',
    credentialType: 'com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl',
    description: '🔐 Git credentials (for private repos)',
    required: false
)
```

---

## 💡 Pro Tips

### Tip 1: Save Favorite Repos

Create multiple pipelines with different default values:

- **Pipeline 1:** `security-scanner-frontend` (default: frontend repo)
- **Pipeline 2:** `security-scanner-backend` (default: backend repo)
- **Pipeline 3:** `security-scanner-infra` (default: terraform repo)

Each can have different defaults but use the same Jenkinsfile!

### Tip 2: Build History Shows Parameters

In build history, you'll see which repo/branch was scanned:

```
#1 - https://github.com/user/app1.git (main)
#2 - https://github.com/user/app2.git (develop)
#3 - file:///Users/apple/test-code (master)
```

### Tip 3: API Trigger with Parameters

You can trigger builds via API with parameters:

```bash
curl -X POST http://localhost:8080/job/security-scanner/buildWithParameters \
     --user admin:your-token \
     --data GIT_REPO_URL=https://github.com/user/repo.git \
     --data GIT_BRANCH=main
```

---

## 🔐 For Private Repositories

### Step 1: Add Credentials

1. Jenkins → **Manage Jenkins** → **Credentials**
2. Click **Add Credentials**
3. Fill in:
   - Kind: Username with password
   - Username: your-git-username
   - Password: your-token-or-password
   - ID: `git-credentials`
4. Save

### Step 2: Update Download Stage

In Jenkinsfile, find the "Download Test Code" stage and modify:

```groovy
dir("${SCANNER_INPUT}/${PROJECT_NAME}") {
    git branch: "${TEST_REPO_BRANCH}", 
        url: "${TEST_REPO_URL}",
        credentialsId: 'git-credentials'  // Add this line
}
```

Now it works with private repos!

---

## ✅ Quick Test

### Create Test Repository:

```bash
mkdir ~/test-vulnerable-app
cd ~/test-vulnerable-app

cat > app.py << 'EOF'
# Test vulnerable code
API_KEY = "sk-test123456"
PASSWORD = "admin"

import os
def run(cmd):
    os.system(cmd)  # Command injection
EOF

git init
git add .
git commit -m "test"
```

### In Jenkins:

1. Click **"Build with Parameters"**
2. Enter:
   ```
   GIT_REPO_URL: file:///Users/apple/test-vulnerable-app
   GIT_BRANCH: master
   ```
3. Click **Build**

### Expected Result:

```
✅ Code downloaded
✅ Scan completed
📊 Files Scanned: 1
📊 Findings: 3-5 vulnerabilities
```

---

## 📋 Summary

**Before (Old Way):**
- ❌ Edit Jenkinsfile every time
- ❌ Commit changes to Git
- ❌ Not flexible

**Now (New Way):**
- ✅ Enter Git URL in Jenkins UI
- ✅ No code changes needed
- ✅ Scan different repos easily
- ✅ Perfect for multiple projects!

---

## 🎉 You're All Set!

**Just:**
1. Create/update your pipeline
2. Run it once (to create parameters)
3. Click **"Build with Parameters"**
4. Enter your Git repo URL
5. Click **Build**

**Done!** Each build can scan a different repository! 🚀

