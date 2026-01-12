"""
FastAPI server for vulnerability scanning - Jenkins CI/CD ready
Supports: single files, folders, zip uploads, and direct path scanning
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import tempfile
import os
import zipfile
import shutil
from typing import Optional
from datetime import datetime
from scan_local import scan_path

# Initialize FastAPI
app = FastAPI(
    title="SecOps Vulnerability Scanner API",
    description="Scan Python and Terraform code for security vulnerabilities",
    version="1.0.0"
)

# Enable CORS for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= Models =============
class ScanPathRequest(BaseModel):
    path: str
    output_results: Optional[bool] = False

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    supported_languages: list

# ============= Endpoints =============

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint for pipeline monitoring"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "supported_languages": ["python", "terraform"]
    }

@app.post("/scan/file")
async def scan_single_file(file: UploadFile = File(...)):
    """
    Upload and scan a single file (.py or .tf)
    Used for: Quick single file validation
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    # Validate file extension
    if not (file.filename.endswith('.py') or file.filename.endswith('.tf')):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type. Only .py and .tf files are supported. Got: {file.filename}"
        )
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, file.filename)
            
            # Save uploaded file
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Scan the file
            result = scan_path(file_path)
            
            return JSONResponse(content={
                "success": True,
                "scan_type": "single_file",
                "filename": file.filename,
                "timestamp": datetime.now().isoformat(),
                **result
            })
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@app.post("/scan/zip")
async def scan_zip_folder(zip_file: UploadFile = File(...)):
    """
    Upload and scan a zipped folder containing multiple files
    Used for: Project-level scanning with multiple files
    """
    if not zip_file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    
    if not zip_file.filename.endswith('.zip'):
        raise HTTPException(
            status_code=400, 
            detail=f"Only .zip files are supported. Got: {zip_file.filename}"
        )
    
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, zip_file.filename)
            extract_dir = os.path.join(tmpdir, "extracted")
            
            # Save and extract zip
            content = await zip_file.read()
            with open(zip_path, "wb") as f:
                f.write(content)
            
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # Scan the extracted folder
            result = scan_path(extract_dir)
            
            return JSONResponse(content={
                "success": True,
                "scan_type": "zip_folder",
                "filename": zip_file.filename,
                "timestamp": datetime.now().isoformat(),
                **result
            })
            
    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid zip file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@app.post("/scan/path")
async def scan_local_path(request: ScanPathRequest):
    """
    Scan a file or folder already on the server (e.g., Jenkins workspace)
    Used for: CI/CD pipelines where code is already checked out
    
    Request body:
    {
        "path": "/path/to/code",
        "output_results": false  // optional, save to scan_results folder
    }
    """
    target_path = request.path
    
    # Validate path exists
    if not os.path.exists(target_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Path does not exist: {target_path}"
        )
    
    # Security: Basic path validation (customize based on your needs)
    abs_path = os.path.abspath(target_path)
    
    try:
        # Scan the path
        result = scan_path(abs_path)
        
        # Optionally save results to file
        if request.output_results:
            output_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), 
                "scan_results"
            )
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.basename(abs_path) or "scan"
            output_file = os.path.join(
                output_dir, 
                f"{base_name}_{timestamp}_results.json"
            )
            
            import json
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
            
            result["output_file"] = output_file
        
        return JSONResponse(content={
            "success": True,
            "scan_type": "local_path",
            "path": abs_path,
            "timestamp": datetime.now().isoformat(),
            **result
        })
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")

@app.get("/")
async def root():
    """API documentation root"""
    return {
        "service": "SecOps Vulnerability Scanner API",
        "version": "1.0.0",
        "endpoints": {
            "health_check": "GET /health",
            "scan_single_file": "POST /scan/file (upload file)",
            "scan_zip_folder": "POST /scan/zip (upload .zip)",
            "scan_local_path": "POST /scan/path (JSON body with 'path')"
        },
        "supported_formats": [".py", ".tf"],
        "documentation": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

