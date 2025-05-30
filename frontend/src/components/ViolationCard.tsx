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
  
  if (lowerRuleId.includes('meal_break') || lowerRuleId.includes('rest_break')) {
    return {
      level: 'Critical',
      cardClass: 'violation-card violation-card-critical',
      badgeClass: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800 border border-red-200',
      iconColor: 'text-red-500',
      dotColor: 'bg-red-500'
    };
  } else if (lowerRuleId.includes('daily_ot') || lowerRuleId.includes('double_ot')) {
    return {
      level: 'Warning',
      cardClass: 'violation-card violation-card-warning',
      badgeClass: 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-orange-100 text-orange-800 border border-orange-200',
      iconColor: 'text-orange-500',
      dotColor: 'bg-orange-500'
    };
  } else {
    return {
      level: 'Info',
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
    const date = new Date(dateString);
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
    <div className={`${severityInfo.cardClass} ${isCompact ? 'p-3' : 'p-4'}`}>
      {/* Compact Header - Always Visible */}
      <div className="flex items-center justify-between">
        <div className="flex items-start gap-3 min-w-0 flex-1">
          {/* Severity badge - with consistent width for alignment */}
          <div className="flex-shrink-0 pt-0.5 w-16">
            <span className={`${severityInfo.badgeClass}`}>
              {severityInfo.level}
            </span>
          </div>
          
          {/* Main content */}
          <div className="min-w-0 flex-1">
            <div className="mb-1">
              <h4 className="text-sm font-medium text-gray-900 leading-tight">
                {renderHighlightedText(violation.rule_description)}
              </h4>
            </div>
            
            {/* Meta information */}
            <div className="flex items-center gap-4 text-xs text-gray-500">
              {showEmployee && (
                <span className="font-medium text-gray-700">
                  {renderHighlightedText(violation.employee_identifier)}
                </span>
              )}
              {showDate && (
                <span>{formatDate(violation.date_of_violation)}</span>
              )}
              <code className="px-1 py-0.5 bg-gray-100 text-gray-600 rounded text-xs">
                {violation.rule_id}
              </code>
            </div>
          </div>
        </div>

        {/* Expand/Collapse Toggle */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="ml-2 p-1.5 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-md transition-colors flex-shrink-0"
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

      {/* Expanded Details */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-gray-100 space-y-4">
          {/* Violation Details */}
          <div>
            <h5 className="text-sm font-medium text-gray-900 mb-2">Details</h5>
            <div className="text-sm text-gray-700 leading-relaxed bg-gray-50 p-3 rounded-md">
              {renderHighlightedText(violation.specific_details)}
            </div>
          </div>

          {/* Recommended Action */}
          <div>
            <h5 className="text-sm font-medium text-gray-900 mb-2 flex items-center gap-1.5">
              <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Recommended Action
            </h5>
            <div className="text-sm text-gray-700 leading-relaxed bg-blue-50 p-3 rounded-md border border-blue-100">
              {renderHighlightedText(violation.suggested_action_generic)}
            </div>
          </div>

          {/* Action Buttons - More compact */}
          <div className="flex items-center gap-2 pt-2">
            <button className="px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 rounded-md transition-colors">
              Mark Resolved
            </button>
            <button className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 rounded-md transition-colors">
              Export
            </button>
            <button className="px-3 py-1.5 text-xs font-medium text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-md transition-colors">
              Create Task
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ViolationCard; 