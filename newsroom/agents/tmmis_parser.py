"""
TMMIS Parser - Specialized parser for Toronto Meeting Management Information System.
"""

import re
import requests
from typing import Optional, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from pydantic import BaseModel, Field


class TMMISDocument(BaseModel):
    """Document extracted from TMMIS portal."""
    url: str = Field(description="Direct URL to download the document")
    title: str = Field(description="Document title")
    doc_type: str = Field(description="Type: Agenda, Minutes, Report, etc.")
    date: Optional[str] = Field(default=None, description="Meeting date")


class TMMISParser:
    """
    Specialized parser for Toronto's TMMIS (Toronto Meeting Management Information System).
    Reference: https://github.com/gabesawhney/tabstoronto-scraper
    """
    
    def __init__(self):
        """Initialize TMMIS parser."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def is_tmmis_url(self, url: str) -> bool:
        """
        Check if URL is a TMMIS portal.
        
        Args:
            url: URL to check
        
        Returns:
            True if it's a TMMIS portal
        """
        tmmis_patterns = [
            'secure.toronto.ca',
            'app.toronto.ca',
            'tmmis.toronto.ca',
        ]
        return any(pattern in url.lower() for pattern in tmmis_patterns)
    
    def extract_documents(self, meeting_url: str) -> List[TMMISDocument]:
        """
        Extract all documents from a TMMIS meeting page.
        
        Args:
            meeting_url: URL of the meeting page
        
        Returns:
            List of TMMISDocument objects
        """
        try:
            print(f"   Fetching TMMIS page...")
            response = requests.get(meeting_url, headers=self.headers, timeout=45, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            documents = []
            
            # Debug: count total links
            all_links = soup.find_all('a', href=True)
            print(f"   Page contains {len(all_links)} total links")
            
            # Method 1: Look for PDF links
            pdf_keywords = ['pdf', 'document', 'agenda', 'minutes', 'report']
            pdf_link_count = 0
            
            for link in all_links:
                href = link['href']
                
                # Check if href contains document-related keywords or ends in .pdf
                is_doc_link = (
                    href.lower().endswith('.pdf') or
                    any(keyword in href.lower() for keyword in pdf_keywords)
                )
                
                if is_doc_link:
                    pdf_link_count += 1
                    full_url = urljoin(meeting_url, href)
                    text = link.get_text(strip=True)
                    
                    # Get title from various sources
                    title = link.get('aria-label', '') or link.get('title', '') or text
                    
                    # If no title, try parent or sibling elements
                    if not title or len(title) < 3:
                        parent = link.find_parent()
                        if parent:
                            title = parent.get_text(strip=True)[:100]
                    
                    doc_type = self._classify_document(title, href)
                    
                    if title and len(title) > 2:
                        documents.append(TMMISDocument(
                            url=full_url,
                            title=title,
                            doc_type=doc_type
                        ))
                        print(f"      Found: {doc_type} - {title[:60]}")
            
            print(f"   Detected {pdf_link_count} potential document links")
            
            # Deduplicate documents by URL
            seen = set()
            unique_documents = []
            for doc in documents:
                if doc.url not in seen:
                    seen.add(doc.url)
                    unique_documents.append(doc)
            
            return unique_documents
            
        except Exception as e:
            print(f"   TMMIS extraction error: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def _classify_document(self, text: str, url: str) -> str:
        """
        Classify document type based on text and URL.
        
        Args:
            text: Link text or title
            url: Document URL
        
        Returns:
            Document type string
        """
        combined = (text + " " + url).lower()
        
        if 'minute' in combined:
            return 'Minutes'
        elif 'agenda' in combined:
            return 'Agenda'
        elif 'report' in combined:
            return 'Report'
        elif 'decision' in combined:
            return 'Decision'
        else:
            return 'Document'
    
    def find_latest_meeting(self, base_url: str) -> Optional[str]:
        """
        Find the URL of the most recent meeting from TMMIS.
        Toronto TMMIS pattern: secure.toronto.ca/council/report.do?meeting=YYYY.CCnn&type=agenda
        
        Args:
            base_url: Base URL of the TMMIS portal
        
        Returns:
            URL of the most recent meeting page, or None
        """
        try:
            # Try different TMMIS paths
            paths_to_try = [
                base_url,
                urljoin(base_url, '/council/'),
                'https://secure.toronto.ca/council/',
                'https://www.toronto.ca/city-government/council/council-committee-meetings/',
            ]
            
            for url_to_try in paths_to_try:
                try:
                    print(f"   Trying TMMIS URL: {url_to_try[:80]}...")
                    response = requests.get(url_to_try, headers=self.headers, timeout=45, verify=False)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for meeting links - TMMIS uses specific patterns
                    meeting_links = []
                    
                    # Pattern 1: TMMIS report.do pattern (e.g., meeting=2026.CC01)
                    for link in soup.find_all('a', href=re.compile(r'report\.do\?meeting=', re.I)):
                        href = link['href']
                        text = link.get_text(strip=True)
                        
                        # Extract meeting code (e.g., 2026.CC01)
                        meeting_match = re.search(r'meeting=(202[456]\.\w+)', href)
                        if meeting_match:
                            meeting_code = meeting_match.group(1)
                            full_url = urljoin(url_to_try, href)
                            meeting_links.append((full_url, meeting_code, text))
                            print(f"      Found meeting: {text[:60]} - {meeting_code}")
                    
                    # Pattern 2: Generic meeting/agenda/council links
                    if not meeting_links:
                        for link in soup.find_all('a', href=True):
                            href = link['href']
                            text = link.get_text(strip=True)
                            
                            # Check if it's a meeting-related link
                            is_meeting = (
                                'meeting' in href.lower() or
                                'agenda' in href.lower() or
                                ('council' in href.lower() and 'report' in href.lower())
                            )
                            
                            if is_meeting:
                                # Extract date from text or href
                                date_str = ""
                                # Try meeting code format
                                meeting_match = re.search(r'202[456]\.\w+', text + href)
                                if meeting_match:
                                    date_str = meeting_match.group()
                                else:
                                    # Try ISO date
                                    date_match = re.search(r'202[456]-\d{2}-\d{2}', text + href)
                                    if date_match:
                                        date_str = date_match.group()
                                    else:
                                        # Try month/day/year
                                        date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+202[456]', text, re.I)
                                        if date_match:
                                            date_str = date_match.group()
                                
                                if date_str:
                                    full_url = urljoin(url_to_try, href)
                                    meeting_links.append((full_url, date_str, text))
                                    print(f"      Found meeting: {text[:60]} - {date_str}")
                    
                    if meeting_links:
                        # Sort by date/meeting code and return most recent
                        meeting_links.sort(key=lambda x: x[1], reverse=True)
                        best_meeting = meeting_links[0]
                        print(f"   Selected latest meeting: {best_meeting[2][:60]}")
                        return best_meeting[0]
                
                except Exception as e:
                    print(f"      Path {url_to_try[:60]} failed: {e}")
                    continue
            
            print("   No meeting links found in any TMMIS path")
            return None
            
        except Exception as e:
            print(f"   TMMIS search error: {e}")
            import traceback
            traceback.print_exc()
            return None
