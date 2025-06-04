'use client';

import React from 'react';
import { Accordion, AccordionItemProps } from './ui/Accordion';
import ViolationCard, { ViolationInstance } from './ViolationCard';

export interface DailyViolationGroupProps {
  violations: ViolationInstance[];
  defaultCollapsed?: boolean;
  searchTerm?: string;
}

interface DailyViolationGroup {
  employee: string;
  date: string;
  displayDate: string;
  violations: ViolationInstance[];
  mealBreakViolations: ViolationInstance[];
  overtimeViolations: ViolationInstance[];
}

// Helper function to get work date (considering midnight-crossing shifts)
// For now, we use the violation date as-is, but this could be enhanced
// to group by shift start date if needed
const getWorkDate = (violation: ViolationInstance): string => {
  return violation.date_of_violation;
};

// Format date for display
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
    
    return date.toLocaleDateString('en-US', { 
      weekday: 'short', 
      month: 'short', 
      day: 'numeric' 
    });
  } catch {
    return dateString;
  }
};

// Calculate estimated payroll correction for a day
const calculateDailyCorrection = (violations: ViolationInstance[], baseWage: number = 18.00): number => {
  let total = 0;
  
  violations.forEach(violation => {
    const ruleId = violation.rule_id.toLowerCase();
    
    // Meal break violations = 1 hour penalty each
    if (ruleId.includes('meal_break')) {
      total += baseWage;
    }
    
    // Overtime violations - extract hours from violation details
    if (ruleId.includes('daily_ot') || ruleId.includes('weekly_ot')) {
      // Try to extract overtime hours from violation details
      const details = violation.specific_details;
      const hoursMatch = details.match(/(\d+\.?\d*)\s*hours?/i);
      const overtimeMatch = details.match(/overtime.*?(\d+\.?\d*)\s*hours?/i);
      
      if (overtimeMatch) {
        const overtimeHours = parseFloat(overtimeMatch[1]);
        if (ruleId.includes('double')) {
          total += overtimeHours * baseWage; // Double time premium
        } else {
          total += overtimeHours * (baseWage * 0.5); // Time-and-a-half premium
        }
      }
    }
  });
  
  return total;
};

export const DailyViolationGroup: React.FC<DailyViolationGroupProps> = ({
  violations,
  defaultCollapsed = true,
  searchTerm = ''
}) => {
  // Group violations by employee and work date
  const dailyGroups: DailyViolationGroup[] = React.useMemo(() => {
    const groupMap = new Map<string, DailyViolationGroup>();
    
    violations.forEach(violation => {
      const workDate = getWorkDate(violation);
      const key = `${violation.employee_identifier}|${workDate}`;
      
      if (!groupMap.has(key)) {
        groupMap.set(key, {
          employee: violation.employee_identifier,
          date: workDate,
          displayDate: formatDisplayDate(workDate),
          violations: [],
          mealBreakViolations: [],
          overtimeViolations: []
        });
      }
      
      const group = groupMap.get(key)!;
      group.violations.push(violation);
      
      const ruleId = violation.rule_id.toLowerCase();
      if (ruleId.includes('meal_break')) {
        group.mealBreakViolations.push(violation);
      } else if (ruleId.includes('daily_ot') || ruleId.includes('weekly_ot') || ruleId.includes('double_ot')) {
        group.overtimeViolations.push(violation);
      }
    });
    
    return Array.from(groupMap.values()).sort((a, b) => {
      // Sort by employee name, then by date (newest first)
      if (a.employee !== b.employee) {
        return a.employee.localeCompare(b.employee);
      }
      
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
  }, [violations]);

  // Convert to accordion items
  const accordionItems: AccordionItemProps[] = dailyGroups.map((group) => {
    const estimatedCorrection = calculateDailyCorrection(group.violations);
    
    // Create summary of issues
    const issueSummary = [];
    if (group.overtimeViolations.length > 0) {
      issueSummary.push(`${group.overtimeViolations.length} overtime issue${group.overtimeViolations.length !== 1 ? 's' : ''}`);
    }
    if (group.mealBreakViolations.length > 0) {
      issueSummary.push(`${group.mealBreakViolations.length} meal break issue${group.mealBreakViolations.length !== 1 ? 's' : ''}`);
    }
    
    const getSeverityIcon = () => {
      if (group.mealBreakViolations.length > 0 && group.overtimeViolations.length > 0) return '🔴';
      if (group.mealBreakViolations.length > 0 || group.overtimeViolations.length > 0) return '🔴';
      return '🟡';
    };

    return {
      id: `daily-${group.employee}-${group.date}`,
      title: `${getSeverityIcon()} ${group.employee} - ${group.displayDate}`,
      count: group.violations.length,
      variant: 'violation' as const,
      isDefaultOpen: !defaultCollapsed,
      children: (
        <div className="space-y-4">
          {/* Daily Summary */}
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex items-start justify-between">
              <div>
                <h4 className="text-sm font-semibold text-red-800 mb-2">Daily Compliance Issues</h4>
                <div className="space-y-1">
                  {group.overtimeViolations.length > 0 && (
                    <div className="text-sm text-red-700">
                      • Overtime: {group.overtimeViolations.map(v => {
                        const match = v.specific_details.match(/(\d+\.?\d*)\s*hours/i);
                        return match ? `${match[1]} hours` : 'overtime detected';
                      }).join(', ')}
                    </div>
                  )}
                  {group.mealBreakViolations.length > 0 && (
                    <div className="text-sm text-red-700">
                      • Meal breaks: {group.mealBreakViolations.length} violation{group.mealBreakViolations.length !== 1 ? 's' : ''}
                    </div>
                  )}
                </div>
              </div>
              {estimatedCorrection > 0 && (
                <div className="text-right">
                  <div className="text-xs font-medium text-red-600 uppercase tracking-wide">Est. Correction</div>
                  <div className="text-lg font-bold text-red-800">${estimatedCorrection.toFixed(2)}</div>
                </div>
              )}
            </div>
          </div>

          {/* Detailed Violation Cards */}
          <div className="space-y-2">
            <h5 className="text-xs font-medium text-gray-500 uppercase tracking-wide">Detailed Violations</h5>
            {group.violations.map((violation, index) => (
              <ViolationCard
                key={`${violation.rule_id}-${violation.date_of_violation}-${index}`}
                violation={violation}
                showEmployee={false} // Don't show employee name since it's in the group header
                showDate={false} // Don't show date since it's in the group header
                isCompact={true}
                searchTerm={searchTerm}
              />
            ))}
          </div>
        </div>
      )
    };
  });

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

export default DailyViolationGroup; 