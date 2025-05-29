import { NextRequest, NextResponse } from 'next/server';

const BACKEND_URL = process.env.BACKEND_URL || 'http://localhost:8000';

interface LeadData {
  analysisId: string;
  managerName: string;
  managerEmail: string;
  managerPhone: string;
  storeName: string;
  storeAddress: string;
}

export async function POST(request: NextRequest) {
  try {
    // Parse the JSON body
    const leadData: LeadData = await request.json();

    // Validate required fields
    const requiredFields = ['analysisId', 'managerName', 'managerEmail', 'storeName', 'storeAddress'];
    const missingFields = requiredFields.filter(field => !leadData[field as keyof LeadData]);

    if (missingFields.length > 0) {
      return NextResponse.json(
        { 
          error: 'Missing required fields',
          missingFields: missingFields
        },
        { status: 400 }
      );
    }

    // Validate email format (basic validation)
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(leadData.managerEmail)) {
      return NextResponse.json(
        { error: 'Invalid email format' },
        { status: 400 }
      );
    }

    // Forward the lead data to the FastAPI backend
    const backendResponse = await fetch(`${BACKEND_URL}/submit-lead`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        analysis_id: leadData.analysisId,
        manager_name: leadData.managerName,
        email: leadData.managerEmail,
        phone: leadData.managerPhone || null,
        store_name: leadData.storeName,
        store_address: leadData.storeAddress,
      }),
    });

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json().catch(() => ({
        message: 'Backend lead submission failed'
      }));
      
      return NextResponse.json(
        { 
          error: errorData.message || `Backend error: ${backendResponse.status}`,
          details: errorData
        },
        { status: backendResponse.status || 500 }
      );
    }

    // Get the response from the backend
    const result = await backendResponse.json();

    // Return success response
    return NextResponse.json({
      success: true,
      message: 'Lead data submitted successfully',
      data: result
    });

  } catch (error) {
    console.error('Lead submission API route error:', error);
    
    return NextResponse.json(
      { 
        error: 'Internal server error during lead submission',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

// Handle OPTIONS for CORS if needed
export async function OPTIONS(request: NextRequest) {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
} 