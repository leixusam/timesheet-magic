#!/bin/bash

# High-resolution icon creation script for TimeSheet Magic
# Creates a professional icon with better design

echo "Creating high-resolution TimeSheet Magic icon..."

# Create SVG icon with professional design
cat > icon-source.svg << 'EOF'
<svg width="512" height="512" viewBox="0 0 512 512" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#1746d4;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#0d47a1;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="iconGradient" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#ffffff;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#e3f2fd;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Rounded square background -->
  <rect x="0" y="0" width="512" height="512" rx="102" ry="102" fill="url(#bgGradient)"/>
  
  <!-- Subtle shadow/depth -->
  <rect x="8" y="8" width="496" height="496" rx="98" ry="98" fill="rgba(0,0,0,0.1)"/>
  
  <!-- Main timesheet/grid icon -->
  <g transform="translate(128, 100)">
    <!-- Timesheet background -->
    <rect x="0" y="0" width="256" height="320" rx="16" ry="16" fill="url(#iconGradient)" stroke="rgba(255,255,255,0.3)" stroke-width="2"/>
    
    <!-- Header row -->
    <rect x="16" y="16" width="224" height="32" rx="8" ry="8" fill="rgba(0,0,0,0.1)"/>
    
    <!-- Time grid lines -->
    <g stroke="rgba(0,0,0,0.15)" stroke-width="1" fill="none">
      <!-- Vertical lines -->
      <line x1="80" y1="60" x2="80" y2="300"/>
      <line x1="144" y1="60" x2="144" y2="300"/>
      <line x1="208" y1="60" x2="208" y2="300"/>
      
      <!-- Horizontal lines -->
      <line x1="16" y1="80" x2="240" y2="80"/>
      <line x1="16" y1="120" x2="240" y2="120"/>
      <line x1="16" y1="160" x2="240" y2="160"/>
      <line x1="16" y1="200" x2="240" y2="200"/>
      <line x1="16" y1="240" x2="240" y2="240"/>
      <line x1="16" y1="280" x2="240" y2="280"/>
    </g>
    
    <!-- Clock icon overlay -->
    <g transform="translate(200, 200)">
      <circle cx="0" cy="0" r="28" fill="#1746d4" stroke="white" stroke-width="3"/>
      <circle cx="0" cy="0" r="3" fill="white"/>
      <line x1="0" y1="0" x2="0" y2="-16" stroke="white" stroke-width="2" stroke-linecap="round"/>
      <line x1="0" y1="0" x2="12" y2="0" stroke="white" stroke-width="2" stroke-linecap="round"/>
    </g>
    
    <!-- Magic sparkle -->
    <g transform="translate(60, 140)">
      <path d="M0,-12 L3,-3 L12,0 L3,3 L0,12 L-3,3 L-12,0 L-3,-3 Z" fill="#ffd700" opacity="0.9"/>
    </g>
    <g transform="translate(180, 80)">
      <path d="M0,-8 L2,-2 L8,0 L2,2 L0,8 L-2,2 L-8,0 L-2,-2 Z" fill="#ffd700" opacity="0.7"/>
    </g>
  </g>
  
  <!-- Subtle highlight on top -->
  <rect x="0" y="0" width="512" height="256" rx="102" ry="102" fill="url(#topHighlight)" opacity="0.1"/>
  
  <defs>
    <linearGradient id="topHighlight" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#ffffff;stop-opacity:0.3" />
      <stop offset="100%" style="stop-color:#ffffff;stop-opacity:0" />
    </linearGradient>
  </defs>
</svg>
EOF

echo "✅ SVG icon created"

# Convert SVG to high-resolution PNG using available tools
if command -v convert &> /dev/null; then
    echo "Using ImageMagick to convert SVG to PNG..."
    # Create 1024x1024 high-res version
    convert icon-source.svg -resize 1024x1024 -background transparent favicon-1024.png
    # Create standard 512x512 version  
    convert icon-source.svg -resize 512x512 -background transparent favicon.png
    echo "✅ Created favicon.png (512x512) and favicon-1024.png (1024x1024)"
elif command -v rsvg-convert &> /dev/null; then
    echo "Using rsvg-convert to convert SVG to PNG..."
    rsvg-convert -w 1024 -h 1024 icon-source.svg -o favicon-1024.png
    rsvg-convert -w 512 -h 512 icon-source.svg -o favicon.png
    echo "✅ Created favicon.png (512x512) and favicon-1024.png (1024x1024)"
elif command -v inkscape &> /dev/null; then
    echo "Using Inkscape to convert SVG to PNG..."
    inkscape icon-source.svg --export-type=png --export-filename=favicon-1024.png --export-width=1024 --export-height=1024
    inkscape icon-source.svg --export-type=png --export-filename=favicon.png --export-width=512 --export-height=512
    echo "✅ Created favicon.png (512x512) and favicon-1024.png (1024x1024)"
else
    echo "⚠️  No SVG conversion tool found. Please install ImageMagick, rsvg-convert, or Inkscape"
    echo "For now, you can manually convert icon-source.svg to PNG using online tools"
    echo "SVG file created: icon-source.svg"
fi

echo "🎉 High-resolution icon creation complete!"
echo "Files created:"
echo "  📁 icon-source.svg (vector source)"
if [ -f "favicon.png" ]; then
    echo "  📁 favicon.png (512x512)"
fi
if [ -f "favicon-1024.png" ]; then
    echo "  📁 favicon-1024.png (1024x1024)"
fi 