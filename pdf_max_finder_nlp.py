#!/usr/bin/env python3
"""
NLP-Enhanced PDF Maximum Number Finder
Uses natural language processing to understand context and scale modifiers
(millions, billions, thousands, etc.) to find the true largest number.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import PyPDF2


# Scale multipliers for common units
SCALE_MULTIPLIERS = {
    # Standard scales
    'trillion': 1_000_000_000_000,
    'trillions': 1_000_000_000_000,
    'billion': 1_000_000_000,
    'billions': 1_000_000_000,
    'million': 1_000_000,
    'millions': 1_000_000,
    'thousand': 1_000,
    'thousands': 1_000,
    'hundred': 100,
    'hundreds': 100,
    
    # Abbreviated forms
    'tn': 1_000_000_000_000,
    'bn': 1_000_000_000,
    'mn': 1_000_000,
    'mil': 1_000_000,
    'k': 1_000,
    
    # Metric prefixes
    'giga': 1_000_000_000,
    'mega': 1_000_000,
    'kilo': 1_000,
    
    # Scientific notation indicators
    'e': 1,  # Will be handled specially
    
    # Financial/business terms
    'b': 1_000_000_000,  # Often used for billions in finance
    'm': 1_000_000,      # Often used for millions in finance
}


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            print(f"Processing {num_pages} pages...")
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n"
                
                if (page_num + 1) % 10 == 0:
                    print(f"Processed {page_num + 1}/{num_pages} pages...")
    
    except Exception as e:
        print(f"Error reading PDF: {e}", file=sys.stderr)
        sys.exit(1)
    
    return text


def parse_scientific_notation(text: str) -> List[Tuple[float, str]]:
    """
    Parse scientific notation like 1.23e6, 4.56e-3, 10^120
    Returns list of (value, original_string) tuples
    """
    results = []
    
    # Pattern for scientific notation: 1.23e6, 1.23E6, 1.23e+6, 1.23e-6
    sci_pattern = r'(\d+\.?\d*)[eE]([+-]?\d+)'
    for match in re.finditer(sci_pattern, text):
        try:
            base = float(match.group(1))
            exponent = int(match.group(2))
            value = base * (10 ** exponent)
            results.append((value, match.group(0)))
        except (ValueError, OverflowError):
            continue
    
    # Pattern for power notation: 10^120, 2^32
    power_pattern = r'(\d+\.?\d*)\^(\d+)'
    for match in re.finditer(power_pattern, text):
        try:
            base = float(match.group(1))
            exponent = int(match.group(2))
            # Limit exponent to prevent overflow
            if exponent <= 1000:
                value = base ** exponent
                results.append((value, match.group(0)))
        except (ValueError, OverflowError):
            continue
    
    return results


def extract_numbers_with_context(text: str, context_window: int = 50) -> List[Tuple[float, str]]:
    """
    Extract numbers along with their surrounding context to detect scale modifiers.
    Returns list of (actual_value, context_string) tuples.
    """
    numbers_with_context = []
    
    # First, handle scientific notation separately
    sci_numbers = parse_scientific_notation(text)
    numbers_with_context.extend(sci_numbers)
    
    # Pattern to match numbers with various formats
    number_pattern = r'-?\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|-?\$?\d+\.?\d*%?'
    
    for match in re.finditer(number_pattern, text):
        number_str = match.group(0)
        number_pos = match.start()
        
        # Get surrounding context
        context_start = max(0, number_pos - context_window)
        context_end = min(len(text), match.end() + context_window)
        context = text[context_start:context_end].lower()
        
        # Extract the base number
        try:
            cleaned = number_str.replace('$', '').replace(',', '').replace('%', '')
            base_number = float(cleaned)
        except ValueError:
            continue
        
        # Look for scale multipliers in the context
        multiplier = 1.0
        found_scale = None
        
        # Check for scale words before and after the number
        for scale_word, scale_value in SCALE_MULTIPLIERS.items():
            # Look for patterns like "3.5 million", "million dollars", "in millions"
            patterns = [
                rf'\b{re.escape(number_str)}\s+{scale_word}\b',  # "3.5 million"
                rf'\b{scale_word}\s+(?:of\s+)?(?:dollars?|pounds?|euros?)',  # "million dollars"
                rf'\bin\s+{scale_word}s?\b',  # "in millions"
                rf'\({scale_word}s?\)',  # "(millions)"
                rf'{scale_word}s?\s+of\s+(?:dollars?|pounds?)',  # "millions of dollars"
            ]
            
            for pattern in patterns:
                if re.search(pattern, context, re.IGNORECASE):
                    if scale_value > multiplier:
                        multiplier = scale_value
                        found_scale = scale_word
        
        # Special handling for standalone letters that might be abbreviations
        # Only apply if the number is small (< 1000) to avoid false positives
        if base_number < 1000 and multiplier == 1.0:
            # Look for patterns like "3.5M", "150K", "2.3B"
            abbrev_pattern = rf'{re.escape(number_str)}\s*([KMBT])\b'
            abbrev_match = re.search(abbrev_pattern, text[context_start:context_end], re.IGNORECASE)
            if abbrev_match:
                abbrev = abbrev_match.group(1).lower()
                abbrev_multipliers = {'k': 1_000, 'm': 1_000_000, 'b': 1_000_000_000, 't': 1_000_000_000_000}
                if abbrev in abbrev_multipliers:
                    multiplier = abbrev_multipliers[abbrev]
                    found_scale = abbrev.upper()
        
        actual_value = base_number * multiplier
        
        # Store with context information
        if found_scale:
            context_info = f"{number_str} (scaled by {found_scale}: x{multiplier:,.0f})"
        else:
            context_info = number_str
        
        numbers_with_context.append((actual_value, context_info))
    
    return numbers_with_context


def find_largest_number_nlp(pdf_path: str) -> Tuple[float, str, List[Tuple[float, str]]]:
    """
    Find the largest number in a PDF using NLP context awareness.
    Returns (max_value, context, top_10_numbers)
    """
    print(f"Reading PDF: {pdf_path}")
    
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        print("Warning: No text extracted from PDF", file=sys.stderr)
        return None, None, []
    
    print(f"Extracted {len(text)} characters of text")
    
    # Extract numbers with context
    print("Analyzing numbers with NLP context...")
    numbers_with_context = extract_numbers_with_context(text)
    
    if not numbers_with_context:
        print("Warning: No numbers found in document", file=sys.stderr)
        return None, None, []
    
    print(f"Found {len(numbers_with_context)} numerical values (including scaled values)")
    
    # Sort by value (descending)
    sorted_numbers = sorted(numbers_with_context, key=lambda x: x[0], reverse=True)
    
    # Get the maximum
    max_number, max_context = sorted_numbers[0]
    
    # Get top 10 for display
    top_10 = sorted_numbers[:10]
    
    return max_number, max_context, top_10


def main():
    if len(sys.argv) < 2:
        print("Usage: python find_max_number_nlp.py <path_to_pdf>")
        print("Example: python find_max_number_nlp.py document.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"Error: File '{pdf_path}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Find the largest number with NLP
    max_number, max_context, top_10 = find_largest_number_nlp(pdf_path)
    
    if max_number is not None:
        print(f"\n{'='*70}")
        print(f"LARGEST NUMBER FOUND (NLP-Enhanced): {max_number:,.2f}")
        print(f"Context: {max_context}")
        print(f"{'='*70}")
        
        if top_10:
            print(f"\nTop 10 Largest Numbers Found:")
            print(f"{'-'*70}")
            for i, (value, context) in enumerate(top_10, 1):
                print(f"{i:2d}. {value:>20,.2f}  |  {context}")
            print(f"{'-'*70}")
        
        print("\n💡 Note: This uses NLP to understand context like 'in millions'")
        print("   and applies appropriate scale multipliers to find the true")
        print("   largest value in the document.")
    else:
        print("No numbers found in the document")
        sys.exit(1)


if __name__ == "__main__":
    main()
