const fs = require('fs');
const sharp = require('sharp');

async function convertSvgToPng() {
  console.log('Converting SVG to high-resolution PNG...');
  
  try {
    // Read the SVG file
    const svgBuffer = fs.readFileSync('icon-source.svg');
    
    // Convert to high-resolution PNG (1024x1024)
    await sharp(svgBuffer)
      .resize(1024, 1024)
      .png()
      .toFile('favicon-1024.png');
    
    console.log('✅ Created favicon-1024.png (1024x1024)');
    
    // Convert to standard PNG (512x512)
    await sharp(svgBuffer)
      .resize(512, 512)
      .png()
      .toFile('favicon.png');
    
    console.log('✅ Created favicon.png (512x512)');
    
    // Also create a smaller version for better quality at small sizes
    await sharp(svgBuffer)
      .resize(256, 256)
      .png()
      .toFile('favicon-256.png');
    
    console.log('✅ Created favicon-256.png (256x256)');
    
    console.log('🎉 All icon sizes created successfully!');
    
  } catch (error) {
    console.error('❌ Error converting SVG:', error.message);
    process.exit(1);
  }
}

convertSvgToPng(); 