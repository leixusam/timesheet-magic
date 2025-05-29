'use client';

import { useState } from 'react';
import UploadForm, { LeadData } from '@/components/UploadForm';
import ReportDisplay from '@/components/ReportDisplay';
import { FinalAnalysisReport } from '@/hooks/useFileUpload';

export default function Home() {
  const [currentView, setCurrentView] = useState<'upload' | 'report'>('upload');
  const [analysisReport, setAnalysisReport] = useState<FinalAnalysisReport | null>(null);
  const [leadData, setLeadData] = useState<LeadData | null>(null);
  const [reportGeneratedAt, setReportGeneratedAt] = useState<string | null>(null);

  const handleAnalysisComplete = (report: FinalAnalysisReport, submittedLeadData: LeadData) => {
    setAnalysisReport(report);
    setLeadData(submittedLeadData);
    setReportGeneratedAt(new Date().toISOString());
    setCurrentView('report');
  };

  const handleNewAnalysis = () => {
    setAnalysisReport(null);
    setLeadData(null);
    setReportGeneratedAt(null);
    setCurrentView('upload');
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {currentView === 'upload' && (
        <div className="container mx-auto px-4 py-8">
          <div className="max-w-4xl mx-auto">
            {/* Header */}
            <div className="text-center mb-12">
              <h1 className="text-4xl font-bold text-gray-900 mb-4">
                Timesheet Magic
              </h1>
              <p className="text-xl text-gray-800 mb-2">
                AI-Powered Compliance Analysis for Restaurant Timesheets
              </p>
              <p className="text-gray-700">
                Upload your timesheet file and get instant compliance insights
              </p>
            </div>

            {/* Upload Form */}
            <div className="bg-white rounded-xl shadow-lg p-8 max-w-2xl mx-auto">
              <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center">
                Upload Your Timesheet
              </h2>
              <UploadForm onAnalysisComplete={handleAnalysisComplete} />
            </div>

            {/* Features Section */}
            <div className="mt-16 grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
              <div className="text-center">
                <div className="bg-blue-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Multiple Formats</h3>
                <p className="text-gray-800">Support for CSV, Excel, PDF, and image files</p>
              </div>
              <div className="text-center">
                <div className="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Compliance Checks</h3>
                <p className="text-gray-800">Automatic detection of overtime and break violations</p>
              </div>
              <div className="text-center">
                <div className="bg-purple-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-purple-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
                  </svg>
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Cost Analysis</h3>
                <p className="text-gray-800">Instant calculation of overtime costs and savings</p>
              </div>
            </div>
          </div>
        </div>
      )}

      {currentView === 'report' && analysisReport && (
        <div className="container mx-auto px-4 py-8">
          <ReportDisplay 
            analysisReport={analysisReport}
            onNewAnalysis={handleNewAnalysis}
            requestedBy={leadData?.managerName}
            requestedAt={reportGeneratedAt || undefined}
          />
        </div>
      )}
    </div>
  );
}
