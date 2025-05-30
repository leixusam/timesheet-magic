#!/bin/bash

# Generate Checkmark Icons
# This script converts the SVG checkmark icon to all required PNG formats

echo "🚀 Generating checkmark icons from SVG..."

# Make sure we're in the frontend directory
cd "$(dirname "$0")/.."

# Install dependencies if needed
if ! command -v sharp &> /dev/null; then
    echo "📦 Installing Sharp for image processing..."
    npm install sharp
fi

# Run the conversion script
echo "🔄 Converting SVG to PNG formats..."
node scripts/convert-checkmark-icon.js

echo ""
echo "✨ Checkmark icon generation complete!"
echo ""
echo "📁 Files created:"
echo "   • design-assets/checkmark-icon-1024.png (high-res)"
echo "   • design-assets/checkmark-icon-512.png (high-res)" 
echo "   • design-assets/checkmark-icon-256.png (high-res)"
echo "   • public/favicon.png (32x32 - main favicon)"
echo "   • public/favicon.ico (32x32 - ICO format)"
echo "   • public/favicon-16x16.png"
echo "   • public/favicon-32x32.png"
echo "   • public/favicon-180x180.png (Apple touch icon)"
echo "   • public/favicon-192x192.png (Android icon)"
echo "   • public/favicon-512x512.png (Android icon large)"
echo "   • public/icon-high-res.png (256x256 - Logo component)"
echo ""
echo "🔄 Your website will now use the new checkmark icon!"
echo "🌐 Restart your dev server to see changes: npm run dev" 