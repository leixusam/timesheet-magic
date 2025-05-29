'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Calendar, ChevronDown } from 'lucide-react';
import { DateRange } from '@/hooks/useReportFilters';

interface DateRangeFilterProps {
  selectedRange: DateRange;
  customStart?: Date;
  customEnd?: Date;
  onRangeChange: (range: DateRange, customStart?: Date, customEnd?: Date) => void;
  className?: string;
}

const DATE_RANGE_OPTIONS: { value: DateRange; label: string }[] = [
  { value: 'All', label: 'All Dates' },
  { value: 'Today', label: 'Today' },
  { value: 'This Week', label: 'This Week' },
  { value: 'This Month', label: 'This Month' },
  { value: 'Custom', label: 'Custom Range' },
];

export const DateRangeFilter: React.FC<DateRangeFilterProps> = ({
  selectedRange,
  customStart,
  customEnd,
  onRangeChange,
  className = ""
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [showCustomInputs, setShowCustomInputs] = useState(false);
  const [tempCustomStart, setTempCustomStart] = useState<string>(
    customStart ? customStart.toISOString().split('T')[0] : ''
  );
  const [tempCustomEnd, setTempCustomEnd] = useState<string>(
    customEnd ? customEnd.toISOString().split('T')[0] : ''
  );
  
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
        setShowCustomInputs(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleRangeSelect = (range: DateRange) => {
    if (range === 'Custom') {
      setShowCustomInputs(true);
      return;
    }
    
    onRangeChange(range);
    setIsOpen(false);
    setShowCustomInputs(false);
  };

  const handleCustomRangeApply = () => {
    if (tempCustomStart && tempCustomEnd) {
      const startDate = new Date(tempCustomStart);
      const endDate = new Date(tempCustomEnd);
      
      if (startDate <= endDate) {
        onRangeChange('Custom', startDate, endDate);
        setIsOpen(false);
        setShowCustomInputs(false);
      }
    }
  };

  const getDisplayLabel = () => {
    if (selectedRange === 'Custom' && customStart && customEnd) {
      const startStr = customStart.toLocaleDateString();
      const endStr = customEnd.toLocaleDateString();
      return `${startStr} - ${endStr}`;
    }
    
    return DATE_RANGE_OPTIONS.find(option => option.value === selectedRange)?.label || 'All Dates';
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="
          inline-flex items-center gap-2 px-3 py-2 
          bg-gray-50 border border-gray-200 rounded-md shadow-sm
          text-sm font-medium text-gray-700 hover:bg-gray-100
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          transition-colors duration-200
        "
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <Calendar className="h-4 w-4" />
        <span className="truncate max-w-40">{getDisplayLabel()}</span>
        <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="
          absolute top-full left-0 mt-1 w-72 z-50
          bg-white border border-gray-200 rounded-lg shadow-lg
          dark:bg-gray-800 dark:border-gray-600
        ">
          <div className="py-1">
            {DATE_RANGE_OPTIONS.map((option) => (
              <button
                key={option.value}
                type="button"
                onClick={() => handleRangeSelect(option.value)}
                className={`
                  w-full text-left px-4 py-2 text-sm
                  hover:bg-gray-100 dark:hover:bg-gray-700
                  transition-colors duration-150
                  ${selectedRange === option.value 
                    ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300' 
                    : 'text-gray-700 dark:text-gray-300'
                  }
                `}
                role="option"
                aria-selected={selectedRange === option.value}
              >
                {option.label}
              </button>
            ))}
          </div>

          {showCustomInputs && (
            <div className="border-t border-gray-200 dark:border-gray-600 p-4">
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Start Date
                  </label>
                  <input
                    type="date"
                    value={tempCustomStart}
                    onChange={(e) => setTempCustomStart(e.target.value)}
                    className="
                      w-full px-3 py-1.5 text-sm border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                      dark:bg-gray-700 dark:border-gray-600 dark:text-gray-300
                      dark:focus:ring-blue-400 dark:focus:border-blue-400
                    "
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                    End Date
                  </label>
                  <input
                    type="date"
                    value={tempCustomEnd}
                    onChange={(e) => setTempCustomEnd(e.target.value)}
                    min={tempCustomStart}
                    className="
                      w-full px-3 py-1.5 text-sm border border-gray-300 rounded
                      focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                      dark:bg-gray-700 dark:border-gray-600 dark:text-gray-300
                      dark:focus:ring-blue-400 dark:focus:border-blue-400
                    "
                  />
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={handleCustomRangeApply}
                    disabled={!tempCustomStart || !tempCustomEnd}
                    className="
                      flex-1 px-3 py-1.5 text-sm font-medium text-white
                      bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400
                      rounded focus:outline-none focus:ring-2 focus:ring-blue-500
                      transition-colors duration-200
                    "
                  >
                    Apply
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowCustomInputs(false)}
                    className="
                      flex-1 px-3 py-1.5 text-sm font-medium text-gray-700
                      bg-gray-100 hover:bg-gray-200 dark:bg-gray-600 dark:text-gray-300
                      dark:hover:bg-gray-500 rounded focus:outline-none focus:ring-2 focus:ring-gray-500
                      transition-colors duration-200
                    "
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}; 