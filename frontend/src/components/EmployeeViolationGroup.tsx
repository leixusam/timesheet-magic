'use client';

import React from 'react';
import { Accordion, AccordionItemProps } from './ui/Accordion';
import ViolationCard, { ViolationInstance } from './ViolationCard';

export interface EmployeeViolationGroupProps {
  violations: ViolationInstance[];
  defaultCollapsed?: boolean;
  searchTerm?: string;
}

export const EmployeeViolationGroup: React.FC<EmployeeViolationGroupProps> = ({
  violations,
  defaultCollapsed = true,
  searchTerm = ''
}) => {
  // Group violations by employee
  const violationsByEmployee = violations.reduce((acc, violation) => {
    const employeeId = violation.employee_identifier;
    if (!acc[employeeId]) {
      acc[employeeId] = [];
    }
    acc[employeeId].push(violation);
    return acc;
  }, {} as Record<string, ViolationInstance[]>);

  // Convert to accordion items
  const accordionItems: AccordionItemProps[] = Object.entries(violationsByEmployee).map(([employeeId, employeeViolations]) => {
    // Sort violations by date (newest first) and severity
    const sortedViolations = [...employeeViolations].sort((a, b) => {
      const dateA = new Date(a.date_of_violation);
      const dateB = new Date(b.date_of_violation);
      return dateB.getTime() - dateA.getTime();
    });

    // Calculate severity summary
    const criticalCount = employeeViolations.filter(v => 
      v.rule_id.toLowerCase().includes('meal_break') || 
      v.rule_id.toLowerCase().includes('rest_break')
    ).length;
    
    const warningCount = employeeViolations.filter(v => 
      v.rule_id.toLowerCase().includes('daily_ot') || 
      v.rule_id.toLowerCase().includes('double_ot')
    ).length;

    const getSeverityBadge = () => {
      if (criticalCount > 0) return '🔴';
      if (warningCount > 0) return '🟡';
      return '🔵';
    };

    return {
      id: `employee-${employeeId}`,
      title: `${getSeverityBadge()} ${employeeId}`,
      count: employeeViolations.length,
      variant: 'employee' as const,
      isDefaultOpen: !defaultCollapsed,
      children: (
        <div className="space-y-3">
          {/* Severity Summary */}
          {(criticalCount > 0 || warningCount > 0) && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
              <h4 className="text-sm font-medium text-blue-900 mb-2">Violation Summary</h4>
              <div className="flex items-center space-x-4 text-sm">
                {criticalCount > 0 && (
                  <span className="text-red-700">
                    <span className="font-medium">{criticalCount}</span> Critical (Break violations)
                  </span>
                )}
                {warningCount > 0 && (
                  <span className="text-orange-700">
                    <span className="font-medium">{warningCount}</span> Warning (Overtime)
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Violation Cards */}
          {sortedViolations.map((violation, index) => (
            <ViolationCard
              key={`${violation.rule_id}-${violation.date_of_violation}-${index}`}
              violation={violation}
              showEmployee={false} // Don't show employee name since it's already in the group header
              showDate={true}
              isCompact={false}
              searchTerm={searchTerm}
            />
          ))}
        </div>
      )
    };
  });

  // Sort employees by violation count (highest first)
  const sortedAccordionItems = accordionItems.sort((a, b) => {
    return (b.count || 0) - (a.count || 0);
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
        items={sortedAccordionItems} 
        allowMultiple={true}
        className=""
      />
    </div>
  );
};

export default EmployeeViolationGroup; 