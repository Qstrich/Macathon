"""
eSCRIBE Parser - Specialized parser for eSCRIBE meeting management portals.
"""

import re
import requests
from typing import Optional, List
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs
from pydantic import BaseModel, Field


class eSCRIBEDocument(BaseModel):
    """Document extracted from eSCRIBE portal."""
    url: str = Field(description="Direct URL to download the document")
    title: str = Field(description="Document title")
    doc_type: str = Field(description="Type: Agenda, Minutes, Packet, etc.")
    date: Optional[str] = Field(default=None, description="Meeting date")


class eSCRIBEParser:
    """
    Specialized parser for eSCRIBE meeting management system.
    Used by many Canadian municipalities.
    """
    
    def __init__(self):
        """Initialize eSCRIBE parser."""
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
    
    def is_escribe_url(self, url: str) -> bool:
        """
        Check if URL is an eSCRIBE portal.
        
        Args:
            url: URL to check
        
        Returns:
            True if it's an eSCRIBE portal
        """
        return 'escribemeetings.com' in url.lower()
    
    def extract_documents(self, meeting_url: str) -> List[eSCRIBEDocument]:
        """
        Extract all documents from an eSCRIBE meeting page.
        
        Args:
            meeting_url: URL of the meeting page (Meeting.aspx or Meeting?)
        
        Returns:
            List of eSCRIBEDocument objects
        """
        try:
            # Remove Tab parameter if present to get main meeting page
            if 'Tab=' in meeting_url:
                meeting_url = meeting_url.split('&Tab=')[0]
            
            print(f"   Fetching eSCRIBE page...")
            response = requests.get(meeting_url, headers=self.headers, timeout=45, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            documents = []
            
            # Debug: count total links
            all_links = soup.find_all('a', href=True)
            print(f"   Page contains {len(all_links)} total links")
            
            # Method 1: Look for ANY links containing document-related keywords
            pdf_keywords = ['pdf', 'getfile', 'download', 'file.aspx', 'attachment', 'document']
            pdf_link_count = 0
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                
                # Check if href contains any document keyword
                is_doc_link = any(keyword in href.lower() for keyword in pdf_keywords)
                
                if is_doc_link:
                    pdf_link_count += 1
                    full_url = urljoin(meeting_url, href)
                    text = link.get_text(strip=True)
                    
                    # Get title from aria-label or title attribute if available
                    title = link.get('aria-label', '') or link.get('title', '') or text
                    
                    # If no title, try parent or sibling elements
                    if not title or len(title) < 3:
                        parent = link.find_parent()
                        if parent:
                            title = parent.get_text(strip=True)[:100]
                    
                    doc_type = self._classify_document(title, href)
                    
                    if title and len(title) > 2:  # Only add if we have a meaningful title
                        documents.append(eSCRIBEDocument(
                            url=full_url,
                            title=title,
                            doc_type=doc_type
                        ))
                        print(f"      Found: {doc_type} - {title[:60]}")
            
            print(f"   Detected {pdf_link_count} potential document links")
            
            # Method 2: Look for eSCRIBE-specific download buttons/links
            # Common patterns: "View Agenda", "View Minutes", "Download Packet"
            for button in soup.find_all(['button', 'a', 'input'], attrs={'value': re.compile(r'agenda|minutes|packet', re.I)}):
                onclick = button.get('onclick', '')
                href = button.get('href', '')
                
                if onclick:
                    # Extract URL from JavaScript onclick
                    url_match = re.search(r"['\"](.*?(?:\.pdf|GetFile|download).*?)['\"]", onclick, re.I)
                    if url_match:
                        pdf_url = urljoin(meeting_url, url_match.group(1))
                        documents.append(eSCRIBEDocument(
                            url=pdf_url,
                            title=button.get('value', 'Meeting Document'),
                            doc_type=self._classify_document(button.get('value', ''), pdf_url)
                        ))
                elif href:
                    full_url = urljoin(meeting_url, href)
                    documents.append(eSCRIBEDocument(
                        url=full_url,
                        title=button.get('value', 'Meeting Document'),
                        doc_type=self._classify_document(button.get('value', ''), href)
                    ))
            
            # Method 3: Look for GetFile.ashx links (common eSCRIBE pattern)
            for link in soup.find_all('a', href=re.compile(r'GetFile\.ashx|File\.aspx', re.I)):
                full_url = urljoin(meeting_url, link['href'])
                text = link.get_text(strip=True)
                title = link.get('aria-label', '') or link.get('title', '') or text
                doc_type = self._classify_document(title, link['href'])
                
                if title:
                    documents.append(eSCRIBEDocument(
                        url=full_url,
                        title=title,
                        doc_type=doc_type
                    ))
            
            # Method 4: Look in iframes (eSCRIBE sometimes uses iframes for PDFs)
            for iframe in soup.find_all('iframe', src=True):
                src = iframe['src']
                if '.pdf' in src.lower() or 'getfile' in src.lower():
                    full_url = urljoin(meeting_url, src)
                    documents.append(eSCRIBEDocument(
                        url=full_url,
                        title="Meeting Document (iframe)",
                        doc_type="Unknown"
                    ))
            
            # Method 5: Look for specific eSCRIBE classes/IDs
            for element in soup.find_all(['div', 'span'], class_=re.compile(r'agenda|minutes|document', re.I)):
                for link in element.find_all('a', href=True):
                    href = link['href']
                    if '.pdf' in href.lower() or 'getfile' in href.lower():
                        full_url = urljoin(meeting_url, href)
                        text = link.get_text(strip=True)
                        title = link.get('aria-label', '') or link.get('title', '') or text
                        
                        if title:
                            documents.append(eSCRIBEDocument(
                                url=full_url,
                                title=title,
                                doc_type=self._classify_document(title, href)
                            ))
            
            # Deduplicate documents by URL
            seen = set()
            unique_documents = []
            for doc in documents:
                if doc.url not in seen:
                    seen.add(doc.url)
                    unique_documents.append(doc)
            
            return unique_documents
            
        except Exception as e:
            print(f"   eSCRIBE extraction error: {e}")
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
        elif 'packet' in combined:
            return 'Packet'
        elif 'report' in combined:
            return 'Report'
        else:
            return 'Document'
    
    def find_latest_meeting(self, base_url: str) -> Optional[str]:
        """
        Find the URL of the most recent meeting from an eSCRIBE calendar.
        
        Args:
            base_url: Base URL of the eSCRIBE portal
        
        Returns:
            URL of the most recent meeting page, or None
        """
        try:
            # Try common eSCRIBE calendar URLs
            calendar_paths = [
                '',  # Try base URL first
                '/Meetings.aspx',
                '/CalendarView.aspx',
                '/?View=List',
            ]
            
            for path in calendar_paths:
                try:
                    url = urljoin(base_url, path) if path else base_url
                    print(f"   Trying eSCRIBE URL: {url[:80]}...")
                    response = requests.get(url, headers=self.headers, timeout=45, verify=False)
                    if response.status_code != 200:
                        continue
                    
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for meeting links - eSCRIBE uses multiple patterns
                    meeting_links = []
                    
                    # Pattern 1: Meeting.aspx?Id=
                    for link in soup.find_all('a', href=re.compile(r'Meeting\.aspx\?Id=|Meeting\?Id=', re.I)):
                        href = link['href']
                        text = link.get_text(strip=True)
                        
                        # Skip if it's a past meeting archive (check text)
                        if 'archive' in text.lower():
                            continue
                        
                        # Extract date from text or nearby elements
                        date_str = ""
                        # Look for date in text
                        date_match = re.search(r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+202[456]', text, re.I)
                        if date_match:
                            date_str = date_match.group()
                        else:
                            # Try to find date in ISO format
                            date_match = re.search(r'202[456]-\d{2}-\d{2}', text + href)
                            if date_match:
                                date_str = date_match.group()
                            else:
                                # Look for 8-digit date like 20260126
                                date_match = re.search(r'202[456]\d{4}', text + href)
                                if date_match:
                                    date_str = date_match.group()
                        
                        # Add link with date
                        full_url = urljoin(url, href)
                        meeting_links.append((full_url, date_str, text))
                        print(f"      Found meeting: {text[:60]} - {date_str}")
                    
                    if meeting_links:
                        # Sort by date string (reverse chronological) and return most recent
                        meeting_links.sort(key=lambda x: x[1], reverse=True)
                        best_meeting = meeting_links[0]
                        print(f"   Selected latest meeting: {best_meeting[2][:60]}")
                        return best_meeting[0]
                
                except Exception as e:
                    print(f"      Path {path} failed: {e}")
                    continue
            
            print("   No meeting links found in any eSCRIBE path")
            return None
            
        except Exception as e:
            print(f"   eSCRIBE calendar error: {e}")
            import traceback
            traceback.print_exc()
            return None
