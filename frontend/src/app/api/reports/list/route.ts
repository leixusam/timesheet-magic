import { NextRequest, NextResponse } from 'next/server';

interface SavedReportSummary {
  id: string;
  original_filename: string;
  manager_name?: string;
  store_name?: string;
  created_at: string;
  employee_count?: number;
  total_violations?: number;
  total_hours?: number;
  overtime_cost?: number;
}

const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const skip = searchParams.get('skip') || '0';
    const limit = searchParams.get('limit') || '50';
    
    const response = await fetch(`${backendUrl}/api/reports/list?skip=${skip}&limit=${limit}`);
    
    if (!response.ok) {
      throw new Error(`Backend responded with ${response.status}`);
    }
    
    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching reports:', error);
    return NextResponse.json(
      { error: 'Failed to fetch reports' },
      { status: 500 }
    );
  }
} 