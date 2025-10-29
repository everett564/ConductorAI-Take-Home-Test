#!/usr/bin/env python3
"""
NLP-Enhanced PDF Maximum Number Finder
Uses natural language processing to understand context and scale modifiers
(millions, billions, thousands, etc.) to find the true largest number.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional
import PyPDF2

# Optional NLP: spaCy
try:
    import spacy
    _SPACY_AVAILABLE = True
except Exception:
    spacy = None  # type: ignore
    _SPACY_AVAILABLE = False

def load_spacy_model(model_name: str = "en_core_web_sm"):
    """Try to load a spaCy model. Returns the nlp object or None."""
    if not _SPACY_AVAILABLE:
        return None
    try:
        # Prefer a full model if installed
        return spacy.load(model_name)
    except Exception:
        try:
            # Fall back to a blank English pipeline (no NER)
            return spacy.blank('en')
        except Exception:
            return None


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
    
    # (scientific notation handled separately)
    
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


def parse_scientific_notation(text: str) -> List[Tuple[float, str, int, int]]:
    """
    Parse scientific notation (e.g. 1.23e6) and power notation (e.g. 10^12).
    Returns list of tuples (value, original_string, start_index, end_index).
    """
    results = []
    
    # Pattern for scientific notation: 1.23e6, 1.23E6, 1.23e+6, 1.23e-6
    sci_pattern = r'(\d+\.?\d*)[eE]([+-]?\d+)'
    for match in re.finditer(sci_pattern, text):
        try:
            base = float(match.group(1))
            exponent = int(match.group(2))
            value = base * (10 ** exponent)
            results.append((value, match.group(0), match.start(), match.end()))
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
                results.append((value, match.group(0), match.start(), match.end()))
        except (ValueError, OverflowError):
            continue
    
    return results


def extract_numbers_with_context(text: str, context_window: int = 50, nlp: Optional[object] = None) -> List[Tuple[float, str]]:
    """
    Extract numbers along with their surrounding context to detect scale modifiers.
    Returns list of (actual_value, context_string) tuples.
    """
    numbers_with_context = []
    
    # First, handle scientific notation separately (and keep spans to avoid duplicates)
    used_spans = []  # list of (start, end) to dedupe
    sci_numbers = parse_scientific_notation(text)
    for value, orig, start, end in sci_numbers:
        numbers_with_context.append((value, orig))
        used_spans.append((start, end))

    # If spaCy is available and a model was provided, use entity extraction first
    if _SPACY_AVAILABLE and nlp is not None:
        try:
            # spacy-based extraction will return triples with spans for deduplication
            spacy_results = extract_entities_with_spacy(nlp, text)
            for val, ctx, span in spacy_results:
                numbers_with_context.append((val, ctx))
                used_spans.append(span)
        except Exception:
            # Fall back silently to regex approach if spaCy extraction fails
            pass
    
    # Pattern to match numbers with various formats
    number_pattern = r'-?\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|-?\$?\d+\.?\d*%?'
    
    for match in re.finditer(number_pattern, text):
        number_str = match.group(0)
        number_pos = match.start()
        number_end = match.end()

        # Skip if this span overlaps a previously-used span (from sci or spaCy)
        overlap = False
        for s, e in used_spans:
            if not (number_end <= s or number_pos >= e):
                overlap = True
                break
        if overlap:
            continue
        
        # Get surrounding context
        context_start = max(0, number_pos - context_window)
        context_end = min(len(text), match.end() + context_window)
        context = text[context_start:context_end].lower()
        
        # Extract the base number
        try:
            cleaned = number_str.replace('$', '').replace(',', '')
            is_percent = '%' in number_str
            base_number = float(cleaned.replace('%', ''))
            if is_percent:
                # Convert percent to fraction (e.g., 50% -> 0.5)
                base_number = base_number / 100.0
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
        # mark this regex match span as used to avoid duplicates later
        used_spans.append((number_pos, number_end))

        actual_value = base_number * multiplier
        
        # Store with context information
        if found_scale:
            context_info = f"{number_str} (scaled by {found_scale}: x{multiplier:,.0f})"
        else:
            context_info = number_str
        
        numbers_with_context.append((actual_value, context_info))
    
    return numbers_with_context


def extract_entities_with_spacy(nlp, text: str) -> List[Tuple[float, str, Tuple[int, int]]]:
    """
    Use spaCy NER to extract MONEY/QUANTITY/PERCENT entities and convert them to numeric values.
    Returns list of (value, context_info, (start, end))
    """
    results: List[Tuple[float, str, Tuple[int, int]]] = []
    if nlp is None:
        return results

    doc = nlp(text)

    # Regex to find a numeric token inside the entity text
    num_re = re.compile(r'-?\$?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?|-?\$?\d+\.?\d*%?')

    for ent in doc.ents:
        if ent.label_ not in {'MONEY', 'QUANTITY', 'PERCENT', 'CARDINAL'}:
            continue

        ent_text = ent.text
        m = num_re.search(ent_text)
        if not m:
            continue

        number_str = m.group(0)
        try:
            cleaned = number_str.replace('$', '').replace(',', '')
            is_percent = '%' in number_str or ent.label_ == 'PERCENT'
            base_number = float(cleaned.replace('%', ''))
            if is_percent:
                base_number = base_number / 100.0
        except ValueError:
            continue

        # Look for scale words in a small window after the entity
        context_start = max(0, ent.start_char - 20)
        context_end = min(len(text), ent.end_char + 50)
        context = text[context_start:context_end].lower()

        multiplier = 1.0
        found_scale = None
        for scale_word, scale_value in SCALE_MULTIPLIERS.items():
            if re.search(rf'\b{re.escape(scale_word)}s?\b', context):
                if scale_value > multiplier:
                    multiplier = scale_value
                    found_scale = scale_word

        actual_value = base_number * multiplier
        if found_scale:
            context_info = f"{number_str} (scaled by {found_scale}: x{multiplier:,.0f})"
        else:
            context_info = number_str

        results.append((actual_value, context_info, (ent.start_char, ent.end_char)))

    return results


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
    # Try to load a spaCy model (if spaCy is installed). If no model is available
    # we'll fall back to the original regex-based extraction.
    nlp = None
    if _SPACY_AVAILABLE:
        nlp = load_spacy_model()
        if nlp is None:
            print("spaCy is installed but no model was found; falling back to regex heuristics.")

    numbers_with_context = extract_numbers_with_context(text, nlp=nlp)
    
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
