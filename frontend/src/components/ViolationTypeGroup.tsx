'use client';

import React from 'react';
import { Accordion, AccordionItemProps } from './ui/Accordion';
import ViolationCard, { ViolationInstance } from './ViolationCard';

export interface ViolationTypeGroupProps {
  violations: ViolationInstance[];
  defaultCollapsed?: boolean;
  searchTerm?: string;
}

const getViolationType = (ruleId: string): string => {
  const lowerRuleId = ruleId.toLowerCase();
  
  if (lowerRuleId.includes('meal_break') || lowerRuleId.includes('meal')) {
    return 'Meal Break Violations';
  } else if (lowerRuleId.includes('rest_break') || lowerRuleId.includes('rest')) {
    return 'Rest Break Violations';
  } else if (lowerRuleId.includes('daily_ot') || lowerRuleId.includes('daily')) {
    return 'Daily Overtime Violations';
  } else if (lowerRuleId.includes('weekly_ot') || lowerRuleId.includes('weekly')) {
    return 'Weekly Overtime Violations';
  } else if (lowerRuleId.includes('double_ot') || lowerRuleId.includes('double')) {
    return 'Double Overtime Violations';
  } else {
    return 'Other Violations';
  }
};

const getTypeIcon = (violationType: string): string => {
  switch (violationType) {
    case 'Meal Break Violations':
      return '🍽️';
    case 'Rest Break Violations':
      return '☕';
    case 'Daily Overtime Violations':
      return '⏰';
    case 'Weekly Overtime Violations':
      return '📅';
    case 'Double Overtime Violations':
      return '⚠️';
    default:
      return '📋';
  }
};

const getTypeVariant = (violationType: string): 'violation' | 'default' => {
  if (violationType.includes('Break')) {
    return 'violation'; // Critical violations get red styling
  }
  return 'default'; // Overtime violations get default styling
};

export const ViolationTypeGroup: React.FC<ViolationTypeGroupProps> = ({
  violations,
  defaultCollapsed = true,
  searchTerm = ''
}) => {
  // Group violations by type
  const violationsByType = violations.reduce((acc, violation) => {
    const violationType = getViolationType(violation.rule_id);
    if (!acc[violationType]) {
      acc[violationType] = [];
    }
    acc[violationType].push(violation);
    return acc;
  }, {} as Record<string, ViolationInstance[]>);

  // Define the order of violation types for consistent display
  const typeOrder = [
    'Meal Break Violations',
    'Rest Break Violations', 
    'Daily Overtime Violations',
    'Weekly Overtime Violations',
    'Double Overtime Violations',
    'Other Violations'
  ];

  // Convert to accordion items in the specified order
  const accordionItems: AccordionItemProps[] = typeOrder
    .filter(type => violationsByType[type] && violationsByType[type].length > 0)
    .map(violationType => {
      const typeViolations = violationsByType[violationType];
      
      // Sort violations by date (newest first) and then by employee
      const sortedViolations = [...typeViolations].sort((a, b) => {
        // BUGFIX: MISC-001 - Handle timezone issues in date parsing
        const parseDate = (dateString: string): Date => {
          if (dateString.includes('T') || dateString.includes('Z')) {
            return new Date(dateString);
          } else {
            const [year, month, day] = dateString.split('-').map(Number);
            return new Date(year, month - 1, day);
          }
        };
        
        const dateA = parseDate(a.date_of_violation);
        const dateB = parseDate(b.date_of_violation);
        const dateDiff = dateB.getTime() - dateA.getTime();
        
        if (dateDiff !== 0) return dateDiff;
        
        // If dates are the same, sort by employee name
        return a.employee_identifier.localeCompare(b.employee_identifier);
      });

      // Get unique employees affected
      const uniqueEmployees = [...new Set(typeViolations.map(v => v.employee_identifier))];

      return {
        id: `type-${violationType.replace(/\s+/g, '-').toLowerCase()}`,
        title: `${getTypeIcon(violationType)} ${violationType}`,
        count: typeViolations.length,
        variant: getTypeVariant(violationType),
        isDefaultOpen: !defaultCollapsed,
        children: (
          <div className="space-y-2">
            {/* Type Summary */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-2">
              <h4 className="text-sm font-medium text-gray-900 mb-2">Summary</h4>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-600">Total Violations:</span>
                  <span className="ml-2 font-medium">{typeViolations.length}</span>
                </div>
                <div>
                  <span className="text-gray-600">Employees Affected:</span>
                  <span className="ml-2 font-medium">{uniqueEmployees.length}</span>
                </div>
              </div>
              
              {uniqueEmployees.length > 0 && (
                <div className="mt-2">
                  <span className="text-gray-600 text-xs">Affected employees:</span>
                  <div className="mt-1 flex flex-wrap gap-1">
                    {uniqueEmployees.map(employee => (
                      <span 
                        key={employee}
                        className="inline-flex items-center px-2 py-1 rounded text-xs bg-blue-100 text-blue-800"
                      >
                        {employee}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Violation Cards */}
            {sortedViolations.map((violation, index) => (
              <ViolationCard
                key={`${violation.rule_id}-${violation.employee_identifier}-${violation.date_of_violation}-${index}`}
                violation={violation}
                showEmployee={true}
                showDate={true}
                isCompact={true}
                searchTerm={searchTerm}
              />
            ))}
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
        <p className="text-green-700">All timesheet entries appear to be in compliance with labor regulations.</p>
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

export default ViolationTypeGroup; 