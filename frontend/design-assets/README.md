# ShiftIQ Icon Assets

This folder contains the source files and high-resolution variants of the ShiftIQ icon.

## Files

- **icon-source.svg** - Vector source file (can be edited in any vector graphics editor)
- **favicon-1024.png** - High-resolution PNG (1024x1024) for future use
- **favicon-256.png** - Medium resolution PNG (256x256)

## Design Description

The icon features:
- **Blue gradient background** (#1746d4 to #0d47a1) representing trust and professionalism
- **Timesheet grid** showing a realistic timesheet layout with rows and columns
- **Clock overlay** indicating time tracking functionality
- **Magic sparkles** representing the AI/automation aspect
- **Modern rounded corners** following contemporary design trends

## Usage

The main favicon.png (512x512) in the root directory is used to generate all the required favicon variants automatically via the `process-favicon.sh` script.

All favicon sizes are automatically generated and placed in:
- `public/favicon-16x16.png`
- `public/favicon-32x32.png`
- `public/favicon.ico`
- `public/apple-touch-icon.png`
- `public/android-chrome-192x192.png`
- `public/android-chrome-512x512.png`
- `src/app/favicon.png` (Next.js App Router)

## Regenerating Icons

To regenerate all favicon variants:
1. Edit `design-assets/icon-source.svg` if needed
2. Run `node scripts/convert-icon.js` to create PNG versions
3. Run `./scripts/process-favicon.sh` to generate all favicon variants
