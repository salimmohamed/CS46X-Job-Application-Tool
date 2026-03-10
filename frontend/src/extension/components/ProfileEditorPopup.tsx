// main popup component for the chrome extension
import { useState, useEffect } from 'react';
import { PopupHeader } from './PopupHeader';
import { PopupFooter } from './PopupFooter';
import { ProfileSectionCard } from './ProfileSectionCard';
import { useProfileStorage } from '../hooks/useProfileStorage';
import { emptyUserProfile } from '../types/ProfileTypes';
import type { UserProfile } from '../types/ProfileTypes';
import './ProfileEditorPopup.css';

type TabType = 'profile' | 'matches' | 'saved';

export function ProfileEditorPopup() {
  const [activeTab, setActiveTab] = useState<TabType>('profile');
  const { profile, isLoading, error, saveProfile } = useProfileStorage();
  const [localProfile, setLocalProfile] = useState<UserProfile | null>(null);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle');

  useEffect(() => {
    if (profile) {
      setLocalProfile(JSON.parse(JSON.stringify(profile)));
    } else {
      setLocalProfile(null);
    }
  }, [profile]);

  const updateField = (field: keyof UserProfile['applicant_info'], value: string) => {
    setLocalProfile((prev) => {
      if (!prev) return prev;
      const next = JSON.parse(JSON.stringify(prev)) as UserProfile;
      const info = next.applicant_info as unknown as Record<string, unknown>;
      info[field] = value;
      return next;
    });
  };

  const handleSave = async () => {
    if (!localProfile) return;
    setSaveStatus('saving');
    const ok = await saveProfile(localProfile);
    setSaveStatus(ok ? 'saved' : 'error');
    if (ok) setTimeout(() => setSaveStatus('idle'), 2000);
  };

  const handleCreateProfile = async () => {
    const empty = JSON.parse(JSON.stringify(emptyUserProfile)) as UserProfile;
    setLocalProfile(empty);
    const ok = await saveProfile(empty);
    if (!ok) setSaveStatus('error');
  };

  const displayProfile = localProfile ?? profile;

  const getFieldCount = (obj: Record<string, unknown> | undefined): { completed: number; total: number } => {
    if (!obj) return { completed: 0, total: 0 };
    let completed = 0;
    let total = 0;

    Object.values(obj).forEach(value => {
      if (typeof value === 'string') {
        total++;
        if (value.trim() !== '') completed++;
      }
    });

    return { completed, total };
  };

  const personalInfo = displayProfile?.applicant_info;
  const contactFields = getFieldCount({
    first_name: personalInfo?.first_name,
    last_name: personalInfo?.last_name,
    email: personalInfo?.email,
    phone: personalInfo?.phone,
  });

  const locationFields = getFieldCount({
    address: personalInfo?.address,
    city: personalInfo?.city,
    state: personalInfo?.state,
    zip_code: personalInfo?.zip_code,
    country: personalInfo?.country,
  });

  const linksFields = getFieldCount({
    linkedin_url: personalInfo?.linkedin_url,
    portfolio_url: personalInfo?.portfolio_url,
  });

  const experienceFields = getFieldCount({
    years_of_experience: personalInfo?.years_of_experience,
  });

  const educationFields = getFieldCount({
    education_level: personalInfo?.education_level,
    college_name: personalInfo?.college_name,
  });

  const renderProfileContent = () => {
    if (isLoading) {
      return (
        <div className="popup-loading">
          <span>Loading profile...</span>
        </div>
      );
    }

    if (error) {
      return (
        <div className="popup-error">
          <span>Error: {error}</span>
        </div>
      );
    }

    if (!displayProfile) {
      return (
        <div className="popup-empty">
          <h3>No Profile Yet</h3>
          <p>Upload your resume to get started, or fill in your details manually.</p>
          <button className="popup-empty-button" onClick={() => window.open('http://localhost:5173/', '_blank')}>
            Create Profile
          </button>
        </div>
      );
    }

    return (
      <div className="popup-sections">
        <ProfileSectionCard
          title="Contact Info"
          completedFields={contactFields.completed}
          totalFields={contactFields.total}
        >
          <div className="profile-field">
            <label>First Name</label>
            <input type="text" value={personalInfo?.first_name ?? ''} onChange={(e) => updateField('first_name', e.target.value)} placeholder="Enter first name" />
          </div>
          <div className="profile-field">
            <label>Last Name</label>
            <input type="text" value={personalInfo?.last_name ?? ''} onChange={(e) => updateField('last_name', e.target.value)} placeholder="Enter last name" />
          </div>
          <div className="profile-field">
            <label>Email</label>
            <input type="email" value={personalInfo?.email ?? ''} onChange={(e) => updateField('email', e.target.value)} placeholder="Enter email" />
          </div>
          <div className="profile-field">
            <label>Phone</label>
            <input type="tel" value={personalInfo?.phone ?? ''} onChange={(e) => updateField('phone', e.target.value)} placeholder="Enter phone" />
          </div>
        </ProfileSectionCard>

        <ProfileSectionCard
          title="Location"
          completedFields={locationFields.completed}
          totalFields={locationFields.total}
        >
          <div className="profile-field">
            <label>Address</label>
            <input type="text" value={personalInfo?.address ?? ''} onChange={(e) => updateField('address', e.target.value)} placeholder="Enter address" />
          </div>
          <div className="profile-field-row">
            <div className="profile-field">
              <label>City</label>
              <input type="text" value={personalInfo?.city ?? ''} onChange={(e) => updateField('city', e.target.value)} placeholder="City" />
            </div>
            <div className="profile-field">
              <label>State</label>
              <input type="text" value={personalInfo?.state ?? ''} onChange={(e) => updateField('state', e.target.value)} placeholder="State" />
            </div>
          </div>
          <div className="profile-field-row">
            <div className="profile-field">
              <label>Zip Code</label>
              <input type="text" value={personalInfo?.zip_code ?? ''} onChange={(e) => updateField('zip_code', e.target.value)} placeholder="Zip" />
            </div>
            <div className="profile-field">
              <label>Country</label>
              <input type="text" value={personalInfo?.country ?? ''} onChange={(e) => updateField('country', e.target.value)} placeholder="Country" />
            </div>
          </div>
        </ProfileSectionCard>

        <ProfileSectionCard
          title="Links"
          completedFields={linksFields.completed}
          totalFields={linksFields.total}
        >
          <div className="profile-field">
            <label>LinkedIn URL</label>
            <input type="url" value={personalInfo?.linkedin_url ?? ''} onChange={(e) => updateField('linkedin_url', e.target.value)} placeholder="https://linkedin.com/in/..." />
          </div>
          <div className="profile-field">
            <label>Portfolio URL</label>
            <input type="url" value={personalInfo?.portfolio_url ?? ''} onChange={(e) => updateField('portfolio_url', e.target.value)} placeholder="https://..." />
          </div>
        </ProfileSectionCard>

        <ProfileSectionCard
          title="Experience"
          completedFields={experienceFields.completed}
          totalFields={experienceFields.total}
        >
          <div className="profile-field">
            <label>Years of Experience</label>
            <select value={personalInfo?.years_of_experience ?? ''} onChange={(e) => updateField('years_of_experience', e.target.value)}>
              <option value="">Select...</option>
              <option value="0-1">0-1 years</option>
              <option value="1-3">1-3 years</option>
              <option value="3-5">3-5 years</option>
              <option value="5-10">5-10 years</option>
              <option value="10+">10+ years</option>
            </select>
          </div>
        </ProfileSectionCard>

        <ProfileSectionCard
          title="Education"
          completedFields={educationFields.completed}
          totalFields={educationFields.total}
        >
          <div className="profile-field">
            <label>Education Level</label>
            <select value={personalInfo?.education_level ?? ''} onChange={(e) => updateField('education_level', e.target.value)}>
              <option value="">Select...</option>
              <option value="high_school">High School</option>
              <option value="associate">Associate's Degree</option>
              <option value="bachelor">Bachelor's Degree</option>
              <option value="master">Master's Degree</option>
              <option value="doctorate">Doctorate</option>
            </select>
          </div>
          <div className="profile-field">
            <label>College/University</label>
            <input type="text" value={personalInfo?.college_name ?? ''} onChange={(e) => updateField('college_name', e.target.value)} placeholder="Enter school name" />
          </div>
        </ProfileSectionCard>

        <div className="popup-save-row">
          <button type="button" className="popup-save-button" onClick={handleSave} disabled={saveStatus === 'saving'}>
            {saveStatus === 'saving' ? 'Saving...' : saveStatus === 'saved' ? 'Saved!' : 'Save Profile'}
          </button>
        </div>
      </div>
    );
  };

  const renderMatchesContent = () => (
    <div className="popup-placeholder">
      <h3>Job Matches</h3>
      <p>Your personalized job matches will appear here.</p>
    </div>
  );

  const renderSavedContent = () => (
    <div className="popup-placeholder">
      <h3>Saved Jobs</h3>
      <p>Jobs you've saved will appear here.</p>
    </div>
  );

  return (
    <div className="profile-editor-popup">
      <PopupHeader
        userName={displayProfile?.applicant_info?.first_name}
        onSettingsClick={() => console.log('Settings clicked')}
      />

      <main className="popup-content">
        {activeTab === 'profile' && renderProfileContent()}
        {activeTab === 'matches' && renderMatchesContent()}
        {activeTab === 'saved' && renderSavedContent()}
      </main>

      <PopupFooter
        activeTab={activeTab}
        onTabChange={setActiveTab}
      />
    </div>
  );
}
