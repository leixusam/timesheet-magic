'use client';

import React, { useState } from 'react';
import EmployeeViolationGroup from './EmployeeViolationGroup';
import ViolationTypeGroup from './ViolationTypeGroup';
import { FilterPanel } from './ui/FilterPanel';
import { useReportFilters } from '@/hooks/useReportFilters';

// Define the interfaces based on the backend Pydantic schemas
interface ViolationInstance {
  rule_id: string;
  rule_description: string;
  employee_identifier: string;
  date_of_violation: string; // Will be a date string from JSON
  specific_details: string;
  suggested_action_generic: string;
}

interface EmployeeReportDetails {
  employee_identifier: string;
  roles_observed?: string[];
  departments_observed?: string[];
  total_hours_worked: number;
  regular_hours: number;
  overtime_hours: number;
  double_overtime_hours: number;
  violations_for_employee: ViolationInstance[];
}

interface ReportKPIs {
  total_scheduled_labor_hours: number;
  total_regular_hours: number;
  total_overtime_hours: number;
  total_double_overtime_hours: number;
  estimated_overtime_cost?: number;
  estimated_double_overtime_cost?: number;
  compliance_risk_assessment?: string;
  count_meal_break_violations: number;
  count_rest_break_violations: number;
  count_daily_overtime_violations: number;
  count_weekly_overtime_violations: number;
  count_daily_double_overtime_violations: number;
  wage_data_source_note: string;
}

interface HeatMapDatapoint {
  hour_timestamp: string; // Will be a datetime string from JSON
  employee_count: number;
}

interface FinalAnalysisReport {
  request_id: string;
  original_filename: string;
  status: string;
  status_message?: string;
  kpis?: ReportKPIs;
  staffing_density_heatmap?: HeatMapDatapoint[];
  all_identified_violations?: ViolationInstance[];
  employee_summaries?: EmployeeReportDetails[];
  duplicate_name_warnings?: string[];
  parsing_issues_summary?: string[];
  overall_report_summary_text?: string;
}

interface ReportDisplayProps {
  analysisReport: FinalAnalysisReport;
  onNewAnalysis?: () => void; // Callback to start a new analysis
  requestedBy?: string; // Manager who requested the report
  requestedAt?: string; // Timestamp when report was requested
}

const ReportDisplay: React.FC<ReportDisplayProps> = ({ 
  analysisReport, 
  onNewAnalysis,
  requestedBy,
  requestedAt
}) => {
  const [viewMode, setViewMode] = useState<'by-employee' | 'by-type'>('by-employee');
  const [isDisclaimersExpanded, setIsDisclaimersExpanded] = useState(false); // Changed to false by default
  
  const { 
    request_id,
    original_filename,
    status,
    status_message,
    kpis,
    all_identified_violations = [],
    employee_summaries = [],
    duplicate_name_warnings = [],
    parsing_issues_summary = [],
    overall_report_summary_text
  } = analysisReport;

  // Initialize filtering system
  const filterHook = useReportFilters(all_identified_violations);
  const { filteredResults } = filterHook;

  // Format timestamp for display
  const formatTimestamp = (timestamp?: string) => {
    if (!timestamp) return 'Just now';
    try {
      const date = new Date(timestamp);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        timeZoneName: 'short'
      });
    } catch {
      return timestamp;
    }
  };

  // Handle error states
  if (status === 'error_parsing_failed' || status === 'error_analysis_failed') {
    return (
      <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
        <div className="text-center">
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <h2 className="text-xl font-semibold text-red-800 mb-2">
              Analysis Failed
            </h2>
            <p className="text-red-700 mb-4">
              {status_message || 'An error occurred while processing your timesheet.'}
            </p>
            <div className="flex gap-4 justify-center">
              <button
                onClick={onNewAnalysis}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
              >
                Try Again
              </button>
              <button
                onClick={onNewAnalysis}
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
              >
                Upload Different File
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
      {/* Enhanced Hero Section with Report Metadata */}
      <div className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-indigo-50 rounded-xl border border-blue-100 shadow-lg">
        {/* Background Pattern */}
        <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
        
        <div className="relative p-8">
          {/* Report Metadata Header */}
          <div className="mb-6 pb-6 border-b border-gray-200">
            <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
              {/* Report Info */}
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                  <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
                <div>
                  <h1 className="text-3xl font-bold text-gray-900 leading-tight">
                    Timesheet Analysis Report
                  </h1>
                  <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-gray-600">
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="font-medium">{original_filename}</span>
                    </div>
                    {requestedBy && (
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                        </svg>
                        <span>Requested by <strong>{requestedBy}</strong></span>
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span>Generated {formatTimestamp(requestedAt)}</span>
                    </div>
                    {request_id && (
                      <div className="flex items-center gap-2">
                        <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 7h.01M7 3h5c.512 0 1.024.195 1.414.586l7 7a2 2 0 010 2.828l-7 7a1.994 1.994 0 01-2.828 0l-7-7A1.994 1.994 0 013 12V7a4 4 0 014-4z" />
                        </svg>
                        <span className="text-xs font-mono bg-gray-100 px-2 py-1 rounded">ID: {request_id}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Status Badge Only */}
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium bg-green-100 text-green-800">
                  <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Analysis Complete
                </span>
              </div>
            </div>
          </div>

          {/* Consolidated Metrics Grid */}
          {kpis && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 mb-8">
              <div className="bg-white rounded-xl px-6 py-4 shadow-sm border border-gray-200">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Employees</div>
                <div className="text-3xl font-bold text-gray-900">{employee_summaries.length}</div>
              </div>
              <div className="bg-white rounded-xl px-6 py-4 shadow-sm border border-gray-200">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Total Hours</div>
                <div className="text-3xl font-bold text-blue-600">{kpis.total_scheduled_labor_hours.toFixed(0)}h</div>
                <div className="text-xs text-gray-500 mt-1">
                  {kpis.total_regular_hours.toFixed(0)} reg, {kpis.total_overtime_hours.toFixed(0)} OT
                </div>
              </div>
              <div className={`rounded-xl px-6 py-4 shadow-sm border ${
                all_identified_violations.length > 0 
                  ? 'bg-red-50 border-red-200' 
                  : 'bg-green-50 border-green-200'
              }`}>
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Violations</div>
                <div className={`text-3xl font-bold ${
                  all_identified_violations.length > 0 ? 'text-red-700' : 'text-green-700'
                }`}>
                  {all_identified_violations.length}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  {kpis.count_meal_break_violations} meal, {kpis.count_daily_overtime_violations} daily OT
                </div>
              </div>
              <div className="bg-white rounded-xl px-6 py-4 shadow-sm border border-gray-200">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">Overtime Cost</div>
                <div className="text-3xl font-bold text-green-600">
                  {kpis.estimated_overtime_cost ? `$${kpis.estimated_overtime_cost.toFixed(0)}` : '$0'}
                </div>
                <div className="text-xs text-gray-500 mt-1">Additional labor costs</div>
              </div>
            </div>
          )}

          {/* Enhanced Executive Summary */}
          {overall_report_summary_text && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <div className="flex items-center gap-3 mb-6">
                <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-lg flex items-center justify-center">
                  <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-900">Executive Summary</h2>
              </div>
              
              {/* Formatted summary text only */}
              <div className="prose prose-blue max-w-none">
                <div className="text-gray-700 leading-relaxed text-base">
                  {/* Parse summary text and format it better */}
                  {overall_report_summary_text.split(/\.\s+/).map((sentence, index) => {
                    if (!sentence.trim()) return null;
                    
                    return (
                      <p key={index} className="mb-3">
                        {sentence.split(/(\$[\d,]+(?:\.\d{2})?|\d+(?:\.\d+)?\s*(?:hours?|violations?|employees?)|\d+\s*(?:meal\s+break|daily\s+overtime|weekly\s+overtime|rest\s+break)\s*violations?)/gi).map((part, partIndex) => {
                          // Highlight money amounts
                          if (part.match(/\$[\d,]+(?:\.\d{2})?/)) {
                            return (
                              <span key={partIndex} className="inline-flex items-center px-2 py-0.5 rounded bg-green-100 text-green-800 font-semibold text-sm">
                                {part}
                              </span>
                            );
                          }
                          // Highlight specific violation types
                          if (part.match(/\d+\s*(?:meal\s+break|daily\s+overtime|weekly\s+overtime|rest\s+break)\s*violations?/gi)) {
                            return (
                              <span key={partIndex} className="inline-flex items-center px-2 py-0.5 rounded bg-red-100 text-red-800 font-semibold text-sm">
                                {part}
                              </span>
                            );
                          }
                          // Highlight general violation counts
                          if (part.match(/\d+\s*violations?/)) {
                            return (
                              <span key={partIndex} className="inline-flex items-center px-2 py-0.5 rounded bg-orange-100 text-orange-800 font-semibold text-sm">
                                {part}
                              </span>
                            );
                          }
                          // Highlight hour counts
                          if (part.match(/\d+(?:\.\d+)?\s*hours?/)) {
                            return (
                              <span key={partIndex} className="inline-flex items-center px-2 py-0.5 rounded bg-blue-100 text-blue-800 font-semibold text-sm">
                                {part}
                              </span>
                            );
                          }
                          // Highlight employee counts
                          if (part.match(/\d+\s*employees?/)) {
                            return (
                              <span key={partIndex} className="inline-flex items-center px-2 py-0.5 rounded bg-purple-100 text-purple-800 font-semibold text-sm">
                                {part}
                              </span>
                            );
                          }
                          return part;
                        })}
                        {index < overall_report_summary_text.split(/\.\s+/).length - 1 && '.'}
                      </p>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Progressive Disclosure Compliance Violations with Filtering */}
      {all_identified_violations.length > 0 && (
        <div className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-indigo-50 rounded-xl border border-blue-100 shadow-lg">
          <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
          <div className="relative p-8">
            <div className="mb-6">
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">Compliance Violations</h2>
                  <p className="text-sm text-gray-600">
                    Detailed analysis of potential labor law violations
                    {filteredResults.activeFilterCount > 0 && (
                      <span className="ml-2">
                        ({filteredResults.filteredCount} of {filteredResults.totalCount} showing)
                      </span>
                    )}
                  </p>
                </div>
                
                {/* View Mode Toggle */}
                <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
                  <button
                    onClick={() => setViewMode('by-employee')}
                    className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      viewMode === 'by-employee'
                        ? 'bg-white text-blue-700 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <span className="hidden sm:inline">👤 By Employee</span>
                    <span className="sm:hidden">👤 Employee</span>
                  </button>
                  <button
                    onClick={() => setViewMode('by-type')}
                    className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                      viewMode === 'by-type'
                        ? 'bg-white text-blue-700 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    <span className="hidden sm:inline">📋 By Type</span>
                    <span className="sm:hidden">📋 Type</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Compact Filter Panel */}
            <FilterPanel
              filteredResults={filteredResults}
              filterHook={filterHook}
              showResultCount={true}
              isCollapsible={true}
              contextInfo={
                viewMode === 'by-employee' 
                  ? `${new Set(filteredResults.violations.map(v => v.employee_identifier)).size} employee${new Set(filteredResults.violations.map(v => v.employee_identifier)).size !== 1 ? 's' : ''}`
                  : (() => {
                      const getViolationType = (ruleId: string): string => {
                        const lowerRuleId = ruleId.toLowerCase();
                        if (lowerRuleId.includes('meal_break') || lowerRuleId.includes('meal')) return 'Meal Break';
                        if (lowerRuleId.includes('rest_break') || lowerRuleId.includes('rest')) return 'Rest Break';
                        if (lowerRuleId.includes('daily_ot') || lowerRuleId.includes('daily')) return 'Daily Overtime';
                        if (lowerRuleId.includes('weekly_ot') || lowerRuleId.includes('weekly')) return 'Weekly Overtime';
                        if (lowerRuleId.includes('double_ot') || lowerRuleId.includes('double')) return 'Double Overtime';
                        return 'Other';
                      };
                      const uniqueTypes = new Set(filteredResults.violations.map(v => getViolationType(v.rule_id)));
                      return `${uniqueTypes.size} violation type${uniqueTypes.size !== 1 ? 's' : ''}`;
                    })()
              }
              className="mb-6"
            />

            {/* Render filtered violations based on selected view mode */}
            {filteredResults.filteredCount > 0 ? (
              <div className="violation-grid">
                {viewMode === 'by-employee' ? (
                  <EmployeeViolationGroup 
                    violations={filteredResults.violations} 
                    defaultCollapsed={true}
                    searchTerm={filterHook.filters.searchText}
                  />
                ) : (
                  <ViolationTypeGroup 
                    violations={filteredResults.violations} 
                    defaultCollapsed={true}
                    searchTerm={filterHook.filters.searchText}
                  />
                )}
              </div>
            ) : (
              <div className="text-center py-8">
                <div className="text-gray-400 mb-2">
                  <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-1">
                  {filteredResults.activeFilterCount > 0 ? 'No violations match your filters' : 'No Violations Found'}
                </h3>
                <p className="text-gray-600">
                  {filteredResults.activeFilterCount > 0 
                    ? 'Try adjusting your filter criteria to see more results.'
                    : 'All employees appear to be in compliance with labor regulations.'
                  }
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Employee Summary Table */}
      {employee_summaries.length > 0 && (
        <div className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-white to-indigo-50 rounded-xl border border-blue-100 shadow-lg">
          <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
          <div className="relative p-8">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">Employee Summary</h2>
              <p className="text-sm text-gray-600">Individual employee hours and violation breakdown</p>
            </div>
            <div className="overflow-x-auto -mx-8">
              <div className="inline-block min-w-full px-8">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Employee
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Roles
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Total Hours
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Regular
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Overtime
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Double OT
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                        Violations
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {employee_summaries.map((employee, index) => (
                      <tr key={index} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">
                            {employee.employee_identifier}
                          </div>
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-500">
                          {employee.roles_observed?.join(', ') || '-'}
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                          {employee.total_hours_worked.toFixed(1)}h
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm text-gray-900">
                          {employee.regular_hours.toFixed(1)}h
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-yellow-600">
                          {employee.overtime_hours.toFixed(1)}h
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap text-sm font-medium text-red-600">
                          {employee.double_overtime_hours.toFixed(1)}h
                        </td>
                        <td className="px-4 py-4 whitespace-nowrap">
                          {employee.violations_for_employee.length > 0 ? (
                            <div className="flex flex-col gap-1">
                              <span className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-semibold bg-red-100 text-red-800 border border-red-200">
                                <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L5.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
                                </svg>
                                {employee.violations_for_employee.length} violation{employee.violations_for_employee.length !== 1 ? 's' : ''}
                              </span>
                              <div className="text-xs text-gray-600 mt-1">
                                Requires attention
                              </div>
                            </div>
                          ) : (
                            <div className="flex flex-col gap-1">
                              <span className="inline-flex items-center px-3 py-1.5 rounded-md text-sm font-semibold bg-green-100 text-green-800 border border-green-200">
                                <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Clean
                              </span>
                              <div className="text-xs text-gray-600 mt-1">
                                No violations
                              </div>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Important Notices & Disclaimers - Moved to Bottom */}
      <div className="relative overflow-hidden bg-gradient-to-br from-yellow-50 via-white to-orange-50 rounded-xl border border-yellow-200 shadow-lg">
        <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
        <div className="relative">
          <button
            onClick={() => setIsDisclaimersExpanded(!isDisclaimersExpanded)}
            className="w-full px-8 py-6 text-left flex items-center justify-between"
          >
            <div className="flex items-center gap-3">
              <svg className="h-5 w-5 text-yellow-400 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L5.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <h3 className="text-lg font-semibold text-yellow-800">
                Important Notices & Disclaimers
                {duplicate_name_warnings.length > 0 || parsing_issues_summary.length > 0 || all_identified_violations.length > 0 ? 
                  ` (${[duplicate_name_warnings.length > 0, parsing_issues_summary.length > 0, all_identified_violations.length > 0].filter(Boolean).length} notices)` : ''}
              </h3>
            </div>
            <svg
              className={`h-5 w-5 text-yellow-600 transition-transform ${isDisclaimersExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {isDisclaimersExpanded && (
            <div className="px-8 pb-6 space-y-4">
              {/* Analysis Warning */}
              <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <svg className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.732-.833-2.464 0L5.732 15.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                  <div>
                    <h3 className="text-sm font-medium text-yellow-800">Analysis Completed with Warnings</h3>
                    <p className="mt-1 text-sm text-yellow-700">
                      Some data may be incomplete. Please review all results carefully.
                    </p>
                  </div>
                </div>
              </div>

              {/* Automated Detection Notice */}
              {all_identified_violations.length > 0 && (
                <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <svg className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <div>
                      <h3 className="text-sm font-medium text-yellow-800">Automated Detection Notice</h3>
                      <p className="mt-1 text-sm text-yellow-700">
                        Violation detection is based on automated analysis of timesheet data. Please review all flagged items and verify accuracy before taking action. Results should be considered advisory and require human validation.
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Duplicate Names Warning */}
              {duplicate_name_warnings.length > 0 && (
                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <svg className="h-5 w-5 text-orange-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                    </svg>
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-orange-800">Potential Duplicate Employee Names</h3>
                      <p className="mt-1 text-sm text-orange-700 mb-3">
                        Similar employee names were detected that may represent the same person. Please verify and consolidate if necessary.
                      </p>
                      <ul className="space-y-1">
                        {duplicate_name_warnings.map((warning, index) => (
                          <li key={index} className="text-sm text-orange-700 flex items-start gap-2">
                            <span className="text-orange-400 font-medium">•</span>
                            <span>{warning}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}

              {/* Data Parsing Issues */}
              {parsing_issues_summary.length > 0 && (
                <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <svg className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div className="flex-1">
                      <h3 className="text-sm font-medium text-red-800">Data Parsing Issues</h3>
                      <p className="mt-1 text-sm text-red-700 mb-3">
                        Some data could not be properly parsed from the uploaded file. This may affect analysis accuracy.
                      </p>
                      <ul className="space-y-1">
                        {parsing_issues_summary.map((issue, index) => (
                          <li key={index} className="text-sm text-red-700 flex items-start gap-2">
                            <span className="text-red-400 font-medium">•</span>
                            <span>{issue}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Action Buttons at Bottom */}
      <div className="relative overflow-hidden bg-gradient-to-br from-gray-50 via-white to-gray-100 rounded-xl border border-gray-200 shadow-lg">
        <div className="absolute inset-0 bg-grid-pattern opacity-5"></div>
        <div className="relative p-8">
          <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
            <button
              onClick={() => {
                // Share functionality - could copy link or open share dialog
                if (navigator.share) {
                  navigator.share({
                    title: 'Timesheet Analysis Report',
                    text: `Analysis report for ${original_filename}`,
                    url: window.location.href
                  });
                } else {
                  // Fallback to copying URL
                  navigator.clipboard.writeText(window.location.href);
                  // You could add a toast notification here
                }
              }}
              className="inline-flex items-center gap-2 px-6 py-3 bg-gray-600 text-white rounded-lg font-medium hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2 transition-colors shadow-sm"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.684 13.342C8.886 12.938 9 12.482 9 12c0-.482-.114-.938-.316-1.342m0 2.684a3 3 0 110-2.684m0 2.684l6.632 3.316m-6.632-6l6.632-3.316m0 0a3 3 0 105.367-2.684 3 3 0 00-5.367 2.684zm0 9.316a3 3 0 105.367 2.684 3 3 0 00-5.367-2.684z" />
              </svg>
              Share Report
            </button>
            
            {onNewAnalysis && (
              <button
                onClick={onNewAnalysis}
                className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 transition-colors shadow-sm"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                New Analysis
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default ReportDisplay;