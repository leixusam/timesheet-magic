'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import analytics from '@/utils/analytics';

interface HeaderProps {
  variant?: 'default' | 'minimal';
  showNavigation?: boolean;
}

export default function Header({ variant = 'default', showNavigation = true }: HeaderProps) {
  const [isScrolled, setIsScrolled] = useState(false);
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  // Handle scroll for sticky nav with opacity change
  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      setIsScrolled(scrollTop > 10);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Close mobile menu when clicking outside or on links
  const closeMobileMenu = () => {
    setIsMobileMenuOpen(false);
  };

  // CTA click tracking handlers
  const handleCtaClick = (buttonText: string, location: string, targetUrl?: string) => {
    analytics.trackCtaClick({
      button_text: buttonText,
      location: location,
      target_url: targetUrl
    });
  };

  // Handle logo click
  const handleLogoClick = () => {
    window.location.href = '/';
  };

  return (
    <header className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
      isScrolled ? 'bg-white backdrop-blur-md border-b border-gray-200' : 'bg-white/98 backdrop-blur-md border-b border-gray-100'
    }`}>
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex items-center justify-between h-16"> 
          <div className="flex items-center space-x-3 cursor-pointer" onClick={handleLogoClick}>
            <div className="w-8 h-8 relative flex-shrink-0">
              <Image src="/icon-high-res.png" alt="ShiftIQ" className="w-full h-full rounded-lg" width={256} height={256} priority />
            </div>
            <span className="font-semibold text-xl text-gray-900">ShiftIQ</span>
          </div>
          
          {showNavigation && variant === 'default' && (
            <>
              {/* Desktop Navigation */}
              <nav className="hidden md:flex items-center space-x-8">
                <a href="#features" className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium">Features</a>
                <a href="#faq" className="text-gray-600 hover:text-gray-900 transition-colors text-sm font-medium">FAQ</a>
                <a 
                  href="#upload" 
                  onClick={() => handleCtaClick('Start for Free', 'header_desktop', '#upload')}
                  className="bg-black text-white px-6 py-2.5 rounded-full text-sm font-medium hover:bg-gray-800 transition-colors"
                >
                  Start for Free
                </a>
              </nav>

              {/* Mobile Hamburger Menu Button */}
              <button
                onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
                className="md:hidden p-2 rounded-lg hover:bg-gray-100 transition-colors"
                aria-label="Toggle mobile menu"
                aria-expanded={isMobileMenuOpen}
              >
                <div className="w-6 h-6 relative">
                  <span className={`absolute block h-0.5 w-6 bg-gray-900 transition-all duration-300 ease-in-out ${
                    isMobileMenuOpen ? 'rotate-45 top-3' : 'top-1'
                  }`}></span>
                  <span className={`absolute block h-0.5 w-6 bg-gray-900 transition-all duration-300 ease-in-out ${
                    isMobileMenuOpen ? 'opacity-0' : 'top-3'
                  }`}></span>
                  <span className={`absolute block h-0.5 w-6 bg-gray-900 transition-all duration-300 ease-in-out ${
                    isMobileMenuOpen ? '-rotate-45 top-3' : 'top-5'
                  }`}></span>
                </div>
              </button>
            </>
          )}

          {variant === 'minimal' && (
            <div className="text-sm text-gray-500">
              {/* Optional minimal header content */}
            </div>
          )}
        </div>
      </div>

      {/* Mobile Menu Slide-down Drawer */}
      {showNavigation && variant === 'default' && (
        <div className={`md:hidden transition-all duration-300 ease-in-out overflow-hidden ${
          isMobileMenuOpen ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
        }`}>
          <div className="bg-white/95 backdrop-blur-md border-t border-gray-200 shadow-lg" style={{ height: '100vh' }}>
            <nav className="px-6 py-8 space-y-6">
              <a 
                href="#features" 
                onClick={closeMobileMenu}
                className="block text-gray-700 hover:text-black text-lg font-medium py-3 border-b border-gray-100 transition-colors"
              >
                Features
              </a>
              <a 
                href="#faq" 
                onClick={closeMobileMenu}
                className="block text-gray-700 hover:text-black text-lg font-medium py-3 border-b border-gray-100 transition-colors"
              >
                FAQ
              </a>
              <button 
                className="w-full bg-black text-white px-6 py-4 rounded-full text-lg font-medium text-center hover:bg-gray-800 transition-colors mt-8"
                onClick={() => {
                  handleCtaClick('Start for Free', 'header_mobile', '#upload');
                  closeMobileMenu();
                }}
              >
                Start for Free
              </button>
            </nav>
          </div>
        </div>
      )}
    </header>
  );
} 