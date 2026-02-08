"""
PDF Parser - Convert council meeting PDFs or HTML to Markdown.
"""

import aiohttp
from pathlib import Path
from datetime import datetime
from typing import Optional
from docling.document_converter import DocumentConverter
from bs4 import BeautifulSoup


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
            pdf_bytes = await self._download_pdf(pdf_url)
            
            # Save PDF temporarily
            temp_pdf = self.output_dir / "temp_download.pdf"
            temp_pdf.write_bytes(pdf_bytes)
            
            try:
                # Step 2: Convert PDF to Markdown using Docling
                print("   Converting PDF to Markdown...")
                result = self.converter.convert(str(temp_pdf))
                markdown_content = result.document.export_to_markdown()
                
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
                
                return output_path
                
            finally:
                # Clean up temporary PDF
                if temp_pdf.exists():
                    temp_pdf.unlink()
    
    async def _download_pdf(self, url: str) -> bytes:
        """
        Download PDF content from URL.
        
        Args:
            url: URL of the PDF file
        
        Returns:
            PDF content as bytes
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download PDF: HTTP {response.status}")
                
                return await response.read()
    
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
