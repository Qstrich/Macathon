# CivicSense

**Autonomous agent that finds and summarizes local government news from City Council meeting minutes.**

## 🎯 Concept

Most people don't read City Council meeting minutes because they're boring PDFs. CivicSense autonomously scrapes city documents and transforms them into a "Daily Briefing" news feed, explaining how new bylaws affect you (e.g., "Parking fines on King St. just went up").

## 🚀 Quick Start

### Prerequisites

- **Python 3.11** (Required for docling stability)
- Google AI API Key ([Get one here](https://aistudio.google.com/apikey))

### Installation

1. **Clone the repository** (or download the files)

2. **Create a virtual environment**:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**:
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit .env and add your API key
   GOOGLE_API_KEY=your_actual_api_key_here
   ```

### Usage

Run the CLI with a city name:

```bash
python -m newsroom.main "Hamilton, Ontario"
```

The agent will:
1. 🔍 Search the web for the city's official Council Minutes repository
2. 🤖 Use Gemini 2.0 Flash to identify the official government link
3. 🌐 Navigate the page to find the latest PDF
4. 📄 Parse the PDF into clean Markdown with AI-powered layout analysis
5. 💾 Save the result to the `data/` directory

## 🏗️ Architecture

### Tech Stack

- **AI Model**: Gemini 2.0 Flash (via `google-genai` SDK)
- **Search**: DuckDuckGo Search
- **Web Crawling**: Crawl4AI (async)
- **PDF Parsing**: Docling (IBM)
- **Validation**: Pydantic v2

### Project Structure

```
civic-sense/
├── .env.example            # Environment variable template
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── newsroom/
│   ├── __init__.py
│   ├── main.py             # CLI Entry point (Async)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── scout.py        # Search + AI Filter
│   │   └── navigator.py    # Web crawler for PDF discovery
│   └── processors/
│       ├── __init__.py
│       └── parser.py       # Docling PDF-to-Markdown converter
└── data/                   # Output directory for .md files
```

## 🧠 How It Works

### 1. Scout Agent (`scout.py`)
- Performs DuckDuckGo search for city council minutes
- Uses Gemini 2.0 Flash to analyze results with structured output (Pydantic)
- Filters out news articles and identifies the **official government source**
- Returns the URL with confidence score and reasoning

### 2. Navigator Agent (`navigator.py`)
- Uses Crawl4AI to asynchronously crawl the official website
- Parses HTML to find all PDF links
- Extracts dates from link text and surrounding context
- Returns the **latest available PDF** based on date sorting

### 3. PDF Parser (`parser.py`)
- Downloads the PDF using aiohttp
- Converts PDF to Markdown using **Docling** (layout-aware parsing)
- Adds YAML frontmatter with metadata:
  - City name
  - Meeting date
  - Source URLs
  - Processing timestamp
- Saves to `data/` directory with standardized filename

## 📝 Example Output

The generated Markdown file includes:

```markdown
---
title: "Hamilton, Ontario Council Meeting Minutes"
city: "Hamilton, Ontario"
meeting_date: 2024-01-15
source_url: "https://hamilton.ca/council/meetings"
pdf_url: "https://hamilton.ca/council/minutes/2024-01-15.pdf"
processed_date: "2024-01-16 10:30:00"
generated_by: "CivicSense"
---

# Council Meeting Minutes - January 15, 2024

[Converted content from PDF with preserved layout...]
```

## 🛠️ Error Handling

The system gracefully handles:
- ❌ Missing API keys (exits with helpful message)
- ❌ No official source found (exits after scout phase)
- ❌ No PDFs available (exits after navigation phase)
- ❌ Download failures (reports error and exits)
- ❌ Low confidence AI results (requires >0.5 confidence)

## 🔧 Configuration

### Environment Variables

- `GOOGLE_API_KEY`: Your Google AI API key (required)

### Customization

You can modify:
- `scout.py`: Adjust `max_results` or confidence threshold
- `navigator.py`: Add custom date patterns or PDF filtering logic
- `parser.py`: Change output directory or frontmatter fields

## 📦 Dependencies

Key dependencies:
- `google-genai==0.3.0` - New 2025 Unified Google AI SDK
- `crawl4ai==0.4.248` - Async web crawler
- `docling==2.16.2` - IBM PDF parser
- `duckduckgo-search==7.0.1` - Search API
- `pydantic==2.10.4` - Data validation

See `requirements.txt` for full list.

## 🚧 Known Limitations

- Only supports cities with publicly accessible PDF minutes
- Requires Python 3.11 for Docling compatibility
- Date extraction may fail on unconventional date formats
- Some government sites may block automated crawlers

## 🔮 Future Enhancements

- [ ] Multi-city batch processing
- [ ] Sentiment analysis of meeting topics
- [ ] Email digest notifications
- [ ] Web UI for browsing processed documents
- [ ] LLM-powered summarization into "plain English" news briefs

## 📄 License

MIT License - Feel free to use and modify for your own projects!

## 🙏 Acknowledgments

- Built with [Docling](https://github.com/DS4SD/docling) by IBM
- Powered by [Gemini 2.0 Flash](https://deepmind.google/technologies/gemini/)
- Search by [DuckDuckGo](https://duckduckgo.com)

---

**Made with ❤️ for civic engagement**
