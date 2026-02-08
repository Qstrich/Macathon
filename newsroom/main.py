"""
CivicSense CLI Entry Point
Usage: python -m newsroom.main "Hamilton, Ontario"
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import os

from newsroom.agents.scout import ScoutAgent
try:
    from newsroom.agents.navigator import NavigatorAgent
except ImportError:
    # Fall back to simple version if crawl4ai is not installed
    from newsroom.agents.navigator_simple import NavigatorAgent
from newsroom.processors.parser import PDFParser


async def main(city_name: str) -> None:
    """
    Main orchestration function for the CivicSense autonomous agent.
    
    Args:
        city_name: Name of the city to search for (e.g., "Hamilton, Ontario")
    """
    # Load environment variables
    load_dotenv()
    
    # Validate API key
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ Error: GOOGLE_API_KEY not found in environment variables.")
        print("Please create a .env file with your API key.")
        sys.exit(1)
    
    print(f"Starting CivicSense for: {city_name}")
    print("=" * 60)
    
    try:
        # Add 5-minute timeout to prevent indefinite hangs
        async with asyncio.timeout(300):  # 300 seconds = 5 minutes
            # Step 1: Scout - Find official government source
            print("\n[STEP 1] Searching for official council minutes repository...")
            scout = ScoutAgent()
            official_source = await scout.find_official_source(city_name)
        
            if not official_source:
                print(f"[ERROR] Could not find official council minutes for {city_name}")
                sys.exit(1)
            
            print(f"[SUCCESS] Found official source: {official_source.url}")
            print(f"   Reasoning: {official_source.reasoning}")
            
            # Step 2: Navigator - Find latest PDF
            print("\n[STEP 2] Navigating to find latest PDF...")
            navigator = NavigatorAgent()
            pdf_info = await navigator.find_latest_pdf(official_source.url)
            
            if not pdf_info:
                print(f"[ERROR] Could not find any PDF documents at {official_source.url}")
                sys.exit(1)
            
            print(f"[SUCCESS] Found PDF: {pdf_info.title}")
            print(f"   URL: {pdf_info.url}")
            print(f"   Date: {pdf_info.date or 'Unknown'}")
            
            # Step 3: Parser - Download and convert to Markdown
            content_type = "HTML content" if pdf_info.is_html else "PDF"
            print(f"\n[STEP 3] Processing {content_type}...")
            parser = PDFParser()
            markdown_path = await parser.process_pdf(
                pdf_url=pdf_info.url,
                city_name=city_name,
                source_url=official_source.url,
                meeting_date=pdf_info.date,
                is_html=pdf_info.is_html,
                html_content=pdf_info.html_content
            )
            
            print(f"[SUCCESS] Successfully processed document!")
            print(f"   Output: {markdown_path}")
            print("\n" + "=" * 60)
            print("CivicSense completed successfully!")
    
    except asyncio.TimeoutError:
        print("\n" + "=" * 60)
        print(f"[ERROR] Processing timeout - operation took longer than 5 minutes")
        print(f"[RESULT] Could not complete processing for {city_name}")
        print("This may indicate a complex document or system issue.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[WARNING] Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def cli():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python -m newsroom.main \"City Name, Province/State\"")
        print("Example: python -m newsroom.main \"Hamilton, Ontario\"")
        sys.exit(1)
    
    city_name = sys.argv[1]
    asyncio.run(main(city_name))


if __name__ == "__main__":
    cli()
