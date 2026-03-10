import { ProfileData } from '../types/profile';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const uploadResume = async (file: File): Promise<ProfileData> => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE_URL}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || `Error: ${response.statusText}`);
  }

  const data = await response.json();
  return data as ProfileData;
};

export const getProfile = async (): Promise<ProfileData> => {
  const response = await fetch(`${API_BASE_URL}/profile`);
  if (!response.ok) throw new Error('Failed to load profile');
  const data = await response.json();
  return data as ProfileData;
};

export const clearProfile = async (): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/profile/clear`, { method: 'POST' });
  if (!response.ok) throw new Error('Failed to clear profile');
};

export const saveProfile = async (profile: ProfileData): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/profile`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(profile),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Failed to save profile' }));
    throw new Error(error.detail || `Error: ${response.statusText}`);
  }
};

export interface RunAutofillResult {
  success: boolean;
  status: string;
  pages_processed?: number;
  fields_filled?: number;
  error?: string;
  results?: Array<{ field?: string; status?: string }>;
}

export const runAutofill = async (
  jobUrl: string,
  headless: boolean = false
): Promise<RunAutofillResult> => {
  const response = await fetch(`${API_BASE_URL}/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ job_url: jobUrl, headless }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Run failed' }));
    throw new Error(error.detail || `Error: ${response.statusText}`);
  }
  return response.json() as Promise<RunAutofillResult>;
};
