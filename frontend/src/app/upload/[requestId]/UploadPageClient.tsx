'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/ui/Header';
import Footer from '@/components/ui/Footer';
import LeadCaptureForm from '@/components/LeadCaptureForm';
import analytics from '@/utils/analytics';

interface RequestData {
  requestId: string;
  status: string;
  originalFilename?: string;
  createdAt?: string;
  statusMessage?: string;
}

interface AnalysisReport {
  request_id: string;
  original_filename: string;
  status: string;
  status_message?: string;
  kpis?: any;
  all_identified_violations?: any[];
  employee_summaries?: any[];
}

interface UploadPageClientProps {
  requestData: RequestData;
}

export default function UploadPageClient({ requestData }: UploadPageClientProps) {
  const router = useRouter();
  const [analysisReport, setAnalysisReport] = useState<AnalysisReport | null>(null);
  const [analysisStatus, setAnalysisStatus] = useState(requestData.status);
  const [leadCaptureComplete, setLeadCaptureComplete] = useState(false);
  const [leadFormCollapsed, setLeadFormCollapsed] = useState(false);
  const [pollingForAnalysis, setPollingForAnalysis] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analysisStartTime] = useState(Date.now());
  const [elapsedTime, setElapsedTime] = useState(0);

  const fetchAnalysisStatus = useCallback(async () => {
    try {
      console.log(`Fetching analysis status for ${requestData.requestId}...`);
      const response = await fetch(`/api/reports/${requestData.requestId}`);
      
      if (response.ok) {
        const data = await response.json();
        console.log(`Analysis status: ${data.status}`);
        setAnalysisReport(data);
        setAnalysisStatus(data.status);
        setError(null);
        
        // Stop polling if analysis is complete
        const completionStatuses = ['success', 'partial_success_with_warnings', 'error_parsing_failed', 'error_analysis_failed'];
        if (completionStatuses.includes(data.status)) {
          console.log('Analysis complete, stopping polling');
          setPollingForAnalysis(false);
          
          // Track analysis completion
          if (data.status === 'success' || data.status === 'partial_success_with_warnings') {
            analytics.trackReportView({
              requestId: requestData.requestId,
              violationCount: data.all_identified_violations?.length || 0,
              employeeCount: data.employee_summaries?.length || 0
            });
          }
        }
      } else if (response.status === 404) {
        setError('Analysis not found');
        setPollingForAnalysis(false);
      } else {
        console.error('Failed to fetch analysis status');
      }
    } catch (err) {
      console.error('Error fetching analysis status:', err);
    }
  }, [requestData.requestId]);

  // Update elapsed time every second
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - analysisStartTime) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [analysisStartTime]);

  // Poll for analysis completion
  useEffect(() => {
    const isAnalysisInProgress = analysisStatus === 'processing' || analysisStatus === 'analyzing';
    
    if (isAnalysisInProgress) {
      console.log('Starting polling for analysis completion');
      setPollingForAnalysis(true);
      
      const interval = setInterval(() => {
        fetchAnalysisStatus();
      }, 3000); // Poll every 3 seconds

      return () => {
        console.log('Cleaning up polling interval');
        clearInterval(interval);
      };
    } else {
      setPollingForAnalysis(false);
    }
  }, [analysisStatus, fetchAnalysisStatus]);

  // Handle completion states and redirects
  useEffect(() => {
    const isAnalysisComplete = ['success', 'partial_success_with_warnings', 'error_parsing_failed', 'error_analysis_failed'].includes(analysisStatus);
    
    // Only redirect when BOTH analysis is complete AND lead capture form is submitted
    if (isAnalysisComplete && leadCaptureComplete) {
      console.log('Analysis complete and lead captured, redirecting to report...');
      setTimeout(() => {
        router.push(`/reports/${requestData.requestId}`);
      }, 2000);
    }
  }, [analysisStatus, leadCaptureComplete, requestData.requestId, router]);

  const handleLeadCaptureSuccess = (result: any) => {
    console.log('[CLIENT] Lead capture successful:', result);
    setLeadCaptureComplete(true);
    setLeadFormCollapsed(true);
  };

  const handleLeadCaptureError = (error: any) => {
    console.error('[CLIENT] Lead capture error:', error);
  };

  const isAnalysisInProgress = analysisStatus === 'processing' || analysisStatus === 'analyzing';
  const isAnalysisComplete = ['success', 'partial_success_with_warnings', 'error_parsing_failed', 'error_analysis_failed'].includes(analysisStatus);
  const isAnalysisError = ['error_parsing_failed', 'error_analysis_failed'].includes(analysisStatus);

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Header variant="minimal" showNavigation={false} />
      
      <div className="max-w-2xl mx-auto py-12 px-6 pt-24">
        
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center gap-2 bg-green-100 rounded-full px-3 py-1 text-sm text-green-800 mb-6">
            <span>✓</span>
            <span>2,847+ restaurants analyzed this month</span>
          </div>
          
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Your Compliance Report is Almost Ready
          </h1>
          <p className="text-lg text-gray-600 mb-2">
            Analyzing: <span className="font-semibold">{requestData.originalFilename}</span>
          </p>
        </div>

        {/* TOP: Analysis Progress */}
        <div className="bg-white rounded-lg shadow-sm border p-8 mb-12">
          <div className="text-center">
            
            {/* Progress Circle */}
            <div className="w-16 h-16 mx-auto mb-6 relative">
              {isAnalysisInProgress ? (
                <>
                  <svg className="animate-spin w-16 h-16 text-blue-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-xs font-bold text-blue-600">{Math.min(99, Math.floor((elapsedTime / 90) * 100))}%</span>
                  </div>
                </>
              ) : isAnalysisComplete && !isAnalysisError ? (
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                  </svg>
                </div>
              ) : (
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center">
                  <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              )}
            </div>

            {/* Status */}
            <h2 className="text-xl font-semibold text-gray-900 mb-3">
              {isAnalysisInProgress ? 'AI Analysis in Progress' :
               isAnalysisComplete && !isAnalysisError ? 'Analysis Complete!' :
               isAnalysisError ? 'Analysis Issue' :
               'Preparing Analysis'}
            </h2>

            {/* Simple Progress Message */}
            {isAnalysisInProgress && (
              <div className="space-y-4">
                <p className="text-gray-600">
                  {analysisStatus === 'processing' ? 
                    'Processing your timesheet data...' : 
                    'Analyzing labor compliance violations...'}
                </p>
                
                <div className="flex items-center justify-center gap-8 text-sm">
                  <div className="text-center">
                    <div className="text-lg font-bold text-blue-600">{formatTime(elapsedTime)}</div>
                    <div className="text-gray-500">Elapsed</div>
                  </div>
                  <div className="text-center">
                    <div className="text-lg font-bold text-green-600">{Math.min(99, Math.floor((elapsedTime / 90) * 100))}%</div>
                    <div className="text-gray-500">Complete</div>
                  </div>
                </div>
              </div>
            )}

            {isAnalysisComplete && !isAnalysisError && (
              <div className="space-y-2">
                <p className="text-green-700 font-medium">
                  Your compliance report is ready!
                </p>
                {!leadCaptureComplete ? (
                  <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mt-4">
                    <div className="flex items-start">
                      <svg className="w-5 h-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                      <div>
                        <p className="text-sm font-medium text-yellow-800">
                          Complete the form below to access your report
                        </p>
                        <p className="text-xs text-yellow-700 mt-1">
                          We need your business location for state-specific compliance recommendations
                        </p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <p className="text-sm text-gray-600">
                    Preparing your customized report...
                  </p>
                )}
              </div>
            )}
          </div>
        </div>

        {/* BOTTOM: Lead Capture Form */}
        {!leadFormCollapsed ? (
          <div className="bg-white rounded-lg shadow-sm border p-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-3">
                Complete Your Analysis
              </h2>
              <p className="text-gray-600 mb-6">
                We need your business details to provide accurate, state-specific compliance recommendations
              </p>
              
              {isAnalysisInProgress && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
                  <p className="text-sm text-blue-800">
                    <strong>Please provide your details</strong> so we can customize your compliance analysis
                  </p>
                </div>
              )}

              {isAnalysisComplete && !leadCaptureComplete && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
                  <div className="flex items-center justify-center mb-2">
                    <svg className="w-5 h-5 text-green-600 mr-2" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                    </svg>
                    <span className="text-sm font-semibold text-green-800">Analysis Complete!</span>
                  </div>
                  <p className="text-sm text-green-700">
                    <strong>Your report is ready.</strong> Complete this form to access your customized compliance analysis.
                  </p>
                </div>
              )}
            </div>

            <LeadCaptureForm 
              requestId={requestData.requestId}
              onSuccess={handleLeadCaptureSuccess}
              onError={handleLeadCaptureError}
            />
          </div>
        ) : (
          <div className="bg-green-50 border border-green-200 rounded-lg p-8 text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-green-900 mb-2">Information Received</h3>
            <p className="text-green-700">
              {isAnalysisComplete ? 
                'Preparing your customized compliance report...' : 
                'We\'ll finalize your analysis when processing completes'}
            </p>
          </div>
        )}

        {/* Debug info in development */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-8 p-4 bg-gray-100 rounded text-sm">
            <strong>Debug Info:</strong>
            <pre className="mt-2 text-xs">
              {JSON.stringify({ 
                requestData, 
                analysisStatus, 
                leadCaptureComplete, 
                leadFormCollapsed,
                isAnalysisComplete,
                isAnalysisInProgress,
                elapsedTime
              }, null, 2)}
            </pre>
          </div>
        )}
      </div>
      
      <Footer />
    </div>
  );
} 