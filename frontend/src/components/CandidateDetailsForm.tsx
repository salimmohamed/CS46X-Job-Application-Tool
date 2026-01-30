import { useState, useEffect } from 'react';
import { ProfileData, JobExperience } from '../types/profile';
import './CandidateDetailsForm.css';

interface CandidateDetailsFormProps {
  initialData: ProfileData;
  onSubmit: (data: ProfileData) => void;
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const YEARS = Array.from({ length: 50 }, (_, i) => (new Date().getFullYear() - i).toString());

function CandidateDetailsForm({ initialData, onSubmit }: CandidateDetailsFormProps) {
  const [formData, setFormData] = useState<ProfileData>(initialData);
  const [unknownFields, setUnknownFields] = useState<Set<string>>(new Set());

  useEffect(() => {
    const unknown = new Set<string>();
    const info = initialData.applicant_info;

    // Check top-level fields
    const topLevelFields = [
      'first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state',
      'zip_code', 'country', 'linkedin_url', 'portfolio_url', 'years_of_experience',
      'education_level', 'college_name', 'salary_expectation', 'willing_to_relocate',
      'availability_date', 'work_authorization', 'gender', 'race_ethnicity', 'race',
      'ethnicity', 'veteran_status', 'disability_status', 'requires_visa_sponsorship'
    ];

    topLevelFields.forEach(field => {
      if (!info[field as keyof typeof info]) {
        unknown.add(field);
      }
    });

    // Check work experience
    ['job_1', 'job_2', 'job_3'].forEach(job => {
      const jobData = info.work_experience[job as keyof typeof info.work_experience];
      Object.keys(jobData).forEach(field => {
        if (!jobData[field as keyof JobExperience]) {
          unknown.add(`work_experience.${job}.${field}`);
        }
      });
    });

    // Check skills
    ['skill_1', 'skill_2', 'skill_3', 'skill_4', 'skill_5'].forEach(skill => {
      const skillData = info.technical_experience[skill as keyof typeof info.technical_experience];
      if (!skillData.skill_name) {
        unknown.add(`technical_experience.${skill}.skill_name`);
      }
    });

    // Check education dates
    ['start_month', 'start_year', 'end_month', 'end_year'].forEach(field => {
      if (!info.education[field as keyof typeof info.education]) {
        unknown.add(`education.${field}`);
      }
    });

    setUnknownFields(unknown);
  }, [initialData]);

  const handleChange = (path: string, value: string) => {
    setFormData(prev => {
      const newData = JSON.parse(JSON.stringify(prev)) as ProfileData;
      const parts = path.split('.');

      let current: Record<string, unknown> = newData.applicant_info;
      for (let i = 0; i < parts.length - 1; i++) {
        current = current[parts[i]] as Record<string, unknown>;
      }
      current[parts[parts.length - 1]] = value;

      return newData;
    });
  };

  const isUnknown = (path: string) => unknownFields.has(path);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const info = formData.applicant_info;

  return (
    <form className="candidate-form" onSubmit={handleSubmit}>
      <div className="form-header">
        <h1>Complete Your Profile</h1>
        <p className="form-description">
          Fields highlighted in <span className="unknown-indicator">yellow</span> could not be extracted from your resume and need your input.
        </p>
      </div>

      {/* Personal Information Section */}
      <section className="form-section">
        <h2>Personal Information</h2>
        <div className="form-grid">
          <div className={`form-group ${isUnknown('first_name') ? 'unknown' : ''}`}>
            <label htmlFor="first_name">First Name *</label>
            <input
              id="first_name"
              type="text"
              value={info.first_name}
              onChange={(e) => handleChange('first_name', e.target.value)}
              required
            />
          </div>
          <div className={`form-group ${isUnknown('last_name') ? 'unknown' : ''}`}>
            <label htmlFor="last_name">Last Name *</label>
            <input
              id="last_name"
              type="text"
              value={info.last_name}
              onChange={(e) => handleChange('last_name', e.target.value)}
              required
            />
          </div>
          <div className={`form-group ${isUnknown('email') ? 'unknown' : ''}`}>
            <label htmlFor="email">Email *</label>
            <input
              id="email"
              type="email"
              value={info.email}
              onChange={(e) => handleChange('email', e.target.value)}
              required
            />
          </div>
          <div className={`form-group ${isUnknown('phone') ? 'unknown' : ''}`}>
            <label htmlFor="phone">Phone</label>
            <input
              id="phone"
              type="tel"
              value={info.phone}
              onChange={(e) => handleChange('phone', e.target.value)}
            />
          </div>
        </div>
      </section>

      {/* Address Section */}
      <section className="form-section">
        <h2>Address</h2>
        <div className="form-grid">
          <div className={`form-group full-width ${isUnknown('address') ? 'unknown' : ''}`}>
            <label htmlFor="address">Street Address</label>
            <input
              id="address"
              type="text"
              value={info.address}
              onChange={(e) => handleChange('address', e.target.value)}
            />
          </div>
          <div className={`form-group ${isUnknown('city') ? 'unknown' : ''}`}>
            <label htmlFor="city">City</label>
            <input
              id="city"
              type="text"
              value={info.city}
              onChange={(e) => handleChange('city', e.target.value)}
            />
          </div>
          <div className={`form-group ${isUnknown('state') ? 'unknown' : ''}`}>
            <label htmlFor="state">State</label>
            <input
              id="state"
              type="text"
              value={info.state}
              onChange={(e) => handleChange('state', e.target.value)}
            />
          </div>
          <div className={`form-group ${isUnknown('zip_code') ? 'unknown' : ''}`}>
            <label htmlFor="zip_code">ZIP Code</label>
            <input
              id="zip_code"
              type="text"
              value={info.zip_code}
              onChange={(e) => handleChange('zip_code', e.target.value)}
            />
          </div>
          <div className={`form-group ${isUnknown('country') ? 'unknown' : ''}`}>
            <label htmlFor="country">Country</label>
            <input
              id="country"
              type="text"
              value={info.country}
              onChange={(e) => handleChange('country', e.target.value)}
            />
          </div>
        </div>
      </section>

      {/* Online Presence Section */}
      <section className="form-section">
        <h2>Online Presence</h2>
        <div className="form-grid">
          <div className={`form-group ${isUnknown('linkedin_url') ? 'unknown' : ''}`}>
            <label htmlFor="linkedin_url">LinkedIn URL</label>
            <input
              id="linkedin_url"
              type="url"
              value={info.linkedin_url}
              onChange={(e) => handleChange('linkedin_url', e.target.value)}
              placeholder="https://linkedin.com/in/..."
            />
          </div>
          <div className={`form-group ${isUnknown('portfolio_url') ? 'unknown' : ''}`}>
            <label htmlFor="portfolio_url">Portfolio URL</label>
            <input
              id="portfolio_url"
              type="url"
              value={info.portfolio_url}
              onChange={(e) => handleChange('portfolio_url', e.target.value)}
              placeholder="https://..."
            />
          </div>
        </div>
      </section>

      {/* Education Section */}
      <section className="form-section">
        <h2>Education</h2>
        <div className="form-grid">
          <div className={`form-group ${isUnknown('education_level') ? 'unknown' : ''}`}>
            <label htmlFor="education_level">Degree / Education Level</label>
            <input
              id="education_level"
              type="text"
              value={info.education_level}
              onChange={(e) => handleChange('education_level', e.target.value)}
              placeholder="e.g., Bachelor's in Computer Science"
            />
          </div>
          <div className={`form-group ${isUnknown('college_name') ? 'unknown' : ''}`}>
            <label htmlFor="college_name">College / University</label>
            <input
              id="college_name"
              type="text"
              value={info.college_name}
              onChange={(e) => handleChange('college_name', e.target.value)}
            />
          </div>
          <div className={`form-group ${isUnknown('education.start_month') ? 'unknown' : ''}`}>
            <label htmlFor="edu_start_month">Start Month</label>
            <select
              id="edu_start_month"
              value={info.education.start_month}
              onChange={(e) => handleChange('education.start_month', e.target.value)}
            >
              <option value="">Select Month</option>
              {MONTHS.map(month => (
                <option key={month} value={month}>{month}</option>
              ))}
            </select>
          </div>
          <div className={`form-group ${isUnknown('education.start_year') ? 'unknown' : ''}`}>
            <label htmlFor="edu_start_year">Start Year</label>
            <select
              id="edu_start_year"
              value={info.education.start_year}
              onChange={(e) => handleChange('education.start_year', e.target.value)}
            >
              <option value="">Select Year</option>
              {YEARS.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
          <div className={`form-group ${isUnknown('education.end_month') ? 'unknown' : ''}`}>
            <label htmlFor="edu_end_month">End Month</label>
            <select
              id="edu_end_month"
              value={info.education.end_month}
              onChange={(e) => handleChange('education.end_month', e.target.value)}
            >
              <option value="">Select Month</option>
              {MONTHS.map(month => (
                <option key={month} value={month}>{month}</option>
              ))}
            </select>
          </div>
          <div className={`form-group ${isUnknown('education.end_year') ? 'unknown' : ''}`}>
            <label htmlFor="edu_end_year">End Year</label>
            <select
              id="edu_end_year"
              value={info.education.end_year}
              onChange={(e) => handleChange('education.end_year', e.target.value)}
            >
              <option value="">Select Year</option>
              {YEARS.map(year => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>
      </section>

      {/* Work Experience Section */}
      <section className="form-section">
        <h2>Work Experience</h2>
        {(['job_1', 'job_2', 'job_3'] as const).map((jobKey, index) => {
          const job = info.work_experience[jobKey];
          return (
            <div key={jobKey} className="job-entry">
              <h3>Position {index + 1}</h3>
              <div className="form-grid">
                <div className={`form-group ${isUnknown(`work_experience.${jobKey}.company_name`) ? 'unknown' : ''}`}>
                  <label htmlFor={`${jobKey}_company`}>Company Name</label>
                  <input
                    id={`${jobKey}_company`}
                    type="text"
                    value={job.company_name}
                    onChange={(e) => handleChange(`work_experience.${jobKey}.company_name`, e.target.value)}
                  />
                </div>
                <div className={`form-group ${isUnknown(`work_experience.${jobKey}.position`) ? 'unknown' : ''}`}>
                  <label htmlFor={`${jobKey}_position`}>Position / Title</label>
                  <input
                    id={`${jobKey}_position`}
                    type="text"
                    value={job.position}
                    onChange={(e) => handleChange(`work_experience.${jobKey}.position`, e.target.value)}
                  />
                </div>
                <div className={`form-group ${isUnknown(`work_experience.${jobKey}.start_month`) ? 'unknown' : ''}`}>
                  <label htmlFor={`${jobKey}_start_month`}>Start Month</label>
                  <select
                    id={`${jobKey}_start_month`}
                    value={job.start_month}
                    onChange={(e) => handleChange(`work_experience.${jobKey}.start_month`, e.target.value)}
                  >
                    <option value="">Select Month</option>
                    {MONTHS.map(month => (
                      <option key={month} value={month}>{month}</option>
                    ))}
                  </select>
                </div>
                <div className={`form-group ${isUnknown(`work_experience.${jobKey}.start_year`) ? 'unknown' : ''}`}>
                  <label htmlFor={`${jobKey}_start_year`}>Start Year</label>
                  <select
                    id={`${jobKey}_start_year`}
                    value={job.start_year}
                    onChange={(e) => handleChange(`work_experience.${jobKey}.start_year`, e.target.value)}
                  >
                    <option value="">Select Year</option>
                    {YEARS.map(year => (
                      <option key={year} value={year}>{year}</option>
                    ))}
                  </select>
                </div>
                <div className={`form-group ${isUnknown(`work_experience.${jobKey}.end_month`) ? 'unknown' : ''}`}>
                  <label htmlFor={`${jobKey}_end_month`}>End Month</label>
                  <select
                    id={`${jobKey}_end_month`}
                    value={job.end_month}
                    onChange={(e) => handleChange(`work_experience.${jobKey}.end_month`, e.target.value)}
                  >
                    <option value="">Select Month</option>
                    <option value="Present">Present</option>
                    {MONTHS.map(month => (
                      <option key={month} value={month}>{month}</option>
                    ))}
                  </select>
                </div>
                <div className={`form-group ${isUnknown(`work_experience.${jobKey}.end_year`) ? 'unknown' : ''}`}>
                  <label htmlFor={`${jobKey}_end_year`}>End Year</label>
                  <select
                    id={`${jobKey}_end_year`}
                    value={job.end_year}
                    onChange={(e) => handleChange(`work_experience.${jobKey}.end_year`, e.target.value)}
                  >
                    <option value="">Select Year</option>
                    <option value="Present">Present</option>
                    {YEARS.map(year => (
                      <option key={year} value={year}>{year}</option>
                    ))}
                  </select>
                </div>
                <div className={`form-group full-width ${isUnknown(`work_experience.${jobKey}.description`) ? 'unknown' : ''}`}>
                  <label htmlFor={`${jobKey}_description`}>Description</label>
                  <textarea
                    id={`${jobKey}_description`}
                    value={job.description}
                    onChange={(e) => handleChange(`work_experience.${jobKey}.description`, e.target.value)}
                    rows={3}
                  />
                </div>
              </div>
            </div>
          );
        })}
      </section>

      {/* Technical Skills Section */}
      <section className="form-section">
        <h2>Technical Skills</h2>
        <div className="form-grid skills-grid">
          {(['skill_1', 'skill_2', 'skill_3', 'skill_4', 'skill_5'] as const).map((skillKey, index) => (
            <div key={skillKey} className={`form-group ${isUnknown(`technical_experience.${skillKey}.skill_name`) ? 'unknown' : ''}`}>
              <label htmlFor={skillKey}>Skill {index + 1}</label>
              <input
                id={skillKey}
                type="text"
                value={info.technical_experience[skillKey].skill_name}
                onChange={(e) => handleChange(`technical_experience.${skillKey}.skill_name`, e.target.value)}
                placeholder="e.g., Python, React, SQL..."
              />
            </div>
          ))}
        </div>
      </section>

      {/* Professional Details Section */}
      <section className="form-section">
        <h2>Professional Details</h2>
        <div className="form-grid">
          <div className={`form-group ${isUnknown('years_of_experience') ? 'unknown' : ''}`}>
            <label htmlFor="years_of_experience">Years of Experience</label>
            <input
              id="years_of_experience"
              type="text"
              value={info.years_of_experience}
              onChange={(e) => handleChange('years_of_experience', e.target.value)}
            />
          </div>
          <div className={`form-group ${isUnknown('salary_expectation') ? 'unknown' : ''}`}>
            <label htmlFor="salary_expectation">Salary Expectation ($)</label>
            <input
              id="salary_expectation"
              type="text"
              value={info.salary_expectation}
              onChange={(e) => handleChange('salary_expectation', e.target.value)}
              placeholder="e.g., 75000"
            />
          </div>
          <div className={`form-group ${isUnknown('willing_to_relocate') ? 'unknown' : ''}`}>
            <label htmlFor="willing_to_relocate">Willing to Relocate</label>
            <select
              id="willing_to_relocate"
              value={info.willing_to_relocate}
              onChange={(e) => handleChange('willing_to_relocate', e.target.value)}
            >
              <option value="">Select...</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
              <option value="Maybe">Maybe</option>
            </select>
          </div>
          <div className={`form-group ${isUnknown('availability_date') ? 'unknown' : ''}`}>
            <label htmlFor="availability_date">Availability Date</label>
            <input
              id="availability_date"
              type="date"
              value={info.availability_date}
              onChange={(e) => handleChange('availability_date', e.target.value)}
            />
          </div>
          <div className={`form-group ${isUnknown('work_authorization') ? 'unknown' : ''}`}>
            <label htmlFor="work_authorization">Work Authorization</label>
            <select
              id="work_authorization"
              value={info.work_authorization}
              onChange={(e) => handleChange('work_authorization', e.target.value)}
            >
              <option value="">Select...</option>
              <option value="U.S. Citizen">U.S. Citizen</option>
              <option value="Permanent Resident">Permanent Resident</option>
              <option value="Work Visa">Work Visa</option>
              <option value="Student Visa">Student Visa</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div className={`form-group ${isUnknown('requires_visa_sponsorship') ? 'unknown' : ''}`}>
            <label htmlFor="requires_visa_sponsorship">Requires Visa Sponsorship</label>
            <select
              id="requires_visa_sponsorship"
              value={info.requires_visa_sponsorship}
              onChange={(e) => handleChange('requires_visa_sponsorship', e.target.value)}
            >
              <option value="">Select...</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
        </div>
      </section>

      {/* Equal Employment Opportunity Section */}
      <section className="form-section">
        <h2>Equal Employment Opportunity (Optional)</h2>
        <p className="section-description">
          This information is collected for statistical purposes and will not affect your application.
        </p>
        <div className="form-grid">
          <div className={`form-group ${isUnknown('gender') ? 'unknown' : ''}`}>
            <label htmlFor="gender">Gender</label>
            <select
              id="gender"
              value={info.gender}
              onChange={(e) => handleChange('gender', e.target.value)}
            >
              <option value="">Prefer not to say</option>
              <option value="Male">Male</option>
              <option value="Female">Female</option>
              <option value="Non-binary">Non-binary</option>
              <option value="Other">Other</option>
            </select>
          </div>
          <div className={`form-group ${isUnknown('race_ethnicity') ? 'unknown' : ''}`}>
            <label htmlFor="race_ethnicity">Race/Ethnicity</label>
            <select
              id="race_ethnicity"
              value={info.race_ethnicity}
              onChange={(e) => handleChange('race_ethnicity', e.target.value)}
            >
              <option value="">Prefer not to say</option>
              <option value="American Indian or Alaska Native">American Indian or Alaska Native</option>
              <option value="Asian">Asian</option>
              <option value="Black or African American">Black or African American</option>
              <option value="Hispanic or Latino">Hispanic or Latino</option>
              <option value="Native Hawaiian or Pacific Islander">Native Hawaiian or Pacific Islander</option>
              <option value="White">White</option>
              <option value="Two or More Races">Two or More Races</option>
            </select>
          </div>
          <div className={`form-group ${isUnknown('veteran_status') ? 'unknown' : ''}`}>
            <label htmlFor="veteran_status">Veteran Status</label>
            <select
              id="veteran_status"
              value={info.veteran_status}
              onChange={(e) => handleChange('veteran_status', e.target.value)}
            >
              <option value="">Prefer not to say</option>
              <option value="Veteran">Veteran</option>
              <option value="Not a Veteran">Not a Veteran</option>
            </select>
          </div>
          <div className={`form-group ${isUnknown('disability_status') ? 'unknown' : ''}`}>
            <label htmlFor="disability_status">Disability Status</label>
            <select
              id="disability_status"
              value={info.disability_status}
              onChange={(e) => handleChange('disability_status', e.target.value)}
            >
              <option value="">Prefer not to say</option>
              <option value="Has Disability">Has Disability</option>
              <option value="No Disability">No Disability</option>
            </select>
          </div>
        </div>
      </section>

      <div className="form-actions">
        <button type="submit" className="submit-button">
          Save Profile
        </button>
      </div>
    </form>
  );
}

export default CandidateDetailsForm;
