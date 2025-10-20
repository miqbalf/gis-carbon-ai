# 🚀 GitHub Push Guide - GIS Carbon AI

## ✅ Pre-Push Checklist

### 1. **Sensitive Files Check**
```bash
# Check for any sensitive files that might be tracked
cd /Users/miqbalf/gis-carbon-ai
find . -name "user_id.json" -o -name "*.json" | grep -E "(user_id|service-account|credentials)"
```

### 2. **Docker Volume Check**
```bash
# Check if any Docker volume data is being tracked
git status --porcelain | grep -E "(data|media|static|cache)"
```

### 3. **Large Files Check**
```bash
# Check for large files that shouldn't be in git
find . -type f -size +10M -not -path "./.git/*"
```

## 🔒 **Protected Files & Directories**

Your `.gitignore` now protects:

### **Sensitive Data:**
- ✅ `user_id.json` (GCP credentials)
- ✅ `*.json` (except package.json, tsconfig.json)
- ✅ Environment files (`.env*`)
- ✅ SSL certificates (`*.pem`, `*.key`, `*.crt`)

### **Docker Volumes:**
- ✅ `postgres_data_dev/`
- ✅ `redis_data_dev/`
- ✅ `django_static_dev/`
- ✅ `django_media_dev/`
- ✅ `geoserver_data_dev/`
- ✅ `gee_tiles_cache_dev/`

### **Data Directories:**
- ✅ `jupyter/data/*` (except `.gitkeep`)
- ✅ `jupyter/shared/*` (except `.gitkeep`)
- ✅ `jupyter/notebooks/*.ipynb`
- ✅ `backend/sv_carbon_removal/media/`
- ✅ `GEE_notebook_Forestry/data/`
- ✅ `ex_ante/data/`

### **Development Files:**
- ✅ `fastapi-gee-service/enhanced_main.py`
- ✅ `fastapi-gee-service/auth_layers.py`
- ✅ `mapstore/localConfig.json`
- ✅ Documentation files (`*_SETUP_SUMMARY.md`, etc.)

## 🚀 **Safe Push Commands**

### **Step 1: Check what will be added**
```bash
cd /Users/miqbalf/gis-carbon-ai
git status
git add . --dry-run  # See what would be added without actually adding
```

### **Step 2: Add files safely**
```bash
# Add all files (gitignore will protect sensitive ones)
git add .

# Or add specific directories
git add docker-compose*.yml
git add backend/
git add fastapi-gee-service/
git add jupyter/
git add mapstore/
git add ex_ante/
```

### **Step 3: Verify before commit**
```bash
# Check what's staged
git status --cached

# Make sure no sensitive files are staged
git diff --cached --name-only | grep -E "(user_id|\.env|\.json)"
```

### **Step 4: Commit and push**
```bash
git commit -m "feat: Add GIS Carbon AI infrastructure with Docker, Django, FastAPI, MapStore, and GeoServer integration"
git push origin main
```

## ⚠️ **What NOT to Push**

### **Never Push:**
- ❌ `user_id.json` (GCP service account credentials)
- ❌ `.env` files (environment variables)
- ❌ Docker volume data directories
- ❌ Jupyter notebook outputs (`.ipynb` files)
- ❌ Database files (`*.db`, `*.sqlite3`)
- ❌ Log files (`*.log`)
- ❌ Cache directories
- ❌ SSL certificates

### **Safe to Push:**
- ✅ Docker configuration files (`docker-compose*.yml`)
- ✅ Source code (`.py` files)
- ✅ Requirements files (`requirements.txt`)
- ✅ Dockerfiles
- ✅ Configuration templates
- ✅ Documentation (without sensitive info)
- ✅ `.gitignore` file

## 🔧 **If You Accidentally Add Sensitive Files**

### **Remove from staging:**
```bash
git reset HEAD <filename>
```

### **Remove from git history (if already committed):**
```bash
git filter-branch --force --index-filter 'git rm --cached --ignore-unmatch <filename>' --prune-empty --tag-name-filter cat -- --all
```

### **Force push (be careful!):**
```bash
git push origin --force
```

## 📋 **Repository Structure (What Gets Pushed)**

```
gis-carbon-ai/
├── docker-compose.yml          ✅
├── docker-compose.dev.yml      ✅
├── .gitignore                  ✅
├── README.md                   ✅
├── backend/                    ✅
│   ├── Dockerfile              ✅
│   ├── requirements.txt        ✅
│   └── sv_carbon_removal/      ✅
├── fastapi-gee-service/        ✅
│   ├── Dockerfile              ✅
│   ├── requirements.txt        ✅
│   └── main.py                 ✅
├── jupyter/                    ✅
│   ├── Dockerfile              ✅
│   ├── requirements.txt        ✅
│   ├── data/.gitkeep           ✅
│   └── shared/.gitkeep         ✅
├── mapstore/                   ✅
│   └── geostore-datasource-ovr-postgres.properties ✅
├── GEE_notebook_Forestry/      ✅ (structure only)
└── ex_ante/                    ✅ (structure only)
```

## 🎯 **Ready to Push!**

Your repository is now safe to push to GitHub. The `.gitignore` file will protect all sensitive data and Docker volumes from being accidentally committed.

**Run this to push safely:**
```bash
cd /Users/miqbalf/gis-carbon-ai
git add .
git status  # Verify what's being added
git commit -m "Initial commit: GIS Carbon AI infrastructure"
git push origin main
```
