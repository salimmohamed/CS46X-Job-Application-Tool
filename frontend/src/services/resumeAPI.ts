const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const uploadResume = async (file: File): Promise<void> => {
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
};