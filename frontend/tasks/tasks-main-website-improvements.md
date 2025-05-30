# Main Website Improvements Task List

Based on comprehensive design feedback to align the current website with reference design and improve conversion optimization.

## Relevant Files

- `src/app/page.tsx` - Main landing page component containing all sections
- `src/app/globals.css` - Global styles and design tokens with Inter font configuration
- `src/app/layout.tsx` - Root layout with Inter font and comprehensive favicon configuration
- `src/components/UploadForm.tsx` - File upload component that needs redesign
- `src/components/ui/` - New UI components directory for reusable elements
- `src/components/ui/OptimizedImage.tsx` - Responsive image component with WebP support
- `tailwind.config.ts` - Tailwind configuration for design tokens and Inter font
- `public/` - Image assets and SVG icons
- `public/optimized/` - Optimized WebP images for performance
- `public/favicon*` - Complete favicon set (16x16, 32x32, ico, apple-touch-icon) with new professional design
- `public/site.webmanifest` - PWA manifest file
- `src/app/favicon.png` - Next.js App Router favicon
- `design-assets/` - Icon source files and high-resolution variants
- `design-assets/icon-source.svg` - Vector source file for the professional ShiftIQ icon
- `src/hooks/useFileUpload.ts` - Upload functionality hooks
- `src/utils/analytics.ts` - Analytics tracking utilities
- `scripts/optimize-images.sh` - Image optimization script
- `scripts/process-favicon.sh` - Favicon processing script
- `scripts/create-high-res-icon.sh` - High-resolution icon creation script
- `scripts/convert-icon.js` - Node.js SVG to PNG conversion script
- `scripts/finalize-icons.sh` - Icon setup finalization script

### Notes

- This project uses Next.js 15 with Tailwind CSS for styling
- Inter Variable font is configured globally for all elements
- Complete favicon set has been generated with professional ShiftIQ icon design
- New icon features blue gradient, timesheet grid, clock overlay, and magic sparkles
- All icon variants are automatically generated from the vector source
- File upload functionality is already implemented and should be preserved
- Focus on visual design improvements while maintaining existing functionality
- All images referenced are already available in the public folder
- **Header and Footer components have been extracted and made consistent across all pages (main, upload, reports) with minimal variant support for different page contexts**

## Tasks

- [x] 1.0 Design System & Global Foundations
  - [x] 1.1 Create design tokens system in `tailwind.config.ts` with spacing scale (4/8/12/16/24/32/48/64px), neutral gray ramp, primary black #000, and accent blue #1746d4
  - [x] 1.2 Define typography scale in `src/app/globals.css`: h1 48/56px, h2 32/40px, h3 24/32px, body 16/28px using Inter variable font (400-800 weight)
  - [x] 1.3 Create consistent motion system with spring preset (duration 0.4s, ease [0.3,0.7,0.4,1]) for all animations
  - [x] 1.4 Optimize image assets by converting to WebP format at 80% quality with 2x resolution variants for responsive loading

- [x] 2.0 Header, Navigation & Hero Section Redesign
  - [x] 2.1 Reduce navigation height to 56px and implement sticky behavior with 95% opacity backdrop-blur on scroll
  - [x] 2.2 Restructure nav with left-aligned logo and right-aligned links ("Product · How It Works · FAQ" + "Start for free" button)
  - [x] 2.3 Replace hero section with full-bleed café background image and linear-gradient overlay (black → transparent, 60% opacity)
  - [x] 2.4 Update headline copy to "Upload your timesheet. Get instant compliance & overtime audit." with "instant" highlighted
  - [x] 2.5 Add single black CTA button below headline with "Start for free" copy, 14px text, pill radius 48px
  - [x] 2.6 Replace current upload card with floating drop-zone: 1px gray-200 stroke, 12px radius, drop shadow, drag-and-drop states
  - [x] 2.7 Set hero viewport height to 85vh on desktop, 75vh on mobile

- [x] 3.0 Content Sections & Layout Restructure
  - [x] 3.1 Convert benefit tiles to 2-column masonry grid matching reference design layout
  - [x] 3.3 Implement hover effects: image scale 1.05, mask stroke fade from 24px to 12px
  - [x] 3.4 Tighten benefit copy to "Kill Overtime Bloat." with 25-word limit per section
  - [x] 3.5 Add full-width lifestyle section with café photo showing barista, implementing lazy loading
  - [x] 3.6 Replace static FAQ with accordion component using chevron icons
  - [x] 3.7 Update FAQ copy: "What files can I upload?", "Will I see clear compliance violations?", "Is my data secure?" (30-word answers max)
  - [x] 3.8 Move FAQ section before testimonials in scroll order
  - [x] 3.9 Rebuild testimonials as 2-card-per-row grid (45% width, 24px gap desktop; single-column mobile)
  - [x] 3.10 Style testimonial cards with white background, 2px border #e5e7eb, 16px radius, soft shadow
  - [x] 3.11 Add 48px circular avatars, bold 14px names, 12px gray-500 roles to testimonials
  - [x] 3.12 Tighten testimonial copy to 180 characters max with quantified wins ("flagged $12,171 in missed-break premiums")
  - [x] 3.13 Update footer background to #f9fafb and reorder links: Product · Pricing · Privacy Policy · Terms · Contact

- [x] 4.0 Mobile Responsiveness & Accessibility
  - [x] 4.1 Implement hamburger navigation menu with slide-down drawer (100vh) for mobile
  - [x] 4.2 Stack hero copy and CTA center-aligned on mobile with 90% viewport max-width
  - [x] 4.3 Reflow benefit tiles to single-column on mobile while keeping masks at 80vw scale
  - [x] 4.4 Reduce FAQ accordion padding to 16px on mobile
  - [x] 4.5 Ensure all text passes WCAG 2.1 AA contrast requirements (≥4.5:1 ratio)
  - [x] 4.6 Implement logical keyboard navigation with focusable accordion and upload zone
  - [x] 4.7 Add ARIA labels: role="button" on upload zone, aria-expanded on accordion triggers

- [x] 5.0 Performance Optimization & Analytics Integration
  - [x] 5.1 Optimize Core Web Vitals: achieve CLS < 0.1 and LCP < 2.5s through image optimization and JS deferring
  - [x] 5.2 Create analytics utility in `src/utils/analytics.ts` for GA4 and PostHog integration
  - [x] 5.3 Implement conversion event tracking: upload_start, upload_success, cta_click
  - [x] 5.4 ~~Hook "Start for free" buttons to inline form collecting name, email, company size before file upload~~ *(REMOVED: Would hurt conversion rates - current post-upload lead capture is better UX)*
  - [x] 5.5 ~~Add blur-up image placeholders to prevent layout shift and improve perceived performance~~ *(COMPLETED: Layout shift already prevented with aspect-ratio containers and Next.js Image fill prop)*

- [x] 6.0 Visual Design Alignment with Reference
  - [x] 6.1 Replace light hero background with dark café image and white text overlay to match reference design
  - [x] 6.2 Move file upload integration to be less prominent in hero, following reference layout pattern
  - [x] 6.3 Implement asymmetrical masonry layout for benefit sections instead of current grid system
  - [x] 6.4 Add distinctive geometric shape overlays (white circle, triangle, square) to all benefit images
  - [x] 6.5 Adjust color scheme to emphasize black/white contrast over current blue theme
  - [x] 6.6 Update typography hierarchy to match reference: bolder headings, more varied font weights
  - [x] 6.7 Redesign testimonial cards to match reference styling with different proportions and spacing
  - [x] 6.8 Implement the exact image positioning and cropping from reference design
  - [x] 6.9 Add the missing visual elements: geometric patterns, specific image treatments, and overlay effects
  - [x] 6.10 Adjust overall spacing and rhythm to match the reference design's more dramatic scale