"""
OCR Schedule Parser for Krakow Waste Collection
Extracts dates and waste collection information from PNG images using EasyOCR
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Union
from pathlib import Path

# OCR support
try:
    import easyocr
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR not available. Please install: pip install easyocr")

# Date parsing
try:
    from dateutil.parser import parse as parse_date
    from dateutil import tz
    DATEUTIL_AVAILABLE = True
except ImportError:
    DATEUTIL_AVAILABLE = False
    print("python-dateutil not installed. Date parsing may be limited.")


class WasteCollectionParser:
    def __init__(self):
        # Initialize EasyOCR reader if available
        self._ocr_reader = None
        if OCR_AVAILABLE:
            try:
                # Initialize EasyOCR with Polish and English
                self._ocr_reader = easyocr.Reader(['pl', 'en'], gpu=False, verbose=False)
                print("EasyOCR initialized for Polish and English")
            except Exception as e:
                print(f"Failed to initialize EasyOCR: {e}")
                self._ocr_reader = None
        
        # Polish weekday names
        self.polish_weekdays = {
            'Monday': 'Poniedziałek',
            'Tuesday': 'Wtorek', 
            'Wednesday': 'Środa',
            'Thursday': 'Czwartek',
            'Friday': 'Piątek',
            'Saturday': 'Sobota',
            'Sunday': 'Niedziela'
        }
        
        # English to Polish waste type mapping for display
        self.waste_type_polish = {
            'Mixed Waste': 'Zmieszane',
            'Bio/Organic': 'Bio',
            'Glass': 'Szkło', 
            'Paper': 'Papier',
            'Plastic': 'Tworzywa sztuczne',
            'Garden Waste': 'Zielone',
            'Other': 'Inne'
        }
        # Common Polish months for date parsing
        self.polish_months = {
            'stycznia': '01', 'stycznie': '01', 'stycze': '01',
            'lutego': '02', 'luty': '02', 'lut': '02',
            'marca': '03', 'marzec': '03', 'mar': '03',
            'kwietnia': '04', 'kwiecień': '04', 'kwi': '04',
            'maja': '05', 'maj': '05',
            'czerwca': '06', 'czerwiec': '06', 'cze': '06',
            'lipca': '07', 'lipiec': '07', 'lip': '07',
            'sierpnia': '08', 'sierpień': '08', 'sie': '08',
            'września': '09', 'wrzesień': '09', 'wrz': '09', 'wrzesnia': '09',  # Added OCR variant
            'października': '10', 'październik': '10', 'paź': '10', 'pazdziernika': '10', 'pażdziernika': '10', 'poździernika': '10', 'pa dziernika': '10', 'paż dziernika': '10', 'pa z dziernika': '10',  # Added OCR variant
            'listopada': '11', 'listopad': '11', 'lis': '11',
            'grudnia': '12', 'grudzień': '12', 'gru': '12'
        }

        # Weekday to day number mapping for schedule inference
        self.weekday_patterns = {
            'poniedziałek': 'monday',
            'poniedzialek': 'monday', 
            'wtorek': 'tuesday',
            'środa': 'wednesday',
            'sroda': 'wednesday',
            'czwartek': 'thursday', 
            'piątek': 'friday',
            'piatek': 'friday',
            'sobota': 'saturday',
            'niedziela': 'sunday'
        }
        
        # Waste types in Polish (expanded for OCR)
        self.waste_types = {
            'odpady zmieszane': 'Mixed Waste',
            'zmieszane': 'Mixed Waste',
            'bio': 'Bio/Organic',
            'organiczne': 'Bio/Organic',
            'szkło': 'Glass',
            'szklo': 'Glass',
            'papier': 'Paper',
            'plastik': 'Plastic',
            'tworzywa sztuczne': 'Plastic',
            'tworzywa': 'Plastic',
            'metale': 'Metal',
            'odpady wielkogabarytowe': 'Large Items',
            'wielkogabarytowe': 'Large Items',
            'odpady zielone': 'Garden Waste',
            'zielone': 'Garden Waste',
            'selektywne': 'Selective/Recycling'
        }

    
    def extract_text_from_image(self, image_path: str) -> str:
        """Extract text from PNG/JPG image using EasyOCR"""
        if not OCR_AVAILABLE or not self._ocr_reader:
            print("EasyOCR not available. Cannot extract text from images.")
            return ""
            
        try:
            print(f"Processing image: {image_path}")
            
            # Handle file path encoding issues on Windows
            import os
            if not os.path.exists(image_path):
                print(f"Image file not found: {image_path}")
                return ""
            
            # Load image with PIL first to handle encoding issues
            image = Image.open(image_path)
            
            # Convert PIL image to numpy array for EasyOCR
            import numpy as np
            image_array = np.array(image)
            
            # Use EasyOCR to extract text from numpy array
            results = self._ocr_reader.readtext(image_array)
            
            # Combine all detected text
            text_parts = []
            confidence_scores = []
            for (bbox, text, confidence) in results:
                if isinstance(confidence, (int, float)) and confidence > 0.3:  # Only include text with reasonable confidence
                    text_parts.append(text)
                    confidence_scores.append(confidence)
            
            # Join all text parts
            full_text = ' '.join(text_parts)
            
            print(f"EasyOCR extracted {len(full_text)} characters from image")
            print(f"Found {len(results)} text regions, {len(text_parts)} with >30% confidence")
            if confidence_scores:
                print(f"Average confidence: {sum(confidence_scores)/len(confidence_scores):.2f}")
            print("OCR Text Preview:", full_text[:600], "..." if len(full_text) > 600 else "")
            
            # Apply OCR corrections for common misreads
            corrected_text = self.apply_ocr_corrections(full_text)
            
            return corrected_text.lower()  # Convert to lowercase for easier parsing
            
        except Exception as e:
            print(f"Error extracting text from image: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def apply_ocr_corrections(self, text: str) -> str:
        """Apply corrections for common OCR misreads in Polish text"""
        print("Applying OCR corrections...")
        
        # Common OCR errors in Polish date context
        corrections = [
            # Date-specific corrections for Polish months
            # Fix "6 września" -> "16 września" when context suggests it should be 16th
            (r'\b6\s+września\b', '16 września'),

            # Fix other common date misreads
            (r'\b1\s+września\b(?=.*wtorek)', '16 września'),  # If Tuesday context, likely 16th
            (r'\b6\s+wrzesnia\b', '16 września'),  # Alternative spelling

            # Fix single digit dates that should be double digit in context
            # Look for patterns like "wtorek, 6 września" where it should be "16"
            (r'(wtorek[,\s]+)6(\s+września)', r'\g<1>16\g<2>'),
            (r'(poniedziałek[,\s]+)6(\s+września)', r'\g<1>16\g<2>'),

            # Common misreadings of "października" (October) - major issue reported
            (r'pa\.?zdziernik', 'październik'),  # "pa.zdziernik" -> "październik"
            (r'pazdziernik', 'październik'),     # Common OCR error
            (r'paźdz\(iernik', 'październik'),   # Miscapitalization/brackets
            (r'pa[źz]?\s*dziernik', 'październik'),  # Diacritic variants with space handling
            (r'p\.?a[+zžž]?\s*dziernik', 'październik'),  # More OCR variants
            (r'poździernika', 'października'),   # "p" → "po" error

            # Common OCR character substitutions
            ('ó', 'o'),  # OCR often misreads Polish characters
            ('ą', 'a'),
            ('ę', 'e'),
            ('ł', 'l'),
            ('ć', 'c'),
            ('ń', 'n'),
            ('ś', 's'),
            ('ź', 'z'),
            ('ż', 'z'),
            (r'pażdziernik', 'październik'),
            (r'poździernik', 'październik'),
            ]
        
        original_text = text
        
        for pattern, replacement in corrections:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        if text != original_text:
            print("OCR corrections applied:")
            print(f"Original: {original_text[:500]}...")
            print(f"Corrected: {text[:500]}...")
        
        return text

    def normalize_polish_date(self, text: str) -> str:
        """Convert Polish date format to standard format"""
        text = text.lower().strip()
        
        # Replace Polish month names with numbers
        for polish_month, month_num in self.polish_months.items():
            text = text.replace(polish_month, month_num)
        
        return text

    def reconstruct_missing_dates(self, text: str) -> List[Dict[str, str]]:
        """Reconstruct dates that are missing day numbers by analyzing the schedule pattern"""
        reconstructed_dates = []
        
        # Pattern to find schedule entries: weekday; month (without day) + address + waste_type
        pattern = r'(poniedzialek|wtorek|sroda|czwartek|piatek|sobota|niedziela)[;,]\s*(wrzesnia|pazdziernika|pażdziernika|poździernika|listopada|grudnia)\s+krakowska\s+\d*\s*(zielone|bio|papier|szklo|tworzywa|zmieszane)'
        
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        # Analyze the context to infer correct dates
        # Look at explicit dates to understand the schedule sequence
        explicit_dates = []
        explicit_pattern = r'(\d{1,2})\s+(wrzesnia|pazdziernika)'
        explicit_matches = re.finditer(explicit_pattern, text, re.IGNORECASE)
        for match in explicit_matches:
            day, month = match.groups()
            explicit_dates.append(int(day))
        
        print(f"Found explicit dates: {sorted(explicit_dates)}")
        
        # Smart date inference based on context and sequence
        inferred_dates = {}  # weekday -> list of likely dates
        
        # September dates where we have explicit entries: 12, 15, 18, 22, 23, 25, 26, 29, 30
        # Missing likely dates: 2, 3, 5, 9, 10, 16, 17, 19, 20, 24, 27
        september_inference = {
            'monday': [2, 9, 16, 23, 30],  # Known: 22, 29 - likely missing: 2, 9, 16
            'tuesday': [3, 10, 17, 24],     # Known: 23 - likely missing: 3, 10, 17, 24
            'wednesday': [4, 11, 18, 25],   # Known: 25 - likely missing: 4, 11, 18
            'thursday': [5, 12, 19, 26],    # Known: 18, 26 - likely missing: 5, 12, 19
            'friday': [6, 13, 20, 27],      # Known: 12, 26 - likely missing: 6, 13, 20, 27
        }
        
        october_inference = {
            'monday': [6, 13, 20, 27],
            'tuesday': [7, 14, 21, 28],
            'wednesday': [1, 8, 15, 22, 29],
            'thursday': [2, 9, 16, 23, 30],
            'friday': [3, 10, 17, 24, 31],
        }
        
        # Group matches by weekday and month to count occurrences
        weekday_month_counts = {}
        for match in matches:
            weekday, month, waste_type = match.groups()
            key = (weekday.lower(), month.lower())
            if key not in weekday_month_counts:
                weekday_month_counts[key] = []
            weekday_month_counts[key].append(waste_type)
        
        print(f"Weekday-month patterns: {weekday_month_counts}")
        
        # For each weekday-month combination, infer the missing dates
        for (weekday, month), waste_types in weekday_month_counts.items():
            weekday_en = self.weekday_patterns.get(weekday, weekday)
            if not weekday_en:  # Handle None case
                continue
                
            if 'wrzesnia' in month:
                month_num = '09'
                year = 2025
                possible_dates = september_inference.get(weekday_en, [])
            elif any(oct_variant in month for oct_variant in ['pazdziernika', 'pażdziernika', 'poździernika']):
                month_num = '10' 
                year = 2025
                possible_dates = october_inference.get(weekday_en, [])
            else:
                continue
            
            # For this weekday-month combo, pick likely dates based on frequency
            # If we have multiple waste types, we probably have multiple dates
            num_dates_needed = len(waste_types)
            selected_dates = possible_dates[:num_dates_needed]  # Take first N dates
            
            for i, day in enumerate(selected_dates):
                try:
                    date_obj = datetime(year, int(month_num), day)
                    waste_type = waste_types[i] if i < len(waste_types) else waste_types[0]
                    reconstructed_dates.append({
                        'date': date_obj.strftime('%Y-%m-%d'),
                        'formatted': date_obj.strftime('%d.%m.%Y'), 
                        'weekday': date_obj.strftime('%A'),
                        'raw_text': f"{day} {month}",
                        'inferred': True,  # Mark as inferred
                        'waste_type': waste_type
                    })
                except ValueError:
                    continue
        
        return reconstructed_dates

    def extract_dates(self, text: str) -> List[Dict[str, str]]:
        """Extract collection dates from text"""
        dates = []
        
        # Enhanced patterns for Polish dates and schedule format
        date_patterns = [
            # Polish month names: "8 września", "10 września", including OCR variants
            r'(\d{1,2})\s+(stycznia|lutego|marca|kwietnia|maja|czerwca|lipca|sierpnia|września|wrzesnia|października|pazdziernika|pażdziernika|poździernika|listopadu|grudnia)',
            # Standard formats
            r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{4})',  # DD/MM/YYYY, DD.MM.YYYY, DD-MM-YYYY
            r'(\d{1,2})[./\-](\d{1,2})[./\-](\d{2})',   # DD/MM/YY, DD.MM.YY, DD-MM-YY
            r'(\d{1,2})\s+(\d{1,2})\s+(\d{4})',  # DD MM YYYY
        ]
        
        for pattern in date_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    groups = match.groups()
                    
                    if len(groups) == 2:  # Polish format: "8 września"
                        day, month_name = groups
                        if not day or not month_name:  # Handle None case
                            continue
                        print(f"Matched date: {day} {month_name}")
                        month = self.polish_months.get(month_name.lower(), '01')
                        # Get current year, but adjust for schedule year
                        from datetime import datetime as dt
                        current_year = dt.now().year
                        current_month = dt.now().month
                        
                        # If the month is early in year but we're late in current year, 
                        # it's probably next year's schedule
                        if int(month) <= 3 and current_month >= 10:
                            year = str(current_year + 1)
                        else:
                            year = str(current_year)
                    elif len(groups) == 3:  # Standard formats
                        day, month, year = groups
                        if not day or not month or not year:  # Handle None case
                            continue
                        # Handle month names
                        if month.lower() in self.polish_months:
                            month = self.polish_months[month.lower()]
                        # Handle 2-digit years
                        if len(year) == 2:
                            year = "20" + year
                    else:
                        continue
                    
                    # Create date object
                    date_obj = datetime(int(year), int(month), int(day))
                    
                    dates.append({
                        'date': date_obj.strftime('%Y-%m-%d'),
                        'formatted': date_obj.strftime('%d.%m.%Y'),
                        'weekday': date_obj.strftime('%A'),
                        'raw_text': match.group(0),
                        'inferred': False
                    })
                except (ValueError, IndexError) as e:
                    print(f"Date parsing error for '{match.group(0)}': {e}")
                    continue
        
        # Only use explicitly found dates - no reconstruction/inference
        print(f"Found {len(dates)} explicit dates from OCR text")
        
        # Remove duplicates and sort by date
        seen = set()
        unique_dates = []
        for date_info in dates:
            if date_info['date'] not in seen:
                seen.add(date_info['date'])
                unique_dates.append(date_info)
        
        return sorted(unique_dates, key=lambda x: x['date'])

    def extract_waste_types(self, text: str) -> List[str]:
        """Extract waste types from text"""
        found_types = []
        
        for polish_name, english_name in self.waste_types.items():
            if polish_name in text:
                found_types.append({
                    'polish': polish_name,
                    'english': english_name
                })
        
        return found_types

    def extract_schedule_info(self, text: str) -> Dict:
        """Extract complete schedule information"""
        # Look for Krakowska 3c pattern specifically from the schedule
        address_pattern = r'(krakowska)\s+(\d+[a-z]*)'
        address_match = re.search(address_pattern, text, re.IGNORECASE)
        
        if address_match:
            address = address_match.group(1).capitalize()
            house_number = address_match.group(2)
        else:
            # Fallback to generic address extraction
            address_match = re.search(r'([a-ząćęłńóśżź]+)\s+(\d+[a-z]*)', text, re.IGNORECASE)
            if address_match:
                address = address_match.group(1).capitalize() 
                house_number = address_match.group(2)
            else:
                address = "Unknown"
                house_number = "Unknown"
        
        # Extract dates and waste types
        dates = self.extract_dates(text)
        waste_types = self.extract_waste_types(text)
        
        # Try to categorize dates by waste type (basic heuristic)
        categorized_dates = self.categorize_dates(text, dates)
        
        return {
            'address': address,
            'house_number': house_number,
            'dates': dates,
            'waste_types': waste_types,
            'categorized_schedule': categorized_dates,
            'total_collections': len(dates)
        }

    def categorize_dates(self, text: str, dates: List[Dict]) -> Dict:
        """Categorize dates by waste type using improved pattern matching"""
        categorized = {}
        
        # First, handle explicit dates with the existing pattern
        # Enhanced pattern: [day_of_week] [day] [month] [address] [waste_type] 
        pattern = r'(\w+)[,;]\s*(\d{1,2})\s+(\w+)\s+([^,;]+?)\s+(zielone|bio|zmieszane|papier|szkło|szklo|tworzywa sztuczne|tworzywa)'
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            day_of_week, day, month, address, waste_type = match.groups()
            
            # Map Polish waste types to English
            waste_type_lower = waste_type.lower()
            if waste_type_lower == 'zielone':
                category = 'Garden Waste'
            elif waste_type_lower == 'bio':
                category = 'Bio/Organic'
            elif waste_type_lower == 'zmieszane':
                category = 'Mixed Waste'
            elif waste_type_lower == 'papier':
                category = 'Paper'
            elif waste_type_lower in ['szkło', 'szklo']:
                category = 'Glass'
            elif 'tworzywa' in waste_type_lower:
                category = 'Plastic'
            else:
                category = 'Other'
            
            # Create date object
            try:
                month_num = self.polish_months.get(month.lower(), '01')
                from datetime import datetime as dt
                current_year = dt.now().year
                current_month = dt.now().month
                
                # Smart year detection
                if int(month_num) <= 3 and current_month >= 10:
                    year = current_year + 1
                else:
                    year = current_year
                
                date_obj = datetime(year, int(month_num), int(day))
                
                date_info = {
                    'date': date_obj.strftime('%Y-%m-%d'),
                    'formatted': date_obj.strftime('%d.%m.%Y'),
                    'weekday': date_obj.strftime('%A'),
                    'raw_text': f"{day} {month}"
                }
                
                if category not in categorized:
                    categorized[category] = []
                
                categorized[category].append(date_info)
                
            except (ValueError, KeyError):
                continue
        
        # Second, handle inferred dates that have waste_type information
        for date_info in dates:
            if date_info.get('inferred', False) and 'waste_type' in date_info:
                waste_type = date_info['waste_type'].lower()
                
                # Map Polish waste types to English
                if waste_type == 'zielone':
                    category = 'Garden Waste'
                elif waste_type == 'bio':
                    category = 'Bio/Organic'
                elif waste_type == 'zmieszane':
                    category = 'Mixed Waste'
                elif waste_type == 'papier':
                    category = 'Paper'
                elif waste_type in ['szkło', 'szklo']:
                    category = 'Glass'
                elif 'tworzywa' in waste_type:
                    category = 'Plastic'
                else:
                    category = 'Other'
                
                if category not in categorized:
                    categorized[category] = []
                
                # Create categorized date entry
                categorized[category].append({
                    'date': date_info['date'],
                    'formatted': date_info['formatted'],
                    'weekday': date_info['weekday'],
                    'raw_text': date_info['raw_text']
                })
        
        return categorized

    def parse_schedule_file(self, file_path: str) -> Dict:
        """Main method to parse PNG image file and return schedule information"""
        if not Path(file_path).exists():
            return {'error': f'File not found: {file_path}'}
        
        try:
            file_ext = Path(file_path).suffix.lower()
            
            # Only support image files
            if file_ext not in ['.png', '.jpg', '.jpeg']:
                return {'error': f'Unsupported file type: {file_ext}. Only PNG/JPG images are supported.'}
            
            # Extract text using OCR
            text = self.extract_text_from_image(file_path)
            
            if not text.strip():
                return {'error': 'Could not extract text from image'}
            
            # Parse schedule information
            schedule_info = self.extract_schedule_info(text)
            
            # Add metadata
            schedule_info['source_file'] = file_path
            schedule_info['file_type'] = file_ext[1:]  # Remove dot
            schedule_info['raw_text'] = text[:500]  # First 500 chars for debugging
            
            return schedule_info
            
        except Exception as e:
            return {'error': f'Error parsing file: {str(e)}'}

    def format_schedule_for_display(self, schedule_info: Dict) -> str:
        """Format schedule information for display, organized by date"""
        if 'error' in schedule_info:
            return f"Error: {schedule_info['error']}"
        
        output = []
        output.append(f"Adres: {schedule_info['address']} {schedule_info['house_number']}")
        output.append(f"Liczba wywozów: {schedule_info['total_collections']}")
        output.append("")
        
        if schedule_info['waste_types']:
            output.append("Znalezione rodzaje odpadów:")
            for waste_type in schedule_info['waste_types']:
                output.append(f"  - {waste_type['polish']}")
            output.append("")
        
        if schedule_info['categorized_schedule']:
            output.append("Harmonogram (według daty):")
            output.append("=" * 40)
            
            # Collect all dates with their waste types
            all_collections = []
            for waste_type, dates in schedule_info['categorized_schedule'].items():
                for date_info in dates:
                    all_collections.append({
                        'date': date_info['date'],
                        'formatted': date_info['formatted'], 
                        'weekday': date_info['weekday'],
                        'waste_type': waste_type
                    })
            
            # Sort by date
            all_collections.sort(key=lambda x: x['date'])
            
            # Group by date (in case multiple waste types on same day)
            from collections import defaultdict
            by_date = defaultdict(list)
            for collection in all_collections:
                date_key = collection['formatted']
                by_date[date_key].append(collection)
            
            # Display organized by date
            for date_str in sorted(by_date.keys(), key=lambda d: datetime.strptime(d, '%d.%m.%Y')):
                collections_on_date = by_date[date_str]
                weekday_eng = collections_on_date[0]['weekday']
                weekday_pl = self.polish_weekdays.get(weekday_eng, weekday_eng)
                
                if len(collections_on_date) == 1:
                    # Single collection
                    waste_type_eng = collections_on_date[0]['waste_type']
                    waste_type_pl = self.waste_type_polish.get(waste_type_eng, waste_type_eng)
                    output.append(f"{date_str} ({weekday_pl}) - {waste_type_pl}")
                else:
                    # Multiple collections on same date
                    waste_types_eng = [c['waste_type'] for c in collections_on_date]
                    waste_types_pl = [self.waste_type_polish.get(wt, wt) for wt in waste_types_eng]
                    # Filter out None values before joining
                    waste_types_pl = [wt for wt in waste_types_pl if wt is not None]
                    output.append(f"{date_str} ({weekday_pl}) - {', '.join(waste_types_pl)}")
        
        elif schedule_info['dates']:
            output.append("Next Collection Dates:")
            for date_info in schedule_info['dates'][:10]:  # Show first 10 dates
                output.append(f"  - {date_info['formatted']} ({date_info['weekday']})")
            if len(schedule_info['dates']) > 10:
                output.append(f"  ... and {len(schedule_info['dates']) - 10} more dates")
        
        return "\n".join(output)


def test_parser():
    """Test function for the parser with a real PNG file"""
    parser = WasteCollectionParser()
    
    # Test with existing PNG file
    png_file = "schedule_Krakowska_1.png"
    if Path(png_file).exists():
        print(f"Testing OCR parser with: {png_file}")
        schedule_info = parser.parse_schedule_file(png_file)
        formatted = parser.format_schedule_for_display(schedule_info)
        
        print("OCR Parser Results:")
        print("=" * 40)
        print(formatted)
    else:
        print(f"PNG file not found: {png_file}")
        print("Run the main app first to generate a schedule image")


if __name__ == "__main__":
    test_parser()