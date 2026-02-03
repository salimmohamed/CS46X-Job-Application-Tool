import { useLocation } from 'react-router-dom';
import CandidateDetailsForm from './components/CandidateDetailsForm';
import { ProfileData, createEmptyProfile } from './types/profile';
import { saveProfile } from './services/resumeAPI';
import { useState } from 'react';

function CandidateDetailsPage() {
  const location = useLocation();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Get parsed data from navigation state, or use empty profile as fallback
  const parsedData = (location.state?.profileData as ProfileData) || createEmptyProfile();

  const handleSubmit = async (data: ProfileData) => {
    setSaving(true);
    setError(null);
    setSuccess(false);

    try {
      await saveProfile(data);
      setSuccess(true);
      // Optionally navigate to a confirmation page or dashboard
      // navigate('/dashboard');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="candidate-details-page">
      {error && (
        <div className="error-banner">
          {error}
        </div>
      )}
      {success && (
        <div className="success-banner">
          Profile saved successfully!
        </div>
      )}
      {saving && (
        <div className="saving-overlay">
          Saving...
        </div>
      )}
      <CandidateDetailsForm
        initialData={parsedData}
        onSubmit={handleSubmit}
      />
      <style>{`
        .candidate-details-page {
          min-height: 100vh;
          background-color: #f5f5f5;
          padding: 2rem 1rem;
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
