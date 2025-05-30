import React from 'react';
import { Metadata } from 'next';

export default function Loading() {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full mx-auto text-center">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Loading Spinner */}
          <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-indigo-100 mb-6">
            <svg
              className="animate-spin h-8 w-8 text-indigo-600"
              xmlns="http://www.w3.org/2000/svg"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                stroke="currentColor"
                strokeWidth="4"
              ></circle>
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              ></path>
            </svg>
          </div>

          {/* Loading Message */}
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Validating Request
          </h1>
          <p className="text-gray-600 mb-6">
            We're checking your analysis request and preparing your information form.
          </p>

          {/* Progress Steps */}
          <div className="text-left mb-6">
            <div className="space-y-3">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-2 w-2 bg-indigo-600 rounded-full animate-pulse"></div>
                </div>
                <div className="ml-3 text-sm text-gray-700">
                  Verifying request ID
                </div>
              </div>
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-2 w-2 bg-gray-300 rounded-full"></div>
                </div>
                <div className="ml-3 text-sm text-gray-500">
                  Loading analysis status
                </div>
              </div>
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <div className="h-2 w-2 bg-gray-300 rounded-full"></div>
                </div>
                <div className="ml-3 text-sm text-gray-500">
                  Preparing lead capture form
                </div>
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
            <div className="bg-indigo-600 h-2 rounded-full animate-pulse" style={{ width: '33%' }}></div>
          </div>

          {/* Help Text */}
          <p className="text-xs text-gray-500">
            This usually takes just a few seconds
          </p>
        </div>
      </div>
    </div>
  );
}

// Metadata for the loading page
export const metadata: Metadata = {
  title: 'Loading Analysis Request - ShiftIQ',
  description: 'Loading your timesheet analysis request...',
  robots: {
    index: false,
    follow: false,
  },
}; 