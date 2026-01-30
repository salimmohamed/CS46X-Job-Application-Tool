// main popup component for the chrome extension
import { useState } from 'react';
import { PopupHeader } from './PopupHeader';
import { PopupFooter } from './PopupFooter';
import { ProfileSectionCard } from './ProfileSectionCard';
import { useProfileStorage } from '../hooks/useProfileStorage';
import './ProfileEditorPopup.css';

type TabType = 'profile' | 'matches' | 'saved';

export function ProfileEditorPopup() {
  const [activeTab, setActiveTab] = useState<TabType>('profile');
  const { profile, isLoading, error } = useProfileStorage();

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

  const personalInfo = profile?.applicant_info;
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

    if (!profile) {
      return (
        <div className="popup-empty">
          <h3>No Profile Yet</h3>
          <p>Upload your resume to get started, or fill in your details manually.</p>
          <button className="popup-empty-button">
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
            <input type="text" defaultValue={personalInfo?.first_name} placeholder="Enter first name" />
          </div>
          <div className="profile-field">
            <label>Last Name</label>
            <input type="text" defaultValue={personalInfo?.last_name} placeholder="Enter last name" />
          </div>
          <div className="profile-field">
            <label>Email</label>
            <input type="email" defaultValue={personalInfo?.email} placeholder="Enter email" />
          </div>
          <div className="profile-field">
            <label>Phone</label>
            <input type="tel" defaultValue={personalInfo?.phone} placeholder="Enter phone" />
          </div>
        </ProfileSectionCard>

        <ProfileSectionCard
          title="Location"
          completedFields={locationFields.completed}
          totalFields={locationFields.total}
        >
          <div className="profile-field">
            <label>Address</label>
            <input type="text" defaultValue={personalInfo?.address} placeholder="Enter address" />
          </div>
          <div className="profile-field-row">
            <div className="profile-field">
              <label>City</label>
              <input type="text" defaultValue={personalInfo?.city} placeholder="City" />
            </div>
            <div className="profile-field">
              <label>State</label>
              <input type="text" defaultValue={personalInfo?.state} placeholder="State" />
            </div>
          </div>
          <div className="profile-field-row">
            <div className="profile-field">
              <label>Zip Code</label>
              <input type="text" defaultValue={personalInfo?.zip_code} placeholder="Zip" />
            </div>
            <div className="profile-field">
              <label>Country</label>
              <input type="text" defaultValue={personalInfo?.country} placeholder="Country" />
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
            <input type="url" defaultValue={personalInfo?.linkedin_url} placeholder="https://linkedin.com/in/..." />
          </div>
          <div className="profile-field">
            <label>Portfolio URL</label>
            <input type="url" defaultValue={personalInfo?.portfolio_url} placeholder="https://..." />
          </div>
        </ProfileSectionCard>

        <ProfileSectionCard
          title="Experience"
          completedFields={experienceFields.completed}
          totalFields={experienceFields.total}
        >
          <div className="profile-field">
            <label>Years of Experience</label>
            <select defaultValue={personalInfo?.years_of_experience}>
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
            <select defaultValue={personalInfo?.education_level}>
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
            <input type="text" defaultValue={personalInfo?.college_name} placeholder="Enter school name" />
          </div>
        </ProfileSectionCard>
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
        userName={profile?.applicant_info?.first_name}
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
