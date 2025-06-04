'use client';

import React, { useState } from 'react';
import { highlightSearchTerms } from '@/utils/searchHighlight';

export interface ViolationInstance {
  rule_id: string;
  rule_description: string;
  employee_identifier: string;
  date_of_violation: string;
  specific_details: string;
  suggested_action_generic: string;
  // Cost information from backend calculate_violation_costs function
  estimated_cost?: number;
  cost_description?: string;
  penalty_hours?: number; // For meal/rest break penalties (usually 1 hour)
  overtime_hours?: number; // For overtime violations (actual excess hours)
  // New fields for transparency and debugging
  related_punch_events?: Array<{
    employee_identifier: string;
    timestamp: string;
    formatted_time: string;
    punch_type: string;
    role?: string;
    department?: string;
    notes?: string;
    hourly_wage?: number;
  }>;
  shift_summary?: {
    employee_identifier: string;
    shift_date: string;
    clock_in_time?: string;
    clock_out_time?: string;
    clock_in_formatted?: string;
    clock_out_formatted?: string;
    total_hours_worked: number;
    meal_breaks: Array<{
      start_time: string;
      end_time: string;
      start_formatted: string;
      end_formatted: string;
      duration_minutes: number;
    }>;
    meal_break_count: number;
    total_punch_events: number;
  };
}

export interface ViolationCardProps {
  violation: ViolationInstance;
  showEmployee?: boolean;
  showDate?: boolean;
  isCompact?: boolean;
  searchTerm?: string;
}

const getSeverityInfo = (ruleId: string) => {
  const lowerRuleId = ruleId.toLowerCase();
  
  // Violations: Require immediate payroll action (meal breaks + overtime)
  if (lowerRuleId.includes('meal_break') || lowerRuleId.includes('daily_ot') || lowerRuleId.includes('double_ot') || lowerRuleId.includes('weekly_ot')) {
    return {
      level: 'Violation',
      cardClass: 'violation-card violation-card-critical',
      badgeClass: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200',
      iconColor: 'text-red-500',
      dotColor: 'bg-red-500'
    };
  } else {
    // Information: Awareness only (rest breaks and other low-confidence items)
    return {
      level: 'Information',
      cardClass: 'violation-card violation-card-info',
      badgeClass: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-200',
      iconColor: 'text-yellow-600',
      dotColor: 'bg-yellow-500'
    };
  }
};

export const ViolationCard: React.FC<ViolationCardProps> = ({
  violation,
  showEmployee = true,
  showDate = true,
  isCompact = false,
  searchTerm = ''
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const severityInfo = getSeverityInfo(violation.rule_id);
  
  const formatDate = (dateString: string) => {
    // BUGFIX: MISC-001 - Handle timezone issues in date parsing
    // Ensure consistent date parsing regardless of browser/timezone
    let date: Date;
    
    if (dateString.includes('T') || dateString.includes('Z')) {
      // Full ISO string with time/timezone - parse directly
      date = new Date(dateString);
    } else {
      // Date-only string (YYYY-MM-DD) - parse as local date to prevent timezone shift
      const [year, month, day] = dateString.split('-').map(Number);
      date = new Date(year, month - 1, day); // month is 0-indexed
    }
    
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    if (date.toDateString() === today.toDateString()) {
      return 'Today';
    } else if (date.toDateString() === yesterday.toDateString()) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString('en-US', { 
        weekday: 'short', 
        month: 'short', 
        day: 'numeric' 
      });
    }
  };

  // Helper function to render text with search highlighting
  const renderHighlightedText = (text: string, className?: string) => {
    if (!searchTerm.trim()) {
      return <span className={className}>{text}</span>;
    }
    return highlightSearchTerms(text, searchTerm, {
      className,
      highlightClassName: 'bg-yellow-200 dark:bg-yellow-700 px-0.5 rounded font-medium'
    });
  };

  return (
    <div className={`bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden ${isCompact ? 'mb-2' : 'mb-4'}`}>
      {/* Card Header - Always Visible */}
      <div className={`${isCompact ? 'p-3' : 'p-4'} bg-gray-50 border-b border-gray-200`}>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0 flex-1">
            {/* Severity badge - positioned with proper spacing */}
            <div className="flex-shrink-0">
              <span className={`${severityInfo.badgeClass} ${isCompact ? 'text-xs px-2 py-0.5' : ''}`}>
                {severityInfo.level}
              </span>
            </div>
            
            {/* Main content - Issue description with proper spacing */}
            <div className="min-w-0 flex-1 pl-2">
              <div className={`${isCompact ? 'mb-1' : 'mb-2'}`}>
                <h4 className={`${isCompact ? 'text-sm' : 'text-sm'} font-medium text-gray-900 leading-tight`}>
                  {renderHighlightedText(violation.rule_description)}
                </h4>
              </div>
              
              {/* Meta information */}
              <div className={`flex items-center gap-4 ${isCompact ? 'text-xs' : 'text-xs'} text-gray-500`}>
                {showEmployee && (
                  <span className="font-medium text-gray-700">
                    {renderHighlightedText(violation.employee_identifier)}
                  </span>
                )}
                {showDate && (
                  <span>{formatDate(violation.date_of_violation)}</span>
                )}
              </div>
            </div>
          </div>

          {/* Cost Information - Right side with proper alignment */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {/* Cost to remedy */}
            {violation.estimated_cost !== undefined && violation.estimated_cost > 0 ? (
              <div className="text-right">
                <div className={`${isCompact ? 'text-xs' : 'text-xs'} font-medium text-gray-500 uppercase tracking-wide`}>
                  {violation.rule_id.toLowerCase().includes('meal_break') ? 'Penalty Cost' : 'Premium Cost'}
                </div>
                <div className={`${isCompact ? 'text-base' : 'text-lg'} font-bold text-red-600`}>
                  ${violation.estimated_cost.toFixed(2)}
                </div>
                {violation.penalty_hours && violation.penalty_hours > 0 && (
                  <div className="text-xs text-gray-500">
                    {violation.penalty_hours}hr penalty
                  </div>
                )}
                {violation.overtime_hours && violation.overtime_hours > 0 && (
                  <div className="text-xs text-gray-500">
                    {violation.overtime_hours}hr overtime
                  </div>
                )}
              </div>
            ) : (
              // Show hours if available, otherwise don't show cost section
              (() => {
                const penaltyHours = violation.penalty_hours || 0;
                const overtimeHours = violation.overtime_hours || 0;
                const totalHours = penaltyHours + overtimeHours;
                
                if (totalHours > 0) {
                  return (
                    <div className="text-right">
                      <div className={`${isCompact ? 'text-xs' : 'text-xs'} font-medium text-gray-500 uppercase tracking-wide`}>
                        {violation.rule_id.toLowerCase().includes('meal_break') ? 'Penalty Cost' : 'Premium Cost'}
                      </div>
                      <div className={`${isCompact ? 'text-sm' : 'text-sm'} text-red-600 font-semibold`}>
                        {totalHours.toFixed(1)}hr
                      </div>
                    </div>
                  );
                }
                return null; // Don't show cost section if no data
              })()
            )}
            
            {/* Expand/Collapse Toggle - always show unless disabled */}
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors flex-shrink-0"
              aria-label={isExpanded ? 'Collapse details' : 'Expand details'}
            >
              <svg
                className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Card Content - Expanded Details */}
      {isExpanded && (
        <div className="p-4 space-y-4">
          {/* Shift Details - Combined Time Punches and Shift Summary */}
          {(violation.shift_summary || (violation.related_punch_events && violation.related_punch_events.length > 0)) && (
            <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
              <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
                <h5 className="text-sm font-medium text-gray-900 flex items-center gap-1.5">
                  <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  Shift Details
                </h5>
              </div>
              <div className="p-4 space-y-4">
                {/* Basic shift info and work date */}
                {violation.shift_summary && (
                  <div>
                    <div className="grid grid-cols-2 gap-4 mb-4">
                      <div className="space-y-1">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Work Date</span>
                        <div className="text-sm text-gray-900">
                          {(() => {
                            // BUGFIX: MISC-001 - Handle timezone issues in date parsing
                            let date: Date;
                            const dateString = violation.date_of_violation;
                            
                            if (dateString.includes('T') || dateString.includes('Z')) {
                              date = new Date(dateString);
                            } else {
                              const [year, month, day] = dateString.split('-').map(Number);
                              date = new Date(year, month - 1, day);
                            }
                            
                            return date.toLocaleDateString('en-US', { 
                              weekday: 'long', 
                              year: 'numeric', 
                              month: 'long', 
                              day: 'numeric' 
                            });
                          })()}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Hours</span>
                        <div className="text-sm text-gray-900 font-semibold">
                          {violation.shift_summary.total_hours_worked.toFixed(1)} hours
                        </div>
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Clock In</span>
                        <div className="font-mono text-sm text-gray-900">
                          {violation.shift_summary.clock_in_formatted || 'Not recorded'}
                        </div>
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Clock Out</span>
                        <div className="font-mono text-sm text-gray-900">
                          {violation.shift_summary.clock_out_formatted || 'Not recorded'}
                        </div>
                      </div>
                    </div>
                    
                    {/* Meal Break Details */}
                    {violation.shift_summary.meal_breaks && violation.shift_summary.meal_breaks.length > 0 && (
                      <div className="pt-4 border-t border-gray-100">
                        <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-3">
                          Meal Breaks ({violation.shift_summary.meal_break_count})
                        </span>
                        <div className="space-y-2">
                          {violation.shift_summary.meal_breaks.map((mealBreak, index) => (
                            <div key={index} className="flex items-center justify-between text-sm">
                              <span className="text-gray-700">
                                Break {index + 1}
                              </span>
                              <span className="font-mono text-gray-900">
                                {mealBreak.start_formatted} → {mealBreak.end_formatted}
                                <span className="text-gray-500 ml-2">({mealBreak.duration_minutes}m)</span>
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                {/* Time Punches */}
                {violation.related_punch_events && violation.related_punch_events.length > 0 && (
                  <div className="pt-4 border-t border-gray-100">
                    <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-3">
                      All Time Punches ({violation.related_punch_events.length})
                    </span>
                    <div className="space-y-2">
                      {violation.related_punch_events.map((punch, index) => (
                        <div key={index} className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className="font-mono text-sm text-gray-700 font-medium">
                              {punch.formatted_time}
                            </span>
                            <span className="px-2 py-1 bg-gray-100 text-gray-600 rounded-md text-xs font-medium">
                              {punch.punch_type}
                            </span>
                            {punch.role && (
                              <span className="text-gray-500 text-xs">
                                {punch.role}
                              </span>
                            )}
                          </div>
                          {punch.hourly_wage && (
                            <span className="text-gray-400 text-xs font-medium">
                              ${punch.hourly_wage}/hr
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Issue Details & Recommended Action - Combined */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-100 overflow-hidden">
            <div className="px-4 py-3 bg-gray-50 border-b border-gray-100">
              <h5 className="text-sm font-medium text-gray-900 flex items-center gap-1.5">
                <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Issue Details & Next Steps
              </h5>
            </div>
            <div className="p-4 space-y-4">
              {/* Issue Description */}
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-2">
                  What Happened
                </span>
                <div className="text-sm text-gray-700 leading-relaxed bg-gray-50 rounded-lg p-3">
                  {(() => {
                    const details = violation.specific_details;
                    
                    // Check if this looks like structured data with pipe separators
                    if (details.includes('Employee:') && details.includes('|')) {
                      // Parse structured employee/shift data
                      const parts = details.split('|').map(part => part.trim());
                      const structuredData: Record<string, string> = {};
                      
                      parts.forEach(part => {
                        const colonIndex = part.indexOf(':');
                        if (colonIndex > -1) {
                          const key = part.substring(0, colonIndex).trim();
                          const value = part.substring(colonIndex + 1).trim();
                          structuredData[key] = value;
                        }
                      });
                      
                      return (
                        <div className="space-y-3">
                          {/* Employee Info */}
                          {structuredData['Employee'] && (
                            <div className="flex items-start gap-3">
                              <div className="w-2 h-2 bg-blue-500 rounded-full mt-2 flex-shrink-0"></div>
                              <div>
                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Employee</span>
                                <div className="font-medium text-gray-900">{renderHighlightedText(structuredData['Employee'])}</div>
                              </div>
                            </div>
                          )}
                          
                          {/* Date and Hours in a row */}
                          <div className="grid grid-cols-2 gap-4">
                            {structuredData['Date'] && (
                              <div className="flex items-start gap-3">
                                <div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0"></div>
                                <div>
                                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Date</span>
                                  <div className="font-medium text-gray-900">{renderHighlightedText(structuredData['Date'])}</div>
                                </div>
                              </div>
                            )}
                            
                            {structuredData['Total Hours'] && (
                              <div className="flex items-start gap-3">
                                <div className="w-2 h-2 bg-orange-500 rounded-full mt-2 flex-shrink-0"></div>
                                <div>
                                  <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Total Hours</span>
                                  <div className="font-medium text-gray-900">{renderHighlightedText(structuredData['Total Hours'])}</div>
                                </div>
                              </div>
                            )}
                          </div>
                          
                          {/* Overtime Hours */}
                          {structuredData['Time-and-a-half Hours'] && (
                            <div className="flex items-start gap-3">
                              <div className="w-2 h-2 bg-red-500 rounded-full mt-2 flex-shrink-0"></div>
                              <div>
                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Overtime Hours</span>
                                <div className="font-medium text-gray-900">{renderHighlightedText(structuredData['Time-and-a-half Hours'])}</div>
                              </div>
                            </div>
                          )}
                          
                          {/* Shift Times */}
                          {structuredData['Shift'] && (
                            <div className="flex items-start gap-3">
                              <div className="w-2 h-2 bg-purple-500 rounded-full mt-2 flex-shrink-0"></div>
                              <div>
                                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide">Shift Time</span>
                                <div className="font-medium text-gray-900 font-mono">{renderHighlightedText(structuredData['Shift'])}</div>
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    }
                    
                    // For daily overtime violations, format the text better
                    if (violation.rule_id.toLowerCase().includes('daily_ot')) {
                      // Try to break up the long sentence into more readable parts
                      const parts = details.split('|').map(part => part.trim()).filter(part => part);
                      
                      if (parts.length > 1) {
                        return (
                          <div className="space-y-2">
                            {parts.map((part, index) => (
                              <div key={index} className="text-sm">
                                {renderHighlightedText(part)}
                              </div>
                            ))}
                          </div>
                        );
                      }
                    }
                    
                    // For other violations or if no pipe separators, show as before but with better formatting
                    // Improved sentence splitting that preserves decimal numbers
                    const sentences = details.split(/\.(?=\s+[A-Z]|\s*$)/).filter(s => s.trim());
                    if (sentences.length > 1) {
                      return (
                        <div className="space-y-1">
                          {sentences.map((sentence, index) => (
                            <div key={index} className="text-sm">
                              {renderHighlightedText(sentence.trim() + (index < sentences.length - 1 && !sentence.endsWith('.') ? '.' : ''))}
                            </div>
                          ))}
                        </div>
                      );
                    }
                    
                    // Fallback to original formatting
                    return renderHighlightedText(details);
                  })()}
                </div>
              </div>
              
              {/* Recommended Actions */}
              <div>
                <span className="text-xs font-medium text-gray-500 uppercase tracking-wide block mb-3">
                  Required Actions
                </span>
                {(() => {
                  const recommendation = violation.suggested_action_generic;
                  
                  // Parse IMMEDIATE ACTION and PREVENTION sections
                  const immediateMatch = recommendation.match(/IMMEDIATE ACTION:\s*([\s\S]+?)(?=\s+PREVENTION:|$)/);
                  const preventionMatch = recommendation.match(/PREVENTION:\s*([\s\S]+?)$/);
                  
                  const immediateAction = immediateMatch ? immediateMatch[1].trim() : null;
                  const prevention = preventionMatch ? preventionMatch[1].trim() : null;
                  
                  // If we can parse the sections, show them separately; otherwise show as before
                  if (immediateAction && prevention) {
                    return (
                      <div className="space-y-3">
                        {/* Immediate Action Section */}
                        <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                          <div className="flex items-start gap-3">
                            <div className="flex-shrink-0 w-6 h-6 bg-red-100 rounded-full flex items-center justify-center mt-0.5">
                              <svg className="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            </div>
                            <div className="flex-1 min-w-0">
                              <h6 className="text-sm font-semibold text-red-800 mb-1">
                                Immediate Payroll Action
                              </h6>
                              <div className="text-sm text-red-700 leading-relaxed whitespace-pre-wrap break-words">
                                {renderHighlightedText(immediateAction)}
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Prevention Section */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                          <div className="flex items-start gap-3">
                            <div className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center mt-0.5">
                              <svg className="w-3 h-3 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                              </svg>
                            </div>
                            <div className="flex-1 min-w-0">
                              <h6 className="text-sm font-semibold text-blue-800 mb-1">
                                Prevention Measures
                              </h6>
                              <div className="text-sm text-blue-700 leading-relaxed whitespace-pre-wrap break-words">
                                {renderHighlightedText(prevention)}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  } else {
                    // Fallback to original design for non-structured recommendations
                    return (
                      <div className="text-sm text-gray-700 leading-relaxed bg-blue-50 rounded-lg p-3">
                        {renderHighlightedText(recommendation)}
                      </div>
                    );
                  }
                })()}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ViolationCard; 