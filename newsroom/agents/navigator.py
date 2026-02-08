"""
Navigator Agent - Crawl government websites to find latest PDF documents.
"""

import re
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from crawl4ai import AsyncWebCrawler
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# Use html.parser instead of lxml for Windows compatibility
BS_PARSER = 'html.parser'


class PDFInfo(BaseModel):
    """Information about a discovered PDF document."""
    url: str = Field(description="Direct URL to the PDF file")
    title: str = Field(description="Title or description of the document")
    date: Optional[str] = Field(default=None, description="Meeting date if found (YYYY-MM-DD format)")
    file_size: Optional[str] = Field(default=None, description="File size if available")


class NavigatorAgent:
    """
    Agent responsible for navigating government websites to find PDF documents.
    Uses Crawl4AI for async web crawling and BeautifulSoup for parsing.
    """
    
    def __init__(self):
        """Initialize Navigator Agent."""
        self.date_patterns = [
            r'(\d{4}[-/]\d{2}[-/]\d{2})',  # 2024-01-15 or 2024/01/15
            r'(\d{2}[-/]\d{2}[-/]\d{4})',  # 01-15-2024 or 01/15/2024
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}',
        ]
    
    async def find_latest_pdf(self, source_url: str) -> Optional[PDFInfo]:
        """
        Navigate the source URL and find the latest PDF document.
        
        Args:
            source_url: URL of the government repository page
        
        Returns:
            PDFInfo object with details about the latest PDF, or None if not found
        """
        try:
            async with AsyncWebCrawler(verbose=False) as crawler:
                print(f"   Crawling: {source_url}")
                result = await crawler.arun(url=source_url)
                
                if not result.success:
                    print(f"   Failed to crawl page: {result.error_message}")
                    return None
                
                # Parse the HTML content (using html.parser for Windows compatibility)
                soup = BeautifulSoup(result.html, BS_PARSER)
                
                # Find all PDF links
                pdf_links = self._extract_pdf_links(soup, source_url)
                
                if not pdf_links:
                    print("   No PDF links found on page")
                    return None
                
                print(f"   Found {len(pdf_links)} PDF links")
                
                # Sort by date and get the latest
                latest_pdf = self._select_latest_pdf(pdf_links)
                
                return latest_pdf
                
        except Exception as e:
            print(f"   Navigation error: {e}")
            return None
    
    def _extract_pdf_links(self, soup: BeautifulSoup, base_url: str) -> list[PDFInfo]:
        """
        Extract all PDF links from the page.
        
        Args:
            soup: BeautifulSoup object of the page
            base_url: Base URL for resolving relative links
        
        Returns:
            List of PDFInfo objects
        """
        pdf_links = []
        
        # Find all links that might point to PDFs
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Check if it's a PDF link
            if not (href.lower().endswith('.pdf') or 'pdf' in href.lower()):
                continue
            
            # Resolve relative URLs
            full_url = urljoin(base_url, href)
            
            # Extract title from link text or nearby context
            title = link.get_text(strip=True)
            if not title:
                # Try to find title in nearby elements
                parent = link.parent
                if parent:
                    title = parent.get_text(strip=True)[:100]
            
            if not title:
                title = "Council Meeting Minutes"
            
            # Try to extract date from title or nearby text
            date = self._extract_date(title)
            
            # Try to extract date from parent elements if not found in title
            if not date and link.parent:
                parent_text = link.parent.get_text()
                date = self._extract_date(parent_text)
            
            pdf_links.append(PDFInfo(
                url=full_url,
                title=title,
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
            '%m-%d-%Y',
            '%m/%d/%Y',
            '%B %d, %Y',
            '%B %d %Y',
            '%b %d, %Y',
            '%b %d %Y',
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
