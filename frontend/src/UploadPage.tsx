import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { uploadResume } from './services/resumeAPI'
import { ProfileData } from './types/profile'

// Sample data for demo mode - simulates partially parsed resume
const SAMPLE_PARSED_DATA: ProfileData = {
    applicant_info: {
        first_name: "Alex",
        last_name: "Johnson",
        email: "alex.johnson@example.com",
        phone: "+1-415-555-2478",
        address: "",
        city: "San Francisco",
        state: "CA",
        zip_code: "",
        country: "USA",
        resume_path: "",
        cover_letter_path: "",
        linkedin_url: "https://www.linkedin.com/in/alexjohnson",
        portfolio_url: "",
        years_of_experience: "5",
        education_level: "Bachelor's Degree in Computer Science",
        college_name: "University of California, Berkeley",
        salary_expectation: "",
        work_experience: {
            job_1: {
                company_name: "TechNova Solutions",
                position: "Machine Learning Engineer",
                start_month: "March",
                start_year: "2022",
                end_month: "",
                end_year: "",
                description: "Developed and deployed predictive models for client analytics."
            },
            job_2: {
                company_name: "DataEdge Analytics",
                position: "Data Scientist",
                start_month: "May",
                start_year: "2019",
                end_month: "February",
                end_year: "2022",
                description: ""
            },
            job_3: {
                company_name: "",
                position: "",
                start_month: "",
                start_year: "",
                end_month: "",
                end_year: "",
                description: ""
            }
        },
        technical_experience: {
            skill_1: { skill_name: "Python" },
            skill_2: { skill_name: "Machine Learning" },
            skill_3: { skill_name: "" },
            skill_4: { skill_name: "" },
            skill_5: { skill_name: "" }
        },
        education: {
            start_month: "August",
            start_year: "2015",
            end_month: "May",
            end_year: "2019"
        },
        willing_to_relocate: "",
        availability_date: "",
        work_authorization: "",
        gender: "",
        race_ethnicity: "",
        race: "",
        ethnicity: "",
        veteran_status: "",
        disability_status: "",
        requires_visa_sponsorship: ""
    }
};

function UploadPage() {
    const [resume, setResume] = useState<File | null>(null)
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const navigate = useNavigate()

    const handleUpload = async () => {
        if (!resume) return

        setLoading(true)
        setError(null)

        try {
            const profileData = await uploadResume(resume)
            navigate('/candidate-details', { state: { profileData } })
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Failed to upload resume')
        } finally {
            setLoading(false)
        }
    }

    // Demo mode - skip backend and use sample data
    const handleDemo = () => {
        navigate('/candidate-details', { state: { profileData: SAMPLE_PARSED_DATA } })
    }

    return (
        <div className="upload-page">
            <div className="upload-container">
                <h1>Upload Your Resume</h1>
                <p className="subtitle">
                    Upload your resume and we'll extract your information automatically.
                    You can review and complete any missing details on the next page.
                </p>

                <div className="upload-area">
                    <input
                        type="file"
                        id="resume-input"
                        accept=".pdf,.doc,.docx"
                        onChange={(e) => setResume(e.target.files?.[0] || null)}
                        disabled={loading}
                    />
                    <label htmlFor="resume-input" className="file-label">
                        {resume ? resume.name : 'Choose a file or drag it here'}
                    </label>
                    <p className="file-hint">Supported formats: PDF, DOC, DOCX</p>
                </div>

                <button
                    onClick={handleUpload}
                    disabled={!resume || loading}
                    className="upload-button"
                >
                    {loading ? 'Processing...' : 'Upload & Continue'}
                </button>

                <div className="divider">
                    <span>or</span>
                </div>

                <button
                    onClick={handleDemo}
                    className="demo-button"
                    type="button"
                >
                    Try Demo with Sample Data
                </button>

                {error && <p className="error-message">{error}</p>}
            </div>

            <style>{`
                .upload-page {
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 1rem;
                }
                .upload-container {
                    background: white;
                    padding: 3rem;
                    border-radius: 12px;
                    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
                    max-width: 500px;
                    width: 100%;
                    text-align: center;
                }
                .upload-container h1 {
                    color: #1a1a2e;
                    margin-bottom: 0.5rem;
                }
                .subtitle {
                    color: #666;
                    margin-bottom: 2rem;
                    font-size: 0.95rem;
                }
                .upload-area {
                    border: 2px dashed #ccc;
                    border-radius: 8px;
                    padding: 2rem;
                    margin-bottom: 1.5rem;
                    transition: border-color 0.2s;
                }
                .upload-area:hover {
                    border-color: #667eea;
                }
                .upload-area input[type="file"] {
                    display: none;
                }
                .file-label {
                    display: block;
                    cursor: pointer;
                    color: #667eea;
                    font-weight: 500;
                    margin-bottom: 0.5rem;
                }
                .file-hint {
                    color: #999;
                    font-size: 0.85rem;
                    margin: 0;
                }
                .upload-button {
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    border: none;
                    padding: 0.875rem 2rem;
                    font-size: 1rem;
                    font-weight: 600;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: transform 0.1s, opacity 0.2s;
                    width: 100%;
                }
                .upload-button:hover:not(:disabled) {
                    transform: scale(1.02);
                }
                .upload-button:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }
                .error-message {
                    color: #dc3545;
                    margin-top: 1rem;
                    font-size: 0.9rem;
                }
                .divider {
                    display: flex;
                    align-items: center;
                    margin: 1.5rem 0;
                }
                .divider::before,
                .divider::after {
                    content: '';
                    flex: 1;
                    height: 1px;
                    background: #ddd;
                }
                .divider span {
                    padding: 0 1rem;
                    color: #999;
                    font-size: 0.85rem;
                }
                .demo-button {
                    background: transparent;
                    color: #667eea;
                    border: 2px solid #667eea;
                    padding: 0.75rem 2rem;
                    font-size: 0.95rem;
                    font-weight: 500;
                    border-radius: 6px;
                    cursor: pointer;
                    transition: background 0.2s, color 0.2s;
                    width: 100%;
                }
                .demo-button:hover {
                    background: #667eea;
                    color: white;
                }
            `}</style>
        </div>
    )
}

export default UploadPage
