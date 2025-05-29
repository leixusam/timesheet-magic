'use client';

import React from 'react';
import { Search, X } from 'lucide-react';

interface SearchBoxProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export const SearchBox: React.FC<SearchBoxProps> = ({
  value,
  onChange,
  placeholder = "Search violations, employees, or details...",
  className = "",
  disabled = false
}) => {
  const handleClear = () => {
    onChange('');
  };

  return (
    <div className={`relative ${className}`}>
      <div className="relative">
        <Search 
          className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" 
          aria-hidden="true"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          className="
            w-full pl-10 pr-10 py-2.5 
            bg-white border border-gray-300 rounded-lg
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            disabled:opacity-50 disabled:cursor-not-allowed
            text-sm placeholder-gray-500 text-gray-900
            transition-colors duration-200
          "
          aria-label="Search violations"
        />
        {value && (
          <button
            type="button"
            onClick={handleClear}
            disabled={disabled}
            className="
              absolute right-3 top-1/2 transform -translate-y-1/2
              text-gray-400 hover:text-gray-600
              transition-colors duration-200
              disabled:opacity-50 disabled:cursor-not-allowed
              focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2
              rounded-full p-0.5
            "
            aria-label="Clear search"
          >
            <X className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}; 