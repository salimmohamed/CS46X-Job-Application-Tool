// collapsible card for profile sections with completion tracking
import { useState } from 'react';
import './ProfileSectionCard.css';

interface ProfileSectionCardProps {
  title: string;
  completedFields: number;
  totalFields: number;
  children: React.ReactNode;
}

export function ProfileSectionCard({
  title,
  completedFields,
  totalFields,
  children
}: ProfileSectionCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const isComplete = completedFields === totalFields;
  const completionPercent = totalFields > 0 ? Math.round((completedFields / totalFields) * 100) : 0;

  return (
    <div className={`profile-section-card ${isComplete ? 'complete' : 'incomplete'}`}>
      <button
        className="profile-section-header"
        onClick={() => setIsExpanded(!isExpanded)}
        aria-expanded={isExpanded}
      >
        <div className="profile-section-info">
          <span className="profile-section-title">{title}</span>
        </div>
        <div className="profile-section-status">
          <span className="profile-section-progress">
            {completedFields}/{totalFields}
          </span>
          <div className="profile-section-progress-bar">
            <div
              className="profile-section-progress-fill"
              style={{ width: `${completionPercent}%` }}
            />
          </div>
          <span className={`profile-section-chevron ${isExpanded ? 'expanded' : ''}`}>
            ▼
          </span>
        </div>
      </button>
      {isExpanded && (
        <div className="profile-section-content">
          {children}
        </div>
      )}
    </div>
  );
}
