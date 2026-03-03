import React from 'react'
import { createRoot } from 'react-dom/client'
import { ProfileEditorPopup } from './extension'
import './index.css'

createRoot(document.getElementById('popup-root')!).render(
  <React.StrictMode>
    <ProfileEditorPopup />
  </React.StrictMode>
)
