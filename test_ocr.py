#!/usr/bin/env python3
"""
Test OCR functionality with existing schedule PNG
"""

import os
from pathlib import Path

def test_ocr():
    try:
        from ocr_parser import WasteCollectionParser
        
        parser = WasteCollectionParser()
        
        # Test with the existing PNG file
        png_file = "schedule_Krakowska_1.png"
        
        if not Path(png_file).exists():
            print(f"PNG file not found: {png_file}")
            print("Run the main app first to generate a schedule image")
            return
        
        print(f"Testing OCR with: {png_file}")
        print("="*50)
        
        # Parse the image
        schedule_info = parser.parse_schedule_file(png_file)
        
        if 'error' in schedule_info:
            print(f"ERROR: {schedule_info['error']}")
            return
        
        # Display results
        formatted = parser.format_schedule_for_display(schedule_info)
        print("EXTRACTED DATA:")
        print("-" * 30)
        print(formatted)
        
        # Show raw OCR text for debugging
        if 'raw_text' in schedule_info:
            print("\nRAW OCR TEXT (first 300 chars):")
            print("-" * 40)
            print(schedule_info['raw_text'][:300] + "..." if len(schedule_info['raw_text']) > 300 else schedule_info['raw_text'])
        
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure to install: pip install easyocr Pillow python-dateutil")
    except Exception as e:
        print(f"Error: {e}")
        
        if "easyocr" in str(e).lower():
            print("\nEasyOCR is not working properly!")
            print("Try installing: pip install easyocr")
            print("Or with pip: pip install easyocr")

if __name__ == "__main__":
    test_ocr()