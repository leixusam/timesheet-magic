'use client';

import { useState, useEffect } from 'react';

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
  isAnalyzing: boolean;
  error: string | null;
  analysisReport: FinalAnalysisReport | null;
  requestId: string | null;
}

export interface LeadSubmissionProgress {
  isLoading: boolean;
  error: string | null;
  isSuccess: boolean;
}

export function useFileUpload() {
  // UploadProgress state is now managed entirely by the component
  // Remove the conflicting uploadProgress state from the hook

  const [leadSubmissionProgress, setLeadSubmissionProgress] = useState<LeadSubmissionProgress>({
    isLoading: false,
    error: null,
    isSuccess: false,
  });

  const submitLeadData = async (leadData: any, currentRequestId: string | null): Promise<{ success: boolean; error: string | null }> => {
    setLeadSubmissionProgress({ isLoading: true, error: null, isSuccess: false });

    try {
      if (!currentRequestId) { // Expect requestId to be passed in
        throw new Error('No analysis request ID available. Please upload a file first.');
      }

      const analysisId = currentRequestId;

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

      // const result = await response.json(); // Result not directly used here
      await response.json();
      setLeadSubmissionProgress({ isLoading: false, error: null, isSuccess: true });
      return { success: true, error: null };
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred while submitting lead data.';
      console.error('Lead submission error (from hook):', errorMessage);
      setLeadSubmissionProgress({ isLoading: false, error: errorMessage, isSuccess: false });
      return { success: false, error: errorMessage };
    }
  };

  return {
    submitLeadData,
    leadSubmissionProgress,
  };
}

export type { FinalAnalysisReport }; 