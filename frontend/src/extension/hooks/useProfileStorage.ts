import { useState, useEffect, useCallback } from 'react';
import type { UserProfile } from '../types/ProfileTypes';

const STORAGE_KEY = 'user_profile';

// hook for managing profile data in chrome storage
// falls back to localstorage in dev mode
export function useProfileStorage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isChromeExtension = typeof chrome !== 'undefined' && chrome.storage;

  // load profile on mount
  useEffect(() => {
    const loadProfile = async () => {
      try {
        setIsLoading(true);

        if (isChromeExtension) {
          chrome.storage.local.get([STORAGE_KEY], (result: { [key: string]: UserProfile | undefined }) => {
            if (chrome.runtime.lastError) {
              setError(chrome.runtime.lastError.message || 'failed to load profile');
            } else {
              setProfile(result[STORAGE_KEY] ?? null);
            }
            setIsLoading(false);
          });
        } else {
          const stored = localStorage.getItem(STORAGE_KEY);
          setProfile(stored ? JSON.parse(stored) : null);
          setIsLoading(false);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'failed to load profile');
        setIsLoading(false);
      }
    };

    loadProfile();
  }, [isChromeExtension]);

  // save profile to storage
  const saveProfile = useCallback(async (newProfile: UserProfile): Promise<boolean> => {
    try {
      if (isChromeExtension) {
        return new Promise((resolve) => {
          chrome.storage.local.set({ [STORAGE_KEY]: newProfile }, () => {
            if (chrome.runtime.lastError) {
              setError(chrome.runtime.lastError.message || 'failed to save profile');
              resolve(false);
            } else {
              setProfile(newProfile);
              resolve(true);
            }
          });
        });
      } else {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(newProfile));
        setProfile(newProfile);
        return true;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed to save profile');
      return false;
    }
  }, [isChromeExtension]);

  // clear profile from storage
  const clearProfile = useCallback(async (): Promise<boolean> => {
    try {
      if (isChromeExtension) {
        return new Promise((resolve) => {
          chrome.storage.local.remove([STORAGE_KEY], () => {
            if (chrome.runtime.lastError) {
              setError(chrome.runtime.lastError.message || 'failed to clear profile');
              resolve(false);
            } else {
              setProfile(null);
              resolve(true);
            }
          });
        });
      } else {
        localStorage.removeItem(STORAGE_KEY);
        setProfile(null);
        return true;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed to clear profile');
      return false;
    }
  }, [isChromeExtension]);

  return {
    profile,
    isLoading,
    error,
    saveProfile,
    clearProfile,
    isChromeExtension
  };
}
