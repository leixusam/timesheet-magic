import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

interface RouteParams {
  params: Promise<{ id: string }>;
}

export async function GET(
  request: NextRequest,
  { params }: RouteParams
) {
  try {
    const { id: reportId } = await params;

    if (!reportId) {
      return NextResponse.json(
        { error: 'Report ID is required' },
        { status: 400 }
      );
    }

    // Forward the request to the FastAPI backend
    const backendResponse = await fetch(`${BACKEND_URL}/api/reports/${reportId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!backendResponse.ok) {
      if (backendResponse.status === 404) {
        return NextResponse.json(
          { error: 'Report not found' },
          { status: 404 }
        );
      }
      
      const errorData = await backendResponse.json().catch(() => ({
        message: 'Backend error'
      }));
      
      return NextResponse.json(
        { 
          error: errorData.message || `Backend error: ${backendResponse.status}`,
          details: errorData
        },
        { status: backendResponse.status || 500 }
      );
    }

    // Get the report from the backend
    const report = await backendResponse.json();

    // Return the report to the frontend
    return NextResponse.json(report);

  } catch (error) {
    console.error('Get report API route error:', error);
    
    return NextResponse.json(
      { 
        error: 'Internal server error while fetching report',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: RouteParams
) {
  try {
    const { id: reportId } = await params;
    
    if (!reportId) {
      return NextResponse.json(
        { error: 'Report ID is required' },
        { status: 400 }
      );
    }

    const response = await fetch(`${BACKEND_URL}/api/reports/${reportId}`, {
      method: 'DELETE',
    });
    
    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: 'Report not found' },
          { status: 404 }
        );
      }
      
      const errorData = await response.json().catch(() => ({
        message: 'Backend error'
      }));
      
      return NextResponse.json(
        { 
          error: errorData.message || `Backend error: ${response.status}`,
          details: errorData
        },
        { status: response.status || 500 }
      );
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error deleting report:', error);
    return NextResponse.json(
      { 
        error: 'Internal server error while deleting report',
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
      'Access-Control-Allow-Methods': 'GET, DELETE, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
} 