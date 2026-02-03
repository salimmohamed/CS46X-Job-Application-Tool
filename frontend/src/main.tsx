import React from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import UploadPage from './UploadPage'
import { ProfileEditorPopup } from './extension'
import CandidateDetailsPage from './CandidateDetailsPage'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<UploadPage />} />
        <Route path="/popup" element={<ProfileEditorPopup />} />
        <Route path="/candidate-details" element={<CandidateDetailsPage />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
)
