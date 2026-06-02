# Job Application Tool - Quick Start Guide

Job hunting is repetitive. Every application asks for the same information: your name, address, work history, education, and you end up typing it out over and over. This tool fixes that. Upload your resume once, the app pulls out all your details using AI, and a Chrome extension handles filling in job application forms for you going forward.

---

## Getting It Running

You'll need Python 3.12+, Node.js 18+, and an OpenAI API key before anything else.

```bash
# clone the repo
git clone https://github.com/salimmohamed/CS46X-Job-Application-Tool.git
cd CS46X-Job-Application-Tool

# backend
cd backend
cp .env.example .env          # then open .env and paste in your OPENAI_API_KEY
pip install -r requirements.txt

# frontend
cd ../frontend
npm install

# start everything from the project root
python run_demo.py
```

That last command starts both servers and opens the app at `http://localhost:5173`.

If you'd rather not deal with Python and Node, Docker works too:

```bash
OPENAI_API_KEY=your_key docker compose up -d --build
# frontend at :8080, backend at :8000
```

---

## How It Works

```
┌──────────────────────────────────────────────────────────┐
│                          User                            │
└──────────┬───────────────────────────┬───────────────────┘
           │ uploads resume            │ visits job site
           ▼                           ▼
┌─────────────────────┐     ┌──────────────────────────────┐
│   React Frontend    │     │      Chrome Extension        │
│   (port 5173)       │     │   (Manifest v3 / background  │
│                     │     │    service worker)           │
│  Upload Page        │     │                              │
│  Profile Editor     │     │  reads saved profile and     │
│  Apply Page         │     │  autofills the form          │
└────────┬────────────┘     └──────────────────────────────┘
         │ REST API
         ▼
┌─────────────────────┐
│   FastAPI Backend   │
│   (port 8000)       │
│                     │
│  resume parsing  ───┼──── OpenAI (GPT-4o-mini)
│  profile storage    │
│  form field mapping │
│  encryption         │
└─────────────────────┘
```

---

## Features

### Upload & Parse

Go to the Upload Page and either drop in a resume (PDF, DOC, or DOCX) or hit **"Try Demo with Sample Data"** if you just want to poke around. Click **"Upload & Continue"** and the backend sends it through OpenAI, which pulls out your personal info, address, education, work history, skills, and professional details.

No API key? Use the demo button. It loads a pre-filled sample so you can see how everything looks without needing the backend running.

---

### Profile Editor

After the upload, you land on the Candidate Details form. Fields the parser couldn't find are highlighted in yellow and need your attention. White fields were filled in automatically but you can still edit them. Once everything looks right, hit **"Save Profile"** at the bottom. Green banner means it worked; red means something went wrong (usually the backend isn't running).

The form covers six sections: Personal Info, Address, Education, Work Experience, Skills, and Professional Details.

---

### Chrome Extension (Autofill)

Once your profile is saved, the extension takes over on actual job sites. It works with Workday, Greenhouse, Lever, Taleo, and a few others.

To load it:

1. Run `npm run build` inside `frontend/` to generate the files the extension needs.
2. Open Chrome, go to `chrome://extensions`, and turn on **Developer mode** in the top-right corner.
3. Click **"Load unpacked"** and point it at the `extension` folder in the project root.
4. The "Job Application Tool" extension shows up and starts running automatically.

Your profile stays loaded even if Chrome puts the extension to sleep in the background.

---

## User Flow

```
Upload resume (or use the demo)
         │
         ▼
AI parses resume ──────────────────► profile.json saved
         │                                    │
         ▼                                    │
Review form, fill yellow fields               │
         │                                    │
         ▼                                    │
Save Profile ◄────────────────────────────────┘
         │
         ▼
Install Chrome extension
         │
         ▼
Visit a job application page
         │
         ▼
Extension fills in the form
         │
         ▼
Submit and move on
```

---

## If Something Breaks

**"Upload failed":** the backend isn't running. Either start it (`uvicorn resume_parser:app --reload` from `/backend`) or just use the demo button.

**Every field is yellow:** no profile data got loaded. Go back to the Upload Page and try again, or use the demo.

**Extension not showing up in Chrome:** check that Developer mode is on and that you selected the `extension` folder (the one with `manifest.json` in it, not `frontend/dist`).

**OpenAI error on upload:** your API key is missing or wrong. Open `backend/.env` and check `OPENAI_API_KEY`.
