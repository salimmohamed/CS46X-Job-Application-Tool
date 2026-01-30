export interface JobExperience {
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

export interface WorkExperience {
  job_1: JobExperience;
  job_2: JobExperience;
  job_3: JobExperience;
}

export interface TechnicalExperience {
  skill_1: Skill;
  skill_2: Skill;
  skill_3: Skill;
  skill_4: Skill;
  skill_5: Skill;
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
  work_experience: WorkExperience;
  technical_experience: TechnicalExperience;
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

export interface ProfileData {
  applicant_info: ApplicantInfo;
}

export const createEmptyProfile = (): ProfileData => ({
  applicant_info: {
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    address: "",
    city: "",
    state: "",
    zip_code: "",
    country: "",
    resume_path: "",
    cover_letter_path: "",
    linkedin_url: "",
    portfolio_url: "",
    years_of_experience: "",
    education_level: "",
    college_name: "",
    salary_expectation: "",
    work_experience: {
      job_1: { company_name: "", position: "", start_month: "", start_year: "", end_month: "", end_year: "", description: "" },
      job_2: { company_name: "", position: "", start_month: "", start_year: "", end_month: "", end_year: "", description: "" },
      job_3: { company_name: "", position: "", start_month: "", start_year: "", end_month: "", end_year: "", description: "" }
    },
    technical_experience: {
      skill_1: { skill_name: "" },
      skill_2: { skill_name: "" },
      skill_3: { skill_name: "" },
      skill_4: { skill_name: "" },
      skill_5: { skill_name: "" }
    },
    education: { start_month: "", start_year: "", end_month: "", end_year: "" },
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
});
