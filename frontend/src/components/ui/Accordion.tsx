'use client';

import React, { useState, useRef, useEffect } from 'react';
import ViolationInfoBadges from './ViolationInfoBadges';

export interface AccordionItemProps {
  id: string;
  title: string;
  count?: number;
  violationCount?: number;
  infoCount?: number;
  children: React.ReactNode;
  isDefaultOpen?: boolean;
  variant?: 'default' | 'violation' | 'employee';
}

export interface AccordionProps {
  items: AccordionItemProps[];
  allowMultiple?: boolean;
  className?: string;
}

const AccordionItem: React.FC<{
  item: AccordionItemProps;
  isOpen: boolean;
  onToggle: () => void;
}> = ({ item, isOpen, onToggle }) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState<string>('0px');

  // Function to update height based on content
  const updateHeight = () => {
    if (contentRef.current) {
      const newHeight = isOpen ? `${contentRef.current.scrollHeight}px` : '0px';
      setContentHeight(newHeight);
    }
  };

  // Update height when open state changes
  useEffect(() => {
    updateHeight();
  }, [isOpen]);

  // Use a mutation observer to watch for content changes
  useEffect(() => {
    if (!contentRef.current || !isOpen) return;

    const observer = new MutationObserver(() => {
      // Small delay to ensure DOM has updated
      setTimeout(updateHeight, 10);
    });

    // Observe changes to the content and its children
    observer.observe(contentRef.current, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'style']
    });

    // Also observe for any new elements being added
    const resizeObserver = new ResizeObserver(() => {
      updateHeight();
    });

    resizeObserver.observe(contentRef.current);

    return () => {
      observer.disconnect();
      resizeObserver.disconnect();
    };
  }, [isOpen]);

  const getVariantStyles = () => {
    switch (item.variant) {
      case 'violation':
        return {
          header: 'bg-red-50 border-red-200 hover:bg-red-100',
          headerText: 'text-red-900',
          countBadge: 'bg-red-200 text-red-800',
          content: 'border-red-200'
        };
      case 'employee':
        return {
          header: 'bg-blue-50 border-blue-200 hover:bg-blue-100',
          headerText: 'text-blue-900',
          countBadge: 'bg-blue-200 text-blue-800',
          content: 'border-blue-200'
        };
      default:
        return {
          header: 'bg-gray-50 border-gray-200 hover:bg-gray-100',
          headerText: 'text-gray-900',
          countBadge: 'bg-gray-200 text-gray-800',
          content: 'border-gray-200'
        };
    }
  };

  const styles = getVariantStyles();

  return (
    <div className="border rounded-lg overflow-hidden transition-all duration-200">
      <button
        onClick={onToggle}
        className={`w-full px-4 py-3 text-left border-b ${styles.header} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors duration-150`}
        aria-expanded={isOpen}
        aria-controls={`accordion-content-${item.id}`}
        id={`accordion-header-${item.id}`}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <span className={`text-sm font-normal ${styles.headerText}`}>
              {item.title}
            </span>
            {/* Show separate violation and info counts if provided */}
            {item.violationCount !== undefined && item.infoCount !== undefined ? (
              <ViolationInfoBadges 
                violationCount={item.violationCount}
                infoCount={item.infoCount}
                size="md"
                variant="badges"
              />
            ) : item.count !== undefined && (
              <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${styles.countBadge}`}>
                {item.count}
              </span>
            )}
          </div>
          <svg
            className={`w-5 h-5 ${styles.headerText} transform transition-transform duration-200 ${
              isOpen ? 'rotate-180' : 'rotate-0'
            }`}
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 9l-7 7-7-7"
            />
          </svg>
        </div>
      </button>
      <div
        style={{ 
          height: isOpen ? contentHeight : '0px',
          maxHeight: isOpen ? 'none' : '0px'
        }}
        className="overflow-hidden transition-all duration-300 ease-in-out"
      >
        <div
          ref={contentRef}
          id={`accordion-content-${item.id}`}
          role="region"
          aria-labelledby={`accordion-header-${item.id}`}
          className={`border-b ${styles.content}`}
        >
          <div className="p-4">
            {item.children}
          </div>
        </div>
      </div>
    </div>
  );
};

export const Accordion: React.FC<AccordionProps> = ({
  items,
  allowMultiple = false,
  className = ''
}) => {
  const [openItems, setOpenItems] = useState<Set<string>>(() => {
    const defaultOpen = new Set<string>();
    items.forEach(item => {
      if (item.isDefaultOpen) {
        defaultOpen.add(item.id);
      }
    });
    return defaultOpen;
  });

  const toggleItem = (itemId: string) => {
    setOpenItems(prev => {
      const newOpenItems = new Set(prev);
      
      if (newOpenItems.has(itemId)) {
        newOpenItems.delete(itemId);
      } else {
        if (!allowMultiple) {
          newOpenItems.clear();
        }
        newOpenItems.add(itemId);
      }
      
      return newOpenItems;
    });
  };

  const expandAll = () => {
    setOpenItems(new Set(items.map(item => item.id)));
  };

  const collapseAll = () => {
    setOpenItems(new Set());
  };

  return (
    <div className={`space-y-2 ${className}`}>
      {items.length > 1 && (
        <div className="flex justify-end space-x-2 mb-4">
          <button
            onClick={expandAll}
            className="text-sm text-blue-600 hover:text-blue-800 focus:outline-none focus:underline"
          >
            Expand All
          </button>
          <span className="text-gray-300">|</span>
          <button
            onClick={collapseAll}
            className="text-sm text-blue-600 hover:text-blue-800 focus:outline-none focus:underline"
          >
            Collapse All
          </button>
        </div>
      )}
      
      {items.map(item => (
        <AccordionItem
          key={item.id}
          item={item}
          isOpen={openItems.has(item.id)}
          onToggle={() => toggleItem(item.id)}
        />
      ))}
    </div>
  );
};

export default Accordion; 