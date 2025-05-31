'use client';

import { useState, useEffect } from 'react';
import Image from 'next/image';
import SimpleUploadDropzone from '@/components/SimpleUploadDropzone';
import Header from '@/components/ui/Header';
import Footer from '@/components/ui/Footer';
import FAQAccordion from '@/components/ui/FAQAccordion';
import { CafeHeroImage, KitchenStaffImage, EmployeeTimesheetImage, ComplianceChecklistImage } from '@/components/OptimizedImages';
import analytics from '@/utils/analytics';

export default function Home() {
  // State for header functionality
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

  // Task 5.3: CTA click tracking handlers
  const handleCtaClick = (buttonText: string, location: string, targetUrl?: string) => {
    analytics.trackCtaClick({
      button_text: buttonText,
      location: location,
      target_url: targetUrl
    });
  };

  return (
    <div className="min-h-screen bg-white">
      <Header />

      {/* Hero Section */}
      <section className="relative w-full overflow-hidden pt-16">
        {/* Content Container */}
        <div className="relative z-10">
          {/* Mobile Layout */}
          <div className="block lg:hidden relative" style={{ height: '75vh' }}>
            {/* Mobile Background Image */}
            <div className="absolute inset-0 w-full h-full">
              <div className="relative w-full h-full">
                <CafeHeroImage 
                  alt="Professional cafe environment" 
                  className="absolute inset-0 w-full h-full object-cover"
                  priority={true}
                  sizes="100vw"
                />
              </div>
              <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/50 to-black/30"></div>
            </div>
            
            {/* Content - Simple flexbox centering */}
            <div className="relative z-10 h-full flex items-center justify-center px-6">
              <div className="text-center space-y-8 max-w-md w-full">
                <div>
                  <h1 className="mb-4 leading-tight tracking-tight text-white font-black text-5xl" style={{
                    letterSpacing: '-0.02em',
                    lineHeight: '1.1em',
                    fontSize: 'clamp(2rem, 8vw, 3.5rem)'
                  }}>
                    Stop losing money to <span className="text-blue-400">overtime</span> & <span className="text-blue-400">violations</span>
                  </h1>
                  <p className="text-xl text-white font-medium">
                    Get instant compliance audit in 30 seconds
                  </p>
                </div>
                
                <div id="upload" className="w-full">
                  <div className="bg-white/95 backdrop-blur-sm rounded-2xl p-6 border border-white/20 shadow-2xl">
                    <SimpleUploadDropzone />
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Desktop Layout */}
          <div className="hidden lg:block relative" style={{ height: '75vh' }}>
            {/* Desktop Background Image */}
            <div className="absolute inset-0 w-full h-full">
              <div className="relative w-full h-full">
                <CafeHeroImage 
                  alt="Professional cafe environment" 
                  className="absolute inset-0 w-full h-full object-cover"
                  priority={true}
                  sizes="100vw"
                />
              </div>
              <div className="absolute inset-0 bg-gradient-to-b from-black/70 via-black/50 to-black/30"></div>
            </div>
            
            {/* Content - Simple flexbox centering */}
            <div className="relative z-10 h-full flex items-center justify-center px-8">
              <div className="max-w-7xl w-full grid lg:grid-cols-2 gap-20 items-center">
                
                {/* Left Column - Text Content */}
                <div className="text-left">
                  <div className="mb-12">
                    <h1 className="mb-8 leading-none tracking-tight text-white font-black text-8xl xl:text-9xl" style={{
                      letterSpacing: '-0.04em',
                      lineHeight: '0.95em',
                      fontSize: 'clamp(4rem, 12vw, 6rem)'
                    }}>
                      Stop losing money to <span className="text-blue-400">overtime</span> & <span className="text-blue-400">violations</span>
                    </h1>
                    <p className="text-2xl xl:text-3xl text-white font-semibold max-w-xl leading-relaxed"style={{
                      letterSpacing: '-0.04em',
                      lineHeight: '1.2em',
                    }}>
                      Get instant compliance audit in 30 seconds. Upload your timesheet and we'll catch every violation.
                    </p>
                  </div>
                </div>

                {/* Right Column - Upload Form */}
                <div className="flex justify-center lg:justify-end">
                  <div id="upload" className="w-full max-w-lg">
                    <div className="bg-white/95 backdrop-blur-sm rounded-3xl p-8 border border-white/20 shadow-2xl">
                      <SimpleUploadDropzone />
                    </div>
                  </div>
                </div>
                
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="features" className="py-40 bg-white">
        <div className="max-w-6xl mx-auto px-8">
          
          {/* Section Header */}
          <div className="text-center mb-32">
            <div className="inline-flex items-center px-4 py-2 bg-black/10 rounded-full text-gray-900 text-sm font-medium mb-8">
              <span className="w-2 h-2 bg-black rounded-full mr-2"></span>
              Core Features
            </div>
            <h2 style={{
              fontSize: '56px',
              fontWeight: 950,
              letterSpacing: '-0.04em',
              lineHeight: '1.05em',
              color: 'black'
            }} className="mb-6 leading-tight">
              Stop losing money to<br/>overtime violations
            </h2>
            <p style={{
              fontFamily: '"Inter Variable", "Inter", sans-serif',
              fontSize: '24px',
              fontWeight: 400,
              letterSpacing: '-0.01em',
              color: 'rgb(107, 114, 128)'
            }} className="max-w-3xl mx-auto leading-relaxed">
              Three powerful ways ShiftIQ protects your business from costly labor compliance issues and reduces operational overhead.
            </p>
          </div>

          {/* Benefits */}
          <div className="space-y-16 lg:space-y-32">
            
            {/* Benefit 1: Kill Overtime Bloat */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-20 items-center">
              <div className="order-2 lg:order-1 text-center lg:text-left">
                <div className="mb-6">
                  <span className="inline-flex items-center px-3 py-1 bg-blue-50 text-blue-700 text-sm font-medium rounded-full">
                    Cost Control
                  </span>
                </div>
                <div className="mb-6">
                  <h3 style={{
                    fontSize: '36px',
                    fontWeight: 700,
                    letterSpacing: '-0.03em',
                    lineHeight: '1.1em',
                    color: 'black'
                  }} className="text-2xl lg:text-3xl xl:text-4xl">
                    Kill Overtime Bloat
                  </h3>
                </div>
                <div className="mb-8">
                  <p style={{
                    fontSize: '20px',
                    fontWeight: 500,
                    letterSpacing: '-0.01em',
                    color: 'rgb(107, 114, 128)'
                  }} className="leading-relaxed text-base lg:text-lg xl:text-xl max-w-lg mx-auto lg:mx-0">
                    Catch unauthorized overtime before it becomes a budget-busting problem. Our AI spots patterns that manual reviews miss—saving you thousands in unexpected labor costs.
                  </p>
                </div>
                <div className="space-y-3 max-w-md mx-auto lg:mx-0">
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">Instant violation detection across all employees</span>
                  </div>
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">Pattern analysis reveals hidden cost drivers</span>
                  </div>
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-blue-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">Real dollar impact calculated automatically</span>
                  </div>
                </div>
              </div>
              <div className="relative order-1 lg:order-2">
                <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-gray-100 relative shadow-2xl w-[80vw] lg:w-full mx-auto">
                  <KitchenStaffImage 
                    alt="Kitchen staff managing orders efficiently" 
                    className="absolute inset-0 w-full h-full object-cover object-center hover:scale-[1.02] transition-all duration-700"
                    sizes="(max-width: 768px) 80vw, (max-width: 1024px) 50vw, 33vw"
                  />
                </div>
              </div>
            </div>

            {/* Benefit 2: Never Miss a Break */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-20 items-center">
              <div className="relative order-1 lg:order-1">
                <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-gray-100 relative shadow-2xl w-[80vw] lg:w-full mx-auto">
                  <EmployeeTimesheetImage 
                    alt="Employee reviewing accurate timesheet data" 
                    className="absolute inset-0 w-full h-full object-cover object-center hover:scale-[1.02] transition-all duration-700"
                    sizes="(max-width: 768px) 80vw, (max-width: 1024px) 50vw, 33vw"
                  />
                </div>
              </div>
              <div className="order-2 lg:order-2 text-center lg:text-left">
                <div className="mb-6">
                  <span className="inline-flex items-center px-3 py-1 bg-green-50 text-green-700 text-sm font-medium rounded-full">
                    Break Compliance
                  </span>
                </div>
                <div className="mb-6">
                  <h3 style={{
                    fontSize: '36px',
                    fontWeight: 700,
                    letterSpacing: '-0.03em',
                    lineHeight: '1.1em',
                    color: 'black'
                  }} className="text-2xl lg:text-3xl xl:text-4xl">
                    Never Miss a Break
                  </h3>
                </div>
                <div className="mb-8">
                  <p style={{
                    fontSize: '20px',
                    fontWeight: 500,
                    letterSpacing: '-0.01em',
                    color: 'rgb(107, 114, 128)'
                  }} className="leading-relaxed text-base lg:text-lg xl:text-xl max-w-lg mx-auto lg:mx-0">
                    Auto-detect paid break violations before penalties hit payroll. State-specific rules are automatically applied to catch missed meal periods and rest breaks.
                  </p>
                </div>
                <div className="space-y-3 max-w-md mx-auto lg:mx-0">
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">State-specific compliance rules for all 50 states</span>
                  </div>
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">Meal period and rest break violation detection</span>
                  </div>
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-green-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">Premium pay calculations included</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Benefit 3: Smart Compliance Check */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-20 items-center">
              <div className="order-2 lg:order-1 text-center lg:text-left">
                <div className="mb-6">
                  <span className="inline-flex items-center px-3 py-1 bg-purple-50 text-purple-700 text-sm font-medium rounded-full">
                    Audit Protection
                  </span>
                </div>
                <div className="mb-6">
                  <h3 style={{
                    fontSize: '36px',
                    fontWeight: 700,
                    letterSpacing: '-0.03em',
                    lineHeight: '1.1em',
                    color: 'black'
                  }} className="text-2xl lg:text-3xl xl:text-4xl">
                    Smart Compliance Check
                  </h3>
                </div>
                <div className="mb-8">
                  <p style={{
                    fontSize: '20px',
                    fontWeight: 500,
                    letterSpacing: '-0.01em',
                    color: 'rgb(107, 114, 128)'
                  }} className="leading-relaxed text-base lg:text-lg xl:text-xl max-w-lg mx-auto lg:mx-0">
                    Comprehensive audit detects wage violations automatically. Every city, state, and tip-credit rule is checked so you never slip below legal minimum wage requirements.
                  </p>
                </div>
                <div className="space-y-3 max-w-md mx-auto lg:mx-0">
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-purple-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">Multi-jurisdiction compliance checking</span>
                  </div>
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-purple-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">Tip credit and minimum wage calculations</span>
                  </div>
                  <div className="flex items-center text-gray-600 justify-center lg:justify-start">
                    <div className="w-2 h-2 bg-purple-500 rounded-full mr-3 flex-shrink-0"></div>
                    <span className="text-sm lg:text-base">Department of Labor audit preparation</span>
                  </div>
                </div>
              </div>
              <div className="relative order-1 lg:order-2">
                <div className="aspect-[4/3] rounded-2xl overflow-hidden bg-gray-100 relative shadow-2xl w-[80vw] lg:w-full mx-auto">
                  <ComplianceChecklistImage 
                    alt="Compliance checklist and audit documentation" 
                    className="absolute inset-0 w-full h-full object-cover object-center hover:scale-[1.02] transition-all duration-700"
                    sizes="(max-width: 768px) 80vw, (max-width: 1024px) 50vw, 33vw"
                  />
                </div>
              </div>
            </div>

          </div>
        </div>
      </section>

      {/* FAQ Section with Accordion - Moved before testimonials */}
      <section id="faq" className="py-32 bg-gray-50">
        <div className="max-w-4xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 style={{
              fontSize: '32px',
              fontWeight: 800,
              letterSpacing: '-0.02em',
              lineHeight: '1.2em',
              color: 'black'
            }} className="mb-4">
              Frequently Asked Questions
            </h2>
          </div>

          <FAQAccordion items={[
            {
              question: "What files can I upload?",
              answer: "We support CSV, Excel (XLS/XLSX), PDF, and image files. Our AI extracts timesheet data from most common formats including screenshots and scanned documents."
            },
            {
              question: "Will I see clear compliance violations?",
              answer: "Yes, our system automatically detects overtime violations, break compliance issues, and wage violations. Each violation includes clear explanations and cost impact."
            },
            {
              question: "Is my data secure?",
              answer: "Yes, we take security seriously. All data is encrypted in transit and at rest, processed securely, and automatically deleted after your analysis is complete. We follow industry-standard security practices to protect your information."
            }
          ]} />
        </div>
      </section>

      {/* How It Works Section - Now testimonials after FAQ */}
      <section id="how-it-works" className="py-32 bg-white">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-20">
            <h2 style={{
              fontSize: '32px',
              fontWeight: 800,
              letterSpacing: '-0.02em',
              lineHeight: '1.2em',
              color: 'black'
            }} className="mb-4">
              What Our Users Say
            </h2>
          </div>

          {/* Redesigned testimonial cards with reference styling */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-6xl mx-auto">
            {[
              {
                quote: "ShiftIQ flagged $12,171 in missed-break premiums on our first upload. Payroll review now takes five minutes, not an hour—total game-changer for our operations.",
                author: "Lisa Nguyen",
                title: "Owner at Bánh Mi & Co.",
                avatar: "LN"
              },
              {
                quote: "One 30-second audit showed exactly who was double-timing. We shuffled two shifts and cut weekly labor spend by 8%—immediate ROI on compliance tools.",
                author: "Marco Ramirez", 
                title: "GM at Pizzeria Del Sol",
                avatar: "MR"
              },
              {
                quote: "Minimum-wage hikes, tip credit math—ShiftIQ keeps us compliant with every rule. My 3 a.m. compliance panic attacks are completely gone now.",
                author: "Sarah Khan",
                title: "COO at Urban Chickpea",
                avatar: "SK"
              },
              {
                quote: "The DOL inspector asked for records; I handed over the audit report. Ten minutes later—no citations, no stress, no expensive penalties to pay.",
                author: "Ben Thompson",
                title: "Ops Director at GreenLeaf Café",
                avatar: "BT"
              }
            ].map((testimonial, index) => (
              <div key={index} className="bg-white rounded-3xl p-8 border border-gray-100 shadow-xl hover:shadow-2xl transition-all duration-500 transform hover:-translate-y-1">
                <div className="mb-8">
                  <p style={{
                    fontSize: '18px',
                    fontWeight: 450,
                    letterSpacing: '-0.01em',
                    lineHeight: '1.6em',
                    color: 'rgb(17, 24, 39)'
                  }} className="leading-relaxed">
                    "{testimonial.quote}"
                  </p>
                </div>
                <div className="flex items-center space-x-5">
                  <div className="w-16 h-16 bg-gradient-to-br from-gray-900 to-gray-700 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-lg">
                    <span style={{
                      fontWeight: 700,
                      color: 'white'
                    }} className="font-bold">
                      {testimonial.avatar}
                    </span>
                  </div>
                  <div>
                    <p style={{
                      fontSize: '16px',
                      fontWeight: 700,
                      letterSpacing: '-0.01em',
                      color: 'black'
                    }} className="font-bold mb-1">{testimonial.author}</p>
                    <p style={{
                      fontSize: '14px',
                      fontWeight: 500,
                      letterSpacing: '-0.005em',
                      color: 'rgb(107, 114, 128)'
                    }}>{testimonial.title}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <Footer />
    </div>
  );
}


