/**
 * Cache Generator - Convert existing markdown files to JSON cache
 * Run this to pre-populate the cache with already-scraped cities
 */

const fs = require('fs').promises;
const path = require('path');
const { GoogleGenerativeAI } = require('@google/generative-ai');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

// Extract metadata from YAML frontmatter
function extractMetadata(markdown) {
  const frontmatterMatch = markdown.match(/^---\n([\s\S]+?)\n---/);
  if (!frontmatterMatch) return {};

  const frontmatter = frontmatterMatch[1];
  const metadata = {};
  
  const lines = frontmatter.split('\n');
  lines.forEach(line => {
    const match = line.match(/^(\w+):\s*"?(.+?)"?$/);
    if (match) {
      metadata[match[1]] = match[2].replace(/^"|"$/g, '');
    }
  });

  return metadata;
}

// Extract motions using Gemini
async function extractMotions(markdown, city) {
  try {
    const model = genAI.getGenerativeModel({ 
      model: 'gemini-2.5-flash',
      generationConfig: {
        responseMimeType: 'application/json'
      }
    });

    const content = markdown.slice(0, 10000);

    const prompt = `Analyze this city council meeting minutes and extract all motions, decisions, and bylaws that were voted on or approved.

Return a JSON array where each motion has:
{
  "id": <number>,
  "title": "<short plain-language title, max 80 chars>",
  "summary": "<one sentence explaining impact on residents>",
  "status": "<PASSED|FAILED|DEFERRED|AMENDED>",
  "category": "<parking|housing|budget|development|environment|transportation|services|governance|other>",
  "impact_tags": ["<tag1>", "<tag2>"],
  "full_text": "<complete motion text>"
}

IMPORTANT:
- Focus on substantive decisions that affect residents
- Skip procedural items (agenda approval, declarations of interest)
- Use plain language, not government jargon
- Extract 5-15 most important motions
- Prioritize resident impact

Meeting content for ${city}:
${content}`;

    const result = await model.generateContent(prompt);
    const response = result.response.text();
    
    let motions = JSON.parse(response);
    
    if (!Array.isArray(motions)) {
      motions = [];
    }

    return motions;

  } catch (error) {
    console.error(`[ERROR] Gemini extraction failed for ${city}:`, error.message);
    return [];
  }
}

// Process a single markdown file
async function processMarkdownFile(filePath, cacheDir) {
  try {
    console.log(`\nProcessing: ${path.basename(filePath)}`);
    
    // Read markdown
    const markdown = await fs.readFile(filePath, 'utf-8');
    
    // Extract metadata
    const metadata = extractMetadata(markdown);
    const city = metadata.city || 'Unknown';
    
    console.log(`  City: ${city}`);
    
    // Extract motions with Gemini
    console.log(`  Extracting motions with AI...`);
    const motions = await extractMotions(markdown, city);
    console.log(`  Found ${motions.length} motions`);
    
    // Create cache object
    const cacheData = {
      city: city,
      metadata: metadata,
      motions: motions,
      cached_at: new Date().toISOString(),
      source_file: path.basename(filePath)
    };
    
    // Generate cache filename (normalize city name)
    const citySlug = city.toLowerCase()
      .replace(/[^a-z0-9]+/g, '_')
      .replace(/^_+|_+$/g, '');
    
    const cacheFilePath = path.join(cacheDir, `${citySlug}.json`);
    
    // Save to cache
    await fs.writeFile(cacheFilePath, JSON.stringify(cacheData, null, 2));
    console.log(`  ✓ Cached to: ${path.basename(cacheFilePath)}`);
    
    return cacheData;
    
  } catch (error) {
    console.error(`[ERROR] Failed to process ${filePath}:`, error.message);
    return null;
  }
}

// Main function
async function main() {
  console.log('=== CivicSense Cache Generator ===\n');
  
  // Setup paths
  const dataDir = path.join(__dirname, '..', 'data');
  const cacheDir = path.join(__dirname, 'cache');
  
  // Create cache directory
  try {
    await fs.mkdir(cacheDir, { recursive: true });
    console.log(`Cache directory: ${cacheDir}\n`);
  } catch (error) {
    console.error('Failed to create cache directory:', error);
    process.exit(1);
  }
  
  // Find all markdown files
  const files = await fs.readdir(dataDir);
  const markdownFiles = files
    .filter(f => f.endsWith('.md') && f !== '.gitkeep')
    .map(f => path.join(dataDir, f));
  
  console.log(`Found ${markdownFiles.length} markdown files to process\n`);
  
  if (markdownFiles.length === 0) {
    console.log('No markdown files found in data/ directory');
    console.log('Run the scraper first to generate some data');
    process.exit(0);
  }
  
  // Process each file
  let successCount = 0;
  for (const file of markdownFiles) {
    const result = await processMarkdownFile(file, cacheDir);
    if (result) successCount++;
    
    // Small delay to avoid rate limiting
    await new Promise(resolve => setTimeout(resolve, 1000));
  }
  
  console.log(`\n=== Complete ===`);
  console.log(`Successfully cached ${successCount}/${markdownFiles.length} cities`);
  console.log(`Cache location: ${cacheDir}`);
}

// Run
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
