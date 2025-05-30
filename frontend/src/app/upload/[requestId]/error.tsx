'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import { Metadata } from 'next';

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    // Log the error to console for debugging
    console.error('[UPLOAD PAGE ERROR]', error);
    
    // Here you could also send the error to an error reporting service
    // Example: Sentry, LogRocket, or custom analytics
    // errorReportingService.captureException(error, {
    //   tags: { page: 'upload-request' },
    //   extra: { digest: error.digest }
    // });
  }, [error]);

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center">
      <div className="max-w-md w-full mx-auto text-center">
        <div className="bg-white rounded-lg shadow-lg p-8">
          {/* Error Icon */}
          <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-red-100 mb-6">
            <svg
              className="h-8 w-8 text-red-600"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </div>

          {/* Error Message */}
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Something Went Wrong
          </h1>
          <p className="text-gray-600 mb-6">
            We encountered an unexpected error while loading your analysis request. This is usually temporary.
          </p>

          {/* Error Details (only in development) */}
          {process.env.NODE_ENV === 'development' && (
            <div className="text-left mb-6 p-4 bg-red-50 rounded-lg">
              <p className="text-sm font-medium text-red-700 mb-2">Development Error Details:</p>
              <p className="text-xs text-red-600 font-mono break-all">
                {error.message}
              </p>
              {error.digest && (
                <p className="text-xs text-red-500 mt-1">
                  Error ID: {error.digest}
                </p>
              )}
            </div>
          )}

          {/* Action Buttons */}
          <div className="space-y-3">
            <button
              onClick={reset}
              className="w-full inline-flex justify-center items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
            >
              Try Again
            </button>
            <Link
              href="/"
              className="w-full inline-flex justify-center items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
            >
              Start New Analysis
            </Link>
            <Link
              href="/reports"
              className="w-full inline-flex justify-center items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
            >
              View All Reports
            </Link>
          </div>

          {/* Help Text */}
          <p className="text-xs text-gray-500 mt-6">
            If this problem persists, please contact our support team for assistance.
          </p>

          {/* Support Information */}
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <p className="text-xs text-gray-600">
              <strong>Need help?</strong> Include error ID{' '}
              {error.digest ? (
                <code className="bg-gray-200 px-1 rounded text-xs">
                  {error.digest.slice(0, 8)}...
                </code>
              ) : (
                'in your support request'
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Metadata for the error page
export const metadata: Metadata = {
  title: 'Error Loading Request - ShiftIQ',
  description: 'An error occurred while loading your analysis request.',
  robots: {
    index: false,
    follow: false,
  },
}; 