#!/bin/bash

# Favicon processing script for TimeSheet Magic
# Converts favicon.png to multiple formats and sizes required by browsers

echo "Processing favicon for TimeSheet Magic..."

# Check if source favicon exists
if [ ! -f "favicon.png" ]; then
    echo "❌ favicon.png not found in the root directory"
    exit 1
fi

# Create app directory for Next.js App Router favicons
mkdir -p src/app

# Copy original favicon to public folder
cp favicon.png public/favicon.png

echo "Processing favicon into multiple formats..."

# Generate different sizes using ImageMagick/convert or sips (macOS built-in)
if command -v convert &> /dev/null; then
    echo "Using ImageMagick convert..."
    # 16x16 favicon
    convert favicon.png -resize 16x16 public/favicon-16x16.png
    # 32x32 favicon  
    convert favicon.png -resize 32x32 public/favicon-32x32.png
    # Apple touch icon (180x180)
    convert favicon.png -resize 180x180 public/apple-touch-icon.png
    # Android chrome icons
    convert favicon.png -resize 192x192 public/android-chrome-192x192.png
    convert favicon.png -resize 512x512 public/android-chrome-512x512.png
    # Convert to ICO format
    convert favicon.png -resize 32x32 public/favicon.ico
elif command -v sips &> /dev/null; then
    echo "Using macOS sips..."
    # 16x16 favicon
    sips -Z 16 favicon.png --out public/favicon-16x16.png
    # 32x32 favicon
    sips -Z 32 favicon.png --out public/favicon-32x32.png
    # Apple touch icon (180x180)
    sips -Z 180 favicon.png --out public/apple-touch-icon.png
    # Android chrome icons
    sips -Z 192 favicon.png --out public/android-chrome-192x192.png
    sips -Z 512 favicon.png --out public/android-chrome-512x512.png
    # For ICO, we'll just copy the 32x32 PNG
    sips -Z 32 favicon.png --out public/favicon.ico
else
    echo "⚠️  No image processing tool found (ImageMagick or sips)"
    echo "Copying original favicon.png to public folder only"
    cp favicon.png public/favicon.png
fi

# Create Next.js App Router favicon
cp favicon.png src/app/favicon.png

# Create site.webmanifest for PWA support
cat > public/site.webmanifest << EOF
{
    "name": "TimeSheet Magic",
    "short_name": "TimeSheet Magic",
    "icons": [
        {
            "src": "/android-chrome-192x192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/android-chrome-512x512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ],
    "theme_color": "#1746d4",
    "background_color": "#ffffff",
    "display": "standalone"
}
EOF

echo "✅ Favicon processing complete!"
echo "Generated files:"
echo "  📁 public/favicon.png (original)"
echo "  📁 public/favicon-16x16.png"
echo "  📁 public/favicon-32x32.png"
echo "  📁 public/favicon.ico"
echo "  📁 public/apple-touch-icon.png"
echo "  📁 public/android-chrome-192x192.png"
echo "  📁 public/android-chrome-512x512.png"
echo "  📁 public/site.webmanifest"
echo "  📁 src/app/favicon.png (Next.js App Router)" 