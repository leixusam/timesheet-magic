'use client';

import React from 'react';
import { Accordion, AccordionItemProps } from './ui/Accordion';
import ViolationCard, { ViolationInstance } from './ViolationCard';
import ViolationInfoBadges from './ui/ViolationInfoBadges';

export interface EmployeeViolationGroupProps {
  violations: ViolationInstance[];
  defaultCollapsed?: boolean;
  searchTerm?: string;
}

interface DailyViolationGroup {
  date: string;
  displayDate: string;
  violations: ViolationInstance[];
  mealBreakCount: number;
  overtimeCount: number;
}

// Helper function to format date for display
const formatDisplayDate = (dateString: string): string => {
  try {
    // BUGFIX: MISC-001 - Handle timezone issues in date parsing
    let date: Date;
    
    if (dateString.includes('T') || dateString.includes('Z')) {
      // Full ISO string with time/timezone - parse directly
      date = new Date(dateString);
    } else {
      // Date-only string (YYYY-MM-DD) - parse as local date to prevent timezone shift
      const [year, month, day] = dateString.split('-').map(Number);
      date = new Date(year, month - 1, day); // month is 0-indexed
    }
    
    // Check if it's a valid date
    if (isNaN(date.getTime())) {
      return dateString; // Return original if parsing fails
    }
    
    // Format as "Mon, Mar 28" 
    return date.toLocaleDateString('en-US', { 
      weekday: 'short',
      month: 'short', 
      day: 'numeric'
    });
  } catch (error) {
    return dateString; // Return original if any error occurs
  }
};

// Helper function to extract work date from violation
const getWorkDate = (violation: ViolationInstance): string => {
  // date_of_violation is a string, so we need to extract just the date part
  if (violation.date_of_violation.includes('T')) {
    // ISO datetime string - extract date part
    return violation.date_of_violation.split('T')[0];
  }
  // Already a date string
  return violation.date_of_violation;
};

export const EmployeeViolationGroup: React.FC<EmployeeViolationGroupProps> = ({
  violations,
  defaultCollapsed = true,
  searchTerm = ''
}) => {
  if (!violations || violations.length === 0) {
    return null;
  }

  // Filter violations based on search term if provided
  const filteredViolations = searchTerm 
    ? violations.filter(violation => 
        violation.employee_identifier.toLowerCase().includes(searchTerm.toLowerCase()) ||
        violation.rule_description.toLowerCase().includes(searchTerm.toLowerCase()) ||
        violation.specific_details.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : violations;

  if (filteredViolations.length === 0) {
    return null;
  }

  // Group violations by employee first
  const violationsByEmployee = filteredViolations.reduce((acc, violation) => {
    const employeeId = violation.employee_identifier;
    if (!acc[employeeId]) {
      acc[employeeId] = [];
    }
    acc[employeeId].push(violation);
    return acc;
  }, {} as Record<string, ViolationInstance[]>);

  // Convert to accordion items (one per employee)
  const accordionItems: AccordionItemProps[] = Object.entries(violationsByEmployee).map(([employeeId, empViolations]) => {
    // Group all violations by date for timeline display (including weekly violations)
    const dailyViolationGroups: DailyViolationGroup[] = [];
    const dateGroups = empViolations.reduce((acc, violation) => {
      const date = getWorkDate(violation);
      if (!acc[date]) acc[date] = [];
      acc[date].push(violation);
      return acc;
    }, {} as Record<string, ViolationInstance[]>);

    Object.entries(dateGroups).forEach(([date, dateViolations]) => {
      const mealBreakCount = dateViolations.filter(v => 
        v.rule_id.toLowerCase().includes('meal_break')
      ).length;
      
      const overtimeCount = dateViolations.filter(v => 
        v.rule_id.toLowerCase().includes('overtime')
      ).length;

      dailyViolationGroups.push({
        date,
        displayDate: formatDisplayDate(date),
        violations: dateViolations,
        mealBreakCount,
        overtimeCount
      });
    });

    // Sort daily groups by date (newest first)
    dailyViolationGroups.sort((a, b) => {
      // BUGFIX: MISC-001 - Handle timezone issues in date parsing
      const parseDate = (dateString: string): Date => {
        if (dateString.includes('T') || dateString.includes('Z')) {
          return new Date(dateString);
        } else {
          const [year, month, day] = dateString.split('-').map(Number);
          return new Date(year, month - 1, day);
        }
      };
      
      return parseDate(b.date).getTime() - parseDate(a.date).getTime();
    });

    // Get violation level violations and information level violations separately
    const violationLevelViolations = empViolations.filter(v => {
      const ruleId = v.rule_id.toLowerCase();
      return ruleId.includes('meal_break') || ruleId.includes('daily_ot') || ruleId.includes('weekly_ot') || ruleId.includes('double_ot');
    });

    const informationLevelViolations = empViolations.filter(v => {
      const ruleId = v.rule_id.toLowerCase();
      return !ruleId.includes('meal_break') && !ruleId.includes('daily_ot') && !ruleId.includes('weekly_ot') && !ruleId.includes('double_ot');
    });

    return {
      id: `employee-${employeeId.replace(/\s+/g, '-').toLowerCase()}`,
      title: `👤 ${employeeId}`,
      violationCount: violationLevelViolations.length,
      infoCount: informationLevelViolations.length,
      variant: 'employee' as const,
      isDefaultOpen: !defaultCollapsed,
      children: (
        <div className="space-y-4">
          {/* Timeline Section - All Violations */}
          {dailyViolationGroups.length > 0 && (
            <div className="space-y-0">
              {/* Timeline Container */}
              <div className="relative">
                {/* Timeline vertical line - continuous through all items */}
                <div className="absolute left-1.5 top-1.5 bottom-0 w-0.5 bg-gray-200"></div>
                
                {dailyViolationGroups.map((group, groupIndex) => {
                  const violationKey = `daily-${employeeId}-${group.date}`;
                  
                  // Get shift info from first violation
                  const firstViolation = group.violations[0];
                  
                  // Check if this group contains weekly overtime violations
                  const hasWeeklyOvertime = group.violations.some(v => v.rule_id.toLowerCase().includes('weekly'));
                  
                  // Determine the severity and color for this timeline item
                  const violationItems = group.violations.filter(v => {
                    const ruleId = v.rule_id.toLowerCase();
                    return ruleId.includes('meal_break') || ruleId.includes('daily_ot') || ruleId.includes('weekly_ot') || ruleId.includes('double_ot');
                  });
                  const infoItems = group.violations.filter(v => {
                    const ruleId = v.rule_id.toLowerCase();
                    return !ruleId.includes('meal_break') && !ruleId.includes('daily_ot') && !ruleId.includes('weekly_ot') && !ruleId.includes('double_ot');
                  });
                  
                  let displayInfo = '';
                  let displayHours = '';
                  
                  if (hasWeeklyOvertime) {
                    // For weekly overtime, show week period and total weekly hours
                    const weekMatch = firstViolation.specific_details.match(/Week: (\d{2}\/\d{2}\/\d{4}) - (\d{2}\/\d{2}\/\d{4})/);
                    const totalHoursMatch = firstViolation.specific_details.match(/Total Hours: (\d+\.?\d*)/);
                    
                    displayInfo = weekMatch ? `Week: ${weekMatch[1]} - ${weekMatch[2]}` : 'Weekly period';
                    displayHours = totalHoursMatch ? `${parseFloat(totalHoursMatch[1]).toFixed(1)}h total` : 'Total hours N/A';
                  } else {
                    // For daily violations, show shift times and hours as before
                    let shiftHours = 'N/A';
                    
                    if (firstViolation.shift_summary?.total_hours_worked) {
                      shiftHours = firstViolation.shift_summary.total_hours_worked.toFixed(1);
                    } else {
                      // Extract hours from specific_details for daily overtime
                      const hoursMatch = firstViolation.specific_details.match(/Total Hours:\s*(\d+\.?\d*)/i) ||
                                        firstViolation.specific_details.match(/(\d+\.?\d*)\s*hours/i) ||
                                        firstViolation.specific_details.match(/Time-and-a-half Hours:\s*(\d+\.?\d*)/i);
                      if (hoursMatch) {
                        shiftHours = parseFloat(hoursMatch[1]).toFixed(1);
                      }
                    }
                    
                    let shiftTimes = 'Shift data not available';
                    
                    if (firstViolation.shift_summary) {
                      if (firstViolation.shift_summary.clock_in_formatted && firstViolation.shift_summary.clock_out_formatted) {
                        // Use formatted times if available
                        shiftTimes = `${firstViolation.shift_summary.clock_in_formatted} - ${firstViolation.shift_summary.clock_out_formatted}`;
                      } else if (firstViolation.shift_summary.clock_in_time && firstViolation.shift_summary.clock_out_time) {
                        // Use raw times as fallback
                        shiftTimes = `${firstViolation.shift_summary.clock_in_time} - ${firstViolation.shift_summary.clock_out_time}`;
                      } else {
                        // Extract times from specific_details as last resort for daily overtime
                        const timeMatch = firstViolation.specific_details.match(/(\d{1,2}:\d{2})\s*AM\s*-\s*(\d{1,2}:\d{2})\s*PM/i);
                        if (timeMatch) {
                          shiftTimes = `${timeMatch[1]} AM - ${timeMatch[2]} PM`;
                        }
                      }
                    } else {
                      // If no shift summary, try to extract from specific_details
                      const timeMatch = firstViolation.specific_details.match(/(\d{1,2}:\d{2})\s*(AM|PM)\s*-\s*(\d{1,2}:\d{2})\s*(AM|PM)/i);
                      if (timeMatch) {
                        shiftTimes = `${timeMatch[1]} ${timeMatch[2]} - ${timeMatch[3]} ${timeMatch[4]}`;
                      }
                    }
                    
                    displayInfo = shiftTimes;
                    displayHours = `(${shiftHours}h)`;
                  }
                  
                  return (
                    <div key={violationKey} className="relative flex gap-4 pb-6">
                      {/* Timeline dot */}
                      <div className="flex flex-col items-center flex-shrink-0">
                        {/* Timeline dot - consistent light blue */}
                        <div className="w-3 h-3 bg-blue-400 rounded-full border-2 border-white shadow-sm relative z-10 ring-1 ring-blue-200"></div>
                      </div>
                      
                      {/* Timeline content */}
                      <div className="flex-1 min-w-0 -mt-1">
                        {/* Date and shift info */}
                        <div className="flex items-center gap-4 mb-3">
                          <div className="text-sm font-medium text-gray-900">
                            {hasWeeklyOvertime ? 'Weekly' : group.displayDate}
                          </div>
                          <div className="text-sm text-gray-500">
                            {displayInfo} {displayHours}
                          </div>
                          {/* Meal break count - only for daily violations */}
                          {!hasWeeklyOvertime && firstViolation.shift_summary?.meal_break_count !== undefined && (
                            <>
                              <span className="text-gray-300">•</span>
                              <span className="text-gray-500 text-sm">
                                {firstViolation.shift_summary.meal_break_count} meal break{firstViolation.shift_summary.meal_break_count !== 1 ? 's' : ''}
                              </span>
                            </>
                          )}
                          <div className="ml-auto">
                            <ViolationInfoBadges 
                              violationCount={violationItems.length}
                              infoCount={infoItems.length}
                              size="sm"
                              variant="compact"
                            />
                          </div>
                        </div>
                        
                        {/* Violation Cards */}
                        <div className="space-y-3">
                          {group.violations.map((violation, idx) => (
                            <ViolationCard 
                              key={`${violation.rule_id}-${violation.employee_identifier}-${violation.date_of_violation}-${idx}`} 
                              violation={violation} 
                              showEmployee={false}
                              showDate={false}
                              isCompact={true}
                              searchTerm={searchTerm}
                            />
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )
    };
  });

  // Sort accordion items by employee name
  accordionItems.sort((a, b) => a.title.localeCompare(b.title));

  if (violations.length === 0) {
    return (
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 text-center">
        <div className="text-green-600 mb-2">
          <svg className="w-8 h-8 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h3 className="text-lg font-medium text-green-900 mb-1">No Violations Found</h3>
        <p className="text-green-700">All employees appear to be in compliance with labor regulations.</p>
      </div>
    );
  }

  return (
    <div>
      <Accordion 
        items={accordionItems} 
        allowMultiple={true}
        className=""
      />
    </div>
  );
};

export default EmployeeViolationGroup; 