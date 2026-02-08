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

// Check API key
if (!process.env.GOOGLE_API_KEY) {
  console.error('[ERROR] GOOGLE_API_KEY not found in .env file');
  console.error('[ERROR] Please make sure .env file exists in the project root');
  process.exit(1);
}

// Initialize Gemini
const genAI = new GoogleGenerativeAI(process.env.GOOGLE_API_KEY);

// Endpoint to scrape and process a city
app.post('/api/scrape', async (req, res) => {
  const { city } = req.body;
  
  if (!city) {
    return res.status(400).json({ error: 'City name is required' });
  }

  console.log(`[INFO] Starting scrape for: ${city}`);

  try {
    // Step 1: Run Python scraper
    console.log('[INFO] Running Python scraper...');
    const scraperPath = path.join(__dirname, '..');
    const markdownFile = await runScraper(city, scraperPath);
    
    if (!markdownFile) {
      return res.status(500).json({ 
        error: 'Scraper failed to find documents',
        message: `Could not find council minutes for ${city}`
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
    const motions = await extractMotions(markdownContent, city);

    console.log(`[SUCCESS] Extracted ${motions.length} motions`);

    // Step 4: Return the results
    res.json({
      success: true,
      city: city,
      metadata: metadata,
      motions: motions,
      markdownFile: markdownFile
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
    const pythonProcess = spawn('python', ['-m', 'newsroom.main', city], {
      cwd: workingDir,
      shell: true
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
      if (code === 0 && markdownFile) {
        resolve(markdownFile);
      } else if (code === 1) {
        // Graceful exit - no documents found
        resolve(null);
      } else {
        reject(new Error(`Scraper failed with code ${code}: ${errorOutput}`));
      }
    });

    pythonProcess.on('error', (error) => {
      reject(new Error(`Failed to start scraper: ${error.message}`));
    });
  });
}

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

    // Limit content to first 15000 chars to avoid token limits
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
