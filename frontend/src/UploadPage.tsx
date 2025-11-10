import { useState } from 'react'
import { uploadResume } from './services/resumeAPI'

function UploadPage() {
    const [resume, setResume] = useState<File | null>(null)
    const [success, setSuccess] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const handleUpload = () => {
        if (!resume) return

        setSuccess(false)
        setError(null)

        uploadResume(resume)
            .then(() => {
                setSuccess(true)
            })
            .catch((err) => {
                setError(err instanceof Error ? err.message : 'Failed to upload resume')
            })
    }

    return (
        <div>
            <h1>Upload Resume</h1>
            <input
                type="file"
                accept=".pdf,.doc,.docx"
                onChange={(e) => setResume(e.target.files?.[0] || null)}
            />
            <button onClick={handleUpload}>Upload</button>

            {success && <p>✅ Resume uploaded successfully!</p>}
            {error && <p>❌ Error: {error}</p>}
        </div>
    )
}

export default UploadPage