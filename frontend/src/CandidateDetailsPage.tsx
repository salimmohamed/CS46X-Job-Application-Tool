import { useLocation, Link } from 'react-router-dom';
import CandidateDetailsForm from './components/CandidateDetailsForm';
import { ProfileData, createEmptyProfile } from './types/profile';
import { saveProfile, getProfile } from './services/resumeAPI';
import { useState, useEffect } from 'react';

function CandidateDetailsPage() {
  const location = useLocation();
  const [parsedData, setParsedData] = useState<ProfileData | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Use upload state when present; otherwise fetch from backend (empty profile when no upload)
  useEffect(() => {
    const stateData = location.state?.profileData as ProfileData | undefined;
    if (stateData) {
      setParsedData(stateData);
      return;
    }
    getProfile()
      .then((data) => {
        const empty = createEmptyProfile();
        const info = data?.applicant_info;
        if (!info || Object.keys(info).length === 0) {
          setParsedData(empty);
        } else {
          setParsedData({
            applicant_info: {
              ...empty.applicant_info,
              ...info,
              work_experience: { ...empty.applicant_info.work_experience, ...info.work_experience },
              technical_experience: { ...empty.applicant_info.technical_experience, ...info.technical_experience },
              education: { ...empty.applicant_info.education, ...info.education },
            },
          });
        }
      })
      .catch(() => setParsedData(createEmptyProfile()));
  }, [location.state?.profileData]);

  const handleSubmit = async (data: ProfileData) => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await saveProfile(data);

      // Also save to Chrome storage so the extension popup can display it
      if (typeof chrome !== 'undefined' && chrome.storage?.local) {
        chrome.storage.local.set({ user_profile: data });
      } else {
        localStorage.setItem('user_profile', JSON.stringify(data));
      }

      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  if (parsedData === null) {
    return (
      <div className="candidate-details-page">
        <div className="loading-message">Loading profile...</div>
        <style>{`
          .loading-message { text-align: center; padding: 2rem; color: #666; }
        `}</style>
      </div>
    );
  }

  return (
    <div className="candidate-details-page">
      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}
      {success && (
        <div className="success-banner">
          Profile saved successfully!{' '}
          <Link to="/apply" className="success-link">Continue to Apply →</Link>
        </div>
      )}
      <div className="candidate-details-actions">
        <Link to="/apply" className="apply-link">Go to Apply (run autofill) →</Link>
      </div>
      {saving && (
        <div className="saving-overlay">
          Saving...
        </div>
      )}
      <CandidateDetailsForm
        key={parsedData.applicant_info?.resume_path || parsedData.applicant_info?.email || 'new'}
        initialData={parsedData}
        onSubmit={handleSubmit}
      />
      <style>{`
        .candidate-details-page {
          width: 100%;
          min-height: 100vh;
          background-color: #f5f5f5;
          color: #1a1a2e;
          padding: 2rem 1rem;
          box-sizing: border-box;
          pointer-events: auto;
        }
        .error-banner {
          max-width: 900px;
          margin: 0 auto 1rem auto;
          padding: 1rem;
          background-color: #f8d7da;
          border: 1px solid #f5c6cb;
          border-radius: 4px;
          color: #721c24;
          text-align: center;
        }
        .success-banner {
          max-width: 900px;
          margin: 0 auto 1rem auto;
          padding: 1rem;
          background-color: #d4edda;
          border: 1px solid #c3e6cb;
          border-radius: 4px;
          color: #155724;
          text-align: center;
        }
        .success-link {
          color: #0d6e1e;
          font-weight: 600;
        }
        .candidate-details-actions {
          max-width: 900px;
          margin: 0 auto 1rem auto;
          text-align: center;
        }
        .apply-link {
          color: #4361ee;
          font-weight: 500;
        }
        .apply-link:hover {
          text-decoration: underline;
        }
        .saving-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background-color: rgba(255, 255, 255, 0.8);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          color: #4361ee;
          z-index: 1000;
        }
      `}</style>
    </div>
  );
}

export default CandidateDetailsPage;
