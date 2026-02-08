const express = require('express');
const cors = require('cors');
const { spawn } = require('child_process');
const fs = require('fs').promises;
const path = require('path');
const { GoogleGenerativeAI } = require('@google/generative-ai');
require('dotenv').config({ path: path.join(__dirname, '..', '.env') });

const app = express();
const PORT = 3000;

app.use(cors());
app.use(express.json());

// Determine Python executable - use venv if available
const projectRoot = path.join(__dirname, '..');
const venvPython = path.join(projectRoot, 'venv', 'Scripts', 'python.exe');
const pythonExe = require('fs').existsSync(venvPython) ? venvPython : 'python';
console.log(`[INFO] Using Python: ${pythonExe}`);

// Check API key
if (!process.env.GOOGLE_API_KEY) {
  console.error('[ERROR] GOOGLE_API_KEY not found in .env file');
  console.error('[ERROR] Please make sure .env file exists in the project root');
  process.exit(1);
}

// Initialize Gemini
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

// Check if cached data exists for a city (fuzzy matching)
async function checkCache(city) {
  try {
    const cacheDir = path.join(__dirname, '..', 'data', 'cache');
    const fsSync = require('fs');
    
    if (!fsSync.existsSync(cacheDir)) return null;
    
    // Strategy 1: Exact key match
    const citySlug = cityToCacheKey(city);
    const exactFile = path.join(cacheDir, `${citySlug}.json`);
    if (fsSync.existsSync(exactFile)) {
      return await loadCacheFile(exactFile, city);
    }
    
    // Strategy 2: Fuzzy match - extract city core and find any cache file containing it
    const cityCore = extractCityCore(city);
    if (!cityCore) return null;
    
    const cacheFiles = fsSync.readdirSync(cacheDir).filter(f => f.endsWith('.json'));
    for (const file of cacheFiles) {
      const fileCore = file.replace('.json', '').replace(/_ontario$/, '').replace(/_/g, '');
      if (fileCore === cityCore || cityCore.startsWith(fileCore) || fileCore.startsWith(cityCore)) {
        console.log(`[CACHE] Fuzzy match: "${city}" → ${file}`);
        return await loadCacheFile(path.join(cacheDir, file), city);
      }
    }
    
    console.log(`[CACHE MISS] No cache match for "${city}" (slug: ${citySlug}, core: ${cityCore})`);
    return null;
    
  } catch (error) {
    console.error('[CACHE ERROR]', error.message);
    return null;
  }
}

// Load and validate a cache file
async function loadCacheFile(filePath, city) {
  const cacheContent = await fs.readFile(filePath, 'utf-8');
  const cacheData = JSON.parse(cacheContent);
  
  if (!cacheData.motions || cacheData.motions.length === 0) {
    console.log(`[CACHE] Found cached data for ${city} but it has no motions, ignoring`);
    return null;
  }
  
  console.log(`[CACHE HIT] ${city} → ${cacheData.motions.length} motions (cached: ${cacheData.cached_at})`);
  return cacheData;
}

// Normalize city name into a cache key
function cityToCacheKey(city) {
  return city.toLowerCase().trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

// Extract just the city name part (without province) for fuzzy matching
function extractCityCore(input) {
  return input.toLowerCase().trim()
    .replace(/,?\s*(ontario|on|ont)\.?\s*$/i, '')
    .replace(/[^a-z]+/g, '')
    .trim();
}

// Normalize user input - auto-append ", Ontario" if no province given
function normalizeCity(city) {
  const trimmed = city.trim();
  // Already has Ontario in some form
  if (/ontario|\bON\b|\bOnt\b/i.test(trimmed)) {
    // Standardize to "City, Ontario"
    const core = trimmed.replace(/,?\s*(ontario|on|ont)\.?\s*$/i, '').trim();
    return core + ', Ontario';
  }
  // Just a city name - append Ontario
  return trimmed + ', Ontario';
}

// Save data to cache
async function saveToCache(city, data) {
  try {
    const cacheDir = path.join(__dirname, '..', 'data', 'cache');
    const fsSync = require('fs');
    if (!fsSync.existsSync(cacheDir)) {
      fsSync.mkdirSync(cacheDir, { recursive: true });
      console.log(`[CACHE] Created cache directory: ${cacheDir}`);
    }
    
    const citySlug = cityToCacheKey(city);
    const cacheFile = path.join(cacheDir, `${citySlug}.json`);
    
    await fs.writeFile(cacheFile, JSON.stringify(data, null, 2));
    console.log(`[CACHE] Written cache file: ${cacheFile}`);
    
  } catch (error) {
    console.error('[CACHE ERROR] Failed to save cache:', error.message);
  }
}

// Endpoint to scrape and process a city
app.post('/api/scrape', async (req, res) => {
  const { city } = req.body;
  
  if (!city) {
    return res.status(400).json({ error: 'City name is required' });
  }

  // Normalize city input (auto-append Ontario, standardize format)
  const normalizedCity = normalizeCity(city);
  console.log(`[INFO] Request for: "${city}" → normalized: "${normalizedCity}"`);

  try {
    // Step 1: Check cache first (fuzzy match)
    const cachedData = await checkCache(normalizedCity);
    if (cachedData) {
      console.log(`[CACHE HIT] Returning cached data for ${city}`);
      return res.json({
        success: true,
        cached: true,
        ...cachedData
      });
    }

    // Step 2: Cache miss - run Python scraper
    console.log('[CACHE MISS] Running Python scraper...');
    const scraperPath = path.join(__dirname, '..');
    const markdownFile = await runScraper(normalizedCity, scraperPath);
    
    if (!markdownFile) {
      return res.status(500).json({ 
        error: 'Scraper failed to find documents',
        message: `Could not find council minutes for ${normalizedCity}`
      });
    }

    console.log(`[INFO] Scraper completed: ${markdownFile}`);

    // Step 2: Read the markdown file
    const markdownPath = path.join(scraperPath, markdownFile);
    const markdownContent = await fs.readFile(markdownPath, 'utf-8');
    
    // Extract metadata from frontmatter
    const metadata = extractMetadata(markdownContent);

    // Step 3: Extract motions using Gemini
    console.log('[INFO] Extracting motions with Gemini...');
    const motions = await extractMotions(markdownContent, normalizedCity);

    console.log(`[SUCCESS] Extracted ${motions.length} motions`);

    // Step 4: Save to cache (only if we got motions)
    const resultData = {
      city: normalizedCity,
      metadata: metadata,
      motions: motions,
      markdownFile: markdownFile,
      cached_at: new Date().toISOString()
    };
    
    if (motions.length > 0) {
      await saveToCache(normalizedCity, resultData);
      console.log(`[CACHE] Saved ${normalizedCity} to cache (${motions.length} motions)`);
    } else {
      console.log(`[CACHE] Skipping cache for ${normalizedCity} (no motions)`);
    }

    // Step 5: Return the results
    res.json({
      success: true,
      cached: false,
      ...resultData
    });

  } catch (error) {
    console.error('[ERROR]', error);
    res.status(500).json({ 
      error: 'Processing failed', 
      message: error.message 
    });
  }
});

// Run the Python scraper as a subprocess
function runScraper(city, workingDir) {
  return new Promise((resolve, reject) => {
    console.log(`[INFO] Spawning: ${pythonExe} -m newsroom.main "${city}"`);
    console.log(`[INFO] Working dir: ${workingDir}`);
    const pythonProcess = spawn(pythonExe, ['-m', 'newsroom.main', city], {
      cwd: workingDir,
      shell: true,
      env: { ...process.env }
    });

    let output = '';
    let errorOutput = '';
    let markdownFile = null;

    pythonProcess.stdout.on('data', (data) => {
      const text = data.toString();
      output += text;
      console.log(text);
      
      // Extract the output filename
      const match = text.match(/Output: (data[\/\\][^\s]+\.md)/);
      if (match) {
        markdownFile = match[1];
      }
    });

    pythonProcess.stderr.on('data', (data) => {
      errorOutput += data.toString();
      console.error(data.toString());
    });

    pythonProcess.on('close', (code) => {
      console.log(`[INFO] Python process exited with code: ${code}`);
      console.log(`[INFO] Markdown file found: ${markdownFile}`);
      if (markdownFile) {
        // Also try matching just the filename from full output
        resolve(markdownFile);
      } else if (code === 0) {
        // Process succeeded but we missed the filename - check data/ dir
        const dataDir = path.join(workingDir, 'data');
        const fsSync = require('fs');
        try {
          const files = fsSync.readdirSync(dataDir)
            .filter(f => f.endsWith('.md') && f !== '.gitkeep')
            .map(f => ({ name: f, time: fsSync.statSync(path.join(dataDir, f)).mtime }))
            .sort((a, b) => b.time - a.time);
          if (files.length > 0) {
            const latestFile = `data/${files[0].name}`;
            console.log(`[INFO] Found latest file in data/: ${latestFile}`);
            resolve(latestFile);
          } else {
            resolve(null);
          }
        } catch (e) {
          console.error('[ERROR] Could not scan data dir:', e.message);
          resolve(null);
        }
      } else {
        // Non-zero exit
        console.error(`[ERROR] Scraper stderr: ${errorOutput}`);
        resolve(null);
      }
    });

    pythonProcess.on('error', (error) => {
      reject(new Error(`Failed to start scraper: ${error.message}`));
    });
  });
}

// Extract metadata from YAML frontmatter
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

    // Limit content to first 15000 chars to avoid token limits
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
    
    console.log('[DEBUG] Gemini raw response:', response.substring(0, 500));
    
    let motions = JSON.parse(response);
    
    // Ensure it's an array
    if (!Array.isArray(motions)) {
      console.log('[WARNING] Gemini returned non-array, wrapping...');
      motions = [];
    }

    console.log(`[SUCCESS] Parsed ${motions.length} motions from Gemini`);
    return motions;

  } catch (error) {
    console.error('[ERROR] Gemini extraction failed:', error.message);
    console.error('[ERROR] Error details:', error);
    return [];
  }
}

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'CivicSense API is running' });
});

app.listen(PORT, () => {
  console.log(`\n🚀 CivicSense Backend running on http://localhost:${PORT}`);
  console.log(`   Health check: http://localhost:${PORT}/api/health\n`);
});
