# Re-hosting the Job Application Tool

Ways to run the full stack (frontend + backend) locally or on a server.

---

## 1. Quick local run (development)

From the **project root**:

```bash
pip install -r backend/requirements.txt   # once
python run_demo.py
```

- Backend: http://localhost:8000  
- Frontend: http://localhost:5173 (opens in browser)  
- Press **Ctrl+C** to stop.

Requires: Python 3, Node 18+, `OPENAI_API_KEY` in the environment.

---

## 2. Docker Compose (full stack)

Runs backend + frontend in containers. Good for a single server or your own machine.

### Prerequisites

- Docker and Docker Compose
- `OPENAI_API_KEY` set (e.g. in `backend/.env` or export)

### Steps

1. **Create `backend/.env`** (if missing):

   ```
   OPENAI_API_KEY=your-key-here
   ```

2. **Set the API URL the browser will use** (optional):

   - Same machine: `VITE_API_URL=http://localhost:8000` (default)
   - Server with domain: `VITE_API_URL=https://api.yourdomain.com`

3. **Build and start** (from project root):

   ```bash
   docker compose up -d --build
   ```

4. **Open the app**

   - Frontend: http://localhost:8080  
   - Backend API: http://localhost:8000  

5. **Stop**

   ```bash
   docker compose down
   ```

### Docker Compose services

| Service   | Port | Description                    |
|----------|------|--------------------------------|
| backend  | 8000 | Resume parser, upload, profile |
| frontend | 8080 | Static app (Vite build + nginx)|

### Notes

- **Run autofill** (Apply page “Start autofill”) needs a browser and Chrome/Chromium. The Docker backend does **not** include Chrome, so that flow is intended for **local** use (e.g. run `python application_runner.py` or use the app with a local backend started by `run_demo.py`).
- Uploaded resumes are stored in a Docker volume `backend_uploads`.
- Profile saved from the app is written to `backend/profile.json` (mounted from the host).

---

## 3. Manual production-style (build + run)

For hosting on a VPS or server without Docker.

### Backend

```bash
cd backend
pip install -r requirements.txt
export OPENAI_API_KEY=your-key
uvicorn resume_parser:app --host 0.0.0.0 --port 8000
```

Keep this running (e.g. with systemd or a process manager).

### Frontend

1. **Build** with the API URL the browser will use:

   ```bash
   cd frontend
   npm ci
   export VITE_API_URL=https://api.yourdomain.com   # or http://your-server:8000
   npm run build
   ```

2. **Serve** the `frontend/dist` folder:

   - Any static server (e.g. nginx, Caddy, or `npx serve -s dist -p 8080`).
   - SPA routing: point all routes to `index.html` (e.g. nginx `try_files $uri $uri/ /index.html`).

### Example nginx (backend + frontend on same server)

```nginx
# Backend
server {
    listen 8000;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
}

# Frontend
server {
    listen 80;
    root /path/to/frontend/dist;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

Then set `VITE_API_URL=http://your-server:8000` (or the public URL) when building the frontend.

---

## 4. Environment variables

| Variable        | Where     | Purpose                          |
|----------------|-----------|----------------------------------|
| OPENAI_API_KEY | Backend   | Resume parsing, LLM form mapping |
| VITE_API_URL   | Frontend  | API base URL (at **build** time) |
| ENCRYPTED_PROFILE | Backend | Optional; path to encrypted profile for runner |

---

## 5. Checklist for re-hosting

- [ ] Backend reachable at the URL you set as `VITE_API_URL` (CORS allows your frontend origin if needed).
- [ ] `OPENAI_API_KEY` set for the backend.
- [ ] Frontend built with the correct `VITE_API_URL` for the environment.
- [ ] HTTPS in production (terminate SSL at nginx/load balancer or use a hosting provider that does).
- [ ] For “Run autofill” in production you’d need a backend with Chrome/Chromium (e.g. custom Docker image with Chrome + Selenium) or a separate runner service; the default Docker backend does not include it.
