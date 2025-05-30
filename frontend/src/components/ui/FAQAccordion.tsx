'use client';

import { useState, useRef, useEffect } from 'react';

interface FAQItem {
  question: string;
  answer: string;
}

interface FAQAccordionProps {
  items: FAQItem[];
}

export default function FAQAccordion({ items }: FAQAccordionProps) {
  const [openIndex, setOpenIndex] = useState<number | null>(null);
  const [focusedIndex, setFocusedIndex] = useState<number>(-1);
  const buttonRefs = useRef<(HTMLButtonElement | null)[]>([]);

  // Initialize button refs array
  useEffect(() => {
    buttonRefs.current = buttonRefs.current.slice(0, items.length);
  }, [items.length]);

  const toggleItem = (index: number) => {
    setOpenIndex(openIndex === index ? null : index);
  };

  const handleKeyDown = (event: React.KeyboardEvent, index: number) => {
    switch (event.key) {
      case 'ArrowDown':
        event.preventDefault();
        const nextIndex = index < items.length - 1 ? index + 1 : 0;
        setFocusedIndex(nextIndex);
        buttonRefs.current[nextIndex]?.focus();
        break;
        
      case 'ArrowUp':
        event.preventDefault();
        const prevIndex = index > 0 ? index - 1 : items.length - 1;
        setFocusedIndex(prevIndex);
        buttonRefs.current[prevIndex]?.focus();
        break;
        
      case 'Enter':
      case ' ':
        event.preventDefault();
        toggleItem(index);
        break;
        
      case 'Home':
        event.preventDefault();
        setFocusedIndex(0);
        buttonRefs.current[0]?.focus();
        break;
        
      case 'End':
        event.preventDefault();
        const lastIndex = items.length - 1;
        setFocusedIndex(lastIndex);
        buttonRefs.current[lastIndex]?.focus();
        break;
        
      default:
        break;
    }
  };

  const handleFocus = (index: number) => {
    setFocusedIndex(index);
  };

  const handleBlur = () => {
    // Small delay to allow focus to settle on new element
    setTimeout(() => {
      const activeElement = document.activeElement;
      const isWithinAccordion = buttonRefs.current.some(ref => ref === activeElement);
      if (!isWithinAccordion) {
        setFocusedIndex(-1);
      }
    }, 0);
  };

  return (
    <div 
      className="space-y-4"
      role="group"
      aria-label="Frequently Asked Questions"
    >
      {items.map((item, index) => (
        <div key={index} className="bg-white rounded-xl border border-gray-200 shadow-sm">
          <button
            ref={(el) => { buttonRefs.current[index] = el; }}
            onClick={() => toggleItem(index)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            onFocus={() => handleFocus(index)}
            onBlur={handleBlur}
            className="w-full px-4 py-4 md:px-6 md:py-4 text-left flex items-center justify-between hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors rounded-xl"
            aria-expanded={openIndex === index}
            aria-controls={`faq-content-${index}`}
            id={`faq-button-${index}`}
            tabIndex={focusedIndex === -1 ? (index === 0 ? 0 : -1) : (focusedIndex === index ? 0 : -1)}
          >
            <h3 style={{
              fontFamily: '"Inter Variable", "Inter Placeholder", sans-serif',
              fontSize: '24px',
              fontVariationSettings: '"opsz" 32, "wght" 700',
              fontFeatureSettings: '"cv01" on, "cv09" on, "cv05" on, "ss03" on',
              letterSpacing: '-0.02em',
              lineHeight: '1.2em',
              color: 'black'
            }} className="font-semibold text-lg md:text-xl lg:text-2xl">
              {item.question}
            </h3>
            <svg
              className={`w-5 h-5 text-gray-500 transition-transform duration-200 flex-shrink-0 ml-4 ${
                openIndex === index ? 'rotate-180' : ''
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>
          
          <div
            id={`faq-content-${index}`}
            role="region"
            aria-labelledby={`faq-button-${index}`}
            className={`overflow-hidden transition-all duration-300 ease-in-out ${
              openIndex === index ? 'max-h-48 opacity-100' : 'max-h-0 opacity-0'
            }`}
          >
            <div className="px-4 pb-4 md:px-6 md:pb-4">
              <p style={{
                fontFamily: '"Inter Variable", "Inter Placeholder", sans-serif',
                fontSize: '18px',
                fontVariationSettings: '"opsz" 32, "wght" 500',
                fontFeatureSettings: '"cv09" on, "cv01" on, "cv05" on, "ss03" on',
                letterSpacing: '-0.01em',
                color: 'rgb(153, 153, 153)'
              }} className="leading-relaxed text-sm md:text-base lg:text-lg">
                {item.answer}
              </p>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
} 