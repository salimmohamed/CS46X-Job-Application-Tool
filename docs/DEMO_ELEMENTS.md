# Demo elements – itemized breakdown

## In place

### 1. **Resume upload (frontend)**
- **UploadPage** (`/`): File input for PDF; "Upload & Continue" calls `POST /upload`; "Try Demo with Sample Data" uses in-memory sample (Alex Johnson) and navigates to candidate details.
- **Backend** `POST /upload`: Accepts PDF, extracts text (pypdf), runs resume parser (OpenAI), saves file under `backend/uploads/resumes/`, returns `{ applicant_info }` with `resume_path` set.

### 2. **Candidate profile form (frontend)**
- **CandidateDetailsPage** (`/candidate-details`): Receives profile from navigation state (after upload or demo). Renders **CandidateDetailsForm** (full schema: personal info, address, work experience, skills, education, EEOC, etc.).
- **Save Profile**: Calls `POST /profile` to persist to `backend/profile.json`.
- **CandidateDetailsForm**: Controlled form with unknown-field highlighting; submits `ProfileData` to parent.

### 3. **Profile storage (extension + web)**
- **Extension popup** (`popup.html` → ProfileEditorPopup): Loads/saves profile to `chrome.storage.local` (or `localStorage` in dev). Tabs: Profile | Matches | Saved. Profile tab: controlled inputs, Save Profile, Create Profile.
- **Backend** `POST /profile`: Writes request body to `backend/profile.json`.

### 4. **Application runner (backend only)**
- **application_runner.py**: `run(job_url, profile_data, ...)` uses Selenium + FormInteractionEngine to navigate to `job_url`, click Apply/Continue, fill forms from profile (rules + heuristic + LLM), handle multi-page flow. Profile loaded from encrypted file, or `profile.json`, or `tests/fixtures/sample.json`.
- **CLI**: `JOB_URL=<url> python application_runner.py` (no frontend trigger).

### 5. **Routing and build**
- **main.tsx**: Routes `/`, `/popup`, `/candidate-details`. Build outputs `index.html` (main app) and `popup.html` (extension popup).
- **Extension**: Manifest in `frontend/public/manifest.json` with `action.default_popup: "popup.html"`; load unpacked from `frontend/dist`.

### 6. **Supporting backend**
- **resume_parser.py**: `POST /parse` (plaintext), CORS for frontend origins, schema from `profile.json`.
- **Sample data**: `tests/fixtures/sample.json`, `sample_resume.txt`, `sample_resume.pdf`; runner uses `profile.json` then sample when no encrypted profile.

---

### 7. **“Next” step after candidate details**
- **In place**: “Continue to Apply” in the success banner and “Go to Apply (run autofill)” link on Candidate Details; both navigate to `/apply`.

### 8. **Apply / Run page with sidebar**
- **In place**: **ApplyPage** at route `/apply` with:
  - **Sidebar**: Job application URL input (default: MacKay Sposito test URL), “Run browser in background” checkbox, “Start autofill” button, status (idle / running / success / error) and result summary (pages processed, fields filled).
  - **Main area**: Short instructions.

### 9. **Backend API to run the autofill**
- **In place**: **POST /run** in `resume_parser.py`:
  - Body: `{ "job_url": string, "headless": bool }`.
  - Loads profile from `profile.json` or `tests/fixtures/sample.json` (or encrypted profile if set).
  - Calls `application_runner.run(...)` and returns `{ success, status, pages_processed, fields_filled, error?, results? }`.

---

## Summary

| # | Element | Status |
|---|--------|--------|
| 1 | Resume upload (frontend + POST /upload) | In place |
| 2 | Candidate profile form + Save (POST /profile) | In place |
| 3 | Profile storage (extension popup + backend profile.json) | In place |
| 4 | Application runner (Selenium autofill, CLI) | In place |
| 5 | Routing and extension build | In place |
| 6 | Supporting backend (parse, CORS, sample data) | In place |
| 7 | Navigation from Candidate Details to “Apply” step | In place |
| 8 | Apply page with sidebar (URL + Start + status) | In place |
| 9 | Backend POST /run to run autofill | In place |

**Full demo flow:** Upload resume → Complete candidate details → Save profile → Go to Apply → Enter/confirm job URL → Start autofill → Tool runs and fills the form.
