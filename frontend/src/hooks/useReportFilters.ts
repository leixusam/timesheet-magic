'use client';

import { useState, useMemo, useCallback } from 'react';
import { ViolationInstance } from '@/components/ViolationCard';

export type SeverityLevel = 'Critical' | 'Warning' | 'Info';
export type ViolationType = 'Meal Break' | 'Rest Break' | 'Daily Overtime' | 'Weekly Overtime' | 'Double Overtime' | 'Other';
export type DateRange = 'All' | 'Today' | 'This Week' | 'This Month' | 'Custom';

export interface FilterState {
  searchText: string;
  severityLevels: Set<SeverityLevel>;
  violationTypes: Set<ViolationType>;
  selectedEmployees: Set<string>;
  dateRange: DateRange;
  customDateStart?: Date;
  customDateEnd?: Date;
}

export interface FilteredResults {
  violations: ViolationInstance[];
  totalCount: number;
  filteredCount: number;
  activeFilterCount: number;
}

const getSeverityLevel = (ruleId: string): SeverityLevel => {
  const lowerRuleId = ruleId.toLowerCase();
  if (lowerRuleId.includes('meal_break') || lowerRuleId.includes('rest_break')) {
    return 'Critical';
  } else if (lowerRuleId.includes('daily_ot') || lowerRuleId.includes('double_ot')) {
    return 'Warning';
  } else {
    return 'Info';
  }
};

const getViolationType = (ruleId: string): ViolationType => {
  const lowerRuleId = ruleId.toLowerCase();
  
  if (lowerRuleId.includes('meal_break') || lowerRuleId.includes('meal')) {
    return 'Meal Break';
  } else if (lowerRuleId.includes('rest_break') || lowerRuleId.includes('rest')) {
    return 'Rest Break';
  } else if (lowerRuleId.includes('daily_ot') || lowerRuleId.includes('daily')) {
    return 'Daily Overtime';
  } else if (lowerRuleId.includes('weekly_ot') || lowerRuleId.includes('weekly')) {
    return 'Weekly Overtime';
  } else if (lowerRuleId.includes('double_ot') || lowerRuleId.includes('double')) {
    return 'Double Overtime';
  } else {
    return 'Other';
  }
};

const isWithinDateRange = (violationDate: string, dateRange: DateRange, customStart?: Date, customEnd?: Date): boolean => {
  const vDate = new Date(violationDate);
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  switch (dateRange) {
    case 'All':
      return true;
    
    case 'Today':
      const todayEnd = new Date(today);
      todayEnd.setHours(23, 59, 59, 999);
      return vDate >= today && vDate <= todayEnd;
    
    case 'This Week':
      const weekStart = new Date(today);
      weekStart.setDate(today.getDate() - today.getDay()); // Start of week (Sunday)
      const weekEnd = new Date(weekStart);
      weekEnd.setDate(weekStart.getDate() + 6);
      weekEnd.setHours(23, 59, 59, 999);
      return vDate >= weekStart && vDate <= weekEnd;
    
    case 'This Month':
      const monthStart = new Date(today.getFullYear(), today.getMonth(), 1);
      const monthEnd = new Date(today.getFullYear(), today.getMonth() + 1, 0);
      monthEnd.setHours(23, 59, 59, 999);
      return vDate >= monthStart && vDate <= monthEnd;
    
    case 'Custom':
      if (!customStart || !customEnd) return true;
      const customStartDate = new Date(customStart);
      customStartDate.setHours(0, 0, 0, 0);
      const customEndDate = new Date(customEnd);
      customEndDate.setHours(23, 59, 59, 999);
      return vDate >= customStartDate && vDate <= customEndDate;
    
    default:
      return true;
  }
};

export const useReportFilters = (violations: ViolationInstance[]) => {
  const [filters, setFilters] = useState<FilterState>({
    searchText: '',
    severityLevels: new Set<SeverityLevel>(['Critical', 'Warning', 'Info']),
    violationTypes: new Set<ViolationType>(),
    selectedEmployees: new Set<string>(),
    dateRange: 'All',
  });

  // Get available options for filters
  const availableOptions = useMemo(() => {
    const employees = [...new Set(violations.map(v => v.employee_identifier))].sort();
    const violationTypes = [...new Set(violations.map(v => getViolationType(v.rule_id)))].sort();
    const severityLevels: SeverityLevel[] = ['Critical', 'Warning', 'Info'];
    
    return {
      employees,
      violationTypes,
      severityLevels
    };
  }, [violations]);

  // Filter violations based on current filter state
  const filteredResults = useMemo((): FilteredResults => {
    let filtered = violations;

    // Text search filter
    if (filters.searchText.trim()) {
      const searchLower = filters.searchText.toLowerCase();
      filtered = filtered.filter(violation => 
        violation.rule_description.toLowerCase().includes(searchLower) ||
        violation.employee_identifier.toLowerCase().includes(searchLower) ||
        violation.specific_details.toLowerCase().includes(searchLower) ||
        violation.suggested_action_generic.toLowerCase().includes(searchLower) ||
        violation.rule_id.toLowerCase().includes(searchLower)
      );
    }

    // Severity level filter
    if (filters.severityLevels.size > 0 && filters.severityLevels.size < 3) {
      filtered = filtered.filter(violation => 
        filters.severityLevels.has(getSeverityLevel(violation.rule_id))
      );
    }

    // Violation type filter
    if (filters.violationTypes.size > 0) {
      filtered = filtered.filter(violation => 
        filters.violationTypes.has(getViolationType(violation.rule_id))
      );
    }

    // Employee filter
    if (filters.selectedEmployees.size > 0) {
      filtered = filtered.filter(violation => 
        filters.selectedEmployees.has(violation.employee_identifier)
      );
    }

    // Date range filter
    if (filters.dateRange !== 'All') {
      filtered = filtered.filter(violation => 
        isWithinDateRange(
          violation.date_of_violation, 
          filters.dateRange, 
          filters.customDateStart, 
          filters.customDateEnd
        )
      );
    }

    // Calculate active filter count
    let activeFilterCount = 0;
    if (filters.searchText.trim()) activeFilterCount++;
    if (filters.severityLevels.size < 3) activeFilterCount++;
    if (filters.violationTypes.size > 0) activeFilterCount++;
    if (filters.selectedEmployees.size > 0) activeFilterCount++;
    if (filters.dateRange !== 'All') activeFilterCount++;

    return {
      violations: filtered,
      totalCount: violations.length,
      filteredCount: filtered.length,
      activeFilterCount
    };
  }, [violations, filters]);

  // Filter update functions
  const updateSearchText = useCallback((text: string) => {
    setFilters(prev => ({ ...prev, searchText: text }));
  }, []);

  const toggleSeverityLevel = useCallback((level: SeverityLevel) => {
    setFilters(prev => {
      const newLevels = new Set(prev.severityLevels);
      if (newLevels.has(level)) {
        newLevels.delete(level);
      } else {
        newLevels.add(level);
      }
      return { ...prev, severityLevels: newLevels };
    });
  }, []);

  const toggleViolationType = useCallback((type: ViolationType) => {
    setFilters(prev => {
      const newTypes = new Set(prev.violationTypes);
      if (newTypes.has(type)) {
        newTypes.delete(type);
      } else {
        newTypes.add(type);
      }
      return { ...prev, violationTypes: newTypes };
    });
  }, []);

  const toggleEmployee = useCallback((employee: string) => {
    setFilters(prev => {
      const newEmployees = new Set(prev.selectedEmployees);
      if (newEmployees.has(employee)) {
        newEmployees.delete(employee);
      } else {
        newEmployees.add(employee);
      }
      return { ...prev, selectedEmployees: newEmployees };
    });
  }, []);

  const setDateRange = useCallback((range: DateRange, customStart?: Date, customEnd?: Date) => {
    setFilters(prev => ({ 
      ...prev, 
      dateRange: range,
      customDateStart: customStart,
      customDateEnd: customEnd
    }));
  }, []);

  const clearAllFilters = useCallback(() => {
    setFilters({
      searchText: '',
      severityLevels: new Set<SeverityLevel>(['Critical', 'Warning', 'Info']),
      violationTypes: new Set<ViolationType>(),
      selectedEmployees: new Set<string>(),
      dateRange: 'All',
      customDateStart: undefined,
      customDateEnd: undefined,
    });
  }, []);

  const clearSpecificFilter = useCallback((filterType: 'search' | 'severity' | 'type' | 'employee' | 'date') => {
    setFilters(prev => {
      switch (filterType) {
        case 'search':
          return { ...prev, searchText: '' };
        case 'severity':
          return { ...prev, severityLevels: new Set(['Critical', 'Warning', 'Info']) };
        case 'type':
          return { ...prev, violationTypes: new Set() };
        case 'employee':
          return { ...prev, selectedEmployees: new Set() };
        case 'date':
          return { ...prev, dateRange: 'All', customDateStart: undefined, customDateEnd: undefined };
        default:
          return prev;
      }
    });
  }, []);

  return {
    filters,
    filteredResults,
    availableOptions,
    updateSearchText,
    toggleSeverityLevel,
    toggleViolationType,
    toggleEmployee,
    setDateRange,
    clearAllFilters,
    clearSpecificFilter,
  };
}; 