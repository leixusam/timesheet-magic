/**
 * Lead capture types for ShiftIQ
 * Extracted from the original UploadForm component
 */

export interface LeadData {
  analysisId: string;
  managerName: string;
  managerEmail: string;
  managerPhone: string;
  storeName: string;
  storeAddress: string;
}

export interface LeadCaptureState {
  loading: boolean;
  error: string | null;
  success: boolean;
}

export interface LeadValidationErrors {
  managerName?: string;
  managerEmail?: string;
  managerPhone?: string;
  storeName?: string;
  storeAddress?: string;
  analysisId?: string;
}

export interface LeadSubmissionResult {
  success: boolean;
  message?: string;
  error?: string;
  details?: any;
} 