"""
Rest API Resume parser service that converts plaintext resumes to JSON using GPT-3.5.

Takes plaintext resume, returns standardized JSON. Uses two-stage validation with retries. Can send parsed data to an optional endpoint.

Input:
    - Plaintext resume content (string)
    - Optional endpoint URL for forwarding parsed data

Output:
    - Standardized JSON schema matching profile.json structure

Run: uvicorn resume_parser_microservice:app --reload

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
from typing import Dict, Any, Tuple, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import requests

app = FastAPI()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("OPENAI_API_KEY not set")

default_endpoint = os.getenv("DEFAULT_ENDPOINT")
if not default_endpoint:
    print("Warning: DEFAULT_ENDPOINT not set. Parsed data will not be forwarded.")

client = OpenAI(api_key=api_key)
model = "gpt-3.5-turbo"

with open("profile.json", "r") as f:
    schema = json.load(f)


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
    
    system_msg = "Extract information from resume text into JSON schema. Leave fields blank if information is not present."
    
    validation_context = f"\n\nFix these errors:\n{validation_error}\n" if validation_error else ""
    
    user_msg = f"""Extract info from this resume into the JSON schema.

Resume:
{plaintext}

Schema:
{schema_str}

Rules:
- Only fill fields explicitly in the resume, leave blank if unknown
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


@app.get("/")
async def root():
    return {"status": "running"}

