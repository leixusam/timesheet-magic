'use client';

// Task 5.2: Analytics utility for GA4 and PostHog integration

// Types for analytics events
export interface AnalyticsEvent {
  event: string;
  properties?: Record<string, any>;
  user_properties?: Record<string, any>;
}

export interface ConversionEvent extends AnalyticsEvent {
  event: 'upload_start' | 'upload_success' | 'cta_click' | 'lead_capture' | 'report_view';
  properties: {
    timestamp: string;
    user_agent?: string;
    referrer?: string;
    session_id?: string;
    [key: string]: any;
  };
}

export interface UserProperties {
  user_id?: string;
  email?: string;
  company_size?: string;
  industry?: string;
  first_visit?: boolean;
  returning_user?: boolean;
}

// Configuration interface
interface AnalyticsConfig {
  ga4_measurement_id?: string;
  posthog_api_key?: string;
  posthog_host?: string;
  debug?: boolean;
  enabled?: boolean;
}

class Analytics {
  private config: AnalyticsConfig;
  private isInitialized = false;
  private sessionId: string;
  private userId?: string;

  constructor() {
    this.config = {
      ga4_measurement_id: process.env.NEXT_PUBLIC_GA4_MEASUREMENT_ID,
      posthog_api_key: process.env.NEXT_PUBLIC_POSTHOG_API_KEY,
      posthog_host: process.env.NEXT_PUBLIC_POSTHOG_HOST || 'https://app.posthog.com',
      debug: process.env.NODE_ENV === 'development',
      enabled: process.env.NODE_ENV === 'production' || process.env.NEXT_PUBLIC_ANALYTICS_ENABLED === 'true'
    };
    
    this.sessionId = this.generateSessionId();
    this.initialize();
  }

  private generateSessionId(): string {
    return `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  private generateUserId(): string {
    const stored = localStorage.getItem('analytics_user_id');
    if (stored) return stored;
    
    const newId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    localStorage.setItem('analytics_user_id', newId);
    return newId;
  }

  private async initialize(): Promise<void> {
    if (typeof window === 'undefined' || !this.config.enabled) return;
    
    try {
      this.userId = this.generateUserId();
      
      // Initialize Google Analytics 4
      if (this.config.ga4_measurement_id) {
        await this.initializeGA4();
      }
      
      // Initialize PostHog
      if (this.config.posthog_api_key) {
        await this.initializePostHog();
      }
      
      this.isInitialized = true;
      
      // Track initial page view
      this.trackPageView();
      
      if (this.config.debug) {
        console.log('[Analytics] Initialized successfully', {
          ga4: !!this.config.ga4_measurement_id,
          posthog: !!this.config.posthog_api_key,
          userId: this.userId,
          sessionId: this.sessionId
        });
      }
    } catch (error) {
      console.error('[Analytics] Initialization failed:', error);
    }
  }

  private async initializeGA4(): Promise<void> {
    if (!this.config.ga4_measurement_id) return;

    // Load GA4 script
    const script = document.createElement('script');
    script.async = true;
    script.src = `https://www.googletagmanager.com/gtag/js?id=${this.config.ga4_measurement_id}`;
    document.head.appendChild(script);

    // Initialize gtag with proper typing
    window.gtag = window.gtag || function() {
      // @ts-ignore - gtag queue is dynamically created
      (window.gtag.q = window.gtag.q || []).push(arguments);
    };

    window.gtag('js', new Date());
    window.gtag('config', this.config.ga4_measurement_id, {
      user_id: this.userId,
      session_id: this.sessionId,
      custom_map: {
        custom_dimension_1: 'session_id',
        custom_dimension_2: 'user_type'
      }
    });
  }

  private async initializePostHog(): Promise<void> {
    if (!this.config.posthog_api_key || typeof window === 'undefined') return;

    // Load PostHog
    const { default: posthog } = await import('posthog-js');
    
    posthog.init(this.config.posthog_api_key, {
      api_host: this.config.posthog_host,
      debug: this.config.debug,
      capture_pageview: false, // We'll handle this manually
      capture_pageleave: true,
      session_recording: {
        maskAllInputs: true,
        maskInputOptions: {
          password: true,
          email: false
        }
      },
      autocapture: {
        dom_event_allowlist: ['click', 'submit', 'change'],
        url_allowlist: [window.location.origin]
      }
    });

    // Identify user
    if (this.userId) {
      posthog.identify(this.userId);
    }

    // Store PostHog reference globally for access
    window.posthog = posthog;
  }

  // Core tracking methods
  public track(event: string, properties: Record<string, any> = {}): void {
    if (!this.config.enabled || typeof window === 'undefined') return;

    const enrichedProperties = {
      ...properties,
      timestamp: new Date().toISOString(),
      session_id: this.sessionId,
      user_agent: navigator.userAgent,
      referrer: document.referrer,
      url: window.location.href,
      path: window.location.pathname
    };

    try {
      // Track in GA4
      if (window.gtag && this.config.ga4_measurement_id) {
        window.gtag('event', event, enrichedProperties);
      }

      // Track in PostHog
      if (window.posthog) {
        window.posthog.capture(event, enrichedProperties);
      }

      if (this.config.debug) {
        console.log('[Analytics] Event tracked:', event, enrichedProperties);
      }
    } catch (error) {
      console.error('[Analytics] Event tracking failed:', error);
    }
  }

  public trackPageView(path?: string): void {
    const currentPath = path || window.location.pathname;
    
    this.track('page_view', {
      page_path: currentPath,
      page_title: document.title,
      page_url: window.location.href
    });
  }

  public identify(userId: string, properties: UserProperties = {}): void {
    if (!this.config.enabled || typeof window === 'undefined') return;

    this.userId = userId;
    localStorage.setItem('analytics_user_id', userId);

    try {
      // Update GA4 user ID
      if (window.gtag) {
        window.gtag('config', this.config.ga4_measurement_id!, {
          user_id: userId
        });
        window.gtag('event', 'user_identification', properties);
      }

      // Update PostHog user
      if (window.posthog) {
        window.posthog.identify(userId, properties);
      }

      if (this.config.debug) {
        console.log('[Analytics] User identified:', userId, properties);
      }
    } catch (error) {
      console.error('[Analytics] User identification failed:', error);
    }
  }

  public setUserProperties(properties: UserProperties): void {
    if (!this.config.enabled) return;

    try {
      // Set in GA4
      if (window.gtag) {
        window.gtag('event', 'user_properties_update', {
          custom_parameters: properties
        });
      }

      // Set in PostHog
      if (window.posthog) {
        window.posthog.setPersonProperties(properties);
      }

      if (this.config.debug) {
        console.log('[Analytics] User properties set:', properties);
      }
    } catch (error) {
      console.error('[Analytics] Setting user properties failed:', error);
    }
  }

  // Task 5.3: Conversion event tracking methods
  public trackUploadStart(fileInfo: { name: string; size: number; type: string }): void {
    this.track('upload_start', {
      file_name: fileInfo.name,
      file_size: fileInfo.size,
      file_type: fileInfo.type,
      conversion_step: 1
    });
  }

  public trackUploadSuccess(uploadInfo: { requestId: string; fileName: string; processingTime?: number }): void {
    this.track('upload_success', {
      request_id: uploadInfo.requestId,
      file_name: uploadInfo.fileName,
      processing_time: uploadInfo.processingTime,
      conversion_step: 2
    });
  }

  public trackCtaClick(ctaInfo: { button_text: string; location: string; target_url?: string }): void {
    this.track('cta_click', {
      button_text: ctaInfo.button_text,
      click_location: ctaInfo.location,
      target_url: ctaInfo.target_url,
      conversion_step: 0
    });
  }

  public trackLeadCapture(leadInfo: { email: string; company_size?: string; industry?: string }): void {
    this.track('lead_capture', {
      email_domain: leadInfo.email.split('@')[1],
      company_size: leadInfo.company_size,
      industry: leadInfo.industry,
      conversion_step: 3
    });

    // Also identify the user with their email
    this.identify(leadInfo.email, {
      email: leadInfo.email,
      company_size: leadInfo.company_size,
      industry: leadInfo.industry
    });
  }

  public trackReportView(reportInfo: { requestId: string; violationCount?: number; employeeCount?: number }): void {
    this.track('report_view', {
      request_id: reportInfo.requestId,
      violation_count: reportInfo.violationCount,
      employee_count: reportInfo.employeeCount,
      conversion_step: 4
    });
  }

  // Enhanced tracking methods
  public trackError(error: { message: string; stack?: string; context?: string }): void {
    this.track('error_occurred', {
      error_message: error.message,
      error_context: error.context,
      error_stack: error.stack?.substring(0, 500) // Limit stack trace length
    });
  }

  public trackFeatureUsage(feature: string, action: string, properties: Record<string, any> = {}): void {
    this.track('feature_usage', {
      feature_name: feature,
      action,
      ...properties
    });
  }

  public trackPerformance(metrics: { lcp?: number; fid?: number; cls?: number; ttfb?: number }): void {
    this.track('performance_metrics', {
      largest_contentful_paint: metrics.lcp,
      first_input_delay: metrics.fid,
      cumulative_layout_shift: metrics.cls,
      time_to_first_byte: metrics.ttfb
    });
  }

  // Utility methods
  public isEnabled(): boolean {
    return !!this.config.enabled && this.isInitialized;
  }

  public getSessionId(): string {
    return this.sessionId;
  }

  public getUserId(): string | undefined {
    return this.userId;
  }

  public reset(): void {
    if (typeof window === 'undefined') return;
    
    localStorage.removeItem('analytics_user_id');
    this.userId = this.generateUserId();
    this.sessionId = this.generateSessionId();
    
    if (window.posthog) {
      window.posthog.reset();
    }
  }
}

// Global declarations for TypeScript
declare global {
  interface Window {
    gtag: (...args: any[]) => void;
    posthog: any;
  }
}

// Create singleton instance
const analytics = new Analytics();

// Export both the instance and the class
export default analytics;
export { Analytics }; 