import { notFound } from 'next/navigation';
import UploadPageClient from './UploadPageClient';

interface UploadPageProps {
  params: Promise<{
    requestId: string;
  }>;
}

interface RequestData {
  requestId: string;
  status: string;
  originalFilename?: string;
  createdAt?: string;
  statusMessage?: string;
}

// Validate request ID format (basic validation)
function isValidRequestIdFormat(requestId: string): boolean {
  // Check if request ID is not empty and has reasonable length
  if (!requestId || requestId.length < 3 || requestId.length > 100) {
    return false;
  }
  
  // Check for any obvious invalid characters (very basic check)
  const invalidChars = /[<>:"\/\\|?*\s]/;
  if (invalidChars.test(requestId)) {
    return false;
  }
  
  return true;
}

// Server-side function to validate and fetch request data
async function getRequestData(requestId: string): Promise<RequestData | null> {
  try {
    console.log('[SERVER] Validating request ID:', requestId);
    
    // Basic format validation before making API call
    if (!isValidRequestIdFormat(requestId)) {
      console.log('[SERVER] Invalid request ID format:', requestId);
      return null;
    }
    
    // Call the backend API directly from server component
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/reports/${requestId}`, {
      cache: 'no-store', // Always fetch fresh data
      headers: {
        'Accept': 'application/json',
      },
    });

    if (response.status === 404) {
      console.log('[SERVER] Request ID not found in database:', requestId);
      return null;
    }

    if (response.status === 400) {
      console.log('[SERVER] Invalid request ID format (backend validation):', requestId);
      return null;
    }

    if (!response.ok) {
      // For other errors, we might want to show an error state rather than 404
      console.log('[SERVER] Backend error, status:', response.status);
      
      // If it's a 5xx error, assume the request might be valid but there's a server issue
      if (response.status >= 500) {
        return {
          requestId,
          status: 'error',
          originalFilename: 'Unable to load',
          statusMessage: 'Server error - please try again later',
        };
      }
      
      // For other 4xx errors, treat as not found
      return null;
    }

    const data = await response.json();
    console.log('[SERVER] Request data retrieved:', { 
      requestId, 
      status: data.status,
      filename: data.original_filename 
    });
    
    // Validate the response data structure
    if (!data || typeof data !== 'object') {
      console.log('[SERVER] Invalid response data structure');
      return null;
    }
    
    return {
      requestId,
      status: data.status || 'processing',
      originalFilename: data.original_filename || 'Unknown file',
      createdAt: data.created_at,
      statusMessage: data.status_message || `Analysis ${data.status || 'in progress'}`,
    };
  } catch (error) {
    console.error('[SERVER] Error validating request ID:', error);
    
    // Network errors - assume the request might be valid but we can't verify
    return {
      requestId,
      status: 'error',
      originalFilename: 'Connection Error',
      statusMessage: 'Unable to verify request - please check your connection',
    };
  }
}

export default async function UploadPage({ params }: UploadPageProps) {
  const { requestId } = await params;
  
  // Server-side validation
  const requestData = await getRequestData(requestId);
  
  // If request doesn't exist or is invalid, show 404
  if (!requestData) {
    console.log('[SERVER] Request not found, showing 404 for:', requestId);
    notFound();
  }

  // Log successful validation
  console.log('[SERVER] Rendering upload page for:', requestId, 'status:', requestData.status);

  // Pass the validated data to the client component
  return <UploadPageClient requestData={requestData} />;
}

// Separate viewport generation
export async function generateViewport({ params }: { params: Promise<{ requestId: string }> }) {
  return {
    width: 'device-width',
    initialScale: 1,
    maximumScale: 1,
    themeColor: '#4f46e5', // Indigo color matching the UI
    colorScheme: 'light',
  };
}

// Enhanced metadata generation with comprehensive SEO
export async function generateMetadata({ params }: { params: Promise<{ requestId: string }> }) {
  const { requestId } = await params;
  
  // Fetch request data for dynamic metadata
  const requestData = await getRequestData(requestId);
  
  if (!requestData) {
    return {
      title: 'Request Not Found - ShiftIQ',
      description: 'The requested upload session could not be found.',
      robots: 'noindex, nofollow',
    };
  }

  if (requestData.status === 'expired') {
    return {
      title: 'Request Not Found - ShiftIQ',
      description: 'This upload session has expired.',
      robots: 'noindex, nofollow',
      openGraph: {
        siteName: 'ShiftIQ',
      },
    };
  }

  const baseTitle = `Complete Your Information - ShiftIQ`;
  
  const title = requestData.originalFilename 
    ? `Complete Info for ${requestData.originalFilename} - ShiftIQ`
    : baseTitle;

  const description = 'Complete your information to receive your timesheet compliance analysis report.';

  return {
    title,
    description,
    keywords: 'timesheet analysis, lead capture, labor compliance, contact information',
    
    // SEO enhancements
    authors: [{ name: 'ShiftIQ' }],
    creator: 'ShiftIQ',
    publisher: 'ShiftIQ',
    category: 'Business Tools',
    
    // Open Graph for social sharing
    openGraph: {
      title,
      description: 'Complete your information to receive detailed timesheet compliance insights',
      type: 'website',
      siteName: 'ShiftIQ',
      url: `/upload/${requestId}`,
      images: [
        {
          url: '/og-image.png',
          width: 1200,
          height: 630,
          alt: 'ShiftIQ - Labor Compliance Analysis',
        },
      ],
    },
    
    // Twitter metadata
    twitter: {
      card: 'summary_large_image',
      title,
      description: 'Complete your information for timesheet analysis',
      images: ['/og-image.png'],
    },
    
    // PWA enhancements
    manifest: '/site.webmanifest',
    themeColor: '#1746d4',
    viewport: 'width=device-width, initial-scale=1, user-scalable=no',
    
    // App metadata for mobile
    appleWebApp: {
      capable: true,
      statusBarStyle: 'default',
      title: 'ShiftIQ',
    },
    
    applicationName: 'ShiftIQ',
    
    // Additional metadata
    other: {
      'request-id': requestId,
      'upload-status': requestData?.status || 'unknown',
    },
  };
} 