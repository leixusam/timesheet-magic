'use client';

import React from 'react';
import { Filter, X } from 'lucide-react';
import { SearchBox } from './SearchBox';
import { SeverityFilterChips, ViolationTypeFilterChips, EmployeeFilterChips, DateRangeChip, ClearAllFilters } from './FilterChips';
import { DateRangeFilter } from './DateRangeFilter';
import { EmployeeFilter } from './EmployeeFilter';
import { useReportFilters, FilteredResults } from '@/hooks/useReportFilters';

interface FilterPanelProps {
  filteredResults: FilteredResults;
  filterHook: ReturnType<typeof useReportFilters>;
  className?: string;
  showResultCount?: boolean;
  isCollapsible?: boolean;
  contextInfo?: string; // e.g., "3 employees with violations" or "4 violation types detected"
}

export const FilterPanel: React.FC<FilterPanelProps> = ({
  filteredResults,
  filterHook,
  className = "",
  showResultCount = true,
  isCollapsible = false,
  contextInfo
}) => {
  const {
    filters,
    availableOptions,
    updateSearchText,
    toggleSeverityLevel,
    toggleViolationType,
    toggleEmployee,
    setDateRange,
    clearAllFilters,
    clearSpecificFilter,
  } = filterHook;

  const [isExpanded, setIsExpanded] = React.useState(!isCollapsible);

  const hasActiveFilters = filteredResults.activeFilterCount > 0;

  return (
    <div className={`bg-white border border-gray-200 rounded-lg shadow-sm ${className}`}>
      {/* Header - Make entire area clickable when collapsible */}
      <div 
        className={`flex items-center justify-between ${isCollapsible ? 'p-3 border-b border-gray-200' : 'p-4'}`}
      >
        <button
          type="button"
          onClick={isCollapsible ? () => setIsExpanded(!isExpanded) : undefined}
          className={`flex items-center justify-between w-full ${isCollapsible ? 'cursor-pointer hover:bg-gray-50 -m-3 p-3 rounded-t-lg transition-colors' : ''}`}
          disabled={!isCollapsible}
        >
          {/* Left side - Filter icon and active filters */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <Filter className="h-4 w-4 text-gray-500" />
              <h3 className="text-sm font-medium text-gray-900">
                Filters
              </h3>
            </div>
            
            {hasActiveFilters && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                {filteredResults.activeFilterCount} active
              </span>
            )}

            {/* Show active filter pills in collapsed state */}
            {isCollapsible && !isExpanded && hasActiveFilters && (
              <div className="flex flex-wrap gap-1.5 ml-2">
                {/* Search Term Chip */}
                {filters.searchText.trim() && (
                  <div className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700">
                    <span>"{filters.searchText.length > 15 ? filters.searchText.substring(0, 15) + '...' : filters.searchText}"</span>
                  </div>
                )}

                {/* Selected Employee Chips */}
                {filters.selectedEmployees.size > 0 && (
                  <div className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-purple-100 text-purple-800">
                    {filters.selectedEmployees.size === 1 
                      ? Array.from(filters.selectedEmployees)[0]
                      : `${filters.selectedEmployees.size} employees`
                    }
                  </div>
                )}

                {/* Date Range Chip */}
                {filters.dateRange !== 'All' && (
                  <div className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-green-100 text-green-800">
                    {filters.dateRange === 'Custom' && filters.customDateStart && filters.customDateEnd
                      ? `${filters.customDateStart.toLocaleDateString().split('/').slice(0,2).join('/')} - ${filters.customDateEnd.toLocaleDateString().split('/').slice(0,2).join('/')}`
                      : filters.dateRange
                    }
                  </div>
                )}

                {/* Severity Level Chips (only if not all selected) */}
                {filters.severityLevels.size < 3 && filters.severityLevels.size > 0 && (
                  <div className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-orange-100 text-orange-800">
                    {Array.from(filters.severityLevels).join(', ')}
                  </div>
                )}

                {/* Violation Type Chips */}
                {filters.violationTypes.size > 0 && (
                  <div className="inline-flex items-center px-2 py-0.5 rounded text-xs bg-blue-100 text-blue-800">
                    {filters.violationTypes.size === 1 
                      ? Array.from(filters.violationTypes)[0]
                      : `${filters.violationTypes.size} types`
                    }
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right side - Context info, violation count, and expand/collapse */}
          <div className="flex items-center gap-3">
            {/* Context info and violation count together */}
            <div className="text-sm text-gray-600">
              {contextInfo && showResultCount ? (
                <span>
                  {contextInfo} • {filteredResults.filteredCount === filteredResults.totalCount
                    ? `${filteredResults.totalCount} violations`
                    : `${filteredResults.filteredCount} of ${filteredResults.totalCount} violations`
                  }
                </span>
              ) : contextInfo ? (
                <span>{contextInfo}</span>
              ) : showResultCount ? (
                <span>
                  {filteredResults.filteredCount === filteredResults.totalCount
                    ? `${filteredResults.totalCount} violations`
                    : `${filteredResults.filteredCount} of ${filteredResults.totalCount} violations`
                  }
                </span>
              ) : null}
              
              {/* Show result count in collapsed state */}
              {isCollapsible && !isExpanded && !showResultCount && (
                <span>
                  {filteredResults.filteredCount === filteredResults.totalCount
                    ? `${filteredResults.totalCount} violations`
                    : `${filteredResults.filteredCount} of ${filteredResults.totalCount}`
                  }
                </span>
              )}
            </div>
            
            {isCollapsible && (
              <div
                className="text-gray-400 hover:text-gray-600 transition-colors p-1"
                aria-label={isExpanded ? 'Collapse filters' : 'Expand filters'}
              >
                <svg className={`h-4 w-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </div>
            )}
          </div>
        </button>
      </div>

      {/* Filter Content */}
      {(!isCollapsible || isExpanded) && (
        <div className="p-4 space-y-4">
          {/* Search Box */}
          <div>
            <SearchBox
              value={filters.searchText}
              onChange={updateSearchText}
              placeholder="Search violations, employees, or details..."
              className="w-full"
            />
          </div>

          {/* Primary Filters Row */}
          <div className="flex flex-wrap gap-3">
            <DateRangeFilter
              selectedRange={filters.dateRange}
              customStart={filters.customDateStart}
              customEnd={filters.customDateEnd}
              onRangeChange={setDateRange}
            />
            
            <EmployeeFilter
              availableEmployees={availableOptions.employees}
              selectedEmployees={filters.selectedEmployees}
              onToggleEmployee={toggleEmployee}
              onClearAll={() => clearSpecificFilter('employee')}
            />
          </div>

          {/* Filter Chips */}
          <div className="space-y-3">
            {/* Severity Level Chips */}
            <SeverityFilterChips
              selectedLevels={filters.severityLevels}
              onToggle={toggleSeverityLevel}
            />

            {/* Violation Type Chips */}
            {availableOptions.violationTypes.length > 0 && (
              <ViolationTypeFilterChips
                selectedTypes={filters.violationTypes}
                availableTypes={availableOptions.violationTypes}
                onToggle={toggleViolationType}
              />
            )}
          </div>

          {/* Active Filter Chips */}
          {hasActiveFilters && (
            <div className="pt-3 border-t border-gray-200">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-medium text-gray-700">
                  Active Filters:
                </span>
                <ClearAllFilters
                  activeFilterCount={filteredResults.activeFilterCount}
                  onClearAll={clearAllFilters}
                />
              </div>
              
              <div className="flex flex-wrap gap-2">
                {/* Search Term Chip */}
                {filters.searchText.trim() && (
                  <div className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs bg-gray-100 text-gray-700">
                    <span>Search: "{filters.searchText}"</span>
                    <button
                      type="button"
                      onClick={() => clearSpecificFilter('search')}
                      className="text-gray-400 hover:text-gray-600"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                )}

                {/* Selected Employee Chips */}
                <EmployeeFilterChips
                  selectedEmployees={filters.selectedEmployees}
                  onToggle={toggleEmployee}
                />

                {/* Date Range Chip */}
                <DateRangeChip
                  dateRange={filters.dateRange}
                  onClear={() => clearSpecificFilter('date')}
                />

                {/* Severity Level Chips */}
                {filters.severityLevels.size > 0 && filters.severityLevels.size < 3 && (
                  Array.from(filters.severityLevels).map(level => (
                    <div key={level} className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs bg-red-100 text-red-700 border border-red-200">
                      <span>Severity: {level}</span>
                      <button
                        type="button"
                        onClick={() => toggleSeverityLevel(level)}
                        className="text-red-400 hover:text-red-600"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))
                )}

                {/* Violation Type Chips */}
                {filters.violationTypes.size > 0 && (
                  Array.from(filters.violationTypes).map(type => (
                    <div key={type} className="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs bg-blue-100 text-blue-700 border border-blue-200">
                      <span>Type: {type}</span>
                      <button
                        type="button"
                        onClick={() => toggleViolationType(type)}
                        className="text-blue-400 hover:text-blue-600"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}

          {/* No Results Message */}
          {filteredResults.filteredCount === 0 && hasActiveFilters && (
            <div className="text-center py-6">
              <div className="text-gray-400 mb-2">
                <Filter className="h-8 w-8 mx-auto opacity-50" />
              </div>
              <p className="text-sm text-gray-600 mb-2">
                No violations match your current filters
              </p>
              <button
                type="button"
                onClick={clearAllFilters}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium"
              >
                Clear all filters
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}; 