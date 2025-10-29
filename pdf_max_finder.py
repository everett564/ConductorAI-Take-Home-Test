#!/usr/bin/env python3
"""
PDF Maximum Number Finder
Extracts all numerical values from a PDF document and finds the largest one.
"""

import re
import sys
from pathlib import Path
from typing import List, Union
import PyPDF2


def extract_numbers_from_text(text: str) -> List[float]:
    """
    Extract all numerical values from text.
    Handles various formats including:
    - Integers: 123, 1234
    - Decimals: 123.45, .45
    - Numbers with commas: 1,234.56
    - Negative numbers: -123.45
    - Numbers with currency symbols: $1,234.56
    - Percentages: 12.5%
    """
    numbers = []
    
    # Pattern explanation:
    # -? : optional negative sign
    # \$? : optional dollar sign
    # \d{1,3}(,\d{3})* : numbers with comma separators (e.g., 1,234,567)
    # |\d+ : OR just regular digits
    # \.?\d* : optional decimal point and digits
    # %? : optional percentage sign
    pattern = r'-?\$?\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|-?\$?\d+\.?\d*%?'
    
    matches = re.findall(pattern, text)
    
    for match in matches:
        try:
            # Clean the number: remove $, commas, and %
            cleaned = match.replace('$', '').replace(',', '').replace('%', '')
            number = float(cleaned)
            numbers.append(number)
        except ValueError:
            # Skip if conversion fails
            continue
    
    return numbers


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.
    """
    text = ""
    
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            print(f"Processing {num_pages} pages...")
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
                
                if (page_num + 1) % 10 == 0:
                    print(f"Processed {page_num + 1}/{num_pages} pages...")
    
    except Exception as e:
        print(f"Error reading PDF: {e}", file=sys.stderr)
        sys.exit(1)
    
    return text


def find_largest_number(pdf_path: str) -> Union[float, None]:
    """
    Find the largest number in a PDF document.
    """
    print(f"Reading PDF: {pdf_path}")
    
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    
    if not text:
        print("Warning: No text extracted from PDF", file=sys.stderr)
        return None
    
    print(f"Extracted {len(text)} characters of text")
    
    # Extract all numbers
    numbers = extract_numbers_from_text(text)
    
    if not numbers:
        print("Warning: No numbers found in document", file=sys.stderr)
        return None
    
    print(f"Found {len(numbers)} numerical values")
    
    # Find the maximum
    max_number = max(numbers)
    
    return max_number


def main():
    if len(sys.argv) < 2:
        print("Usage: python pdf_max_finder.py <path_to_pdf>")
        print("Example: python pdf_max_finder.py document.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    # Check if file exists
    if not Path(pdf_path).exists():
        print(f"Error: File '{pdf_path}' not found", file=sys.stderr)
        sys.exit(1)
    
    # Find the largest number
    max_number = find_largest_number(pdf_path)
    
    if max_number is not None:
        print(f"\n{'='*50}")
        print(f"LARGEST NUMBER FOUND: {max_number:,.2f}")
        print(f"{'='*50}")
    else:
        print("No numbers found in the document")
        sys.exit(1)


if __name__ == "__main__":
    main()
