/**
 * Seed Cache Script
 * Reads existing markdown files in data/ and generates cached Gemini results.
 * Run: node backend/seed_cache.js
 */

const fs = require('fs');
const path = require('path');
const { GoogleGenerativeAI } = require('@google/generative-ai');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

// Map filenames to proper city names
function fileToCity(filename) {
  const map = {
    'mississauga': 'Mississauga, Ontario',
    'hamilton': 'Hamilton, Ontario',
    'ottawa': 'Ottawa, Ontario',
    'london': 'London, Ontario',
    'kitchener': 'Kitchener, Ontario',
    'toronto': 'Toronto, Ontario',
    'brampton': 'Brampton, Ontario',
    'windsor': 'Windsor, Ontario',
    'waterloo': 'Waterloo, Ontario',
    'hamilton_ontario': 'Hamilton, Ontario',
    'toronto_ontario': 'Toronto, Ontario',
    'ottawa_ontario': 'Ottawa, Ontario',
    'london_ontario': 'London, Ontario',
    'brampton_ontario': 'Brampton, Ontario',
    'windsor_ontario': 'Windsor, Ontario',
    'waterloo_ontario': 'Waterloo, Ontario',
  };
  
  // Extract city part from filename like "mississauga_20260208_020111.md"
  const parts = filename.replace('.md', '').split('_');
  const cityPart = parts[0];
  
  // Try two-part match first (e.g., hamilton_ontario)
  const twoPart = parts.slice(0, 2).join('_');
  if (map[twoPart]) return map[twoPart];
  if (map[cityPart]) return map[cityPart];
  
  // Fallback: capitalize
  return cityPart.charAt(0).toUpperCase() + cityPart.slice(1) + ', Ontario';
}

function cityToCacheKey(city) {
  return city.toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

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

async function extractMotions(markdown, city) {
  const model = genAI.getGenerativeModel({ 
    model: 'gemini-2.5-flash',
    generationConfig: {
      responseMimeType: 'application/json'
    }
  });

  const content = markdown.slice(0, 15000);

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
  if (!Array.isArray(motions)) motions = [];
  return motions;
}

async function main() {
  const dataDir = path.join(__dirname, '..', 'data');
  const cacheDir = path.join(dataDir, 'cache');
  
  if (!fs.existsSync(cacheDir)) {
    fs.mkdirSync(cacheDir, { recursive: true });
  }

  const files = fs.readdirSync(dataDir)
    .filter(f => f.endsWith('.md') && f !== '.gitkeep');

  console.log(`Found ${files.length} markdown files to cache\n`);

  for (const file of files) {
    const city = fileToCity(file);
    const cacheKey = cityToCacheKey(city);
    const cacheFile = path.join(cacheDir, `${cacheKey}.json`);
    
    // Skip if already cached with motions
    if (fs.existsSync(cacheFile)) {
      try {
        const existing = JSON.parse(fs.readFileSync(cacheFile, 'utf-8'));
        if (existing.motions && existing.motions.length > 0) {
          console.log(`⏭️  ${city} - already cached (${existing.motions.length} motions)`);
          continue;
        }
      } catch {}
    }
    
    console.log(`🔄 Processing ${city} (${file})...`);
    
    try {
      const markdown = fs.readFileSync(path.join(dataDir, file), 'utf-8');
      const metadata = extractMetadata(markdown);
      
      console.log(`   Extracting motions with Gemini...`);
      const motions = await extractMotions(markdown, city);
      
      if (motions.length === 0) {
        console.log(`   ⚠️  No motions found, skipping cache`);
        continue;
      }
      
      const cacheData = {
        city: city,
        metadata: metadata,
        motions: motions,
        markdownFile: `data/${file}`,
        cached_at: new Date().toISOString()
      };
      
      fs.writeFileSync(cacheFile, JSON.stringify(cacheData, null, 2));
      console.log(`   ✅ Cached ${motions.length} motions`);
      
      // Small delay between API calls
      await new Promise(r => setTimeout(r, 2000));
      
    } catch (error) {
      console.log(`   ❌ Error: ${error.message}`);
    }
  }
  
  console.log('\n🎉 Cache seeding complete!');
}

main().catch(console.error);
