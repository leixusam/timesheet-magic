'use client';

import { useState } from 'react';

interface UseFileUploadOptions {
  // onUploadSuccess?: (analysisId: string) => void; // Callback for when analysis ID is received
  // onUploadError?: (error: Error) => void;
}

export interface UploadProgress {
  isLoading: boolean;
  error: string | null;
  analysisId: string | null; // Or whatever identifier your backend returns
}

export interface LeadSubmissionProgress {
  isLoading: boolean;
  error: string | null;
  isSuccess: boolean;
}

export function useFileUpload(options?: UseFileUploadOptions) {
  const [uploadProgress, setUploadProgress] = useState<UploadProgress>({
    isLoading: false,
    error: null,
    analysisId: null,
  });

  const [leadSubmissionProgress, setLeadSubmissionProgress] = useState<LeadSubmissionProgress>({
    isLoading: false,
    error: null,
    isSuccess: false,
  });

  const uploadFile = async (file: File): Promise<{ success: boolean; analysisId: string | null; error: string | null }> => {
    setUploadProgress({ isLoading: true, error: null, analysisId: null });

    const formData = new FormData();
    formData.append('file', file);
    // Note: LeadData is not sent here as per the new two-step flow.
    // It will be sent in a separate step.

    try {
      // We'll use the Next.js API route path.
      // The actual backend endpoint might be different if you're proxying.
      const response = await fetch('/api/analyze', { // Assuming Next.js API route
        method: 'POST',
        body: formData,
        // Headers might be needed, e.g., if your backend expects 'multipart/form-data'
        // but fetch usually handles this with FormData.
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to upload file. Server returned an error.' }));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json(); 
      // Assuming the backend returns something like { analysisId: "some-uuid" }
      // Or { message: "File received, processing started", analysisId: "..." }

      setUploadProgress({ isLoading: false, error: null, analysisId: result.analysisId || null });
      // if (options?.onUploadSuccess && result.analysisId) {
      //   options.onUploadSuccess(result.analysisId);
      // }
      return { success: true, analysisId: result.analysisId || null, error: null };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred during file upload.';
      console.error('Upload error:', errorMessage);
      setUploadProgress({ isLoading: false, error: errorMessage, analysisId: null });
      // if (options?.onUploadError) {
      //   options.onUploadError(err as Error);
      // }
      return { success: false, analysisId: null, error: errorMessage };
    }
  };

  const submitLeadData = async (analysisId: string | null, leadData: any): Promise<{ success: boolean; error: string | null }> => {
    if (!analysisId) {
      console.error('Cannot submit lead data without an analysisId.');
      return { success: false, error: 'Missing analysisId.' };
    }

    setLeadSubmissionProgress({ isLoading: true, error: null, isSuccess: false });

    try {
      // Assuming a new Next.js API route like /api/submit-lead
      const response = await fetch('/api/submit-lead', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ analysisId, ...leadData }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to submit lead data.' }));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json(); // Expecting { success: true } or similar
      setLeadSubmissionProgress({ isLoading: false, error: null, isSuccess: true });
      return { success: true, error: null };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred while submitting lead data.';
      console.error('Lead submission error:', errorMessage);
      setLeadSubmissionProgress({ isLoading: false, error: errorMessage, isSuccess: false });
      return { success: false, error: errorMessage };
    }
  };

  return {
    uploadFile,
    uploadProgress,
    setUploadProgress,
    submitLeadData,
    leadSubmissionProgress,
  };
} 