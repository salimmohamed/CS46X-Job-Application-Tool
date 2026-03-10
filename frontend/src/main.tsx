import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import UploadPage from './UploadPage'
import { ProfileEditorPopup } from './extension'
import CandidateDetailsPage from './CandidateDetailsPage'
import ApplyPage from './ApplyPage'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/popup" element={<ProfileEditorPopup />} />
        <Route path="/candidate-details" element={<CandidateDetailsPage />} />
        <Route path="/apply" element={<ApplyPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
