#!/usr/bin/env python3
"""
Extract component data from VAHYA_MINI_IBOM.html
The IBOM file contains LZString-compressed Base64 JSON data.
"""

import re
import json
import base64

def lzstring_decompress(compressed):
    """
    Simple LZString decompression from Base64
    This is a Python implementation of the key parts needed
    """
    # For now, let's just extract what we can from the HTML
    # The full LZString algorithm is complex, but we can get data another way
    pass

def extract_pcbdata_from_html(html_file):
    """Extract the compressed pcbdata from the IBOM HTML"""
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the pcbdata assignment
    match = re.search(r'var pcbdata = JSON\.parse\(LZString\.decompressFromBase64\([\'"]([^\'"]+)[\'"]\)', content)

    if match:
        compressed_data = match.group(1)
        print(f"Found compressed data: {len(compressed_data)} characters")
        return compressed_data
    else:
        print("Could not find pcbdata in HTML")
        return None

def extract_components_from_html(html_file):
    """
    Alternative: Extract component data from the HTML tables if present
    Many IBOM files have both compressed and HTML table representations
    """
    with open(html_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Look for component tables or divs
    # Extract any visible component data
    components = []

    # Try to find component references in the HTML
    refs = re.findall(r'["\'](U\d+|R\d+|C\d+|L\d+|D\d+|J\d+|Y\d+)["\']', content)
    unique_refs = sorted(set(refs))

    print(f"Found {len(unique_refs)} unique component references")
    print("Sample references:", unique_refs[:20])

    return unique_refs

if __name__ == '__main__':
    html_file = '/home/user/orbtrace/vahya/VAHYA_MINI_IBOM.html'

    print("=" * 60)
    print("Extracting VAHYA MINI IBOM Component Data")
    print("=" * 60)

    # Try to get compressed data
    compressed = extract_pcbdata_from_html(html_file)

    # Extract component references
    components = extract_components_from_html(html_file)

    print(f"\nTotal unique components found: {len(components)}")
