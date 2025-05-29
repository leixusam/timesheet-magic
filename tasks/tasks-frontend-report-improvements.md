# Frontend Report Improvements - Task List

## Relevant Files

- `frontend/src/components/TimeSheetReport.tsx` - Main report component that needs UI/UX improvements
- `frontend/src/components/ViolationCard.tsx` - Individual violation display component with search highlighting support
- `frontend/src/components/MetricsGrid.tsx` - Key metrics display component
- `frontend/src/components/EmployeeSummaryTable.tsx` - Employee summary table component
- `frontend/src/hooks/useReportFilters.ts` - Custom hook for filtering and search functionality with state management
- `frontend/src/utils/reportHelpers.ts` - Utility functions for report data processing
- `frontend/src/utils/searchHighlight.tsx` - Search term highlighting utilities with React components
- `frontend/src/styles/globals.css` - Global styles for improved typography and spacing
- `frontend/src/components/ui/Accordion.tsx` - Reusable accordion component for progressive disclosure
- `frontend/src/components/ui/FilterChips.tsx` - Filter chip components for quick filtering with severity and type variants
- `frontend/src/components/ui/SearchBox.tsx` - Search input component with real-time filtering
- `frontend/src/components/ui/DateRangeFilter.tsx` - Date range filter with preset options and custom range support
- `frontend/src/components/ui/EmployeeFilter.tsx` - Multi-select employee filter dropdown with search
- `frontend/src/components/ui/FilterPanel.tsx` - Comprehensive filter panel combining all filter components
- `frontend/src/components/EmployeeViolationGroup.tsx` - Groups violations by employee with collapsible sections and search support
- `frontend/src/components/ViolationTypeGroup.tsx` - Groups violations by type with separate accordions and search support
- `frontend/src/components/ReportDisplay.tsx` - Updated main report component with filtering system integration

### Notes

- Unit tests should typically be placed alongside the code files they are testing (e.g., `ViolationCard.tsx` and `ViolationCard.test.tsx` in the same directory).
- Use `npx jest [optional/path/to/test/file]` to run tests. Running without a path executes all tests found by the Jest configuration.
- Consider using React Testing Library for component testing and user interaction testing.

## Tasks

- [x] 1.0 Implement Progressive Disclosure and Collapsible Content
  - [x] 1.1 Create reusable Accordion component with smooth animations
  - [x] 1.2 Group violations by employee in collapsible sections with violation counts
  - [x] 1.3 Group violations by type (Meal Break, Rest Break, Overtime) in separate accordions
  - [x] 1.4 Add collapse/expand functionality to individual violation cards for detailed information
  - [x] 1.5 Implement "Show details" toggle for lengthy "Suggested Action" text
  - [x] 1.6 Set default state to collapsed with summary counts visible
  - [x] 1.7 Add expand/collapse all functionality for power users

- [x] 2.0 Add Filtering and Search Capabilities  
  - [x] 2.1 Create FilterChips component with toggle states for violation types
  - [x] 2.2 Implement severity level filter chips (Info, Warning, Critical)
  - [x] 2.3 Add date range filter with preset options (Today, This Week, This Month)
  - [x] 2.4 Create employee filter dropdown with multi-select capability
  - [x] 2.5 Build SearchBox component with real-time text filtering
  - [x] 2.6 Implement search result highlighting within violation descriptions
  - [x] 2.7 Add "Clear All Filters" button and active filter count display
  - [x] 2.8 Create useReportFilters hook to manage filter state and logic

- [x] 3.0 Improve Visual Hierarchy and Design System
  - [x] 3.1 Update typography scales - increase base font size to 14-16px with improved line-height
  - [x] 3.2 Implement consistent color system with 3 severity levels (yellow/orange/red)
  - [x] 3.3 Replace full-card red backgrounds with left border accent or small badges
  - [x] 3.4 Add proper spacing between violation cards (8-12px margins)
  - [x] 3.5 Limit violation card width to ~600px for better readability
  - [x] 3.6 Implement dark mode support with system preference detection
  - [x] 3.7 Add responsive breakpoints for mobile-first design
  - [x] 3.8 Create consistent button styles and hover states

- [ ] 4.0 Enhance User Interactions and Actionability
  - [ ] 4.1 Add action buttons to violation cards (Mark Resolved, Export, Create Task)
  - [ ] 4.2 Implement sticky summary metrics bar that remains visible while scrolling
  - [ ] 4.3 Replace full timestamps with relative dates ("Mon 3/17" or "Yesterday")
  - [ ] 4.4 Move legal references to tooltips or expandable footnotes
  - [ ] 4.5 Create consolidated warning banner for repeated caveats (⚠️ detection confidence)
  - [ ] 4.6 Add sorting options (Severity, Date, Employee) with visual indicators
  - [ ] 4.7 Implement pagination or infinite scroll for violation lists >25 items
  - [ ] 4.8 Add keyboard navigation support for accessibility

- [ ] 5.0 Optimize Performance and Responsiveness
  - [ ] 5.1 Implement lazy loading for violation cards below the fold
  - [ ] 5.2 Optimize CSS delivery by inlining critical styles
  - [ ] 5.3 Move Google Fonts loading to non-blocking with font-display: swap
  - [ ] 5.4 Create single-column mobile layout with horizontal scrolling KPI cards
  - [ ] 5.5 Add loading skeletons for better perceived performance
  - [ ] 5.6 Implement virtualization for large violation lists (>100 items)
  - [ ] 5.7 Optimize bundle size by code-splitting heavy components
  - [ ] 5.8 Add performance monitoring and metrics tracking 