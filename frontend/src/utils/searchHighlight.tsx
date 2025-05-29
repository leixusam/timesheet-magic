import React from 'react';

interface HighlightOptions {
  caseSensitive?: boolean;
  className?: string;
  highlightClassName?: string;
}

/**
 * Highlights search terms within text content
 * @param text - The text to search within
 * @param searchTerm - The term to highlight
 * @param options - Options for highlighting behavior
 * @returns React element with highlighted terms
 */
export const highlightSearchTerms = (
  text: string, 
  searchTerm: string, 
  options: HighlightOptions = {}
): React.ReactElement => {
  const {
    caseSensitive = false,
    className = '',
    highlightClassName = 'bg-yellow-200 dark:bg-yellow-700 px-0.5 rounded'
  } = options;

  // If no search term provided, return original text
  if (!searchTerm || !searchTerm.trim()) {
    return <span className={className}>{text}</span>;
  }

  const trimmedSearchTerm = searchTerm.trim();
  
  // Create regex for case-insensitive search
  const regex = new RegExp(
    `(${trimmedSearchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`,
    caseSensitive ? 'g' : 'gi'
  );

  // Split text by search term matches
  const parts = text.split(regex);

  return (
    <span className={className}>
      {parts.map((part, index) => {
        // Check if this part matches the search term
        const isMatch = caseSensitive 
          ? part === trimmedSearchTerm
          : part.toLowerCase() === trimmedSearchTerm.toLowerCase();

        if (isMatch && part) {
          return (
            <mark 
              key={index} 
              className={highlightClassName}
              aria-label={`Search match: ${part}`}
            >
              {part}
            </mark>
          );
        }
        
        return part || null;
      })}
    </span>
  );
};

/**
 * Highlights multiple search terms within text content
 * @param text - The text to search within
 * @param searchTerms - Array of terms to highlight
 * @param options - Options for highlighting behavior
 * @returns React element with highlighted terms
 */
export const highlightMultipleTerms = (
  text: string,
  searchTerms: string[],
  options: HighlightOptions = {}
): React.ReactElement => {
  const {
    caseSensitive = false,
    className = '',
    highlightClassName = 'bg-yellow-200 dark:bg-yellow-700 px-0.5 rounded'
  } = options;

  // Filter out empty terms
  const validTerms = searchTerms.filter(term => term && term.trim());
  
  if (validTerms.length === 0) {
    return <span className={className}>{text}</span>;
  }

  // Escape special regex characters and join terms with OR operator
  const escapedTerms = validTerms.map(term => 
    term.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  );
  
  const regex = new RegExp(
    `(${escapedTerms.join('|')})`,
    caseSensitive ? 'g' : 'gi'
  );

  const parts = text.split(regex);

  return (
    <span className={className}>
      {parts.map((part, index) => {
        // Check if this part matches any of the search terms
        const isMatch = validTerms.some(term => 
          caseSensitive 
            ? part === term.trim()
            : part.toLowerCase() === term.trim().toLowerCase()
        );

        if (isMatch && part) {
          return (
            <mark 
              key={index} 
              className={highlightClassName}
              aria-label={`Search match: ${part}`}
            >
              {part}
            </mark>
          );
        }
        
        return part || null;
      })}
    </span>
  );
};

/**
 * Highlights search terms in a more advanced way, supporting word boundaries
 * @param text - The text to search within
 * @param searchTerm - The term to highlight
 * @param options - Options for highlighting behavior
 * @returns React element with highlighted terms
 */
export const highlightWithWordBoundaries = (
  text: string,
  searchTerm: string,
  options: HighlightOptions & { wholeWords?: boolean } = {}
): React.ReactElement => {
  const {
    caseSensitive = false,
    wholeWords = false,
    className = '',
    highlightClassName = 'bg-yellow-200 dark:bg-yellow-700 px-0.5 rounded'
  } = options;

  if (!searchTerm || !searchTerm.trim()) {
    return <span className={className}>{text}</span>;
  }

  const trimmedSearchTerm = searchTerm.trim();
  const escapedTerm = trimmedSearchTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  
  // Add word boundaries if wholeWords is true
  const pattern = wholeWords ? `\\b(${escapedTerm})\\b` : `(${escapedTerm})`;
  const regex = new RegExp(pattern, caseSensitive ? 'g' : 'gi');

  const parts = text.split(regex);

  return (
    <span className={className}>
      {parts.map((part, index) => {
        const isMatch = regex.test(part);
        // Reset regex lastIndex for consistent behavior
        regex.lastIndex = 0;
        
        if (isMatch && part) {
          return (
            <mark 
              key={index} 
              className={highlightClassName}
              aria-label={`Search match: ${part}`}
            >
              {part}
            </mark>
          );
        }
        
        return part || null;
      })}
    </span>
  );
}; 