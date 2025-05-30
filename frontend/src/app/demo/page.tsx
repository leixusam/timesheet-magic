'use client';

import ReportDisplay from '@/components/ReportDisplay';
import Link from 'next/link';

// Mock data based on the FinalAnalysisReport schema
const mockAnalysisReport = {
  request_id: "demo-123",
  original_filename: "timesheet_sample.xlsx",
  status: "success",
  kpis: {
    total_scheduled_labor_hours: 324.5,
    total_regular_hours: 280.0,
    total_overtime_hours: 32.5,
    total_double_overtime_hours: 12.0,
    estimated_overtime_cost: 650.00,
    estimated_double_overtime_cost: 360.00,
    compliance_risk_assessment: "Medium: 4 violations detected",
    count_meal_break_violations: 2,
    count_rest_break_violations: 1,
    count_daily_overtime_violations: 1,
    count_weekly_overtime_violations: 0,
    count_daily_double_overtime_violations: 0,
    wage_data_source_note: "Default assumption of $20/hr used for overtime cost estimates."
  },
  all_identified_violations: [
    {
      rule_id: "MEAL_BREAK",
      rule_description: "Required meal break violation",
      employee_identifier: "John Smith",
      date_of_violation: "2024-01-15",
      specific_details: "Worked 6.5 hours without a meal break between 9:00 AM and 3:30 PM.",
      suggested_action_generic: "Ensure meal breaks are scheduled and taken for shifts longer than 6 hours."
    },
    {
      rule_id: "DAILY_OT",
      rule_description: "Daily overtime violation",
      employee_identifier: "Sarah Johnson",
      date_of_violation: "2024-01-16",
      specific_details: "Worked 10.5 hours in a single day, exceeding the 8-hour daily limit.",
      suggested_action_generic: "Review scheduling to minimize daily overtime and ensure adequate staffing."
    },
    {
      rule_id: "MEAL_BREAK", 
      rule_description: "Required meal break violation",
      employee_identifier: "Mike Davis",
      date_of_violation: "2024-01-17",
      specific_details: "Worked 7 hours without a documented meal break from 10:00 AM to 5:00 PM.",
      suggested_action_generic: "Implement a break tracking system to ensure compliance with meal break requirements."
    }
  ],
  employee_summaries: [
    {
      employee_identifier: "John Smith",
      roles_observed: ["Server", "Host"],
      departments_observed: ["Front of House"],
      total_hours_worked: 42.5,
      regular_hours: 36.0,
      overtime_hours: 6.5,
      double_overtime_hours: 0.0,
      violations_for_employee: [
        {
          rule_id: "MEAL_BREAK",
          rule_description: "Required meal break violation",
          employee_identifier: "John Smith",
          date_of_violation: "2024-01-15",
          specific_details: "Worked 6.5 hours without a meal break.",
          suggested_action_generic: "Ensure meal breaks are scheduled."
        }
      ]
    },
    {
      employee_identifier: "Sarah Johnson",
      roles_observed: ["Cook"],
      departments_observed: ["Kitchen"],
      total_hours_worked: 45.0,
      regular_hours: 32.0,
      overtime_hours: 10.0,
      double_overtime_hours: 3.0,
      violations_for_employee: [
        {
          rule_id: "DAILY_OT",
          rule_description: "Daily overtime violation", 
          employee_identifier: "Sarah Johnson",
          date_of_violation: "2024-01-16",
          specific_details: "Worked 10.5 hours in a single day.",
          suggested_action_generic: "Review scheduling to minimize daily overtime."
        }
      ]
    },
    {
      employee_identifier: "Mike Davis",
      roles_observed: ["Server"],
      departments_observed: ["Front of House"],
      total_hours_worked: 38.0,
      regular_hours: 35.0,
      overtime_hours: 3.0,
      double_overtime_hours: 0.0,
      violations_for_employee: [
        {
          rule_id: "MEAL_BREAK",
          rule_description: "Required meal break violation",
          employee_identifier: "Mike Davis", 
          date_of_violation: "2024-01-17",
          specific_details: "Worked 7 hours without a documented meal break.",
          suggested_action_generic: "Implement a break tracking system."
        }
      ]
    },
    {
      employee_identifier: "Lisa Chen",
      roles_observed: ["Manager"],
      departments_observed: ["Front of House", "Kitchen"],
      total_hours_worked: 40.0,
      regular_hours: 40.0,
      overtime_hours: 0.0,
      double_overtime_hours: 0.0,
      violations_for_employee: []
    }
  ],
  duplicate_name_warnings: [
    "Potential duplicate: 'John Smith' and 'J. Smith' may refer to the same person",
    "Similar names detected: 'Sarah Johnson' and 'Sarah J.' - please verify these are different employees"
  ],
  parsing_issues_summary: [
    "Line 47: Ambiguous time format '1300' interpreted as 1:00 PM",
    "Employee 'Temp Worker' found without a full name - using temporary identifier"
  ],
  overall_report_summary_text: "Analysis of timesheet data shows 4 compliance violations across 3 employees, with total overtime costs estimated at $1,010. Main concerns include meal break violations and one instance of excessive daily hours. Recommend implementing better break tracking and reviewing scheduling practices."
};

export default function DemoPage() {
  const handleNewAnalysis = () => {
    console.log("New analysis clicked - would redirect to upload page");
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            ReportDisplay Component Demo
          </h1>
          <p className="text-gray-600 mb-6">
            This is a preview of the timesheet analysis report with sample data
          </p>
          <div className="flex gap-4 justify-center">
            <Link 
              href="/reports"
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-600 text-white rounded-lg font-medium hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors shadow-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              View Saved Reports
            </Link>
          </div>
        </div>
        
        <ReportDisplay 
          analysisReport={mockAnalysisReport}
          onNewAnalysis={handleNewAnalysis}
        />
      </div>
    </div>
  );
} 