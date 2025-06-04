'use client';

import React from 'react';
import { X } from 'lucide-react';
import { SeverityLevel, ViolationType } from '@/hooks/useReportFilters';

interface BaseChipProps {
  label: string;
  isActive: boolean;
  onClick: () => void;
  onRemove?: () => void;
  className?: string;
  variant?: 'default' | 'severity' | 'type' | 'employee' | 'date';
  count?: number;
}

const BaseChip: React.FC<BaseChipProps> = ({
  label,
  isActive,
  onClick,
  onRemove,
  className = "",
  variant = 'default',
  count
}) => {
  const getVariantStyles = () => {
    if (!isActive) {
      return `
        bg-white text-gray-600 border-gray-200
        hover:bg-gray-50 hover:border-gray-300
      `;
    }

    switch (variant) {
      case 'severity':
        if (label === 'Violation') {
          return `
            bg-red-50 text-red-700 border-red-200
            hover:bg-red-100 hover:border-red-300
          `;
        } else if (label === 'Information') {
          return `
            bg-yellow-50 text-yellow-700 border-yellow-200
            hover:bg-yellow-100 hover:border-yellow-300
          `;
        } else {
          return `
            bg-gray-50 text-gray-700 border-gray-200
            hover:bg-gray-100 hover:border-gray-300
          `;
        }
      case 'type':
        return `
          bg-blue-50 text-blue-700 border-blue-200
          hover:bg-blue-100 hover:border-blue-300
        `;
      case 'employee':
        return `
          bg-purple-50 text-purple-700 border-purple-200
          hover:bg-purple-100 hover:border-purple-300
        `;
      case 'date':
        return `
          bg-green-50 text-green-700 border-green-200
          hover:bg-green-100 hover:border-green-300
        `;
      default:
        return `
          bg-blue-50 text-blue-700 border-blue-200
          hover:bg-blue-100 hover:border-blue-300
        `;
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md
        border text-sm font-medium transition-all duration-200
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
        ${getVariantStyles()}
        ${className}
      `}
      aria-pressed={isActive}
    >
      <span>{label}</span>
      {count !== undefined && (
        <span className="text-xs opacity-75">({count})</span>
      )}
      {isActive && onRemove && (
        <X 
          className="h-3 w-3 ml-1 opacity-60 hover:opacity-100 transition-opacity" 
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
        />
      )}
    </button>
  );
};

interface SeverityFilterChipsProps {
  selectedLevels: Set<SeverityLevel>;
  onToggle: (level: SeverityLevel) => void;
  availableCounts?: Record<SeverityLevel, number>;
  className?: string;
}

export const SeverityFilterChips: React.FC<SeverityFilterChipsProps> = ({
  selectedLevels,
  onToggle,
  availableCounts,
  className = ""
}) => {
  const severityLevels: SeverityLevel[] = ['Violation', 'Information'];

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 self-center">
        Severity:
      </span>
      {severityLevels.map((level) => (
        <BaseChip
          key={level}
          label={level}
          isActive={selectedLevels.has(level)}
          onClick={() => onToggle(level)}
          variant="severity"
          count={availableCounts?.[level]}
        />
      ))}
    </div>
  );
};

interface ViolationTypeFilterChipsProps {
  selectedTypes: Set<ViolationType>;
  availableTypes: ViolationType[];
  onToggle: (type: ViolationType) => void;
  availableCounts?: Record<ViolationType, number>;
  className?: string;
}

export const ViolationTypeFilterChips: React.FC<ViolationTypeFilterChipsProps> = ({
  selectedTypes,
  availableTypes,
  onToggle,
  availableCounts,
  className = ""
}) => {
  if (availableTypes.length === 0) return null;

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 self-center">
        Type:
      </span>
      {availableTypes.map((type) => (
        <BaseChip
          key={type}
          label={type}
          isActive={selectedTypes.has(type)}
          onClick={() => onToggle(type)}
          onRemove={selectedTypes.has(type) ? () => onToggle(type) : undefined}
          variant="type"
          count={availableCounts?.[type]}
        />
      ))}
    </div>
  );
};

interface EmployeeFilterChipsProps {
  selectedEmployees: Set<string>;
  onToggle: (employee: string) => void;
  className?: string;
}

export const EmployeeFilterChips: React.FC<EmployeeFilterChipsProps> = ({
  selectedEmployees,
  onToggle,
  className = ""
}) => {
  if (selectedEmployees.size === 0) return null;

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 self-center">
        Employees:
      </span>
      {Array.from(selectedEmployees).map((employee) => (
        <BaseChip
          key={employee}
          label={employee}
          isActive={true}
          onClick={() => onToggle(employee)}
          onRemove={() => onToggle(employee)}
          variant="employee"
        />
      ))}
    </div>
  );
};

interface DateRangeChipProps {
  dateRange: string;
  onClear: () => void;
  className?: string;
}

export const DateRangeChip: React.FC<DateRangeChipProps> = ({
  dateRange,
  onClear,
  className = ""
}) => {
  if (dateRange === 'All') return null;

  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      <span className="text-sm font-medium text-gray-700 dark:text-gray-300 self-center">
        Date:
      </span>
      <BaseChip
        label={dateRange}
        isActive={true}
        onClick={() => {}}
        onRemove={onClear}
        variant="date"
      />
    </div>
  );
};

interface ClearAllFiltersProps {
  activeFilterCount: number;
  onClearAll: () => void;
  className?: string;
}

export const ClearAllFilters: React.FC<ClearAllFiltersProps> = ({
  activeFilterCount,
  onClearAll,
  className = ""
}) => {
  if (activeFilterCount === 0) return null;

  return (
    <button
      type="button"
      onClick={onClearAll}
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md
        text-sm font-medium text-gray-700 hover:text-gray-900
        bg-gray-50 hover:bg-gray-100 border border-gray-200 hover:border-gray-300
        transition-colors duration-200
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
        ${className}
      `}
      aria-label={`Clear all ${activeFilterCount} active filters`}
    >
      <X className="h-3 w-3" />
      Clear All ({activeFilterCount})
    </button>
  );
}; 