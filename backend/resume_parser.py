"""
Rest API Resume parser service that converts plaintext resumes to JSON using GPT-3.5.

Takes plaintext resume, returns standardized JSON. Uses two-stage validation with retries. Can send parsed data to an optional endpoint.

Input:
    - Plaintext resume content (string)
    - Optional endpoint URL for forwarding parsed data

Output:
    - Standardized JSON schema matching profile.json structure

Run: uvicorn resume_parser:app --reload

Send POST requests to /parse endpoint with JSON body:
       {
         "plaintext": "resume text as string here...",
         "endpoint": "https://your-endpoint.com/receive"  // If provided, forwards parsed data here after validation
       }
       
If endpoint is provided in request, it will POST parsed JSON there after validation.
If not provided, uses DEFAULT_ENDPOINT env var if set, otherwise just returns the data.


Requires OPENAI_API_KEY environment var. (Send me a message if you need mine)
"""

import json
import os
import re
import uuid
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, File, UploadFile, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import requests

app = FastAPI(
    title="Job Application Tool API",
    description="Resume parsing, upload, and profile management for the job application extension.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173", "http://localhost:3000", "http://localhost:8080",
        "http://127.0.0.1:5173", "http://127.0.0.1:3000", "http://127.0.0.1:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set")

default_endpoint = os.getenv("DEFAULT_ENDPOINT")
if not default_endpoint:
    print("Warning: DEFAULT_ENDPOINT not set. Parsed data will not be forwarded.")

client = OpenAI(api_key=api_key)
model = "gpt-3.5-turbo"

# Schema: structure only, no personal data
BACKEND_DIR = Path(__file__).parent


def _empty_schema_for_parsing(template: Dict[str, Any]) -> Dict[str, Any]:
    """Return schema structure with empty values."""
    if isinstance(template, dict):
        return {k: _empty_schema_for_parsing(v) for k, v in template.items()}
    if isinstance(template, list):
        return [_empty_schema_for_parsing(template[0])] if template else []
    if isinstance(template, str):
        return ""
    if isinstance(template, (int, float)):
        return 0
    return template


def _load_schema() -> Dict[str, Any]:
    """Load schema from sample.json or profile.json, stripped to structure only."""
    sample = BACKEND_DIR / "tests" / "fixtures" / "sample.json"
    if sample.exists():
        with open(sample, encoding="utf-8") as f:
            return _empty_schema_for_parsing(json.load(f))
    profile = BACKEND_DIR / "profile.json"
    if profile.exists():
        with open(profile, encoding="utf-8") as f:
            return _empty_schema_for_parsing(json.load(f))
    raise FileNotFoundError("No schema found (sample.json or profile.json)")


schema = _load_schema()


class ResumeRequest(BaseModel):
    plaintext: str
    endpoint: Optional[str] = None


def process_dates(data: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now()
    current_month = str(now.month)
    current_year = str(now.year)
    
    if "applicant_info" in data:
        applicant_info = data["applicant_info"]
        
        if "work_experience" in applicant_info:
            for job_key in ["job_1", "job_2", "job_3"]:
                if job_key in applicant_info["work_experience"]:
                    job = applicant_info["work_experience"][job_key]
                    if "end_month" in job or "end_year" in job:
                        end_month = str(job.get("end_month", "")).lower()
                        end_year = str(job.get("end_year", "")).lower()
                        if end_month in ["present", "current", "now"] or end_year in ["present", "current", "now"]:
                            job["end_month"] = current_month
                            job["end_year"] = current_year
        
        if "education" in applicant_info:
            edu = applicant_info["education"]
            if "end_month" in edu or "end_year" in edu:
                end_month = str(edu.get("end_month", "")).lower()
                end_year = str(edu.get("end_year", "")).lower()
                if end_month in ["present", "current", "now"] or end_year in ["present", "current", "now"]:
                    edu["end_month"] = current_month
                    edu["end_year"] = current_year
    
    return data


def parse_resume(plaintext: str, validation_error: Optional[str] = None) -> Dict[str, Any]:
    schema_str = json.dumps(schema, indent=2)
    
    system_msg = (
        "Extract information from resume text into JSON schema. Leave fields blank if unknown. "
        "Extract ONLY from the resume text provided. Do not use prior data or schema structure."
    )
    
    validation_context = f"\n\nFix these errors:\n{validation_error}\n" if validation_error else ""
    
    user_msg = f"""Extract info from this resume into the JSON schema.

Resume:
{plaintext}

Schema:
{schema_str}

Rules:
- Only fill fields explicitly in the resume, leave blank if unknown
- Extract ONLY from the resume text; do not copy from the schema
- If the resume contains multiple people, extract the one whose section is MOST COMPLETE (most experience, education, etc.), not necessarily the first
- Dates: separate month/year (use 1-12 for months, current month/year for "Present")
- Skills: only skill_name (no years)
- Return valid JSON matching schema{validation_context}"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    parsed = json.loads(response.choices[0].message.content)
    return process_dates(parsed)


def validate_output(resume_text: str, parsed_json: Dict[str, Any]) -> Tuple[bool, str]:
    schema_str = json.dumps(schema, indent=2)
    parsed_str = json.dumps(parsed_json, indent=2)
    
    system_msg = "Review parsed resume data for accuracy and completeness."
    
    user_msg = f"""Check if this parsed JSON data matches the original resume.

Original:
{resume_text}

Parsed JSON:
{parsed_str}

Schema:
{schema_str}

Verify:
- All filled fields exist in original
- No assumptions or inferred values
- Schema structure matches
- Unknown fields left blank

Return JSON: {{"valid": true/false, "reason": "why"}}"""

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg}
        ],
        response_format={"type": "json_object"},
        temperature=0.1
    )
    
    result = json.loads(response.choices[0].message.content)
    return result.get("valid", False), result.get("reason", "")


def send_to_endpoint(data: Dict[str, Any], endpoint: str):
    try:
        response = requests.post(endpoint, json=data, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Endpoint error: {str(e)}")


def extract_text_from_pdf(content: bytes) -> str:
    """Extract plaintext from PDF bytes for resume parsing."""
    try:
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(content))
        parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n\n".join(parts).strip() if parts else ""
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"PDF text extraction failed: {str(e)}")


UPLOADS_DIR = BACKEND_DIR / "uploads" / "resumes"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    """Accept PDF, extract text, parse, return profile. Saves file and sets resume_path."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename")
    ext = (Path(file.filename).suffix or "").lower()
    if ext != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF is supported. Use .pdf files.")
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    plaintext = extract_text_from_pdf(content)
    if not plaintext or not plaintext.strip():
        raise HTTPException(status_code=400, detail="No text could be extracted from the PDF (e.g. scanned image).")
    # Save file for runner / profile
    safe_name = re.sub(r"[^\w._-]", "_", Path(file.filename).stem)[:80] + f"_{uuid.uuid4().hex[:8]}.pdf"
    saved_path = UPLOADS_DIR / safe_name
    saved_path.write_bytes(content)
    resume_path = f"uploads/resumes/{safe_name}"
    # Parse with existing logic (no validation retries for upload to keep response fast; can add later)
    try:
        parsed = parse_resume(plaintext)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Parsing failed: {str(e)}")
    applicant = parsed.get("applicant_info", parsed)
    if isinstance(applicant, dict):
        applicant["resume_path"] = resume_path
    # Auto-save to profile.json so autofill uses the newly parsed data (real-time profile update)
    try:
        profile_path = BACKEND_DIR / "profile.json"
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump({"applicant_info": applicant}, f, indent=2)
    except Exception as e:
        print(f"Warning: could not auto-save profile after upload: {e}")
    return {"applicant_info": applicant}


@app.get("/profile")
async def get_profile():
    """Return current profile from profile.json."""
    profile_path = BACKEND_DIR / "profile.json"
    if not profile_path.exists():
        return {"applicant_info": {}}
    try:
        with open(profile_path, encoding="utf-8") as f:
            data = json.load(f)
        return data
    except Exception:
        return {"applicant_info": {}}


@app.post("/profile/clear")
async def clear_profile():
    """Clear profile.json to empty."""
    profile_path = BACKEND_DIR / "profile.json"
    empty = {"applicant_info": {}}
    try:
        with open(profile_path, "w", encoding="utf-8") as f:
            json.dump(empty, f, indent=2)
        return {"status": "ok", "message": "Profile cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/profile")
async def save_profile(profile: Dict[str, Any] = Body(...)):
    """Save profile JSON to backend profile.json for the application runner."""
    try:
        path = BACKEND_DIR / "profile.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        return {"status": "ok", "message": "Profile saved"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/parse")
async def parse_resume_endpoint(request: ResumeRequest):
    max_retries = 3
    retry_count = 0
    validation_error = None
    
    print("Parsing resume...")
    while retry_count < max_retries:
        if retry_count > 0:
            print(f"Retry attempt {retry_count}...")
        parsed = parse_resume(request.plaintext, validation_error)
        
        print("Validating output...")
        is_valid, reason = validate_output(request.plaintext, parsed)
        
        if is_valid:
            print("Validation PASSED")
            endpoint = request.endpoint or default_endpoint
            if endpoint:
                print(f"Sending to endpoint: {endpoint}")
                result = send_to_endpoint(parsed, endpoint)
                return {"status": "success", "data": parsed, "endpoint_response": result}
            return {"status": "success", "data": parsed}
        
        print(f"Validation FAILED: {reason}")
        validation_error = reason
        retry_count += 1
        if retry_count >= max_retries:
            raise HTTPException(status_code=422, detail=f"Validation failed after {max_retries} tries: {reason}")


class RunAutofillRequest(BaseModel):
    job_url: str
    headless: bool = False


def _load_profile_for_run() -> Tuple[Dict[str, Any], Optional[str]]:
    """Load profile from profile.json or sample.json. Returns (profile_data, encrypted_path or None)."""
    backend_dir = Path(__file__).resolve().parent
    # Only use encrypted profile when explicitly set; otherwise prefer profile.json (updated by upload)
    encrypted_path = os.environ.get("ENCRYPTED_PROFILE")
    if encrypted_path and os.path.exists(encrypted_path):
        return {}, encrypted_path
    profile_data = {}
    profile_json = backend_dir / "profile.json"
    if profile_json.exists():
        try:
            with open(profile_json, encoding="utf-8") as f:
                data = json.load(f)
            profile_data = data.get("applicant_info", data)
        except Exception:
            pass
    if not profile_data:
        sample = backend_dir / "tests" / "fixtures" / "sample.json"
        if sample.exists():
            with open(sample, encoding="utf-8") as f:
                data = json.load(f)
            profile_data = data.get("applicant_info", data)
    return profile_data, None


@app.post("/run")
def run_autofill_endpoint(request: RunAutofillRequest):
    """Run the application autofill tool on the given job URL. Uses profile from profile.json or sample."""
    try:
        from application_runner import run as run_autofill
    except ImportError:
        raise HTTPException(status_code=503, detail="Application runner not available")
    profile_data, encrypted_path = _load_profile_for_run()
    if not profile_data and not encrypted_path:
        raise HTTPException(status_code=400, detail="No profile found. Save your profile from the candidate details page first.")
    try:
        result = run_autofill(
            request.job_url,
            profile_data,
            encrypted_path=encrypted_path,
            headless=request.headless,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    return {"status": "running"}

