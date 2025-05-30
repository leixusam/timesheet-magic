import React from 'react';
import { notFound } from 'next/navigation';
import { Metadata } from 'next';
import ReportPageClient from './ReportPageClient';

// Define the type inline based on the analysis report structure
interface FinalAnalysisReport {
  request_id: string;
  original_filename: string;
  status: string;
  status_message?: string;
  kpis?: any;
  staffing_density_heatmap?: any[];
  all_identified_violations?: any[];
  employee_summaries?: any[];
  duplicate_name_warnings?: string[];
  parsing_issues_summary?: string[];
  overall_report_summary_text?: string;
}

interface ReportPageProps {
  params: Promise<{ id: string }>;
}

async function getReport(reportId: string): Promise<FinalAnalysisReport | null> {
  try {
    // Call the backend API directly from server component
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/reports/${reportId}`, {
      // Add cache control for better performance
      next: { revalidate: 300 }, // Revalidate every 5 minutes
      headers: {
        'Accept': 'application/json',
      },
    });
    
    if (response.status === 404) {
      return null;
    }
    
    if (!response.ok) {
      throw new Error(`Failed to fetch report: ${response.status}`);
    }
    
    const data = await response.json();
    return data;
  } catch (error) {
    console.error('Error fetching report server-side:', error);
    throw error;
  }
}

export async function generateMetadata({ params }: ReportPageProps): Promise<Metadata> {
  const { id: reportId } = await params;
  
  try {
    const report = await getReport(reportId);
    
    if (!report) {
      return {
        title: 'Report Not Found | ShiftIQ',
        description: 'The requested compliance report could not be found.',
        robots: 'noindex, nofollow',
      };
    }
    
    // Generate metadata based on report data
    const filename = report.original_filename || 'Timesheet';
    const violations = report.all_identified_violations?.length || 0;
    const employees = report.employee_summaries?.length || 0;
    const isInProgress = report.status === 'processing' || report.status === 'analyzing';
    
    const title = isInProgress 
      ? `Analyzing ${filename} | ShiftIQ`
      : `${filename} Compliance Report | ShiftIQ`;
    
    const description = isInProgress
      ? `Your timesheet analysis for ${filename} is currently in progress. View the live status and get results as soon as they're ready.`
      : violations > 0
        ? `Compliance report for ${filename}: Found ${violations} violation${violations !== 1 ? 's' : ''} across ${employees} employee${employees !== 1 ? 's' : ''}. View detailed analysis and cost impact.`
        : `Compliance report for ${filename}: No violations found across ${employees} employee${employees !== 1 ? 's' : ''}. View complete analysis results.`;
    
    const baseUrl = process.env.NEXT_PUBLIC_APP_URL || 'http://localhost:3000';
    const url = `${baseUrl}/reports/${reportId}`;
    
    return {
      title,
      description,
      openGraph: {
        title,
        description,
        url,
        siteName: 'ShiftIQ',
        type: 'article',
        images: [
          {
            url: '/og-image.png',
            width: 1200,
            height: 630,
            alt: 'ShiftIQ Logo',
          },
        ],
      },
      twitter: {
        card: 'summary_large_image',
        title,
        description,
        images: ['/og-image.png'],
        creator: '@timesheetmagic',
      },
      alternates: {
        canonical: url,
      },
      robots: isInProgress ? 'noindex, follow' : 'index, follow',
      keywords: [
        'timesheet analysis',
        'labor compliance',
        'overtime violations',
        'wage compliance',
        'employment law',
        'payroll audit',
        'break compliance',
        filename.toLowerCase(),
      ],
      authors: [{ name: 'ShiftIQ' }],
      creator: 'ShiftIQ',
      publisher: 'ShiftIQ',
      other: {
        'report-id': reportId,
        'report-status': report.status,
        'violations-count': violations.toString(),
        'employees-count': employees.toString(),
        'article:author': 'ShiftIQ',
        'article:section': 'Labor Compliance',
        'article:tag': 'timesheet analysis, labor compliance, audit report',
      },
    };
  } catch (error) {
    console.error('Error generating metadata:', error);
    return {
      title: 'Timesheet Analysis Report | ShiftIQ',
      description: 'View your timesheet compliance analysis report with detailed violation detection and cost impact.',
      robots: 'noindex, follow',
    };
  }
}

export default async function ReportPage({ params }: ReportPageProps) {
  const { id: reportId } = await params;
  
  let report: FinalAnalysisReport | null = null;
  let error: string | null = null;
  
  try {
    report = await getReport(reportId);
    
    if (!report) {
      notFound();
    }
  } catch (err) {
    console.error('Server-side error fetching report:', err);
    error = 'Failed to load report';
  }
  
  // If there's an error, we'll pass it to the client component to handle
  if (error) {
    return <ReportPageClient reportId={reportId} initialError={error} />;
  }
  
  return <ReportPageClient reportId={reportId} initialReport={report} />;
} 