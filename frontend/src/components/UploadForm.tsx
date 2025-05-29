'use client';

import { useLeadCapture } from '@/hooks/useLeadCapture';
import { useFileUpload } from '@/hooks/useFileUpload';
import { APIProvider } from '@vis.gl/react-google-maps';
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';

interface UploadFormProps {
  onAnalysisSubmit: (analysisId: string | null, leadData: LeadData) => void;
}

export interface LeadData {
  managerName: string;
  managerEmail: string;
  managerPhone: string;
  storeName: string;
  storeAddress: string;
}

const initialLeadData: LeadData = {
  managerName: '',
  managerEmail: '',
  managerPhone: '',
  storeName: '',
  storeAddress: '',
};

const UploadFormContent: React.FC<UploadFormProps> = ({ onAnalysisSubmit }) => {
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

  const onDrop = useCallback(async (acceptedFiles: File[]) => {
    if (acceptedFiles && acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      setUploadedFile(file);
      const uploadResult = await uploadFile(file);
      
      if (uploadResult.success) {
        setCurrentStep('leadCapture');
      } else {
        console.error("Upload failed, staying on upload step. Error:", uploadResult.error);
      }
    }
  }, [uploadFile]);

  const handleLeadFormSubmit = async () => {
    const isFormValid = validateForm();
    if (!isFormValid) {
      return;
    }
    
    const submissionResult = await submitLeadData(uploadProgress.analysisId, leadData);

    if (submissionResult.success) {
      onAnalysisSubmit(uploadProgress.analysisId, leadData);
    } else {
      console.error("Lead data submission failed:", submissionResult.error);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'text/csv': ['.csv'],
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'text/plain': ['.txt'],
    },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
    disabled: currentStep === 'leadCapture' || uploadProgress.isLoading,
  });

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
            <p>Uploading: {uploadedFile?.name}</p>
          ) : uploadProgress.error ? (
            <p className="text-red-700">Error: {uploadProgress.error}. Please try again.</p>
          ) : uploadedFile ? (
            <p className="text-green-700">Selected file: {uploadedFile.name}. Ready for lead info.</p> 
          ) : isDragActive ? (
            <p>Drop the file here ...</p>
          ) : (
            <p>Drag 'n' drop a file here, or click to select a file</p>
          )}
          <p className="text-xs text-gray-500 mt-2">
            Supported formats: CSV, XLSX, PDF, JPG, PNG, TXT (Max size: 10MB)
          </p>
        </div>
      )}

      {currentStep === 'leadCapture' && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-800">Manager & Store Information</h2>
          <p className="text-sm text-gray-600">
            Please provide your information. Your file <span className="font-medium">{uploadedFile?.name}</span> has been received and is being processed.
          </p>
          {leadSubmissionProgress.error && (
            <p className="text-red-500 text-sm my-2">
              Error submitting information: {leadSubmissionProgress.error}
            </p>
          )}
          <div>
            <label htmlFor="managerName" className="block text-sm font-medium text-gray-700">
              Manager Name
            </label>
            <input
              type="text"
              name="managerName"
              id="managerName"
              value={leadData.managerName}
              onChange={handleLeadInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
            {errors?.managerName && <p className="text-red-500 text-xs mt-1">{errors.managerName}</p>}
          </div>
          <div>
            <label htmlFor="managerEmail" className="block text-sm font-medium text-gray-700">
              Manager Email
            </label>
            <input
              type="email"
              name="managerEmail"
              id="managerEmail"
              value={leadData.managerEmail}
              onChange={handleLeadInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
            {errors?.managerEmail && <p className="text-red-500 text-xs mt-1">{errors.managerEmail}</p>}
          </div>
          <div>
            <label htmlFor="managerPhone" className="block text-sm font-medium text-gray-700">
              Manager Phone
            </label>
            <input
              type="tel"
              name="managerPhone"
              id="managerPhone"
              value={leadData.managerPhone}
              onChange={handleLeadInputChange}
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
            />
            {errors?.managerPhone && <p className="text-red-500 text-xs mt-1">{errors.managerPhone}</p>}
          </div>
          {/* Store Name with Autocomplete */}
          <div className="relative">
            <label htmlFor="storeName" className="block text-sm font-medium text-gray-700">
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
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              autoComplete="off"
            />
            {errors?.storeName && <p className="text-red-500 text-xs mt-1">{errors.storeName}</p>}
            {storeNamePrediction && storeNamePrediction.length > 0 && (
              <ul className="absolute z-10 w-full bg-white border border-gray-300 rounded-md shadow-lg mt-1">
                {storeNamePrediction.map((prediction) => (
                  <li
                    key={prediction.place_id}
                    onClick={() => handlePredictionSelect('storeName', prediction)}
                    className="px-3 py-2 hover:bg-gray-100 cursor-pointer"
                  >
                    {prediction.description}
                  </li>
                ))}
              </ul>
            )}
          </div>
          {/* Store Address with Autocomplete */}
          <div className="relative">
            <label htmlFor="storeAddress" className="block text-sm font-medium text-gray-700">
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
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm"
              autoComplete="off"
            />
            {errors?.storeAddress && <p className="text-red-500 text-xs mt-1">{errors.storeAddress}</p>}
            {storeAddressPrediction && storeAddressPrediction.length > 0 && (
              <ul className="absolute z-10 w-full bg-white border border-gray-300 rounded-md shadow-lg mt-1">
                {storeAddressPrediction.map((prediction) => (
                  <li
                    key={prediction.place_id}
                    onClick={() => handlePredictionSelect('storeAddress', prediction)}
                    className="px-3 py-2 hover:bg-gray-100 cursor-pointer"
                  >
                    {prediction.description}
                  </li>
                ))}
              </ul>
            )}
          </div>
          <button
            onClick={handleLeadFormSubmit}
            disabled={leadSubmissionProgress.isLoading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:bg-gray-400"
          >
            {leadSubmissionProgress.isLoading ? 'Submitting...' : 'Submit Information & View Report'}
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