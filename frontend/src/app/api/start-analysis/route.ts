import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || 'https://timesheet-magic-backend.fly.dev';

export async function POST(request: NextRequest) {
  try {
    // Get the form data from the request
    const formData = await request.formData();
    const file = formData.get('file') as File;

    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      );
    }

    // Validate file size (10MB limit)
    const maxSize = 10 * 1024 * 1024; // 10MB
    if (file.size > maxSize) {
      return NextResponse.json(
        { error: 'File size exceeds 10MB limit' },
        { status: 413 }
      );
    }

    // Validate file type - be more lenient with CSV files since browsers detect different MIME types
    const allowedTypes = [
      'text/csv',
      'text/plain', // Sometimes CSV files are detected as text/plain
      'application/csv', // Alternative CSV MIME type
      'application/vnd.ms-excel', // Sometimes used for CSV
      'application/octet-stream', // Generic binary - often used when MIME type can't be determined
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/pdf',
      'image/jpeg',
      'image/png'
    ];

    // Additional check for CSV files based on file extension if MIME type is unclear
    const isCSVFile = file.name.toLowerCase().endsWith('.csv');
    const isTXTFile = file.name.toLowerCase().endsWith('.txt');
    const isValidType = allowedTypes.includes(file.type) || 
                       (file.type === 'text/plain' && (isCSVFile || isTXTFile)) ||
                       (file.type === 'application/octet-stream' && isCSVFile) ||
                       (file.type === '' && (isCSVFile || isTXTFile)); // Some systems don't set MIME type

    if (!isValidType) {
      return NextResponse.json(
        { error: `Invalid file type: ${file.type}. Supported formats: CSV, XLSX, PDF, JPG, PNG, TXT` },
        { status: 400 }
      );
    }

    // Create new FormData for the backend request
    const backendFormData = new FormData();
    backendFormData.append('file', file);

    // Forward the request to the FastAPI backend start-analysis endpoint
    const backendResponse = await fetch(`${BACKEND_URL}/api/start-analysis`, {
      method: 'POST',
      body: backendFormData,
      // Don't set Content-Type header - let fetch handle multipart/form-data
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({
        message: 'Backend analysis start failed'
      }));
      
      return NextResponse.json(
        { 
          error: errorData.message || `Backend error: ${backendResponse.status}`,
          details: errorData
        },
        { status: backendResponse.status || 500 }
      );
    }

    // Get the start analysis result from the backend
    const startResult = await backendResponse.json();

    // Convert snake_case response to camelCase for frontend compatibility
    const frontendResponse = {
      success: startResult.success,
      requestId: startResult.request_id, // Convert snake_case to camelCase
      message: startResult.message,
      filename: startResult.filename,
      status: startResult.status
    };

    // Return the result to the frontend
    return NextResponse.json(frontendResponse);

  } catch (error) {
    console.error('Start analysis API route error:', error);
    
    return NextResponse.json(
      { 
        error: 'Internal server error during analysis start',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

// Handle OPTIONS for CORS if needed
export async function OPTIONS(_request: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
} 