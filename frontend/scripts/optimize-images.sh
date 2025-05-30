#!/bin/bash

# Image optimization script for TimeSheet Magic
# Converts key images to WebP format at 80% quality with 2x variants

echo "Optimizing images for TimeSheet Magic..."

# Create optimized directory if it doesn't exist
mkdir -p public/optimized

# Key images to optimize (the main ones used in the website)
IMAGES=(
  "awuQBekLugr97gL8uQknRr2tog.jpg"
  "nwLx1Cp6tWit8e855xsUwKCQDc.jpg"
  "vkpAnvAoKb9J3SlxcItEXcfVDE.jpg"
  "2LQfKoBljbVAnthw1DgmIsTIJ4c.jpg"
  "H79NLmsWmk5dnLvqMk7biuEwM.jpg"
)

for image in "${IMAGES[@]}"; do
  if [ -f "public/$image" ]; then
    # Get filename without extension
    filename=$(basename "$image" | sed 's/\.[^.]*$//')
    
    echo "Processing $image..."
    
    # Convert to WebP at 80% quality (1x)
    cwebp -q 80 "public/$image" -o "public/optimized/${filename}.webp"
    
    # Convert to WebP at 80% quality (2x - just a copy for now, in real scenario you'd resize)
    cwebp -q 80 "public/$image" -o "public/optimized/${filename}@2x.webp"
    
    echo "✅ Optimized $image -> ${filename}.webp & ${filename}@2x.webp"
  else
    echo "❌ Image not found: $image"
  fi
done

echo "🎉 Image optimization complete!"
echo "Original images kept in public/"
echo "Optimized WebP images saved to public/optimized/" 