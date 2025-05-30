'use client';

import React from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/ui/Header';
import Footer from '@/components/ui/Footer';
import ReportDisplay from '@/components/ReportDisplay';
import LeadCaptureForm from '@/components/LeadCaptureForm';
import FriendlyErrorNotice from '@/components/ui/FriendlyErrorNotice';
import analytics from '@/utils/analytics';

// Define the type inline based on the analysis report structure
interface FinalAnalysisReport {
  request_id: string;
  original_filename: string;
  status: string;
  status_message?: string;
  kpis?: any;
  staffing_density_heatmap?: any[];
  all_identified_violations?: any[];
  employee_summaries?: any[];
  duplicate_name_warnings?: string[];
  parsing_issues_summary?: string[];
  overall_report_summary_text?: string;
  manager_name?: string;
  manager_email?: string;
  manager_phone?: string;
  store_name?: string;
  store_address?: string;
  created_at?: string;
}

interface ReportPageClientProps {
  reportId: string;
  initialReport?: FinalAnalysisReport | null;
  initialError?: string | null;
}

export default function ReportPageClient({ 
  reportId, 
  initialReport = null, 
  initialError = null 
}: ReportPageClientProps) {
  const router = useRouter();

  // Track report view for successful reports
  if (initialReport && (initialReport.status === 'success' || initialReport.status === 'partial_success_with_warnings')) {
    analytics.trackReportView({
      requestId: reportId,
      violationCount: initialReport.all_identified_violations?.length || 0,
      employeeCount: initialReport.employee_summaries?.length || 0
    });
  }

  const handleNewAnalysis = () => {
    router.push('/');
  };

  const handleDeleteFile = async (reportIdToDelete: string) => {
    if (!reportIdToDelete) return;
    console.log(`Attempting to delete report: ${reportIdToDelete}`);
    try {
      const response = await fetch(`/api/reports/${reportIdToDelete}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        analytics.track('File Deletion Requested', { reportId: reportIdToDelete, status: 'success' });
        console.log(`Report ${reportIdToDelete} deleted successfully.`);
        router.push('/'); 
      } else {
        const errorData = await response.json().catch(() => ({ detail: 'Failed to parse error response' }));
        console.error(`Failed to delete file ${reportIdToDelete}: ${errorData.detail || response.statusText}`);
        analytics.track('File Deletion Requested', { reportId: reportIdToDelete, status: 'error', errorMessage: errorData.detail || response.statusText });
        alert(`Failed to delete file: ${errorData.detail || 'Please try again.'}`);
        router.push('/');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'An unknown error occurred';
      console.error(`An error occurred while deleting file ${reportIdToDelete}: ${errorMessage}`);
      analytics.track('File Deletion Requested', { reportId: reportIdToDelete, status: 'error', errorMessage });
      alert(`An error occurred: ${errorMessage}`);
      router.push('/');
    }
  };

  const handleTryDifferentFile = () => {
    analytics.track('Try Different File Clicked', { reportId });
    router.push('/');
  };

  const handleNotifyMe = () => {
    analytics.track('Notify Me Clicked', { reportId });
    alert("Thanks for your interest! We'll look into improving support for this file. Please check back later or contact support.");
  };

  // Show error state
  if (initialError) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-white to-amber-50 flex flex-col">
        <Header variant="minimal" showNavigation={false} />
        <div className="flex-grow flex items-center justify-center py-12 px-4">
          <FriendlyErrorNotice 
            fileName="your file"
            reportId={reportId}
            onTryDifferentFile={handleTryDifferentFile}
            onNotifyMe={handleNotifyMe}
          />
        </div>
        <Footer />
      </div>
    );
  }

  // Show completed report
  if (!initialReport) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Header variant="minimal" showNavigation={false} />
        
        <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center pt-16">
          <div className="text-center p-4">
            <div className="max-w-md mx-auto bg-white shadow-xl rounded-lg p-8">
              <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3 className="text-xl font-medium text-gray-900 mb-2">Report Not Found</h3>
              <p className="text-gray-600 mb-6">The requested report could not be found. It might still be processing, or the ID could be incorrect.</p>
              <button
                onClick={() => router.push('/')}
                className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
              >
                Check Status or Upload New File
              </button>
            </div>
          </div>
        </div>
        
        <Footer />
      </div>
    );
  }

  // If it's the special LLM complexity error, show the friendly notice
  if (initialReport.status === 'error_llm_complexity') {
    return (
      <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-white to-amber-50 flex flex-col">
        <Header variant="minimal" showNavigation={false} />
        <div className="flex-grow flex items-center justify-center py-12 px-4">
          <FriendlyErrorNotice 
            fileName={initialReport.original_filename || 'your file'}
            reportId={reportId}
            onTryDifferentFile={handleTryDifferentFile}
            onNotifyMe={handleNotifyMe}
          />
        </div>
        <Footer />
      </div>
    );
  }

  // If report is still processing (and not a complexity error)
  if (initialReport.status === 'processing' || initialReport.status === 'analyzing' || initialReport.status === 'pending') {
    return (
        <div className="min-h-screen bg-gray-50">
         <Header variant="minimal" showNavigation={false} />
         <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 flex items-center justify-center pt-16">
           <div className="text-center p-4">
             <div className="max-w-md mx-auto bg-white shadow-xl rounded-lg p-8">
                <div className="animate-pulse flex flex-col items-center">
                    <svg className="w-16 h-16 text-blue-500 mb-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182m0-4.991v4.99" />
                    </svg>
                    <h3 className="text-xl font-medium text-gray-900 mb-2">Analysis in Progress</h3>
                    <p className="text-gray-600 mb-1">Your report for <span className="font-semibold">{initialReport.original_filename || 'your file'}</span> is currently processing.</p>
                    <p className="text-gray-600 mb-6">Please check back in a few moments.</p>
                </div>
                 <button
                    onClick={() => window.location.reload()}
                    className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
                    >
                    Refresh Status
                </button>
             </div>
           </div>
         </div>
         <Footer />
       </div>
    );
  }

  // Standard error display for other statuses like 'error_parsing_failed', 'error_analysis_failed'
  if (initialReport.status && initialReport.status.startsWith('error_')) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-yellow-50 via-white to-amber-50 flex flex-col">
        <Header variant="minimal" showNavigation={false} />
        <div className="flex-grow flex items-center justify-center py-12 px-4">
          <FriendlyErrorNotice 
            fileName={initialReport.original_filename || 'your file'}
            reportId={reportId}
            onTryDifferentFile={handleTryDifferentFile}
            onNotifyMe={handleNotifyMe}
          />
        </div>
        <Footer />
      </div>
    );
  }
  
  // Fallback to ReportDisplay for 'success' or 'partial_success_with_warnings'
  return (
    <div className="min-h-screen bg-gray-50">
      <Header variant="minimal" showNavigation={false} />
      <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-indigo-50 pt-16">
        <div className="py-8">
          <ReportDisplay
            analysisReport={initialReport}
            onNewAnalysis={handleNewAnalysis}
            requestedBy={initialReport.manager_name || "Manager"}
            requestedAt={initialReport.created_at || new Date().toISOString()}
          />
        </div>
      </div>
      <Footer />
    </div>
  );
} 