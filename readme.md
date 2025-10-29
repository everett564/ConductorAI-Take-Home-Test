# PDF Maximum Number Finder (with NLP Enhancement)

Two Python tools to find the largest numerical value in a PDF document.

## Overview

This package provides two approaches:

1. **Basic Version** (`pdf_max_finder.py`) - Extracts literal numbers as they appear
2. **NLP-Enhanced Version** (`pdf_max_finder_nlp.py`) - Uses natural language processing to understand context and scale modifiers

## Key Difference

The NLP version understands contextual clues like:
- "Revenue was $3.5 million" → interprets as $3,500,000 (not $3.5)
- "Population in thousands: 250" → interprets as 250,000
- "GDP (in billions): 21.5" → interprets as 21,500,000,000
- Scientific notation: "1.5e10" → interprets as 15,000,000,000
- Power notation: "10^120" → interprets as 10^120
- Abbreviations: "150K", "3.5M", "2.1B" → scaled appropriately

## Requirements

- Python 3.6 or higher
- PyPDF2 library

## Installation

```bash
pip install PyPDF2
```

Or using requirements.txt:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Version (Literal Numbers Only)

```bash
python pdf_max_finder.py '.\test_documents\FY25 Air Force Working Capital Fund.pdf'
```

This finds the largest number as literally written in the document.

### NLP-Enhanced Version (Context-Aware)

```bash
python pdf_max_finder_nlp.py '.\test_documents\FY25 Air Force Working Capital Fund.pdf'
```

This understands context and applies scale multipliers to find the true largest value.

## Examples

Given a document with:
- "Revenue: $3.5 million"
- "Population: 450,000"
- "Budget in billions: 2.1"

**Basic version** would report: `450,000` (largest literal number)

**NLP version** would report: `2,100,000,000` (2.1 billion after applying context)

## Output Comparison

### Basic Version Output
```
Reading PDF: document.pdf
Processing 10 pages...
Extracted 50000 characters of text
Found 234 numerical values

==================================================
LARGEST NUMBER FOUND: 450,000.00
==================================================
```

### NLP-Enhanced Version Output
```
Reading PDF: document.pdf
Processing 10 pages...
Extracted 50000 characters of text
Analyzing numbers with NLP context...
Found 234 numerical values (including scaled values)

======================================================================
LARGEST NUMBER FOUND (NLP-Enhanced): 2,100,000,000.00
Context: 2.1 (scaled by billion: x1,000,000,000)
======================================================================

Top 10 Largest Numbers Found:
----------------------------------------------------------------------
 1.      2,100,000,000.00  |  2.1 (scaled by billion: x1,000,000,000)
 2.      3,500,000.00      |  3.5 (scaled by million: x1,000,000)
 3.        450,000.00      |  450,000
...
----------------------------------------------------------------------

💡 Note: This uses NLP to understand context like 'in millions'
   and applies appropriate scale multipliers to find the true
   largest value in the document.
```

## Supported Scale Indicators

The NLP version recognizes these scale modifiers:

**Full Words:**
- trillion, billion, million, thousand, hundred
- Their plural forms (trillions, billions, etc.)

**Abbreviations:**
- K (thousand), M (million), B (billion), T (trillion)
- mn, mil, bn, tn

**Metric Prefixes:**
- kilo, mega, giga

**Contextual Patterns:**
- "3.5 million dollars"
- "in millions"
- "(millions)"
- "millions of dollars"
- "revenue of $3.5M"

**Scientific/Power Notation:**
- 1.5e10 (scientific notation)
- 10^120 (power notation)

## How the NLP Version Works

1. **Text Extraction**: Extracts all text from the PDF
2. **Context Analysis**: For each number found, analyzes surrounding text (50 characters before and after)
3. **Scale Detection**: Looks for scale modifier keywords near the number
4. **Multiplier Application**: Applies the appropriate multiplier to get the actual value
5. **Comparison**: Compares all scaled values to find the maximum

## Limitations

### NLP Version
- Context window is limited to 50 characters around each number
- May misinterpret ambiguous cases
- Assumes standard English scale terminology
- Very large exponents (>1000) are skipped to prevent overflow

### Both Versions
- Require text-based PDFs (not scanned images)
- Cannot process PDFs that require authentication
- Phone numbers and dates may be interpreted as numbers

## Which Version Should I Use?

**Use the Basic Version when:**
- You want the largest number as literally written
- The document doesn't use scale modifiers
- You need simple, straightforward extraction

**Use the NLP Version when:**
- Documents express values "in millions/billions"
- You need to understand the true economic/scientific values
- Financial reports, research papers, or statistical documents
- Documents use abbreviations like "150K" or "3.5M"

## Testing

```bash
# Basic version
python pdf_max_finder.py '.\test_documents\FY25 Air Force Working Capital Fund.pdf'

# NLP version  
python pdf_max_finder_nlp.py '.\test_documents\FY25 Air Force Working Capital Fund.pdf'
```

## Error Handling

Both programs handle:
- Missing files
- Corrupted PDFs
- Documents with no text
- Documents with no numbers
- Invalid number formats

## License

Open source - feel free to use and modify as needed.
