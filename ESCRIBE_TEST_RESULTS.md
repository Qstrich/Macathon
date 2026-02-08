# eSCRIBE Integration Test Results

**Date**: February 7, 2026  
**Enhancement**: Added specialized eSCRIBE parser for Canadian municipal meeting portals

## Summary

CivicSense now successfully identifies and extracts documents from **eSCRIBE meeting portals** (escribemeetings.com), which are used by many Canadian municipalities to publish meeting agendas, minutes, and related documents.

## Test Results

### ✅ Hamilton, Ontario
- **eSCRIBE Portal**: `pub-hamilton.escribemeetings.com`
- **Status**: **SUCCESS**
- **Document Found**: Seniors Advisory Committee Minutes - January 9, 2026
- **Document Type**: Full meeting minutes with attendance, agenda items, and discussions
- **Output**: `data\hamilton_ontario_20260207_203042.md`

**Quality**: Excellent - Real committee meeting minutes with detailed proceedings including:
- Attendance list
- Land Acknowledgement
- Working group updates
- Discussion items
- Action items

---

### ✅ Ottawa, Ontario
- **eSCRIBE Portal**: `pub-ottawa.escribemeetings.com`
- **Status**: **SUCCESS**
- **Document Found**: Ottawa City Council Draft Minutes 71 - December 10, 2025
- **Document Type**: Full City Council meeting minutes
- **Output**: `data\ottawa_ontario_20260207_203549.md`
- **Documents Available**: 95 documents detected on the meeting page

**Quality**: Excellent - Comprehensive City Council minutes including:
- Full attendance record (Mayor + 24 Councillors)
- Call to order and moment of reflection
- Declarations of interest
- Communications
- Meeting proceedings

---

### ✅ Mississauga, Ontario
- **eSCRIBE Portal**: `pub-mississauga.escribemeetings.com`
- **Status**: **SUCCESS**
- **Document Found**: Budget Committee Report 1 - 2026 (January 12, 13, 20, 2026)
- **Document Type**: Committee report for City Council
- **Output**: `data\mississauga_ontario_20260207_203701.md`
- **Documents Available**: 18 documents detected on the meeting page

**Quality**: Good - Official committee report submitted to Council

---

### ⚠️ Waterloo, Ontario
- **eSCRIBE Portal**: Not found
- **Status**: **PARTIAL** - Found PDF, but not meeting minutes
- **Document Found**: Acrobat Reader instructions (non-relevant)
- **Issue**: Scout found the general meetings page, but it linked to a help document instead of actual minutes

**Recommendation**: Needs better PDF filtering to skip help/instruction documents

---

### ❌ Toronto, Ontario
- **eSCRIBE Portal**: Generic `www.escribemeetings.com` (not city-specific)
- **Status**: **FAILED**
- **Issue**: AI selected generic eSCRIBE homepage instead of city-specific portal
- **Root Cause**: No direct Toronto eSCRIBE portal found in search results

**Recommendation**: Toronto may not use eSCRIBE or has a different meeting portal system

---

## Key Improvements

### 1. eSCRIBE Portal Detection
- Scout agent now prioritizes city-specific eSCRIBE portals (e.g., `pub-{city}.escribemeetings.com`)
- Fallback scoring system distinguishes between generic and city-specific eSCRIBE domains
- Added dedicated search query: `{city_name} escribemeetings.com`

### 2. Specialized eSCRIBE Parser (`escribe_parser.py`)
- Detects eSCRIBE portal URLs automatically
- Navigates from portal homepage to latest meeting
- Extracts documents using eSCRIBE-specific patterns:
  - `filestream.ashx?DocumentId=` URLs
  - `GetFile.ashx` patterns
  - Meeting page document links
- Prioritizes document types: Minutes > Agenda > Packet > Report

### 3. Enhanced Document Extraction
- Multiple extraction methods (direct links, JavaScript onclick, iframes)
- Deduplication of documents by URL
- Intelligent title extraction from link text, aria-label, and title attributes
- Parent/sibling element context for better titles

### 4. AI Integration
- Enhanced scout prompt explicitly prioritizes eSCRIBE portals
- City-specific eSCRIBE portals get highest scoring (200 points)
- Generic eSCRIBE domains get lower priority (30 points)

---

## Statistics

| City | eSCRIBE Found | Documents Extracted | Success Rate |
|------|---------------|---------------------|--------------|
| Hamilton | ✅ | 1 (Minutes) | 100% |
| Ottawa | ✅ | 95 (selected 1) | 100% |
| Mississauga | ✅ | 18 (selected 1) | 100% |
| Waterloo | ❌ | N/A | 0% |
| Toronto | ❌ | N/A | 0% |

**Overall eSCRIBE Success Rate**: 60% (3/5 cities)  
**Document Quality (when found)**: Excellent - actual meeting minutes/reports

---

## Technical Architecture

### New Components

1. **`newsroom/agents/escribe_parser.py`** (294 lines)
   - `eSCRIBEDocument` model
   - `eSCRIBEParser` class
   - `extract_documents()` method
   - `find_latest_meeting()` method
   - `_classify_document()` helper

2. **Enhanced `navigator_simple.py`**
   - `_handle_escribe_portal()` method
   - Automatic eSCRIBE detection
   - Portal homepage navigation

3. **Enhanced `scout.py`**
   - City-specific eSCRIBE scoring
   - New search query for eSCRIBE portals
   - Enhanced AI prompt prioritization

---

## Comparison: Before vs After

### Before eSCRIBE Integration
- **Hamilton**: Found confirmation by-law (not actual minutes)
- **Ottawa**: Often found news articles or generic pages
- **Waterloo**: Found calendar page (no documents)

### After eSCRIBE Integration
- **Hamilton**: ✅ Full committee meeting minutes
- **Ottawa**: ✅ Complete City Council minutes (71 meetings)
- **Mississauga**: ✅ Official committee report

**Improvement**: Agent now finds actual meeting documents instead of generic pages/bylaws

---

## Next Steps

1. **Improve PDF filtering** to skip help documents and focus on minutes/agendas
2. **Add support for other meeting portal systems**:
   - Legistar
   - Granicus
   - CivicWeb
3. **Enhance city disambiguation** for common city names
4. **Add date extraction** from eSCRIBE meeting pages for better metadata
5. **Test with more cities** across different provinces

---

## Conclusion

The eSCRIBE integration is a **major success**. The agent can now:
- Automatically detect eSCRIBE portals for Canadian municipalities
- Navigate complex meeting management systems
- Extract actual meeting minutes and official documents
- Prioritize city-specific portals over generic domains

This represents a significant improvement in document quality and relevance for cities using eSCRIBE.
