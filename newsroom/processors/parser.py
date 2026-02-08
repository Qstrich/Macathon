"""
PDF Parser - Convert council meeting PDFs or HTML to Markdown.
"""

import aiohttp
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List
from docling.document_converter import DocumentConverter
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field


class Motion(BaseModel):
    """Represents a single motion or decision from a council meeting."""
    id: int
    title: str
    summary: str
    status: str
    vote: Optional[Dict[str, int]] = None
    category: str
    impact_tags: List[str] = []
    full_text: Optional[str] = None


class MeetingData(BaseModel):
    """Complete meeting data with extracted motions."""
    city: str
    meeting_date: str
    source_url: str
    processed_date: str
    motions: List[Motion]


class PDFParser:
    """
    Parser for converting PDF documents or HTML content to Markdown format.
    Uses IBM's Docling library for layout-aware PDF parsing.
    """
    
    def __init__(self, output_dir: str = "data"):
        """
        Initialize PDF Parser.
        
        Args:
            output_dir: Directory to save output markdown files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.converter = DocumentConverter()
    
    async def process_pdf(
        self,
        pdf_url: str,
        city_name: str,
        source_url: str,
        meeting_date: Optional[str] = None,
        is_html: bool = False,
        html_content: Optional[str] = None
    ) -> Path:
        """
        Download and convert a PDF or process HTML content to Markdown with YAML frontmatter.
        
        Args:
            pdf_url: URL of the PDF to download or webpage URL
            city_name: Name of the city for metadata
            source_url: Original source page URL
            meeting_date: Date of the meeting (optional)
            is_html: True if processing HTML content instead of PDF
            html_content: Raw HTML content (if is_html is True)
        
        Returns:
            Path to the generated markdown file
        """
        if is_html and html_content:
            # Process HTML content
            print("   Processing HTML content...")
            markdown_content = self._html_to_markdown(html_content)
            
            # Create YAML frontmatter
            frontmatter = self._create_frontmatter(
                city_name=city_name,
                source_url=source_url,
                pdf_url=pdf_url,
                meeting_date=meeting_date,
                content_type="HTML"
            )
            
            # Combine frontmatter and content
            full_content = f"{frontmatter}\n\n{markdown_content}"
            
            # Save to output file
            output_filename = self._generate_filename(city_name, meeting_date)
            output_path = self.output_dir / output_filename
            output_path.write_text(full_content, encoding='utf-8')
            
            print(f"   Saved to: {output_path}")
            return output_path
        
        else:
            # Process PDF
            # Step 1: Download PDF
            print(f"   Downloading PDF from: {pdf_url}")
            pdf_bytes = await self._download_pdf(pdf_url, source_url)
            
            # Step 1.5: Validate it's actually a PDF
            if not self._is_valid_pdf(pdf_bytes):
                print(f"   Downloaded file is not a valid PDF, treating as HTML...")
                # Decode as HTML and extract content
                try:
                    html_content = pdf_bytes.decode('utf-8', errors='ignore')
                    markdown_content = self._html_to_markdown(html_content)
                    if not markdown_content or len(markdown_content) < 100:
                        raise Exception("Extracted HTML content is too short or empty")
                except Exception as e:
                    raise Exception(f"File is not a PDF and HTML extraction failed: {e}")
            else:
                # Save PDF temporarily
                temp_pdf = self.output_dir / "temp_download.pdf"
                temp_pdf.write_bytes(pdf_bytes)
                
                try:
                    # Step 2: Convert PDF to Markdown using Docling with error handling
                    print("   Converting PDF to Markdown...")
                    try:
                        result = self.converter.convert(str(temp_pdf))
                        markdown_content = result.document.export_to_markdown()
                    except Exception as docling_error:
                        print(f"   Docling parsing failed: {docling_error}")
                        print(f"   Attempting HTML extraction fallback...")
                        
                        # Try to extract as HTML instead
                        try:
                            html_content = pdf_bytes.decode('utf-8', errors='ignore')
                            markdown_content = self._html_to_markdown(html_content)
                            if not markdown_content or len(markdown_content) < 100:
                                raise Exception("HTML extraction produced insufficient content")
                        except Exception as html_error:
                            raise Exception(f"Both PDF parsing and HTML extraction failed. PDF error: {docling_error}, HTML error: {html_error}")
                except:
                    # Clean up temp file before re-raising
                    if temp_pdf.exists():
                        temp_pdf.unlink()
                    raise
                
            # Step 3: Create YAML frontmatter
            frontmatter = self._create_frontmatter(
                city_name=city_name,
                source_url=source_url,
                pdf_url=pdf_url,
                meeting_date=meeting_date,
                content_type="PDF"
            )
            
            # Step 4: Combine frontmatter and content
            full_content = f"{frontmatter}\n\n{markdown_content}"
            
            # Step 5: Save to output file
            output_filename = self._generate_filename(city_name, meeting_date)
            output_path = self.output_dir / output_filename
            output_path.write_text(full_content, encoding='utf-8')
            
            print(f"   Saved to: {output_path}")
            
            # Clean up temporary PDF if it exists
            try:
                temp_pdf = self.output_dir / "temp_download.pdf"
                if temp_pdf.exists():
                    temp_pdf.unlink()
            except:
                pass
            
            return output_path
    
    def _is_valid_pdf(self, data: bytes) -> bool:
        """
        Check if the downloaded data is actually a PDF file.
        
        Args:
            data: The downloaded file bytes
        
        Returns:
            True if valid PDF, False otherwise
        """
        if not data or len(data) < 4:
            return False
        
        # Check PDF magic bytes (PDF files start with %PDF)
        pdf_header = data[:4]
        if pdf_header == b'%PDF':
            return True
        
        # Check for common HTML indicators (false positives)
        html_indicators = [b'<!DOCTYPE', b'<html', b'<HTML', b'<?xml']
        for indicator in html_indicators:
            if data[:100].find(indicator) != -1:
                return False
        
        return False
    
    async def _download_pdf(self, url: str, source_url: str = None) -> bytes:
        """
        Download PDF content from URL with proper headers to avoid 403 errors.
        
        Args:
            url: URL of the PDF file
            source_url: The page URL where the PDF link was found (for Referer header)
        
        Returns:
            PDF content as bytes
        """
        import ssl
        
        # Create headers that mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/pdf,application/x-pdf,*/*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Add Referer if source URL provided (helps with 403 errors)
        if source_url:
            headers['Referer'] = source_url
        
        # Disable SSL verification for problematic servers
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with aiohttp.ClientSession(headers=headers) as session:
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=60), ssl=ssl_context) as response:
                    if response.status == 403:
                        raise Exception(f"Access forbidden (HTTP 403) - Server blocked the request")
                    elif response.status == 404:
                        raise Exception(f"Document not found (HTTP 404) - URL may be outdated")
                    elif response.status != 200:
                        raise Exception(f"Failed to download PDF: HTTP {response.status}")
                    return await response.read()
            except aiohttp.ClientError as e:
                # Try one more time without SSL verification
                print(f"   First download attempt failed: {e}")
                print(f"   Retrying with different settings...")
                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=60), ssl=False) as response:
                        if response.status == 403:
                            raise Exception(f"Access forbidden (HTTP 403) - Server blocked the request")
                        elif response.status == 404:
                            raise Exception(f"Document not found (HTTP 404) - URL may be outdated")
                        elif response.status != 200:
                            raise Exception(f"Failed to download PDF: HTTP {response.status}")
                        return await response.read()
                except Exception as retry_error:
                    # Final failure - raise with clear message
                    raise Exception(f"Could not download document: {retry_error}")
    
    def _html_to_markdown(self, html_content: str) -> str:
        """
        Convert HTML content to clean Markdown.
        
        Args:
            html_content: Raw HTML content
        
        Returns:
            Markdown formatted content
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Extract text with some structure preservation
        markdown_parts = []
        
        # Process tables
        for table in soup.find_all('table'):
            markdown_parts.append("\n## Meeting Information\n")
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all(['td', 'th'])
                if cells:
                    row_text = ' | '.join([cell.get_text(strip=True) for cell in cells])
                    markdown_parts.append(f"| {row_text} |")
            markdown_parts.append("\n")
        
        # Process lists
        for lst in soup.find_all(['ul', 'ol']):
            items = lst.find_all('li')
            for item in items:
                text = item.get_text(strip=True)
                markdown_parts.append(f"- {text}")
            markdown_parts.append("\n")
        
        # Process remaining text
        for element in soup.find_all(['h1', 'h2', 'h3', 'h4', 'p', 'div']):
            text = element.get_text(strip=True)
            if text and len(text) > 10:  # Skip very short fragments
                if element.name == 'h1':
                    markdown_parts.append(f"\n# {text}\n")
                elif element.name == 'h2':
                    markdown_parts.append(f"\n## {text}\n")
                elif element.name == 'h3':
                    markdown_parts.append(f"\n### {text}\n")
                elif element.name == 'h4':
                    markdown_parts.append(f"\n#### {text}\n")
                else:
                    markdown_parts.append(f"{text}\n")
        
        return '\n'.join(markdown_parts)
    
    def _create_frontmatter(
        self,
        city_name: str,
        source_url: str,
        pdf_url: str,
        meeting_date: Optional[str],
        content_type: str = "PDF"
    ) -> str:
        """
        Create YAML frontmatter for the markdown file.
        
        Args:
            city_name: Name of the city
            source_url: Original repository page URL
            pdf_url: Direct PDF URL or webpage URL
            meeting_date: Date of the meeting (optional)
            content_type: Type of content (PDF or HTML)
        
        Returns:
            YAML frontmatter as a string
        """
        processed_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        frontmatter = f"""---
title: "{city_name} Council Meeting Information"
city: "{city_name}"
meeting_date: {meeting_date or 'Unknown'}
source_url: "{source_url}"
document_url: "{pdf_url}"
content_type: "{content_type}"
processed_date: "{processed_date}"
generated_by: "CivicSense"
---"""
        
        return frontmatter
    
    def _generate_filename(self, city_name: str, meeting_date: Optional[str]) -> str:
        """
        Generate a unique filename for the output markdown.
        
        Args:
            city_name: Name of the city
            meeting_date: Date of the meeting (optional)
        
        Returns:
            Filename string
        """
        # Sanitize city name for filename
        safe_city = city_name.lower().replace(',', '').replace(' ', '_')
        
        if meeting_date:
            # Sanitize date - remove any path separators or invalid characters
            safe_date = meeting_date.replace('/', '-').replace('\\', '-').replace(' ', '_').replace(':', '-')
            return f"{safe_city}_{safe_date}.md"
        else:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            return f"{safe_city}_{timestamp}.md"
    
    async def _extract_and_save_motions(
        self,
        markdown_content: str,
        city_name: str,
        meeting_date: Optional[str],
        source_url: str,
        output_path: Path
    ) -> Optional[Path]:
        """
        Extract motions from markdown content using Gemini AI and save as JSON.
        
        Args:
            markdown_content: The full markdown text
            city_name: Name of the city
            meeting_date: Date of the meeting
            source_url: Original source URL
            output_path: Path to the markdown file
        
        Returns:
            Path to the JSON file if successful, None otherwise
        """
        try:
            from google import genai
            
            client = genai.Client()
            
            # Limit content to avoid token limits (first 15000 chars usually contains the motions)
            content_sample = markdown_content[:15000]
            
            prompt = f"""Analyze this city council meeting minutes and extract all motions, decisions, and bylaws that were voted on or approved.

For each motion, provide:
1. **title**: Short, plain-language title (max 80 characters) - what actually happened, not procedural language
2. **summary**: One sentence explaining the impact on residents (e.g., "Parking fines on King St increased by $10")
3. **status**: PASSED, FAILED, DEFERRED, or AMENDED
4. **vote**: If mentioned, extract {{"for": X, "against": Y, "abstain": Z}}
5. **category**: Classify as one of: parking, housing, budget, development, environment, transportation, services, governance, other
6. **impact_tags**: List of tags like "Downtown", "Residents", "Business", "Taxes", etc.
7. **full_text**: The complete text of the motion/decision

IMPORTANT:
- Focus on substantive decisions that affect residents
- Skip procedural items (agenda approval, minute approval, declarations of interest)
- Use plain language, not government jargon
- Extract 5-15 most important motions (prioritize resident impact)
- If vote details aren't mentioned, set vote to null

Meeting content:
{content_sample}"""

            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config={
                    'response_mime_type': 'application/json',
                    'response_schema': list[Motion],
                },
            )
            
            motions = response.parsed
            
            if not motions:
                print(f"   No motions extracted")
                return None
            
            # Create full meeting data structure
            meeting_data = MeetingData(
                city=city_name,
                meeting_date=meeting_date or "Unknown",
                source_url=source_url,
                processed_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                motions=motions
            )
            
            # Save to JSON file
            json_path = output_path.with_suffix('.json')
            json_path.write_text(
                meeting_data.model_dump_json(indent=2),
                encoding='utf-8'
            )
            
            print(f"   Extracted {len(motions)} motions")
            return json_path
            
        except Exception as e:
            print(f"   Motion extraction failed: {e}")
            print(f"   (Markdown still saved, continuing without JSON)")
            return None
