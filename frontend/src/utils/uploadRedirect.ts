/**
 * Upload redirect utilities for ShiftIQ
 * Handles file upload, progress tracking, and navigation
 */

import { AppRouterInstance } from 'next/dist/shared/lib/app-router-context.shared-runtime';

export interface UploadProgress {
  progress: number;
  stage: 'validating' | 'uploading' | 'processing' | 'complete' | 'error';
  message: string;
}

export interface UploadResult {
  success: boolean;
  requestId?: string;
  error?: string;
  message?: string;
}

export interface UploadRedirectOptions {
  file: File;
  router: AppRouterInstance;
  onProgress?: (progress: UploadProgress) => void;
  onError?: (error: string) => void;
  validateFile?: boolean;
}

/**
 * Validates file before upload
 */
export function validateUploadFile(file: File): { valid: boolean; error?: string } {
  // Check if file exists
  if (!file) {
    return { valid: false, error: 'No file selected' };
  }

  // Check for empty files
  if (file.size === 0) {
    return { valid: false, error: 'File is empty. Please select a valid file.' };
  }

  // File size validation (50MB limit)
  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    return { valid: false, error: 'File size must be less than 50MB' };
  }

  // Minimum file size (to avoid corrupted files)
  const minSize = 10; // 10 bytes minimum
  if (file.size < minSize) {
    return { valid: false, error: 'File appears to be corrupted or too small' };
  }

  // File name validation (check for suspicious names)
  if (!file.name || file.name.trim() === '') {
    return { valid: false, error: 'File must have a valid name' };
  }

  // Check for very long filenames
  if (file.name.length > 255) {
    return { valid: false, error: 'Filename is too long (max 255 characters)' };
  }

  // File type validation
  const allowedTypes = [
    'text/csv',
    'text/plain', // Sometimes CSV files are detected as text/plain
    'application/csv', // Alternative CSV MIME type
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp'
  ];

  // Get file extension
  const fileExtension = file.name.toLowerCase().split('.').pop() || '';
  const allowedExtensions = ['csv', 'txt', 'xls', 'xlsx', 'pdf', 'jpg', 'jpeg', 'png', 'gif', 'webp'];

  // Check both MIME type and extension for better validation
  const isValidMimeType = allowedTypes.includes(file.type);
  const isValidExtension = allowedExtensions.includes(fileExtension);

  // Special handling for CSV files (browsers can be inconsistent with MIME types)
  const isCSVFile = fileExtension === 'csv' || fileExtension === 'txt';
  const isCSVMimeType = ['text/csv', 'text/plain', 'application/csv'].includes(file.type);

  if (isCSVFile && isCSVMimeType) {
    return { valid: true }; // CSV files are valid
  }

  if (!isValidMimeType && !isValidExtension) {
    return { 
      valid: false, 
      error: 'Please upload a CSV, Excel, PDF, or image file (supported formats: .csv, .xlsx, .pdf, .jpg, .png)' 
    };
  }

  // Additional check for Excel files
  if ((fileExtension === 'xlsx' || fileExtension === 'xls') && 
      !file.type.includes('spreadsheet') && !file.type.includes('excel')) {
    // Allow it but warn that it might not be a valid Excel file
    console.warn('File has Excel extension but unexpected MIME type:', file.type);
  }

  return { valid: true };
}

/**
 * Uploads file and redirects to upload page with request ID
 */
export async function uploadAndRedirect(options: UploadRedirectOptions): Promise<UploadResult> {
  const { file, router, onProgress, onError, validateFile = true } = options;

  try {
    // Stage 1: Validation
    if (onProgress) {
      onProgress({
        progress: 10,
        stage: 'validating',
        message: 'Validating file...'
      });
    }

    if (validateFile) {
      const validation = validateUploadFile(file);
      if (!validation.valid) {
        const error = validation.error || 'File validation failed';
        if (onError) onError(error);
        return { success: false, error };
      }
    }

    // Stage 2: Upload
    if (onProgress) {
      onProgress({
        progress: 30,
        stage: 'uploading',
        message: 'Uploading file...'
      });
    }

    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch('/api/start-analysis', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json();
      const error = errorData.error || 'Upload failed';
      if (onError) onError(error);
      return { success: false, error };
    }

    const data = await response.json();
    
    if (!data.requestId) {
      const error = 'No request ID returned from server';
      if (onError) onError(error);
      return { success: false, error };
    }

    // Stage 3: Processing
    if (onProgress) {
      onProgress({
        progress: 80,
        stage: 'processing',
        message: 'Starting analysis...'
      });
    }

    // Small delay for better UX
    await new Promise(resolve => setTimeout(resolve, 500));

    // Stage 4: Complete and redirect
    if (onProgress) {
      onProgress({
        progress: 100,
        stage: 'complete',
        message: 'Redirecting...'
      });
    }

    // Navigate to upload page with request ID
    router.push(`/upload/${data.requestId}`);

    return { 
      success: true, 
      requestId: data.requestId,
      message: data.message || 'Upload successful'
    };

  } catch (error) {
    console.error('Upload error:', error);
    const errorMessage = error instanceof Error ? error.message : 'Upload failed';
    if (onError) onError(errorMessage);
    return { success: false, error: errorMessage };
  }
}

/**
 * Utility function to create progress updates with consistent formatting
 */
export function createProgressUpdate(
  progress: number, 
  stage: UploadProgress['stage'], 
  message: string
): UploadProgress {
  return { progress, stage, message };
}

/**
 * Utility function to handle upload errors consistently
 */
export function handleUploadError(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return 'An unexpected error occurred during upload';
} 