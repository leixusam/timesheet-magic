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
      badgeClass: 'badge-critical'
    };
  } else if (lowerRuleId.includes('daily_ot') || lowerRuleId.includes('double_ot')) {
    return {
      level: 'Warning',
      cardClass: 'violation-card violation-card-warning',
      badgeClass: 'badge-warning'
    };
  } else {
    return {
      level: 'Info',
      cardClass: 'violation-card violation-card-info',
      badgeClass: 'badge-info'
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
  const [showDetails, setShowDetails] = useState(false);
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

  const shouldShowDetailsToggle = violation.suggested_action_generic.length > 100;

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
    <div className={`${severityInfo.cardClass} ${isCompact ? 'p-4' : 'p-6'}`}>
      {/* Header with Title and Severity */}
      <div className="flex items-start justify-between mb-5">
        <div className="flex-1 mr-4">
          <h4 className="text-lg font-semibold text-gray-900 leading-tight mb-2">
            {renderHighlightedText(violation.rule_description)}
          </h4>
          
          {/* Meta row - more compact and readable */}
          <div className="flex items-center gap-4 text-sm text-gray-600">
            {showEmployee && (
              <div className="flex items-center gap-1.5 font-medium text-gray-900">
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
                {renderHighlightedText(violation.employee_identifier)}
              </div>
            )}
            {showDate && (
              <div className="flex items-center gap-1.5">
                <svg className="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 002 2z" />
                </svg>
                <span className="font-medium">{formatDate(violation.date_of_violation)}</span>
              </div>
            )}
            <div className="flex items-center gap-1.5">
              <span className="text-gray-500">Rule:</span>
              <code className="px-2 py-0.5 bg-gray-100 text-gray-800 rounded text-xs font-mono">
                {renderHighlightedText(violation.rule_id)}
              </code>
            </div>
          </div>
        </div>
        
        {/* Severity badge - prominent position */}
        <span className={`${severityInfo.badgeClass} flex-shrink-0`}>
          {severityInfo.level}
        </span>
      </div>

      {/* Details Section - cleaner layout */}
      <div className="space-y-4">
        {/* Violation Details */}
        <div>
          <h5 className="text-sm font-semibold text-gray-900 mb-2">Details</h5>
          <div className="text-gray-700 leading-relaxed bg-gray-50 p-3 rounded-md">
            {renderHighlightedText(violation.specific_details)}
          </div>
        </div>

        {/* Suggested Action */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <h5 className="text-sm font-semibold text-gray-900 flex items-center gap-2">
              <svg className="w-4 h-4 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
              Recommended Action
            </h5>
            {shouldShowDetailsToggle && (
              <button
                onClick={() => setShowDetails(!showDetails)}
                className="text-sm font-semibold text-blue-700 hover:text-blue-900 hover:underline focus:outline-none focus:underline transition-colors"
              >
                {showDetails ? 'Show Less' : 'Show More'}
              </button>
            )}
          </div>
          <div className="text-gray-700 leading-relaxed bg-blue-50 p-3 rounded-md border border-blue-100">
            {shouldShowDetailsToggle && !showDetails 
              ? renderHighlightedText(`${violation.suggested_action_generic.substring(0, 100)}...`)
              : renderHighlightedText(violation.suggested_action_generic)
            }
          </div>
        </div>
      </div>

      {/* Action Buttons - more prominent and easier to read */}
      <div className="flex items-center justify-end gap-3 mt-5 pt-4 border-t border-gray-200">
        <button className="px-3 py-1.5 text-sm font-semibold text-green-700 bg-green-50 hover:bg-green-100 border border-green-200 hover:border-green-300 rounded-md transition-colors">
          Mark Resolved
        </button>
        <button className="px-3 py-1.5 text-sm font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-blue-200 hover:border-blue-300 rounded-md transition-colors">
          Export
        </button>
        <button className="px-3 py-1.5 text-sm font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 hover:border-purple-300 rounded-md transition-colors">
          Create Task
        </button>
      </div>
    </div>
  );
};

export default ViolationCard; 