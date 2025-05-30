'use client';

import { useState } from 'react';

interface UseFileUploadOptions {
  // onUploadSuccess?: (analysisReport: FinalAnalysisReport) => void;
  // onUploadError?: (error: Error) => void;
}

// Define the analysis report interface to match backend schema
interface ViolationInstance {
  rule_id: string;
  rule_description: string;
  employee_identifier: string;
  date_of_violation: string;
  specific_details: string;
  suggested_action_generic: string;
}

interface EmployeeReportDetails {
  employee_identifier: string;
  roles_observed?: string[];
  departments_observed?: string[];
  total_hours_worked: number;
  regular_hours: number;
  overtime_hours: number;
  double_overtime_hours: number;
  violations_for_employee: ViolationInstance[];
}

interface ReportKPIs {
  total_scheduled_labor_hours: number;
  total_regular_hours: number;
  total_overtime_hours: number;
  total_double_overtime_hours: number;
  estimated_overtime_cost?: number;
  estimated_double_overtime_cost?: number;
  compliance_risk_assessment?: string;
  count_meal_break_violations: number;
  count_rest_break_violations: number;
  count_daily_overtime_violations: number;
  count_weekly_overtime_violations: number;
  count_daily_double_overtime_violations: number;
  wage_data_source_note: string;
}

interface HeatMapDatapoint {
  hour_timestamp: string;
  employee_count: number;
}

interface FinalAnalysisReport {
  request_id: string;
  original_filename: string;
  status: string;
  status_message?: string;
  kpis?: ReportKPIs;
  staffing_density_heatmap?: HeatMapDatapoint[];
  all_identified_violations?: ViolationInstance[];
  employee_summaries?: EmployeeReportDetails[];
  duplicate_name_warnings?: string[];
  parsing_issues_summary?: string[];
  overall_report_summary_text?: string;
}

export interface UploadProgress {
  isLoading: boolean;
  error: string | null;
  analysisReport: FinalAnalysisReport | null;
  isAnalyzing: boolean;
  fileValidated: boolean;
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
    analysisReport: null,
    isAnalyzing: false,
    fileValidated: false,
  });

  const [leadSubmissionProgress, setLeadSubmissionProgress] = useState<LeadSubmissionProgress>({
    isLoading: false,
    error: null,
    isSuccess: false,
  });

  const uploadFile = async (file: File): Promise<{ success: boolean; error: string | null }> => {
    setUploadProgress({ 
      isLoading: true, 
      error: null, 
      analysisReport: null, 
      isAnalyzing: false,
      fileValidated: false 
    });

    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      setUploadProgress({ 
        isLoading: false, 
        error: 'File size exceeds 10MB limit', 
        analysisReport: null, 
        isAnalyzing: false,
        fileValidated: false 
      });
      return { success: false, error: 'File size exceeds 10MB limit' };
    }

    const allowedTypes = [
      'text/csv',
      'text/plain', // Sometimes CSV files are detected as text/plain
      'application/csv', // Alternative CSV MIME type
      'application/vnd.ms-excel', // Sometimes used for CSV
      'application/octet-stream', // Generic binary - often used when MIME type can't be determined
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/pdf',
      'image/jpeg',
      'image/png'
    ];

    // Additional check for CSV files based on file extension if MIME type is unclear
    const isCSVFile = file.name.toLowerCase().endsWith('.csv');
    const isTXTFile = file.name.toLowerCase().endsWith('.txt');
    const isValidType = allowedTypes.includes(file.type) || 
                       (file.type === 'text/plain' && (isCSVFile || isTXTFile)) ||
                       (file.type === 'application/octet-stream' && isCSVFile) ||
                       (file.type === '' && (isCSVFile || isTXTFile)); // Some systems don't set MIME type

    if (!isValidType) {
      setUploadProgress({ 
        isLoading: false, 
        error: `Invalid file type: ${file.type}. Please use CSV, XLSX, PDF, JPG, PNG, or TXT files.`, 
        analysisReport: null, 
        isAnalyzing: false,
        fileValidated: false 
      });
      return { success: false, error: `Invalid file type: ${file.type}` };
    }

    setUploadProgress({ 
      isLoading: false, 
      error: null, 
      analysisReport: null, 
      isAnalyzing: true,
      fileValidated: true 
    });

    startAnalysisInBackground(file);

    return { success: true, error: null };
  };

  const startAnalysisInBackground = async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        try {
          const errorData = await response.json();
          // Check if error data contains a detailed error report
          if (errorData.detail && typeof errorData.detail === 'object' && errorData.detail.status_message) {
            setUploadProgress(prev => ({ 
              ...prev, 
              isAnalyzing: false, 
              error: errorData.detail.status_message 
            }));
          } else {
            const errorMessage = errorData.detail || errorData.message || 'Analysis failed';
            setUploadProgress(prev => ({ 
              ...prev, 
              isAnalyzing: false, 
              error: `Analysis failed: ${errorMessage}` 
            }));
          }
        } catch {
          setUploadProgress(prev => ({ 
            ...prev, 
            isAnalyzing: false, 
            error: `Analysis failed with status ${response.status}` 
          }));
        }
        return;
      }

      const analysisReport: FinalAnalysisReport = await response.json();

      // Check if the analysis itself failed, even though HTTP response was OK
      if (analysisReport.status === 'error_parsing_failed' || analysisReport.status === 'error_analysis_failed') {
        setUploadProgress(prev => ({ 
          ...prev, 
          isAnalyzing: false, 
          error: analysisReport.status_message || 'Analysis failed due to processing errors' 
        }));
        return;
      }

      // Success case (including partial success with warnings)
      setUploadProgress(prev => ({ 
        ...prev, 
        isAnalyzing: false, 
        analysisReport 
      }));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Analysis failed';
      console.error('Background analysis error:', errorMessage);
      setUploadProgress(prev => ({ 
        ...prev, 
        isAnalyzing: false, 
        error: `Analysis failed: ${errorMessage}` 
      }));
    }
  };

  const submitLeadData = async (leadData: any): Promise<{ success: boolean; error: string | null }> => {
    setLeadSubmissionProgress({ isLoading: true, error: null, isSuccess: false });

    try {
      // Check if we have a valid analysis report with request_id
      if (!uploadProgress.analysisReport?.request_id) {
        throw new Error('Analysis must be completed before submitting lead information. Please wait for analysis to finish.');
      }

      const analysisId = uploadProgress.analysisReport.request_id;

      const response = await fetch('/api/submit-lead', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          analysisId, 
          ...leadData 
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ message: 'Failed to submit lead data.' }));
        throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
      }

      const result = await response.json();
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

// Export the FinalAnalysisReport type for use in other components
export type { FinalAnalysisReport }; 