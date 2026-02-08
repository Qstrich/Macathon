"""
Scout Agent - Search and identify official government sources using AI.
"""

from typing import Optional
from pydantic import BaseModel, Field
from ddgs import DDGS
from google import genai


class OfficialSource(BaseModel):
    """Structured response for official source identification."""
    url: str = Field(description="The official government council minutes repository URL")
    reasoning: str = Field(description="Explanation of why this is the official source")
    confidence: float = Field(description="Confidence score between 0 and 1", ge=0, le=1)


class SearchResult(BaseModel):
    """Individual search result."""
    title: str
    url: str
    snippet: str


class ScoutAgent:
    """
    Agent responsible for finding official government sources.
    Uses DuckDuckGo for search and Gemini for intelligent filtering.
    """
    
    def __init__(self, max_results: int = 10):
        """
        Initialize Scout Agent.
        
        Args:
            max_results: Maximum number of search results to analyze
        """
        self.max_results = max_results
        self.client = genai.Client()  # Automatically loads GOOGLE_API_KEY from env
    
    async def find_official_source(self, city_name: str) -> Optional[OfficialSource]:
        """
        Find the official council minutes repository for a given city.
        Uses multiple search strategies to find actual meeting documents.
        
        Args:
            city_name: Name of the city (e.g., "Hamilton, Ontario")
        
        Returns:
            OfficialSource with URL and reasoning, or None if not found
        """
        # Extract province/state if provided for better targeting
        location_parts = city_name.split(',')
        city_only = location_parts[0].strip()
        region = location_parts[1].strip() if len(location_parts) > 1 else ""
        
        # Step 1: Try multiple search queries with region specificity
        # Focus on finding actual meeting MINUTES, not bylaws or legislation
        # Prioritize meeting portals (eSCRIBE, TMMIS) for reliable document access
        # Cleaning the input for better search accuracy
        city_clean = city_name.lower().replace("city of", "").strip()
        region_clean = region.lower().strip() if region else ""
        location_query = f"{city_clean} {region_clean}".strip()

        search_queries = [
            # --- TIER 1: The "Big 3" Vendor Portals (Best Data) ---
            # These platforms host 80% of municipal data. finding the portal URL is better than finding a single PDF.
            
            # eSCRIBE (Common in Canada/US) - usually pub-[city].escribemeetings.com
            f"site:escribemeetings.com {city_clean} \"council\"",
            
            # Granicus / Legistar (Common in large US/Canadian cities)
            f"site:legistar.com {city_clean}",
            f"site:granicus.com {city_clean} \"minutes\"",

            # CivicWeb / iCompass (Common in small/mid-sized towns)
            f"site:civicweb.net {city_clean}",
            f"site:civicplus.com {city_clean} \"agenda center\"",
            
            # --- TIER 2: The "Portal" Hunters (Finding the Landing Page) ---
            # These look for the page where the list of minutes lives.
            
            f"\"{city_clean}\" council \"meeting portal\"",
            f"\"{city_clean}\" \"agendas and minutes\" portal",
            f"\"{city_clean}\" \"legislative calendar\" 2026",
            f"\"{city_clean}\" \"clerk\" \"minutes\" archive",

            # --- TIER 3: Direct File Hunting (The Fallback) ---
            # Specific keywords that appear INSIDE the minutes PDF, not just the title.
            
            # "Regular Council Meeting" is the formal term for the main monthly meeting
            f"\"{city_clean}\" \"regular council meeting\" minutes filetype:pdf 2026",
            
            # "Disposition" is a technical term often used instead of "Minutes" in some jurisdictions
            f"\"{city_clean}\" council disposition filetype:pdf 2026",
            
            # Targeted 'clerk' search (The Clerk is legally responsible for minutes)
            f"\"{location_query}\" clerk minutes 2026 filetype:pdf"
        ]

        # Regional Specifics (Toronto uses a custom system called TMMIS)
        if 'toronto' in city_clean:
            search_queries.insert(0, f"site:toronto.ca \"decision body\" minutes 2026")
                
        # Add French queries for Quebec cities
        if region and 'quebec' in region.lower():
            search_queries.extend([
                f'{city_name} "procès-verbal" conseil 2026',  # French for "minutes"
                f'{city_name} "ordre du jour" conseil 2026',  # French for "agenda"
            ])
        
        # Remove None values
        search_queries = [q for q in search_queries if q]
        
        all_results = []
        for query in search_queries:
            print(f"   Searching: {query}")
            try:
                results = await self._search_duckduckgo(query)
                if results:
                    all_results.extend(results)
                    print(f"      Found {len(results)} results")
            except Exception as e:
                print(f"      Search error: {e}")
                continue
        
        if not all_results:
            print("   No search results found")
            return None
        
        # Deduplicate by URL
        seen_urls = set()
        unique_results = []
        for result in all_results:
            if result.url not in seen_urls:
                seen_urls.add(result.url)
                unique_results.append(result)
        
        print(f"   Total unique results: {len(unique_results)}, analyzing with AI...")
        
        # Step 2: Use Gemini to identify the best source with enhanced prompt
        official_source = await self._filter_with_ai_enhanced(city_name, unique_results[:15])
        
        # Fallback: If AI fails, use enhanced heuristic
        if not official_source:
            print("   AI filtering unavailable, using enhanced fallback...")
            official_source = self._simple_filter(unique_results)
        
        return official_source
    
    async def _search_duckduckgo(self, query: str) -> list[SearchResult]:
        """
        Perform a DuckDuckGo search.
        
        Args:
            query: Search query string
        
        Returns:
            List of SearchResult objects
        """
        results = []
        
        try:
            with DDGS() as ddgs:
                raw_results = list(ddgs.text(query, max_results=self.max_results))
                
                for result in raw_results:
                    results.append(SearchResult(
                        title=result.get('title', ''),
                        url=result.get('href', ''),
                        snippet=result.get('body', '')
                    ))
        except Exception as e:
            print(f"   DuckDuckGo search error: {e}")
        
        return results
    
    async def _filter_with_ai_enhanced(
        self, 
        city_name: str, 
        results: list[SearchResult]
    ) -> Optional[OfficialSource]:
        """
        Use Gemini with enhanced prompting to find actual meeting documents.
        
        Args:
            city_name: Name of the city being searched
            results: List of search results to analyze
        
        Returns:
            OfficialSource if identified, None otherwise
        """
        # Format search results for AI analysis with emphasis on URLs
        results_text = "\n".join([
            f"{i+1}. URL: {r.url}\n   Title: {r.title}\n   Snippet: {r.snippet}"
            for i, r in enumerate(results[:15])  # Limit to top 15
        ])
        
        # Extract location for verification
        location_parts = city_name.split(',')
        city_only = location_parts[0].strip().lower()
        region = location_parts[1].strip().lower() if len(location_parts) > 1 else ""
        
        prompt = f"""
You are a Municipal Data Archivist for {city_name}, {region}. 
Your goal is to identify the OFFICIAL repository where this city publishes its Council Meeting Minutes and Agendas.

Analyze the search results below and identify the SINGLE BEST URL.

### 1. STRICT LOCATION VERIFICATION (Critical)
- **Target:** {city_name}, {region} (Canada).
- **REJECT** any results for:
  - {city_name} in the USA (e.g., Hamilton OH, London KY).
  - {city_name} in the UK/Australia.
  - Counties/Regions with similar names but wrong jurisdiction.

### 2. SCORING HIERARCHY (From Best to Worst)
**TIER 1: The "Gold Mine" (Vendor Portals)**
*These are dedicated subdomains hosting all documents. PICK THESE FIRST.*
- **eSCRIBE:** `pub-{city_name.replace(' ', '').lower()}.escribemeetings.com`
- **CivicWeb:** `{city_name}.civicweb.net`
- **Granicus/Legistar:** `{city_name}.legistar.com`
- **Hyland:** `pub-{city_name}.hylandcloud.com`

**TIER 2: The "Library" (Official Landing Pages)**
*City website pages that list meeting dates.*
- URLs containing `/council-meetings`, `/agendas-and-minutes`, `/legislative-calendar`.
- **CORRECTION:** Do NOT reject "Calendar" pages if they are on a government domain. These are often the only way to access documents.

**TIER 3: Direct Files (Fallback)**
*Use only if no Portal or Landing Page is found.*
- Direct links to `.pdf` files.
- Must contain "minutes" or "agenda" in the URL/Title.
- Must be dated **2025** or **2026**.

### 3. NEGATIVE CONSTRAINTS (Ignore These)
- News articles (CBC, Global News, etc.).
- Social media (Facebook, Twitter/X).
- "Committee of Adjustment" or "Police Board" (unless specifically asked for).
- broken or "404" looking links.

### SEARCH RESULTS TO ANALYZE:
{results_text}
"""
        try:
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': OfficialSource,
                },
            )
            
            official_source = response.parsed
            
            # More lenient threshold since we have better prompting
            if official_source.confidence < 0.4:
                print(f"   AI confidence too low ({official_source.confidence:.2f})")
                return None
            
            return official_source
            
        except Exception as e:
            print(f"   AI filtering error: {e}")
            return None
    
    async def _filter_with_ai(
        self, 
        city_name: str, 
        results: list[SearchResult]
    ) -> Optional[OfficialSource]:
        """Legacy method - redirects to enhanced version."""
        return await self._filter_with_ai_enhanced(city_name, results)
    
    def _simple_filter(self, results: list[SearchResult]) -> Optional[OfficialSource]:
        """
        Simple fallback filter when AI is unavailable.
        Looks for official government domains (.gov, .ca, .org).
        
        Args:
            results: List of search results
        
        Returns:
            OfficialSource if found, None otherwise
        """
        # Enhanced scoring with emphasis on PDFs and recent dates
        scored_results = []
        
        for result in results:
            score = 0
            url_lower = result.url.lower()
            title_lower = result.title.lower()
            snippet_lower = result.snippet.lower()
            combined = url_lower + title_lower + snippet_lower
            
            # HIGHEST PRIORITY: Direct PDF links to minutes/agendas
            if url_lower.endswith('.pdf'):
                score += 50
                # Extra points if it's specifically minutes or agenda (in filename, not just path)
                filename = url_lower.split('/')[-1]
                if 'minute' in filename or 'agenda' in filename:
                    score += 40
                if 'council' in filename or 'committee' in filename:
                    score += 15
                
                # PENALTY for bylaws and legislation (not meeting minutes)
                if 'bylaw' in filename or 'by-law' in filename:
                    score -= 50
                if 'bill' in filename or filename.startswith('26-'):
                    score -= 30
                if 'vital' in filename or 'report' in filename and 'minute' not in filename:
                    score -= 20
            
            # HIGH PRIORITY: Recent year indicators
            if '2026' in combined or '2025' in combined:
                score += 20
            
            # Meeting portal systems - LOWER priority unless it has a PDF
            if any(portal in url_lower for portal in ['escribe', 'legistar', 'granicus', 'civicweb']):
                if url_lower.endswith('.pdf'):
                    score += 15
                else:
                    score += 5  # Lower priority if just portal page
            
            # URL contains key paths
            if 'agenda' in url_lower or 'minutes' in url_lower:
                score += 12
            if 'meeting' in url_lower or 'council' in url_lower:
                score += 10
            
            # Official domains
            if '.ca' in url_lower or '.gov' in url_lower or '.on.ca' in url_lower:
                score += 8
            
            # Title/snippet keywords
            if 'agenda' in title_lower:
                score += 5
            if 'minutes' in title_lower:
                score += 5
            if 'packet' in combined:
                score += 4
            
            # City clerk pages
            if 'clerk' in url_lower:
                score += 6
            
            # PENALTIES
            if any(bad in url_lower for bad in ['archive', 'archived', 'old']):
                score -= 10
            if any(bad in url_lower for bad in ['employment', 'jobs', 'careers', 'news', 'blog', 'press']):
                score -= 15
            if any(bad in url_lower for bad in ['facebook', 'twitter', 'youtube', 'instagram']):
                score -= 30
            if 'committee' in url_lower and 'council' not in url_lower:
                score -= 5
            
            scored_results.append((score, result))
        
        # Sort by score (highest first)
        scored_results.sort(reverse=True, key=lambda x: x[0])
        
        # Return best match if score is reasonable
        if scored_results and scored_results[0][0] > 10:
            best_result = scored_results[0][1]
            return OfficialSource(
                url=best_result.url,
                reasoning=f"Enhanced heuristic: Best matching URL (score: {scored_results[0][0]}) - prioritizing PDFs and recent dates",
                confidence=min(0.85, scored_results[0][0] / 60)
            )
        
        return None
