import Link from 'next/link';
import { Metadata } from 'next';

export default function NotFound() {
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
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"
              />
            </svg>
          </div>

          {/* Error Message */}
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Request Not Found
          </h1>
          <p className="text-gray-600 mb-6">
            The analysis request you're looking for doesn't exist or may have expired.
          </p>

          {/* Possible Reasons */}
          <div className="text-left mb-6">
            <p className="text-sm font-medium text-gray-700 mb-3">This might happen if:</p>
            <ul className="text-sm text-gray-600 space-y-2">
              <li className="flex items-start">
                <span className="text-red-400 mr-2">•</span>
                The link is incorrect or incomplete
              </li>
              <li className="flex items-start">
                <span className="text-red-400 mr-2">•</span>
                The analysis request has expired
              </li>
              <li className="flex items-start">
                <span className="text-red-400 mr-2">•</span>
                The request was deleted or never existed
              </li>
            </ul>
          </div>

          {/* Action Buttons */}
          <div className="space-y-3">
            <Link
              href="/"
              className="w-full inline-flex justify-center items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
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
            Need help? Contact our support team for assistance.
          </p>
        </div>
      </div>
    </div>
  );
}

// Enhanced metadata for the 404 page
export const metadata: Metadata = {
  title: 'Analysis Request Not Found - ShiftIQ',
  description: 'The requested analysis session could not be found. It may have expired or never existed.',
  robots: {
    index: false,
    follow: false,
  },
};

// Generate additional metadata for this specific error case
export function generateMetadata(): Metadata {
  return {
    title: 'Analysis Request Not Found - ShiftIQ',
    description: 'The analysis request you are looking for could not be found. It may have expired or been removed.',
    robots: {
      index: false,
      follow: false,
    },
    openGraph: {
      title: 'Analysis Request Not Found - ShiftIQ',
      description: 'The analysis request could not be found.',
      type: 'website',
      siteName: 'ShiftIQ',
    },
    twitter: {
      card: 'summary',
      title: 'Request Not Found - ShiftIQ',
      description: 'The analysis request could not be found.',
    },
  };
} 