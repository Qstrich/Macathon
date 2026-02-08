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
        # Prioritize eSCRIBE portals for reliable document access
        search_queries = [
            f"{city_name} escribemeetings.com",  # Look for eSCRIBE portal first
            f"\"{city_only}\" {region} council minutes.pdf 2026" if region else f"{city_only} council minutes.pdf 2026",
            f"{city_name} \"committee minutes\" filetype:pdf 2026",
            f"{city_name} \"meeting minutes\" \"approved\" filetype:pdf",
            f"{city_name} clerk minutes agenda 2026 site:.ca" if region else f"{city_name} clerk minutes 2026"
        ]
        
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
        
        prompt = f"""You are a civic tech expert finding municipal meeting documents for {city_name}.

CRITICAL: Verify the location matches! The city must be "{city_only}" in "{region}" (Canada).
REJECT any URLs for cities in other provinces/states or countries.

Analyze the following URLs and identify the ONE that is most likely to contain RECENT city council agendas or minutes.

            PRIORITIZE URLs with these signals:
            1. Location match - URL domain or path contains correct city/region - MANDATORY
            2. City-specific eSCRIBE portals (e.g., pub-cityname.escribemeetings.com) - HIGHEST PRIORITY
            3. Generic eSCRIBE domains (www.escribemeetings.com) - ONLY if no city-specific portal found
            4. Direct PDF links to MINUTES or AGENDAS (.pdf extension with "minutes" or "agenda" in filename)
            5. Current year (2026 or 2025) in URL path or filename
            6. Keywords in URL: "minutes.pdf", "agenda.pdf", "packet.pdf"
            7. Meeting document repositories with date-specific PDFs
            8. City clerk document archives with actual meeting files
            9. Official Canadian domains (.ca, .on.ca, etc.) if city is in Canada

DEPRIORITIZE (unless no better option):
- Meeting portals without direct PDF links in the URL
- Calendar pages
- Generic "meetings" landing pages

REJECT:
- Wrong city/province/country (e.g., Hamilton MA vs Hamilton ON)
- Archived meetings (unless no recent alternative)
- News articles, press releases, social media
- Generic pages without meeting documents
- Committee pages (unless they have documents)

Search Results:
{results_text}

Return the BEST URL that matches the CORRECT location and will lead to actual meeting documents."""

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
