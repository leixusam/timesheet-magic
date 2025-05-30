## Relevant Files

- `frontend/src/app/page.tsx` - ✅ Marketing landing page (SIMPLIFIED - removed complex state management)
- `frontend/src/app/upload/[requestId]/page.tsx` - ✅ New upload and lead capture page for specific request (CREATED)
- `frontend/src/app/upload/[requestId]/UploadPageClient.tsx` - ✅ Client component for upload page (CREATED)
- `frontend/src/app/upload/[requestId]/not-found.tsx` - ✅ Custom 404 page for invalid request IDs (CREATED)
- `frontend/src/app/upload/[requestId]/loading.tsx` - ✅ Loading state during request validation (CREATED)
- `frontend/src/app/upload/[requestId]/error.tsx` - ✅ Error boundary for unexpected errors (CREATED)
- `frontend/src/app/reports/[id]/page.tsx` - ✅ Analysis results page with server-side data fetching (ENHANCED)
- `frontend/src/app/reports/[id]/ReportPageClient.tsx` - ✅ Client component for interactive report features (CREATED)
- `frontend/src/app/reports/[id]/not-found.tsx` - ✅ Custom 404 page for non-existent reports (CREATED)
- `frontend/src/components/UploadForm.tsx` - ✅ Deleted old complex component (REMOVED)
- `frontend/src/components/SimpleUploadDropzone.tsx` - ✅ Simple upload component for landing page (CREATED)
- `frontend/src/utils/uploadRedirect.ts` - ✅ New utility for handling upload redirects (CREATED)
- `frontend/src/types/leadCapture.ts` - ✅ Lead capture types and interfaces (CREATED)
- `frontend/src/components/LeadCaptureForm.tsx` - ✅ New dedicated lead capture component (CREATED)
- `frontend/src/components/AnalysisResults.tsx` - Existing analysis results component
- `frontend/src/hooks/useFileUpload.ts` - Existing hook (needs simplification)
- `frontend/src/hooks/useLeadCapture.ts` - ✅ Existing hook (UPDATED - now uses new types)

### Notes

- Each page will have its own URL and can be bookmarked/shared
- State management will be simplified since each page has a specific purpose
- The request ID will be part of the URL, making it easy to track and revisit
- Server-side data fetching can be used for better SEO and performance

## Tasks

- [x] 1.0 Create Upload Page with Request ID Route
  - [x] 1.1 Create `frontend/src/app/upload/[requestId]/page.tsx` file with Next.js dynamic routing
  - [x] 1.2 Add server-side props to validate request ID exists in database
  - [x] 1.3 Implement 404 handling for invalid/expired request IDs
  - [x] 1.4 Add page metadata (title, description) for SEO
  - [x] 1.5 Create loading state while validating request ID
  - [x] 1.6 Add error boundary for unexpected errors

- [x] 2.0 Refactor Landing Page to Remove Upload Logic  
  - [x] 2.1 Remove complex UploadForm component from `frontend/src/app/page.tsx`
  - [x] 2.2 Create simple `SimpleUploadDropzone` component for landing page
  - [x] 2.3 Implement file upload that calls `/api/start-analysis` and redirects
  - [x] 2.4 Add upload progress indicator during redirect
  - [x] 2.5 Remove all state management related to upload progress
  - [x] 2.6 Update landing page styling to focus on marketing content

- [x] 3.0 Update Analysis Results Page for Stable URLs
  - [x] 3.1 Review existing `frontend/src/app/reports/[id]/page.tsx` implementation
  - [x] 3.2 Add server-side data fetching to pre-load analysis results
  - [x] 3.3 Implement proper loading states for analysis in progress
  - [x] 3.4 Add 404 handling for non-existent report IDs
  - [x] 3.5 Ensure page works with JavaScript disabled (SSR)
  - [x] 3.6 Add metadata with analysis summary for social sharing

- [x] 4.0 Implement Upload Flow with Page Redirects
  - [x] 4.1 Create `frontend/src/utils/uploadRedirect.ts` utility function
  - [x] 4.2 Update landing page upload to use `router.push()` for navigation
  - [x] 4.3 Add error handling for failed uploads (show error, don't redirect)
  - [x] 4.4 Implement client-side validation before upload
  - [x] 4.5 Add upload progress tracking during file processing
  - [x] 4.6 Test redirect flow works in both dev and production

- [x] 5.0 Create Dedicated Lead Capture Component
  - [x] 5.1 Extract lead capture logic from existing `UploadForm.tsx`
  - [x] 5.2 Create `frontend/src/components/LeadCaptureForm.tsx` component
  - [x] 5.3 Implement form validation using existing `useLeadCapture` hook
  - [x] 5.4 Add submit handler that calls `/api/submit-lead` with request ID
  - [x] 5.5 Implement redirect to `/reports/[requestId]` after successful submission
  - [x] 5.6 Add loading states and error handling for form submission
  - [x] 5.7 Display analysis progress indicator while processing 