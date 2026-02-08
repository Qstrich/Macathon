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
    'mcmaster': 'McMaster, Ontario',
    'mcmaster_ontario': 'McMaster, Ontario',
  };
  
  const parts = filename.replace('.md', '').split('_');
  const cityPart = parts[0];
  const twoPart = parts.slice(0, 2).join('_');
  if (map[twoPart]) return map[twoPart];
  if (map[cityPart]) return map[cityPart];
  return cityPart.charAt(0).toUpperCase() + cityPart.slice(1) + ', Ontario';
}

function cityToCacheKey(city) {
  return city.toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

function extractMetadata(markdown) {
  // Normalize line endings to \n (Windows files may use \r\n)
  const normalized = markdown.replace(/\r\n/g, '\n');
  const frontmatterMatch = normalized.match(/^---\n([\s\S]+?)\n---/);
  if (!frontmatterMatch) return {};
  const frontmatter = frontmatterMatch[1];
  const metadata = {};
  const lines = frontmatter.split('\n');
  lines.forEach(line => {
    const match = line.match(/^([\w_]+):\s*(.+)$/);
    if (match) {
      // Strip surrounding quotes
      metadata[match[1]] = match[2].replace(/^"|"$/g, '').trim();
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

  const prompt = `You are a local news translator. Read these city council meeting minutes and extract the key decisions that were made.

Your audience is everyday residents who have NO background in government. Explain everything like you're telling a neighbour what happened at the meeting.

Return a JSON array where each item has:
{
  "id": <number>,
  "title": "<short headline a newspaper would use, max 80 chars>",
  "summary": "<1-2 sentences explaining what this means for regular people living in the city. No acronyms, no bylaw numbers, no legal language. Focus on: what changed, who it affects, and why it matters.>",
  "status": "<PASSED|FAILED|DEFERRED|AMENDED>",
  "category": "<parking|housing|budget|development|environment|transportation|services|governance|other>",
  "impact_tags": ["<plain English tag>", "<plain English tag>"],
  "full_text": "<the original motion text from the minutes>"
}

Rules:
- SKIP procedural items (approving the agenda, confirming minutes, declarations of interest)
- SKIP items that are just receiving reports for information with no decision
- Translate ALL government jargon: "bylaw amendment" → "rule change", "zoning" → "land use rules", "debenture" → "borrowing/loan"
- Titles should be understandable by a high school student
- Summaries should answer: "So what does this mean for me?"
- Extract the 5-15 most impactful decisions
- If fewer than 5 substantive decisions exist, return what you find

Meeting minutes from ${city}:
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

  const allFiles = fs.readdirSync(dataDir)
    .filter(f => f.endsWith('.md') && f !== '.gitkeep');

  // Group files by city and pick the largest one per city (most content = best results)
  const cityFileMap = {};
  for (const file of allFiles) {
    const city = fileToCity(file);
    const cacheKey = cityToCacheKey(city);
    const fileSize = fs.statSync(path.join(dataDir, file)).size;
    if (!cityFileMap[cacheKey] || fileSize > cityFileMap[cacheKey].size) {
      cityFileMap[cacheKey] = { file, city, size: fileSize };
    }
  }

  const entries = Object.values(cityFileMap);
  console.log(`Found ${allFiles.length} markdown files, ${entries.length} unique cities to process\n`);

  for (const { file, city } of entries) {
    const cacheKey = cityToCacheKey(city);
    const cacheFile = path.join(cacheDir, `${cacheKey}.json`);
    
    console.log(`Processing ${city} (${file})...`);
    
    try {
      const markdown = fs.readFileSync(path.join(dataDir, file), 'utf-8');
      const metadata = extractMetadata(markdown);
      
      console.log(`   Metadata: source=${metadata.source_url ? 'yes' : 'no'}, doc=${metadata.document_url ? 'yes' : 'no'}`);
      console.log(`   Extracting motions with Gemini (new prompt)...`);
      const motions = await extractMotions(markdown, city);
      
      if (motions.length === 0) {
        console.log(`   No motions found, skipping cache`);
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
      console.log(`   Cached ${motions.length} motions\n`);
      
      // Small delay between API calls
      await new Promise(r => setTimeout(r, 2000));
      
    } catch (error) {
      console.log(`   Error: ${error.message}\n`);
    }
  }
  
  console.log('Cache seeding complete!');
}

main().catch(console.error);
