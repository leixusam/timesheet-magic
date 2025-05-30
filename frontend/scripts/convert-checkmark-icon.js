const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

async function convertCheckmarkIcon() {
  const svgPath = path.join(__dirname, '../design-assets/icon-source-checkmark.svg');
  const svgBuffer = fs.readFileSync(svgPath);
  
  // Create design-assets directory if it doesn't exist
  const designAssetsDir = path.join(__dirname, '../design-assets');
  if (!fs.existsSync(designAssetsDir)) {
    fs.mkdirSync(designAssetsDir, { recursive: true });
  }

  // Generate high-resolution PNGs
  const sizes = [1024, 512, 256];
  
  for (const size of sizes) {
    await sharp(svgBuffer)
      .png()
      .resize(size, size)
      .toFile(path.join(designAssetsDir, `checkmark-icon-${size}.png`));
    
    console.log(`✅ Generated checkmark-icon-${size}.png`);
  }

  // Generate favicon sizes
  const faviconSizes = [16, 32, 180, 192, 512];
  
  for (const size of faviconSizes) {
    await sharp(svgBuffer)
      .png()
      .resize(size, size)
      .toFile(path.join(__dirname, `../public/favicon-${size}x${size}.png`));
    
    console.log(`✅ Generated favicon-${size}x${size}.png`);
  }

  // Generate main favicon.png (32x32)
  await sharp(svgBuffer)
    .png()
    .resize(32, 32)
    .toFile(path.join(__dirname, '../public/favicon.png'));
  
  console.log('✅ Generated favicon.png');

  // Generate high-resolution icon for Logo component (256x256)
  await sharp(svgBuffer)
    .png()
    .resize(256, 256)
    .toFile(path.join(__dirname, '../public/icon-high-res.png'));
  
  console.log('✅ Generated icon-high-res.png for Logo component');

  // Generate favicon.ico
  await sharp(svgBuffer)
    .png()
    .resize(32, 32)
    .toFile(path.join(__dirname, '../public/favicon.ico'));
  
  console.log('✅ Generated favicon.ico');

  console.log('\n🎉 All checkmark icons generated successfully!');
  console.log('📁 High-res PNGs: design-assets/checkmark-icon-*.png');
  console.log('📁 Favicons: public/favicon*.png and favicon.ico');
  console.log('📁 Logo component: public/icon-high-res.png');
}

convertCheckmarkIcon().catch(console.error); 