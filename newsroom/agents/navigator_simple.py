
"""
Navigator Agent - Simple version using requests instead of crawl4ai.
"""

import re
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Use html.parser instead of lxml for Windows compatibility
BS_PARSER = 'html.parser'

# Import specialized parsers for meeting portals
try:
    from newsroom.agents.escribe_parser import eSCRIBEParser, eSCRIBEDocument
    HAS_ESCRIBE_PARSER = True
except ImportError:
    HAS_ESCRIBE_PARSER = False

try:
    from newsroom.agents.tmmis_parser import TMMISParser, TMMISDocument
    HAS_TMMIS_PARSER = True
except ImportError:
    HAS_TMMIS_PARSER = False


class PDFInfo(BaseModel):
    """Information about a discovered PDF document or webpage."""
    url: str = Field(description="Direct URL to the PDF file or webpage")
    title: str = Field(description="Title or description of the document")
    date: Optional[str] = Field(default=None, description="Meeting date if found (YYYY-MM-DD format)")
    file_size: Optional[str] = Field(default=None, description="File size if available")
    is_html: bool = Field(default=False, description="True if this is HTML content, not a PDF")
    html_content: Optional[str] = Field(default=None, description="HTML content if is_html is True")


class NavigatorAgent:
    """
    Agent responsible for navigating government websites to find PDF documents.
    Uses requests and BeautifulSoup for parsing (simplified version).
    """
    
    def __init__(self):
        """Initialize Navigator Agent."""
        self.date_patterns = [
            r'(\d{4}[-/]\d{2}[-/]\d{2})',  # 2024-01-15 or 2024/01/15
            r'(\d{4}\d{2}\d{2})',  # 20240115 (no separators)
            r'(\d{2}[-/]\d{2}[-/]\d{4})',  # 01-15-2024 or 01/15/2024
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\.?\s+\d{1,2},?\s+\d{4}',
            r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
        ]
    
    async def find_latest_pdf(self, source_url: str, use_ai: bool = True) -> Optional[PDFInfo]:
        """
        Navigate the source URL and find the latest PDF document or HTML content.
        
        Args:
            source_url: URL of the government repository page
        
        Returns:
            PDFInfo object with details about the latest PDF/HTML, or None if not found
        """
        try:
            # Check if source URL itself is a PDF
            if source_url.lower().endswith('.pdf'):
                print(f"   Source URL is a direct PDF link!")
                # Extract filename and date from URL
                filename = source_url.split('/')[-1].replace('.pdf', '').replace('_', ' ').replace('-', ' ')
                date = self._extract_date(source_url)
                
                return PDFInfo(
                    url=source_url,
                    title=f"Council Meeting Minutes - {filename}",
                    date=date,
                    is_html=False
                )
            
            # Check if this is an eSCRIBE portal - use specialized parser
            if HAS_ESCRIBE_PARSER and 'escribemeetings.com' in source_url.lower():
                print(f"   Detected eSCRIBE portal, using specialized parser...")
                try:
                    result = await self._handle_escribe_portal(source_url)
                    if result:
                        return result
                    print("   eSCRIBE parser returned no results, trying standard scraping...")
                except Exception as e:
                    print(f"   eSCRIBE parser error: {e}, falling back to standard scraping...")
                    # Fall through to standard scraping
            
            # Check if this is a TMMIS portal (Toronto) - use specialized parser
            if HAS_TMMIS_PARSER and ('secure.toronto.ca' in source_url.lower() or 
                                      'app.toronto.ca' in source_url.lower() or
                                      'tmmis' in source_url.lower()):
                print(f"   Detected TMMIS portal (Toronto), using specialized parser...")
                try:
                    result = await self._handle_tmmis_portal(source_url)
                    if result:
                        return result
                    print("   TMMIS parser returned no results, trying standard scraping...")
                except Exception as e:
                    print(f"   TMMIS parser error: {e}, falling back to standard scraping...")
                    # Fall through to standard scraping
            
            print(f"   Fetching: {source_url}")
            
            # Fetch the page
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            # Disable SSL verification for meeting portals with certificate issues
            response = requests.get(source_url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, BS_PARSER)
            original_soup = soup
            original_url = source_url
            
            # Check if this is a meeting portal/calendar page
            is_portal = any(portal in source_url.lower() for portal in ['escribe', 'legistar', 'granicus', 'civicweb', 'event', 'calendar', 'meeting'])
            
            # Find all PDF links
            pdf_links = self._extract_pdf_links(soup, source_url)
            
            # If it's a portal with no direct PDFs, look for meeting links first
            if is_portal and len(pdf_links) < 3:
                print("   Detected meeting portal, looking for specific meeting pages...")
                meeting_links = self._extract_meeting_links(soup, source_url)
                if meeting_links:
                    print(f"   Found {len(meeting_links)} meeting pages, checking for PDFs...")
                    # Check first few meeting pages for PDFs
                    for meeting_url in meeting_links[:5]:  # Check top 5 meetings
                        try:
                            print(f"   Checking: {meeting_url[:80]}...")
                            response = requests.get(meeting_url, headers=headers, timeout=15, verify=False)
                            response.raise_for_status()
                            meeting_soup = BeautifulSoup(response.text, BS_PARSER)
                            meeting_pdfs = self._extract_pdf_links(meeting_soup, meeting_url)
                            if meeting_pdfs:
                                pdf_links.extend(meeting_pdfs)
                                print(f"      Found {len(meeting_pdfs)} PDFs")
                        except Exception as e:
                            print(f"      Error: {e}")
                            continue
            
            # If no PDFs found, try following "meetings" or "agendas" links
            if not pdf_links:
                print("   No PDFs on main page, checking subpages...")
                subpage_url = self._find_meetings_subpage(soup, source_url)
                if subpage_url:
                    print(f"   Following subpage: {subpage_url}")
                    try:
                        response = requests.get(subpage_url, headers=headers, timeout=30, verify=False)
                        response.raise_for_status()
                        soup = BeautifulSoup(response.text, BS_PARSER)
                        pdf_links = self._extract_pdf_links(soup, subpage_url)
                        if not pdf_links:
                            # Keep the subpage soup and url for HTML extraction
                            original_soup = soup
                            original_url = subpage_url
                    except Exception as e:
                        print(f"   Subpage access failed: {e}, trying with original page...")
            
            if pdf_links:
                print(f"   Found {len(pdf_links)} PDF links")
                
                # If we have AI available, use it to select the best PDF
                if use_ai and len(pdf_links) > 1:
                    try:
                        from google import genai
                        print("   Using AI to select best document...")
                        best_pdf = await self._select_with_ai(pdf_links)
                        if best_pdf:
                            return best_pdf
                    except Exception as e:
                        print(f"   AI selection failed: {e}, using date-based selection...")
                
                # Fallback: Sort by date and get the latest
                latest_pdf = self._select_latest_pdf(pdf_links)
                return latest_pdf
            
            # No PDFs found - try to extract HTML content directly
            print("   No PDFs found, attempting to extract HTML content...")
            html_content = self._extract_html_content(original_soup, original_url)
            
            if html_content:
                return html_content
            
            print("   No content found")
            return None
            
        except Exception as e:
            print(f"   Navigation error: {e}")
            # Don't crash - return None to allow graceful exit
            return None
    
    async def _handle_escribe_portal(self, meeting_url: str) -> Optional[PDFInfo]:
        """
        Handle eSCRIBE meeting portal URLs to extract actual documents.
        
        Args:
            meeting_url: URL of eSCRIBE meeting page or portal homepage
        
        Returns:
            PDFInfo with document information
        """
        if not HAS_ESCRIBE_PARSER:
            return None
        
        parser = eSCRIBEParser()
        
        # Check if URL is incomplete (missing meeting ID)
        if 'Meeting.aspx?Id' in meeting_url and meeting_url.endswith('?Id'):
            print("   Incomplete eSCRIBE URL detected (missing meeting ID)")
            # Extract base URL and try to find latest meeting
            base_url = meeting_url.split('/Meeting.aspx')[0]
            meeting_url = base_url + '/'
        
        # If this is the main portal page, find the latest meeting first
        if 'Meeting.aspx' not in meeting_url and 'Meeting?' not in meeting_url:
            print("   eSCRIBE portal homepage detected, finding latest meeting...")
            latest_meeting_url = parser.find_latest_meeting(meeting_url)
            if latest_meeting_url:
                print(f"   Found latest meeting: {latest_meeting_url[:80]}...")
                meeting_url = latest_meeting_url
            else:
                print("   Could not find any meeting pages")
                return None
        
        # Extract all documents from the meeting page
        documents = parser.extract_documents(meeting_url)
        
        if not documents:
            print("   No documents found in eSCRIBE portal")
            return None
        
        print(f"   Found {len(documents)} documents in eSCRIBE portal")
        
        # Prioritize: Minutes > Agenda > Packet > Other
        priority_order = ['minutes', 'agenda', 'packet', 'report']
        
        for doc_type in priority_order:
            for doc in documents:
                if doc.doc_type.lower() == doc_type:
                    print(f"   Selected: {doc.title} ({doc.doc_type})")
                    return PDFInfo(
                        url=doc.url,
                        title=doc.title,
                        date=doc.date,
                        is_html=False
                    )
        
        # If no prioritized documents, return first one
        if documents:
            print(f"   Using first available document: {documents[0].title}")
            return PDFInfo(
                url=documents[0].url,
                title=documents[0].title,
                date=documents[0].date,
                is_html=False
            )
        
        return None
    
    async def _handle_tmmis_portal(self, meeting_url: str) -> Optional[PDFInfo]:
        """
        Handle Toronto's TMMIS meeting portal URLs to extract documents.
        
        Args:
            meeting_url: URL of TMMIS meeting page or portal homepage
        
        Returns:
            PDFInfo with document information
        """
        if not HAS_TMMIS_PARSER:
            return None
        
        parser = TMMISParser()
        
        # If this is a general council page, try to find a specific meeting
        if 'council/report.do' not in meeting_url and 'agenda' not in meeting_url.lower():
            print("   TMMIS portal homepage detected, finding latest meeting...")
            latest_meeting_url = parser.find_latest_meeting(meeting_url)
            if latest_meeting_url:
                print(f"   Found latest meeting: {latest_meeting_url[:80]}...")
                meeting_url = latest_meeting_url
            else:
                print("   Could not find any meeting pages")
                return None
        
        # Extract all documents from the meeting page
        documents = parser.extract_documents(meeting_url)
        
        if not documents:
            print("   No documents found in TMMIS portal")
            return None
        
        print(f"   Found {len(documents)} documents in TMMIS portal")
        
        # Prioritize: Minutes > Agenda > Decision > Report > Other
        priority_order = ['minutes', 'agenda', 'decision', 'report']
        
        for doc_type in priority_order:
            for doc in documents:
                if doc.doc_type.lower() == doc_type:
                    print(f"   Selected: {doc.title} ({doc.doc_type})")
                    return PDFInfo(
                        url=doc.url,
                        title=doc.title,
                        date=doc.date,
                        is_html=False
                    )
        
        # If no prioritized documents, return first one
        if documents:
            print(f"   Using first available document: {documents[0].title}")
            return PDFInfo(
                url=documents[0].url,
                title=documents[0].title,
                date=documents[0].date,
                is_html=False
            )
        
        return None
    
    def _extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> list[PDFInfo]:
        """
        Extract all PDF links from the page with enhanced metadata and filtering.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
        
        Returns:
            List of PDFInfo objects
        """
        pdf_links = []
        
        # Blacklist for non-meeting documents
        blacklist_keywords = [
            'contact', 'directory', 'phone', 'staff list',
            'organizational chart', 'org chart', 'constitution',
            'budget summary', 'annual report cover', 'letterhead'
        ]
        
        # Find all links that might point to PDFs
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            # Check if it's a PDF link - be more lenient
            is_pdf = (
                href.lower().endswith('.pdf') or
                '.pdf?' in href.lower() or
                'pdf' in href.lower() and ('download' in href.lower() or 'file' in href.lower()) or
                'filetype=pdf' in href.lower() or
                'type=pdf' in href.lower()
            )
            
            if not is_pdf:
                continue
            
            # Skip blacklisted documents
            if any(keyword in text or keyword in href.lower() for keyword in blacklist_keywords):
                continue
            
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Enhanced title extraction - look at more context
            title = link.get_text(strip=True)
            
            if not title or len(title) < 5:
                # Try aria-label
                title = link.get('aria-label', '')
            
            if not title or len(title) < 5:
                # Try title attribute
                title = link.get('title', '')
            
            if not title or len(title) < 5:
                # Look at parent context
                parent = link.parent
                if parent:
                    # Try to get row or list item context
                    row = parent.find_parent(['tr', 'li', 'div'])
                    if row:
                        title = row.get_text(strip=True)[:200]
                    else:
                        title = parent.get_text(strip=True)[:100]
            
            if not title:
                title = href.split('/')[-1].replace('.pdf', '').replace('_', ' ').replace('-', ' ')
            
            # Enhanced date extraction - look in more places
            date = None
            
            # Try URL first
            date = self._extract_date(href)
            
            # Try title
            if not date:
                date = self._extract_date(title)
            
            # Try parent row/context
            if not date and link.parent:
                parent = link.find_parent(['tr', 'li', 'div'])
                if parent:
                    parent_text = parent.get_text()
                    date = self._extract_date(parent_text)
            
            # Try sibling elements (often date is next to link)
            if not date:
                for sibling in link.find_next_siblings(limit=3):
                    sibling_text = sibling.get_text()
                    date = self._extract_date(sibling_text)
                    if date:
                        break
            
            pdf_links.append(PDFInfo(
                url=full_url,
                title=title.strip(),
                date=date
            ))
        
        return pdf_links
    
    def _extract_date(self, text: str) -> Optional[str]:
        """
        Extract date from text using regex patterns.
        
        Args:
            text: Text to search for dates
        
        Returns:
            Date string in YYYY-MM-DD format, or None if not found
        """
        for pattern in self.date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(0)
                try:
                    # Try to parse and normalize the date
                    return self._normalize_date(date_str)
                except:
                    continue
        
        return None
    
    def _normalize_date(self, date_str: str) -> str:
        """
        Normalize various date formats to YYYY-MM-DD.
        
        Args:
            date_str: Date string in various formats
        
        Returns:
            Normalized date string (YYYY-MM-DD)
        """
        # List of possible date formats
        formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y%m%d',  # No separators
            '%m-%d-%Y',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%B %d %Y',
            '%b %d, %Y',
            '%b %d %Y',
            '%b. %d, %Y',
            '%b. %d %Y',
            '%d %B %Y',
            '%d %b %Y',
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # If no format matches, return as-is
        return date_str
    
    def _select_latest_pdf(self, pdf_links: list[PDFInfo]) -> PDFInfo:
        """
        Select the latest PDF from a list based on date.
        
        Args:
            pdf_links: List of PDFInfo objects
        
        Returns:
            The most recent PDFInfo object
        """
        # Separate PDFs with and without dates
        dated_pdfs = [p for p in pdf_links if p.date]
        undated_pdfs = [p for p in pdf_links if not p.date]
        
        if dated_pdfs:
            # Sort by date (descending) and return the latest
            dated_pdfs.sort(key=lambda x: x.date, reverse=True)
            return dated_pdfs[0]
        
        # If no dated PDFs, return the first one found
        return undated_pdfs[0] if undated_pdfs else pdf_links[0]
    
    def _extract_meeting_links(self, soup: BeautifulSoup, base_url: str) -> list[str]:
        """
        Extract links to individual meeting pages from a calendar/portal page.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
        
        Returns:
            List of meeting page URLs
        """
        meeting_urls = []
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text().lower()
            
            # Skip obvious non-meeting links
            if any(skip in href.lower() for skip in ['facebook', 'twitter', 'mailto:', 'javascript:', '#']):
                continue
            
            # Look for meeting-specific patterns
            is_meeting_link = (
                'meeting.aspx' in href.lower() or  # eSCRIBE pattern
                'calendar' in href.lower() and 'meeting' in text or
                'agenda' in href.lower() or
                'minutes' in href.lower() or
                re.search(r'202[456]', text)  # Contains a recent year
            )
            
            if is_meeting_link:
                full_url = urljoin(base_url, href)
                if full_url not in meeting_urls:
                    meeting_urls.append(full_url)
        
        return meeting_urls
    
    def _find_meetings_subpage(self, soup: BeautifulSoup, base_url: str) -> Optional[str]:
        """
        Find a subpage that likely contains meeting PDFs.
        Prioritizes actual document links over navigation.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
        
        Returns:
            URL of subpage if found, None otherwise
        """
        scored_links = []
        
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            text = link.get_text().lower()
            score = 0
            
            # Skip bad links
            if any(skip in href for skip in ['facebook', 'twitter', 'linkedin', 'instagram', 'youtube', 'mailto:', 'javascript:', 'cdn-cgi']):
                continue
            
            # Skip internal anchors
            if href.startswith('#'):
                continue
            
            # High priority: PDF or document-related links
            if 'pdf' in href or 'document' in href or 'file' in href:
                score += 20
            if 'agenda' in href or 'minutes' in href:
                score += 15
            if 'agenda' in text or 'minutes' in text or 'pdf' in text:
                score += 10
            
            # Medium priority: Meeting-related pages
            if 'meeting' in href or 'calendar' in href:
                score += 8
            if 'meeting' in text or 'calendar' in text:
                score += 5
            
            # Lower priority: Generic council links
            if 'council' in href or 'council' in text:
                score += 3
            
            if score > 5:
                full_url = urljoin(base_url, link['href'])
                scored_links.append((score, full_url, text[:50]))
        
        if scored_links:
            # Sort by score and return best
            scored_links.sort(reverse=True, key=lambda x: x[0])
            print(f"   Best subpage candidate: {scored_links[0][2]} (score: {scored_links[0][0]})")
            return scored_links[0][1]
        
        return None
    
    def _extract_html_content(self, soup: BeautifulSoup, url: str) -> Optional[PDFInfo]:
        """
        Extract meeting information from HTML content when no PDFs are available.
        
        Args:
            soup: BeautifulSoup object of the page
            url: URL of the page
        
        Returns:
            PDFInfo with HTML content, or None if no relevant content found
        """
        # Look for main content areas
        content_areas = []
        
        # Try to find main content container
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=lambda x: x and 'content' in x.lower() if x else False)
        
        if main_content:
            content_areas.append(main_content)
        else:
            # Fallback to body
            content_areas.append(soup.body if soup.body else soup)
        
        # Extract text from content areas
        extracted_content = []
        
        for area in content_areas:
            # Look for tables (often contain meeting schedules)
            tables = area.find_all('table')
            for table in tables:
                extracted_content.append(str(table))
            
            # Look for lists that might contain meeting info
            lists = area.find_all(['ul', 'ol'])
            for lst in lists:
                text = lst.get_text(strip=True)
                if any(keyword in text.lower() for keyword in ['meeting', 'agenda', 'minutes', 'council', 'committee']):
                    extracted_content.append(str(lst))
            
            # Look for divs/sections with meeting info
            sections = area.find_all(['section', 'div'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['meeting', 'agenda', 'minutes', 'calendar']
            ) if x else False)
            for section in sections:
                extracted_content.append(str(section))
        
        if not extracted_content:
            # Last resort: get all paragraph text
            paragraphs = soup.find_all('p')
            relevant_paras = [p for p in paragraphs if any(
                keyword in p.get_text().lower() for keyword in ['meeting', 'agenda', 'minutes', 'council']
            )]
            if relevant_paras:
                extracted_content = [str(p) for p in relevant_paras[:10]]  # Limit to first 10 relevant paragraphs
        
        if extracted_content:
            # Get page title
            title = soup.find('title')
            page_title = title.get_text(strip=True) if title else "Council Meeting Information"
            
            # Try to extract date from content
            combined_text = ' '.join([BeautifulSoup(c, BS_PARSER).get_text() for c in extracted_content])
            date = self._extract_date(combined_text)
            
            return PDFInfo(
                url=url,
                title=page_title,
                date=date,
                is_html=True,
                html_content='\n\n'.join(extracted_content)
            )
        
        return None
