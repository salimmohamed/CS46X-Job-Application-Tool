# Job Application Tool – Frontend

React + TypeScript + Vite frontend for the Job Application Tool: profile management, resume upload/parsing, and the extension popup.

## Setup

- **API URL:** The app calls the backend at `http://localhost:8000` by default. Override with `VITE_API_URL` (e.g. in `.env`: `VITE_API_URL=http://localhost:8000`).
- **Backend:** Run the resume parser/API so upload and save work:
  - `cd backend && pip install -r requirements.txt && uvicorn resume_parser:app --reload --port 8000`
- **Dev:** `npm install && npm run dev` (serves the full app with routes: Upload, Candidate Details, Popup view at `/popup`).
- **Build:** `npm run build` produces `dist/` with `index.html` (main app) and `popup.html` (extension popup).

## Frontend structure

- **Profile creation / management**
  - **Extension popup** (`popup.html` → `ProfileEditorPopup`): Loads profile from `chrome.storage.local` (or `localStorage` in dev). All fields are controlled; **Save Profile** persists to storage. **Create Profile** creates an empty profile and saves it.
  - **Full app** (`/`): **Upload Your Resume** → choose PDF → **Upload & Continue** calls `POST /upload` (extract text + parse) → navigates to **Complete Your Profile** with parsed data. **Save Profile** there calls `POST /profile` to save to the backend `profile.json` (used by the application runner when no encrypted profile is set).
- **Resume upload / parsing**
  - **Upload page** (`/`): File input accepts PDF only for real upload. **Try Demo with Sample Data** skips the backend and uses in-memory sample data.
  - **Backend** `POST /upload`: Accepts PDF, extracts text (pypdf), runs resume parser (OpenAI), saves file under `backend/uploads/resumes/`, returns `{ applicant_info }` with `resume_path` set.
- **Extension build:** Load the built app as an unpacked extension: point Chrome to `frontend/dist` and use the manifest there (action popup = `popup.html`).

## React + TypeScript + Vite (template notes)

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Babel](https://babeljs.io/) (or [oxc](https://oxc.rs) when used in [rolldown-vite](https://vite.dev/guide/rolldown)) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])
```
