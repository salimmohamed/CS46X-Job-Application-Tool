# Job Hunting AI Web Tool

An AI-powered web application to expediate job searching by using machine learning, web scraping, and intelligent matching to connect users with relevant job opportunities.

## Project Team

- **Jessica Foley**
- **Gareth Starratt**
- **Salim Mohamed**
- **Zachary Jones**

## Tech Stack

### Frontend
- **Framework:** React 18+ with TypeScript
- **Build Tool:** Vite

# Backend 
 - **Unit/Integration testing** Pytest
 - **Orchestration** LangGraph/LangChain

### Web Scraping
- **Tools:** Selenium
- **Sources:** LinkedIn, Indeed, GitHub Jobs, custom scrapers etc

### DevOps & Deployment
- **Hosting:** Vercel or GitHub Pages
- **CI/CD:** GitHub Actions (planned)
- **Containerization:** Docker + Docker Compose (planned)


## Getting Started

Follow these steps to run the project locally:

### 1. Prerequisites

- [Node.js](https://nodejs.org/)
- [npm](https://www.npmjs.com/)

### 2. Clone the Repository

```bash
git clone https://github.com/DOGBALLGNOSIS/CS46X-Job-Application-Tool.git
cd CS46X-Job-Application-Tool
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
# or
yarn install
```

### 4. Start the Frontend Development Server

```bash
npm run dev
# or
yarn dev
```

By default, the app should be running at [http://localhost:5173](http://localhost:5173).

### 5. Run the full demo (backend + frontend)

From the **project root**, a single runner starts the backend API and frontend dev server and opens the app:

```bash
# Install backend deps first (once)
pip install -r backend/requirements.txt

# Run everything (backend on :8000, frontend on :5173)
python run_demo.py
```

On Windows you can double-click **`run_demo.bat`** (or run `python run_demo.py` from a terminal).

The runner will:
- Install frontend dependencies with `npm install` if needed
- Start the backend (uvicorn) on port 8000
- Start the frontend (Vite) on port 5173
- Open http://localhost:5173 in your browser

Press **Ctrl+C** to stop both servers. Ensure `OPENAI_API_KEY` is set in the environment for resume parsing and autofill.

### 6. Test the upload flow

```bash
cd backend
python run_upload_test.py
# Or: python run_upload_test.py --loop 3
```

Requires `OPENAI_API_KEY`. Verifies upload extracts data from the uploaded file only. If you see old data, click **"Clear cached profile"** on the Upload page first.

### 7. Re-hosting (Docker or production)

See **[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)** for:

- **Docker Compose**: `docker compose up -d --build` to run backend (port 8000) + frontend (port 8080).
- **Manual**: Build frontend with `VITE_API_URL` set, run backend with uvicorn, serve static files with nginx or any static server.
- Environment variables and production notes.
