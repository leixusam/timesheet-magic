'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useLeadCapture } from '@/hooks/useLeadCapture';
import { LeadData, LeadCaptureState, LeadSubmissionResult } from '@/types/leadCapture';
import analytics from '@/utils/analytics';

interface LeadCaptureFormProps {
  requestId: string;
  className?: string;
  onSuccess?: (result: LeadSubmissionResult) => void;
  onError?: (error: string) => void;
}

export default function LeadCaptureForm({ 
  requestId, 
  className = '',
  onSuccess,
  onError 
}: LeadCaptureFormProps) {
  const router = useRouter();
  const [submissionState, setSubmissionState] = useState<LeadCaptureState>({
    loading: false,
    error: null,
    success: false
  });

  // Initialize lead data with empty values for production
  const initialLeadData: LeadData = {
    analysisId: requestId,
    managerName: '',
    managerEmail: '',
    managerPhone: '',
    storeName: '',
    storeAddress: ''
  };

  const {
    leadData,
    handleInputChange,
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (submissionState.loading) return;
    
    // Validate form
    if (!validateForm()) {
      setSubmissionState(prev => ({
        ...prev,
        error: 'Please fill in all required fields correctly.'
      }));
      return;
    }

    setSubmissionState({
      loading: true,
      error: null,
      success: false
    });

    try {
      const response = await fetch('/api/submit-lead', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(leadData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Failed to submit lead information');
      }

      const result: LeadSubmissionResult = await response.json();

      // Track lead capture conversion event
      analytics.trackLeadCapture({
        email: leadData.managerEmail,
        company_size: 'unknown',
        industry: 'food_service'
      });

      setSubmissionState({
        loading: false,
        error: null,
        success: true
      });

      // Call success callback if provided
      if (onSuccess) {
        onSuccess(result);
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Submission failed';
      
      setSubmissionState({
        loading: false,
        error: errorMessage,
        success: false
      });

      // Call error callback if provided
      if (onError) {
        onError(errorMessage);
      }
    }
  };

  // Show success state
  if (submissionState.success) {
    return (
      <div className={`${className}`}>
        <div className="text-center py-6">
          <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
            <svg className="h-8 w-8 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-xl font-bold text-green-900 mb-2">Information Received</h3>
          <p className="text-green-700">
            We'll customize your compliance analysis based on your business details
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={`${className}`}>
      <form onSubmit={handleSubmit} className="space-y-6">
        {submissionState.error && (
          <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-700">{submissionState.error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {/* Manager Name */}
          <div>
            <label htmlFor="managerName" className="block text-sm font-medium text-gray-700 mb-2">
              Your Name *
            </label>
            <input
              type="text"
              id="managerName"
              name="managerName"
              value={leadData.managerName}
              onChange={handleInputChange}
              autoComplete="name"
              className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                errors.managerName ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Your full name"
            />
            {errors.managerName && (
              <p className="mt-1 text-sm text-red-600">{errors.managerName}</p>
            )}
          </div>

          {/* Manager Email */}
          <div>
            <label htmlFor="managerEmail" className="block text-sm font-medium text-gray-700 mb-2">
              Business Email *
            </label>
            <input
              type="email"
              id="managerEmail"
              name="managerEmail"
              value={leadData.managerEmail}
              onChange={handleInputChange}
              autoComplete="email"
              className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                errors.managerEmail ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="your.email@restaurant.com"
            />
            {errors.managerEmail && (
              <p className="mt-1 text-sm text-red-600">{errors.managerEmail}</p>
            )}
          </div>

          {/* Manager Phone */}
          <div>
            <label htmlFor="managerPhone" className="block text-sm font-medium text-gray-700 mb-2">
              Phone Number *
            </label>
            <input
              type="tel"
              id="managerPhone"
              name="managerPhone"
              value={leadData.managerPhone}
              onChange={handleInputChange}
              autoComplete="tel"
              className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                errors.managerPhone ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="(555) 123-4567"
            />
            {errors.managerPhone && (
              <p className="mt-1 text-sm text-red-600">{errors.managerPhone}</p>
            )}
          </div>

          {/* Store Name with Autocomplete */}
          <div className="relative">
            <label htmlFor="storeName" className="block text-sm font-medium text-gray-700 mb-2">
              Business Name *
            </label>
            <input
              type="text"
              id="storeName"
              name="storeName"
              ref={storeNameInputRef}
              value={leadData.storeName}
              onChange={handleInputChange}
              autoComplete="organization"
              className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
                errors.storeName ? 'border-red-300' : 'border-gray-300'
              }`}
              placeholder="Your business name"
            />
            {errors.storeName && (
              <p className="mt-1 text-sm text-red-600">{errors.storeName}</p>
            )}
            
            {/* Store Name Predictions */}
            {storeNamePrediction.length > 0 && (
              <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
                {storeNamePrediction.map((prediction, index) => (
                  <button
                    key={index}
                    type="button"
                    onClick={() => {
                      handlePredictionSelect('storeName', prediction);
                      setStoreNamePrediction([]);
                    }}
                    className="w-full text-left px-3 py-2 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none first:rounded-t-lg last:rounded-b-lg"
                  >
                    <div className="text-sm text-gray-900">{prediction.structured_formatting?.main_text || prediction.description}</div>
                    {prediction.structured_formatting?.secondary_text && (
                      <div className="text-xs text-gray-500">{prediction.structured_formatting.secondary_text}</div>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Store Address with Autocomplete - Full Width */}
        <div className="relative">
          <label htmlFor="storeAddress" className="block text-sm font-medium text-gray-700 mb-2">
            Business Location *
            <span className="text-sm text-gray-500 ml-1">(Required for state-specific compliance)</span>
          </label>
          <input
            type="text"
            id="storeAddress"
            name="storeAddress"
            ref={storeAddressInputRef}
            value={leadData.storeAddress}
            onChange={handleInputChange}
            autoComplete="street-address"
            className={`w-full px-3 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              errors.storeAddress ? 'border-red-300' : 'border-gray-300'
            }`}
            placeholder="123 Main St, City, State 12345"
          />
          {errors.storeAddress && (
            <p className="mt-1 text-sm text-red-600">{errors.storeAddress}</p>
          )}
          
          {/* Store Address Predictions */}
          {storeAddressPrediction.length > 0 && (
            <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
              {storeAddressPrediction.map((prediction, index) => (
                <button
                  key={index}
                  type="button"
                  onClick={() => {
                    handlePredictionSelect('storeAddress', prediction);
                    setStoreAddressPrediction([]);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none first:rounded-t-lg last:rounded-b-lg"
                >
                  <div className="text-sm text-gray-900">{prediction.description}</div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Submit Button */}
        <div className="pt-4">
          <button
            type="submit"
            disabled={submissionState.loading}
            className={`w-full px-6 py-3 text-base font-semibold rounded-lg text-white transition-colors ${
              submissionState.loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2'
            }`}
          >
            {submissionState.loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Processing...
              </span>
            ) : (
              'Complete Analysis'
            )}
          </button>
          
          <p className="text-center text-sm text-gray-500 mt-3">
            This information helps us provide accurate compliance recommendations
          </p>
        </div>
      </form>
    </div>
  );
} 