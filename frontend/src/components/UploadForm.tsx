'use client';

import { useLeadCapture } from '@/hooks/useLeadCapture';
import { useFileUpload, FinalAnalysisReport } from '@/hooks/useFileUpload';
import { APIProvider } from '@vis.gl/react-google-maps';
import React, { useCallback, useState, useEffect } from 'react';
import { useDropzone } from 'react-dropzone';

interface UploadFormProps {
  onAnalysisComplete: (analysisReport: FinalAnalysisReport, leadData: LeadData) => void;
}

export interface LeadData {
  managerName: string;
  managerEmail: string;
  managerPhone: string;
  storeName: string;
  storeAddress: string;
}

const initialLeadData: LeadData = {
  managerName: 'Alex Rodriguez',
  managerEmail: 'alex.rodriguez@example.com',
  managerPhone: '(555) 123-4567',
  storeName: 'Downtown Coffee & Bistro',
  storeAddress: '123 Main Street, San Francisco, CA 94102',
};

const UploadFormContent: React.FC<UploadFormProps> = ({ onAnalysisComplete }) => {
  const {
    leadData,
    handleInputChange: handleLeadInputChange,
    storeNameInputRef,
    storeAddressInputRef,
    storeNamePrediction,
    setStoreNamePrediction,
    storeAddressPrediction,
    setStoreAddressPrediction,
    handlePredictionSelect,
    errors,
    validateForm,
  } = useLeadCapture(initialLeadData);

  const { uploadFile, uploadProgress, submitLeadData, leadSubmissionProgress } = useFileUpload();
  const [currentStep, setCurrentStep] = useState<'upload' | 'leadCapture'>('upload');
  const [uploadedFile, setUploadedFile] = useState<File | null>(null);
  const [isWaitingForAnalysis, setIsWaitingForAnalysis] = useState(false);
  const [pollingCleanup, setPollingCleanup] = useState<(() => void) | null>(null);

  // Auto-redirect when analysis completes after lead submission
  useEffect(() => {
    if (uploadProgress.analysisReport && 
        leadSubmissionProgress.isSuccess && 
        isWaitingForAnalysis) {
      console.log('[DEBUG] Analysis complete via useEffect, proceeding to report');
      setIsWaitingForAnalysis(false);
      
      // Clean up any polling
      if (pollingCleanup) {
        pollingCleanup();
        setPollingCleanup(null);
      }
      
      onAnalysisComplete(uploadProgress.analysisReport, leadData);
    }
  }, [uploadProgress.analysisReport, leadSubmissionProgress.isSuccess, isWaitingForAnalysis, pollingCleanup, leadData, onAnalysisComplete]);

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setUploadedFile(file);
      const uploadResult = await uploadFile(file);
      
      if (uploadResult.success) {
        setCurrentStep('leadCapture');
      } else {
        console.error("File validation failed:", uploadResult.error);
      }
    }
  }, [uploadFile]);

  const handleLeadFormSubmit = async () => {
    const isFormValid = validateForm();
    if (!isFormValid) {
      return;
    }
    
    // Clean up any existing polling
    if (pollingCleanup) {
      pollingCleanup();
      setPollingCleanup(null);
    }
    
    console.log('[DEBUG] Submitting lead data, analysis status:', {
      hasReport: !!uploadProgress.analysisReport,
      isAnalyzing: uploadProgress.isAnalyzing,
      hasError: !!uploadProgress.error
    });
    
    // Submit lead data immediately - don't wait for analysis to complete
    const submissionResult = await submitLeadData(leadData);

    if (submissionResult.success) {
      // Check if analysis is already complete
      if (uploadProgress.analysisReport) {
        console.log('[DEBUG] Analysis already complete, proceeding immediately');
        onAnalysisComplete(uploadProgress.analysisReport, leadData);
      } else if (uploadProgress.error) {
        console.log('[DEBUG] Analysis already failed, staying on form');
        // Error will be displayed by the form
      } else {
        // Analysis still running - wait for it with useEffect handling auto-redirect
        console.log('[DEBUG] Analysis still running, waiting for completion');
        setIsWaitingForAnalysis(true);
        // Start backup polling as failsafe
        waitForAnalysisAndProceed();
      }
    } else {
      console.error("Lead data submission failed:", submissionResult.error);
    }
  };

  const waitForAnalysisAndProceed = () => {
    // Set up polling as backup to the useEffect
    const checkAnalysis = () => {
      console.log('[DEBUG] Checking analysis status (backup polling):', {
        hasReport: !!uploadProgress.analysisReport,
        isAnalyzing: uploadProgress.isAnalyzing,
        hasError: !!uploadProgress.error,
        leadSuccess: leadSubmissionProgress.isSuccess
      });
      
      if (uploadProgress.analysisReport && leadSubmissionProgress.isSuccess) {
        console.log('[DEBUG] Analysis complete via backup polling, proceeding to report');
        setIsWaitingForAnalysis(false);
        onAnalysisComplete(uploadProgress.analysisReport, leadData);
        return true; // Analysis complete
      } else if (uploadProgress.error) {
        console.log('[DEBUG] Analysis error detected:', uploadProgress.error);
        setIsWaitingForAnalysis(false);
        return true; // Stop polling on error
      } else if (!uploadProgress.isAnalyzing && !uploadProgress.analysisReport && isWaitingForAnalysis) {
        console.log('[DEBUG] Analysis finished but no report - unexpected state');
        setIsWaitingForAnalysis(false);
        return true; // Stop polling 
      }
      return false; // Continue polling
    };

    // Initial check
    if (checkAnalysis()) {
      return; // Already complete, don't start polling
    }

    // Start polling every 2 seconds (less aggressive than before)
    const pollInterval = setInterval(() => {
      if (checkAnalysis()) {
        clearInterval(pollInterval);
      }
    }, 2000);
    
    // Set up cleanup timeout (45 seconds max)
    const timeoutId = setTimeout(() => {
      clearInterval(pollInterval);
      setIsWaitingForAnalysis(false);
      console.error('[DEBUG] Analysis polling timed out after 45 seconds');
    }, 45000);
    
    // Return cleanup function
    const cleanup = () => {
      clearInterval(pollInterval);
      clearTimeout(timeoutId);
      setIsWaitingForAnalysis(false);
    };
    setPollingCleanup(() => cleanup);
  };

  // Update button state to account for waiting
  const canSubmit = !leadSubmissionProgress.isLoading && !isWaitingForAnalysis;
  const submitButtonText = leadSubmissionProgress.isLoading 
    ? 'Submitting...' 
    : isWaitingForAnalysis
    ? 'Analyzing - Report will appear automatically...'
    : 'Submit Information & View Report';

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'text/plain': ['.csv', '.txt'],
      'application/csv': ['.csv'],
      'application/vnd.ms-excel': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
    disabled: currentStep === 'leadCapture' || uploadProgress.isLoading,
  });

  useEffect(() => {
    return () => {
      if (pollingCleanup) {
        pollingCleanup();
      }
    };
  }, [pollingCleanup]);

  return (
    <div className="space-y-6">
      {currentStep === 'upload' && (
        <div
          {...getRootProps()}
          className={`border-2 border-dashed border-gray-300 rounded-lg p-10 text-center cursor-pointer hover:border-gray-400 ${
            uploadProgress.isLoading ? 'bg-gray-100' : uploadedFile && !uploadProgress.error ? 'bg-green-50 border-green-300' : uploadProgress.error ? 'bg-red-50 border-red-300' : ''
          }`}
        >
          <input {...getInputProps()} />
          {uploadProgress.isLoading ? (
            <div className="flex flex-col items-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-2"></div>
              <p className="text-gray-900 font-medium">Validating: {uploadedFile?.name}</p>
            </div>
          ) : uploadProgress.error ? (
            <p className="text-red-800 font-medium">Error: {uploadProgress.error}. Please try again.</p>
          ) : uploadedFile ? (
            <p className="text-green-800 font-medium">Selected file: {uploadedFile.name}. Ready for lead info.</p> 
          ) : isDragActive ? (
            <p className="text-gray-900 font-medium">Drop the file here ...</p>
          ) : (
            <p className="text-gray-900 font-medium">Drag &lsquo;n&rsquo; drop a file here, or click to select a file</p>
          )}
          <p className="text-xs text-gray-700 mt-2">
            Supported formats: CSV, XLSX, PDF, JPG, PNG, TXT (Max size: 10MB)
          </p>
        </div>
      )}

      {currentStep === 'leadCapture' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900">Manager & Store Information</h2>
          <p className="text-sm text-gray-800">
            Please provide your information while we analyze your file <span className="font-medium">{uploadedFile?.name}</span>.
          </p>

          {uploadProgress.isAnalyzing && !isWaitingForAnalysis && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 flex items-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600 mr-3"></div>
              <div>
                <p className="text-blue-900 font-medium">Analyzing your timesheet...</p>
                <p className="text-blue-800 text-sm">This may take 20-30 seconds. You can fill out the form while we process.</p>
              </div>
            </div>
          )}

          {isWaitingForAnalysis && (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-center">
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-yellow-600 mr-3"></div>
              <div>
                <p className="text-yellow-900 font-medium">✓ Information submitted! Finishing analysis...</p>
                <p className="text-yellow-800 text-sm">Your report will appear automatically when complete. No need to refresh!</p>
              </div>
            </div>
          )}

          {uploadProgress.analysisReport && !isWaitingForAnalysis && (
            <div className="bg-green-50 border border-green-200 rounded-lg p-4 flex items-center">
              <svg className="w-5 h-5 text-green-600 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <div>
                <p className="text-green-900 font-medium">Analysis complete!</p>
                <p className="text-green-800 text-sm">Your timesheet has been processed successfully.</p>
              </div>
            </div>
          )}

          {uploadProgress.error && !uploadProgress.isAnalyzing && !isWaitingForAnalysis && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4">
              <p className="text-red-900 font-medium">Analysis failed</p>
              <p className="text-red-800 text-sm">{uploadProgress.error}</p>
            </div>
          )}

          {leadSubmissionProgress.error && (
            <p className="text-red-600 text-sm my-2 font-medium">
              Error submitting information: {leadSubmissionProgress.error}
            </p>
          )}

          <div>
            <label htmlFor="managerName" className="block text-sm font-medium text-gray-900">
              Manager Name
            </label>
            <input
              type="text"
              name="managerName"
              id="managerName"
              value={leadData.managerName}
              onChange={handleLeadInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900"
            />
            {errors?.managerName && <p className="text-red-600 text-xs mt-1 font-medium">{errors.managerName}</p>}
          </div>
          <div>
            <label htmlFor="managerEmail" className="block text-sm font-medium text-gray-900">
              Manager Email
            </label>
            <input
              type="email"
              name="managerEmail"
              id="managerEmail"
              value={leadData.managerEmail}
              onChange={handleLeadInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900"
            />
            {errors?.managerEmail && <p className="text-red-600 text-xs mt-1 font-medium">{errors.managerEmail}</p>}
          </div>
          <div>
            <label htmlFor="managerPhone" className="block text-sm font-medium text-gray-900">
              Manager Phone
            </label>
            <input
              type="tel"
              name="managerPhone"
              id="managerPhone"
              value={leadData.managerPhone}
              onChange={handleLeadInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900"
            />
            {errors?.managerPhone && <p className="text-red-600 text-xs mt-1 font-medium">{errors.managerPhone}</p>}
          </div>
          <div className="relative">
            <label htmlFor="storeName" className="block text-sm font-medium text-gray-900">
              Store Name
            </label>
            <input
              ref={storeNameInputRef}
              type="text"
              name="storeName"
              id="storeName"
              value={leadData.storeName}
              onChange={handleLeadInputChange}
              onBlur={() => setTimeout(() => setStoreNamePrediction([]), 100)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900"
              autoComplete="off"
            />
            {errors?.storeName && <p className="text-red-600 text-xs mt-1 font-medium">{errors.storeName}</p>}
            {storeNamePrediction && storeNamePrediction.length > 0 && (
              <ul className="absolute z-10 w-full bg-white border border-gray-300 rounded-md shadow-lg mt-1">
                {storeNamePrediction.map((prediction) => (
                  <li
                    key={prediction.place_id}
                    onClick={() => handlePredictionSelect('storeName', prediction)}
                    className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-gray-900"
                  >
                    {prediction.description}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="relative">
            <label htmlFor="storeAddress" className="block text-sm font-medium text-gray-900">
              Store Physical Address
            </label>
            <input
              ref={storeAddressInputRef}
              type="text"
              name="storeAddress"
              id="storeAddress"
              value={leadData.storeAddress}
              onChange={handleLeadInputChange}
              onBlur={() => setTimeout(() => setStoreAddressPrediction([]), 100)}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-gray-900"
              autoComplete="off"
            />
            {errors?.storeAddress && <p className="text-red-600 text-xs mt-1 font-medium">{errors.storeAddress}</p>}
            {storeAddressPrediction && storeAddressPrediction.length > 0 && (
              <ul className="absolute z-10 w-full bg-white border border-gray-300 rounded-md shadow-lg mt-1">
                {storeAddressPrediction.map((prediction) => (
                  <li
                    key={prediction.place_id}
                    onClick={() => handlePredictionSelect('storeAddress', prediction)}
                    className="px-3 py-2 hover:bg-gray-100 cursor-pointer text-gray-900"
                  >
                    {prediction.description}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            onClick={handleLeadFormSubmit}
            disabled={!canSubmit}
            className={`w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white ${
              canSubmit 
                ? 'bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500' 
                : 'bg-gray-400 cursor-not-allowed'
            }`}
          >
            {submitButtonText}
          </button>
        </div>
      )}
    </div>
  );
};

const UploadForm: React.FC<UploadFormProps> = (props) => {
  const apiKey = process.env.NEXT_PUBLIC_GOOGLE_MAPS_API_KEY;

  if (!apiKey) {
    console.error("Google Maps API key is missing. Autocomplete will not work.");
  }

  return (
    <APIProvider apiKey={apiKey || ''} libraries={['places']}>
      <UploadFormContent {...props} />
    </APIProvider>
  );
};

export default UploadForm; 