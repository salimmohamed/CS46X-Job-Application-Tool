// profile types for the extension popup - mirrors backend schema

export interface WorkExperience {
  company_name: string;
  position: string;
  start_month: string;
  start_year: string;
  end_month: string;
  end_year: string;
  description: string;
}

export interface Skill {
  skill_name: string;
}

export interface Education {
  start_month: string;
  start_year: string;
  end_month: string;
  end_year: string;
}

export interface ApplicantInfo {
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  country: string;
  resume_path: string;
  cover_letter_path: string;
  linkedin_url: string;
  portfolio_url: string;
  years_of_experience: string;
  education_level: string;
  college_name: string;
  salary_expectation: string;
  work_experience: {
    job_1: WorkExperience;
    job_2: WorkExperience;
    job_3: WorkExperience;
  };
  technical_experience: {
    skill_1: Skill;
    skill_2: Skill;
    skill_3: Skill;
    skill_4: Skill;
    skill_5: Skill;
  };
  education: Education;
  willing_to_relocate: string;
  availability_date: string;
  work_authorization: string;
  gender: string;
  race_ethnicity: string;
  race: string;
  ethnicity: string;
  veteran_status: string;
  disability_status: string;
  requires_visa_sponsorship: string;
}

export interface UserProfile {
  applicant_info: ApplicantInfo;
}

// section metadata for rendering completion status
export interface ProfileSection {
  id: string;
  title: string;
  isComplete: boolean;
  fieldCount: number;
  completedFieldCount: number;
}

const emptyWorkExperience: WorkExperience = {
  company_name: '',
  position: '',
  start_month: '',
  start_year: '',
  end_month: '',
  end_year: '',
  description: '',
};

const emptySkill: Skill = { skill_name: '' };

const emptyEducation: Education = {
  start_month: '',
  start_year: '',
  end_month: '',
  end_year: '',
};

/** Empty applicant info for "Create Profile" and initial state */
export const emptyApplicantInfo: ApplicantInfo = {
  first_name: '',
  last_name: '',
  email: '',
  phone: '',
  address: '',
  city: '',
  state: '',
  zip_code: '',
  country: '',
  resume_path: '',
  cover_letter_path: '',
  linkedin_url: '',
  portfolio_url: '',
  years_of_experience: '',
  education_level: '',
  college_name: '',
  salary_expectation: '',
  work_experience: {
    job_1: { ...emptyWorkExperience },
    job_2: { ...emptyWorkExperience },
    job_3: { ...emptyWorkExperience },
  },
  technical_experience: {
    skill_1: { ...emptySkill },
    skill_2: { ...emptySkill },
    skill_3: { ...emptySkill },
    skill_4: { ...emptySkill },
    skill_5: { ...emptySkill },
  },
  education: { ...emptyEducation },
  willing_to_relocate: '',
  availability_date: '',
  work_authorization: '',
  gender: '',
  race_ethnicity: '',
  race: '',
  ethnicity: '',
  veteran_status: '',
  disability_status: '',
  requires_visa_sponsorship: '',
};

export const emptyUserProfile: UserProfile = {
  applicant_info: { ...emptyApplicantInfo },
};
