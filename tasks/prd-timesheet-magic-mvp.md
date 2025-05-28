# PRD – TimeSheet Magic MVP

## 1. Introduction / Overview

Restaurant managers, particularly General Managers (GMs) of single units, waste significant hours manually auditing past weekly timesheets. They often miss costly labor-law compliance violations, inefficient staffing (over/under-staffing), and avoidable overtime costs reflected in these historical records. TimeSheet Magic is a zero-setup web tool designed to directly address these pain points. It allows a manager to upload any timesheet or schedule (CSV, XLSX, pasted text, or photo) and, within approximately 30 seconds, receive a visual, plain-language report. This report will highlight potential compliance violations and areas of labor-cost waste from the audited period, providing actionable insights to help them construct more cost-effective and compliant schedules for the future. The same user flow also serves as a lead generation mechanism by capturing the manager's contact information.

## 2. Goals

| #  | Goal                                                                                                | Metric                                         |
|----|-----------------------------------------------------------------------------------------------------|------------------------------------------------|
| G1 | Deliver a complete schedule analysis in ≤ 30 seconds (P95) from upload click to report display.       | Server-side timing logs.                       |
| G2 | Correctly parse ≥ 90% of rows on supported input formats.                                           | Automated unit tests + sample uploads.         |
| G3 | Collect a verifiable email or phone lead on ≥ 75% of completed uploads.                             | Database lead-capture rate.                    |
| G4 | Support overnight shifts and flag instances of potentially duplicate employee names without crashing. | End-to-end tests; manual review of flagged names. |
| G5 | Clearly highlight key labor cost drivers including compliance risks and overtime.                     | Qualitative review of report clarity.          |

## 3. User Stories

1.  **US-1:** As a single-unit GM, I want to drag-and-drop last week's time sheet and instantly see where I incurred potential compliance violations and overtime costs, so I can adjust future schedules to reduce labor expenses.
2.  **US-2:** As a first-time café owner, I want the system to read my messy Excel sheet without manual clean-up, so I don't waste time reformatting and can quickly understand my staffing efficiency.
3.  **US-3:** As a user whose file fails to parse, I want a clear error message and the ability to enter my email so I get notified when my format is supported or if there are simple fixes I can make.
4.  **US-4:** As a busy restaurant manager, I want to see a quick summary of potential cost savings related to labor, so I can justify spending time on schedule adjustments.
5.  **US-5:** As a restaurant manager, I want to not only see potential compliance violations but also understand actionable steps to address them, so I can ensure my business is compliant and reduce operational risks.

## 4. Functional Requirements

1.  **FR-1 Upload Endpoint:** The system must accept inputs via file picker or drag-and-drop for: `.csv`, `.xlsx`, `.pdf`, plain-text paste, and common image formats including those from mobile devices (e.g., `.jpg`, `.png`, `.heic`, `.heif`).
2.  **FR-2 Enhanced Lead Capture & Parallel Processing:** Immediately after the user initiates an upload, the UI must display a form to capture the following lead information: Manager Name, Email, Phone (optional), Store Name, and Store Physical Address. 
    *   For Store Name and Store Physical Address fields, the system should integrate with a Maps API (e.g., Google Places Autocomplete API) to provide auto-suggestions and help complete the address accurately.
    *   This lead capture process must occur while the timesheet data is being processed in the backend to minimize perceived user waiting time.
    *   Submission of Manager Name, Email, Store Name, and Store Physical Address is mandatory to proceed to the report. If the user closes this form or navigates away before submitting mandatory fields, access to the report for that specific upload is lost.
3.  **FR-3 Parsing with LLM:** The back-end must call an LLM with a defined JSON schema to normalize raw text (including OCR output from images and text extraction from PDFs) into structured data containing: `employee_identifier`, `date`, `clock_in`, `clock_out` (and any explicitly logged break times).
    *   If the system detects rows with identical `employee_identifier` values that appear to be distinct individuals (e.g., based on shift patterns or if the original input clearly had different names that normalized to the same identifier), it should flag these as "Potential Duplicate Employee Name" issues in the report.
4.  **FR-4 Core Compliance & Overtime Analysis (Generic Rules for V1):** The system must identify and flag instances based on common labor rule patterns:
    *   **Meal Break Violation:** e.g., Employee works > 5 consecutive hours without a logged 30-minute meal break.
    *   **Rest Break Violation:** e.g., Employee works an 8-hour shift without evidence of a 10-minute rest break (Note: This may be flagged as 'Potentially Missing' if break data is not typically explicit in uploads, relying on shift length as a proxy).
    *   **Daily Overtime:** e.g., Employee works > 8 hours in a single day.
    *   **Weekly Overtime:** e.g., Employee works > 40 hours in a work week.
    *   **Daily Double Overtime:** e.g., Employee works > 12 hours in a single day.
    *   *(The PRD will note these are V1 assumptions of common rules; state-specifics are future considerations).*
5.  **FR-5 Staffing Density Heat-Map:** The system will generate a heat-map visualizing staffing density. 
    *   The grid will dynamically adjust to the time period covered in the uploaded data (e.g., X days by 24 hours).
    *   Each cell (hour block) will be color-coded to indicate the number of employees staffed during that hour (e.g., lighter to darker shades representing low to high staffing counts).
6.  **FR-6 HTML Report with Actionable Insights:** Render an in-browser, mobile-responsive HTML page showing:
    *   **KPI Tiles:**
        *   Estimated Potential Cost of Identified Compliance Violations (based on a V1 default wage if not otherwise determinable).
        *   Estimated Overtime & Double Overtime Costs (based on a V1 default wage and standard time-and-a-half/double-time assumptions).
        *   Total Scheduled Labor Hours (broken down by Regular, Overtime, Double Overtime where applicable).
    *   The Staffing Density Heat-Map (FR-5).
    *   **Compliance Violations Summary:** A list of all general compliance violations identified (FR-4).
    *   **Employee-Specific Summary Table:**
        *   Rows: Each employee from the timesheet.
        *   Columns: Employee Identifier, Total Hours, Regular Hours, Overtime Hours, Double Overtime Hours, List of Specific Violations (e.g., "Meal Break Violation on [Date]"), Suggested Action Steps for each violation type.
    *   **Actionable Advice:** For each type of violation identified in the report (general or employee-specific), provide generic, plain-language suggestions on how to address or prevent such violations in future scheduling (e.g., "For Meal Break Violations: Ensure shifts are scheduled to include a 30-minute unpaid meal break before an employee works 5 consecutive hours. Verify breaks are taken and recorded.").
    *   A plain-language summary of overall key findings and potential cost-saving areas, referencing the identified issues.
    *   Flagged duplicate name issues (FR-3).
7.  **FR-7 Error Handling & Re-Upload:** If parsing fails after reasonable attempts (e.g., 3 LLM retries), show a friendly message explaining the potential cause of failure (e.g., "We couldn't automatically read your timesheet. This can happen with very unusual formats or poor image quality."). 
    *   The system must provide options to the user: a "Try Again" button (to re-upload the same or a corrected file) and/or an "Upload Different File" button.
    *   Since lead information is captured upfront (FR-2), a separate waitlist form is not needed here.
8.  **FR-8 Synchronous SLA:** The end-to-end flow (FR-1 initiation → FR-6 report display) must ideally complete within 30-45 seconds for files ≤ 200 KB or images ≤ 1024 × 1024 pixels (P95), accounting for parallel lead capture.
9.  **FR-9 Basic Logging:** Log raw input type (CSV, XLSX, text, image), parse success/failure, processing time, and captured lead info to a Postgres table.
10. **FR-10 Hourly Wage Handling:**
    *   The system will attempt to identify an hourly wage if present in the uploaded schedule data.
    *   If no wage is found, the system will use a hardcoded default hourly wage (e.g., $18/hour) for cost-related calculations (FR-6 KPIs). This assumption will be clearly stated in the report.
11. **FR-11 Schedule Period Assumption:** The system will assume uploaded schedules typically cover a one or two-week period. Daily calculations (like >8 hours/day) will be based on calendar days.

## 5. Non-Goals (Out of Scope for V1)

*   User authentication, user accounts, or saved history.
*   PDF export, CSV export, or shareable link generation for reports.
*   Billing, subscriptions, or any payment flow.
*   City/state/country-specific labor-law rules beyond the generic overtime/break logic defined in FR-4. A comprehensive, configurable rule engine is a future consideration.
*   User input for sales data or custom sales/labor heuristics (V1 will use a default).
*   User input for hourly wages (V1 will attempt to parse or use a default).
*   Advanced data retention policies or user controls for data deletion (e.g., auto-purge of raw uploads is not a V1 feature).
*   Direct integration with payroll or scheduling software APIs.
*   AI-powered *prescriptive* advice or automated schedule optimization (V1 focuses on highlighting issues and offering generic corrective actions).

## 6. Design Considerations

*   **UI/UX:**
    *   Mobile-first, single-page application flow.
    *   Large tap targets, highly readable fonts, and clear visual hierarchy.
    *   Intuitive drag-and-drop and file upload experience.
*   **Branding:**
    *   Minimal viable branding: Product word-mark text.
    *   Small footer link to a "Privacy Policy" / "Terms of Service" page (content TBD).
*   **Color Palette (Example):**
    *   Overstaffing / Violations: Red (e.g., Tailwind `red-500` / `#ef4444`)
    *   Understaffing: Blue (e.g., Tailwind `blue-500` / `#3b82f6`)
    *   Optimal / Neutral: Green (e.g., Tailwind `green-500` / `#10b981`) or Gray.
*   **Report Layout:** Prioritize clarity and actionability. KPIs at the top, followed by the visual heat-map, then a detailed list of issues.

## 7. Technical Considerations

*   **Proposed Stack:**
    *   Frontend: Next.js 14
    *   Backend: FastAPI (Python 3.11+)
    *   Deployment: Single container on Fly.io (or similar)
    *   Database: Supabase Postgres (for logging and lead capture)
*   **Parsing & OCR / Text Extraction (LLM-centric):**
    *   The primary approach will be to use a powerful multi-modal LLM (e.g., GPT-4o, Gemini) to handle both the OCR/text extraction from images and the subsequent normalization of all input types (images, CSV, XLSX, pasted text, PDF text). 
    *   The LLM will be prompted with the raw input (or image data) and a detailed function-calling schema (Pydantic model) to directly return the structured schedule data.
    *   This minimizes distinct pre-processing steps and centralizes data extraction and structuring within the LLM.
*   **Performance:**
    *   Design the primary analysis endpoint to be fully asynchronous.
    *   Consider streaming partial OCR text to the LLM if initial full-file processing approaches the 30s budget.
*   **Error Budget & Retries:** If LLM parsing fails, implement a retry mechanism (e.g., up to 3 times with slight variations in prompting or parameters if applicable) before branching to the FR-7 waitlist UI.
*   **Privacy Placeholder:** The report footer and potentially the upload area should include placeholder text for a privacy statement. Example: `"[Placeholder for Data Privacy & Terms of Use Statement. We temporarily process your schedule data to provide this analysis. See our full policy here.]"`

## 8. Success Metrics

1.  **SM-1 Processing Time:** P95 processing time (upload to report) ≤ 30 seconds.
2.  **SM-2 Parse Accuracy:** ≥ 90% parse success rate on a curated test set of 20 diverse schedule inputs (representing common formats and edge cases).
3.  **SM-3 Lead Generation:** ≥ 75% of successful schedule analyses result in captured lead information.
4.  **SM-4 User Satisfaction (Beta):** ≥ 80% of beta users rate the tool's usefulness as ≥ 4/5 via a simple post-report survey (e.g., thumbs up/down or a single-question scale).
5.  **SM-5 Reduction in Labor Cost Queries:** (Longer-term, post-MVP qualitative feedback) Anecdotal evidence from users indicating the tool helped them identify and reduce labor costs.

## 9. Open Questions

1.  ~~Should we assume a default hourly wage ($18) or ask the user to input it for cost calculation?~~ *(Decision: Attempt to parse from upload; if not found, use a stated default for V1. User input is for future).*
2.  ~~What retention duration do we eventually want for raw uploads (auto-purge suggestion: 30 days)?~~ *(Decision: Not a V1 feature. To be considered post-MVP).*
3.  ~~Any legal copy needed regarding data privacy before accepting uploads?~~ *(Decision: Placeholder copy to be used for V1. Actual legal copy TBD).*
4.  What are the most common, high-impact compliance rules (beyond basic overtime/breaks) that we should prioritize for the "top 5" in a near-future iteration if not V1? (Requires further research/user feedback).
5.  For the Over/Under-Staff Heat-Map (FR-5), what is the simplest effective heuristic if detailed sales data is unavailable? (e.g., a manager-defined simple "peak hours" input, or a very generic business type selection with pre-set peak times?)

## 10. Future Considerations / Post-V1 Roadmap

*   **Advanced Compliance Engine:**
    *   Configurable rule engine for city, state, and country-specific labor laws (e.g., predictive scheduling, minor work rules, clopening).
    *   User-defined compliance rules.
*   **Enhanced Data Input & Customization:**
    *   User input for average hourly wage.
    *   User input for sales data or custom sales/labor heuristics for more accurate heat-map analysis.
    *   Support for PDF schedule uploads.
*   **Integrations:**
    *   API integrations with popular scheduling platforms (e.g., 7shifts, Deputy, Homebase).
    *   POS integration for sales data.
*   **User Accounts & Features:**
    *   User authentication and accounts.
    *   Saved schedule history and trend analysis.
    *   Personalized settings (default wages, preferred compliance rule sets).
*   **Reporting & Sharing:**
    *   Export reports to PDF/CSV.
    *   Generate shareable links for reports.
*   **Proactive Assistance:**
    *   AI-powered schedule optimization suggestions.
    *   "What-if" scenario modeling.
*   **Data Management:**
    *   Defined data retention policies and auto-purge options for uploaded schedules.
*   **Expanded Lead Nurturing:**
    *   More detailed information collection on the waitlist form (e.g., restaurant type, current scheduling pain points) to help prioritize feature development and support for new formats. 