'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { Users, ChevronDown, Search, X, Check } from 'lucide-react';

interface EmployeeFilterProps {
  availableEmployees: string[];
  selectedEmployees: Set<string>;
  onToggleEmployee: (employee: string) => void;
  onClearAll?: () => void;
  className?: string;
}

export const EmployeeFilter: React.FC<EmployeeFilterProps> = ({
  availableEmployees,
  selectedEmployees,
  onToggleEmployee,
  onClearAll,
  className = ""
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const filteredEmployees = useMemo(() => {
    if (!searchText.trim()) return availableEmployees;
    
    const searchLower = searchText.toLowerCase();
    return availableEmployees.filter(employee => 
      employee.toLowerCase().includes(searchLower)
    );
  }, [availableEmployees, searchText]);

  const handleSelectAll = () => {
    if (selectedEmployees.size === availableEmployees.length) {
      // If all are selected, clear all
      if (onClearAll) {
        onClearAll();
      } else {
        availableEmployees.forEach(employee => {
          if (selectedEmployees.has(employee)) {
            onToggleEmployee(employee);
          }
        });
      }
    } else {
      // Select all visible filtered employees
      filteredEmployees.forEach(employee => {
        if (!selectedEmployees.has(employee)) {
          onToggleEmployee(employee);
        }
      });
    }
  };

  const getButtonText = () => {
    const count = selectedEmployees.size;
    if (count === 0) return 'All Employees';
    if (count === 1) return Array.from(selectedEmployees)[0];
    return `${count} employees selected`;
  };

  const allFilteredSelected = filteredEmployees.length > 0 && 
    filteredEmployees.every(employee => selectedEmployees.has(employee));

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="
          inline-flex items-center gap-2 px-3 py-2 min-w-0
          bg-gray-50 border border-gray-200 rounded-md shadow-sm
          text-sm font-medium text-gray-700 hover:bg-gray-100
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
          transition-colors duration-200
        "
        aria-haspopup="listbox"
        aria-expanded={isOpen}
      >
        <Users className="h-4 w-4 flex-shrink-0" />
        <span className="truncate max-w-40">{getButtonText()}</span>
        <ChevronDown className={`h-4 w-4 flex-shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="
          absolute top-full left-0 mt-1 w-80 z-50
          bg-white border border-gray-200 rounded-lg shadow-lg
          dark:bg-gray-800 dark:border-gray-600
          max-h-96 flex flex-col
        ">
          {/* Search header */}
          <div className="p-3 border-b border-gray-200 dark:border-gray-600">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
              <input
                type="text"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
                placeholder="Search employees..."
                className="
                  w-full pl-10 pr-8 py-1.5 text-sm
                  border border-gray-300 rounded focus:outline-none 
                  focus:ring-2 focus:ring-blue-500 focus:border-blue-500
                  dark:bg-gray-700 dark:border-gray-600 dark:text-gray-300
                  dark:focus:ring-blue-400 dark:focus:border-blue-400
                  dark:placeholder-gray-400
                "
              />
              {searchText && (
                <button
                  type="button"
                  onClick={() => setSearchText('')}
                  className="absolute right-2 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  <X className="h-3 w-3" />
                </button>
              )}
            </div>
          </div>

          {/* Select all / Clear all button */}
          <div className="p-2 border-b border-gray-200 dark:border-gray-600">
            <button
              type="button"
              onClick={handleSelectAll}
              className="
                w-full text-left px-2 py-1.5 text-sm font-medium
                text-blue-600 hover:text-blue-700 hover:bg-blue-50
                dark:text-blue-400 dark:hover:text-blue-300 dark:hover:bg-blue-900/20
                rounded transition-colors duration-150
              "
            >
              {allFilteredSelected ? 'Clear All' : 'Select All'}
              {searchText && ` (${filteredEmployees.length})`}
            </button>
          </div>

          {/* Employee list */}
          <div className="flex-1 overflow-y-auto">
            {filteredEmployees.length === 0 ? (
              <div className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 text-center">
                {searchText ? 'No employees found' : 'No employees available'}
              </div>
            ) : (
              <div className="py-1">
                {filteredEmployees.map((employee) => {
                  const isSelected = selectedEmployees.has(employee);
                  return (
                    <button
                      key={employee}
                      type="button"
                      onClick={() => onToggleEmployee(employee)}
                      className={`
                        w-full text-left px-4 py-2 text-sm flex items-center gap-3
                        hover:bg-gray-100 dark:hover:bg-gray-700
                        transition-colors duration-150
                        ${isSelected 
                          ? 'bg-blue-50 text-blue-700 dark:bg-blue-900/20 dark:text-blue-300' 
                          : 'text-gray-700 dark:text-gray-300'
                        }
                      `}
                      role="option"
                      aria-selected={isSelected}
                    >
                      <div className={`
                        w-4 h-4 border rounded flex items-center justify-center flex-shrink-0
                        ${isSelected 
                          ? 'bg-blue-600 border-blue-600 text-white' 
                          : 'border-gray-300 dark:border-gray-600'
                        }
                      `}>
                        {isSelected && <Check className="h-3 w-3" />}
                      </div>
                      <span className="truncate">{employee}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Footer with selected count */}
          {selectedEmployees.size > 0 && (
            <div className="px-4 py-2 border-t border-gray-200 dark:border-gray-600 text-xs text-gray-500 dark:text-gray-400">
              {selectedEmployees.size} of {availableEmployees.length} employees selected
            </div>
          )}
        </div>
      )}
    </div>
  );
}; 