"""
Kraków Waste Schedule API Client
Direct API integration for kiedywywoz.pl - no browser automation needed!
"""

import requests
import json
import base64
from typing import List, Dict, Tuple, Optional
import re
from datetime import datetime


class KrakówWasteAPIClient:
    """
    Direct API client for Kraków waste collection schedule
    Much faster and more reliable than web scraping!
    """
    
    def __init__(self):
        self.base_url = "https://kiedywywoz.pl/API/harmo_img/"
        self.token = "OkkxhC6b9etJBAq7WTHJ0LhIglO18sip"  # Fixed token from API analysis
        self.headers = {
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'Accept': '*/*',
            'Referer': 'https://harmonogram.mpo.krakow.pl/',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Cache for performance
        self._streets_cache = None
        self._house_numbers_cache = {}
    
    def get_streets(self) -> List[Dict[str, str]]:
        """
        Get list of all streets in Kraków
        Returns: [{"id": "39936", "name": "Krakowska"}, ...]
        """
        if self._streets_cache is not None:
            return self._streets_cache
        
        try:
            print("Fetching streets list from API...")
            data = {"token": self.token}
            
            response = requests.post(self.base_url, data=data, headers=self.headers)
            response.raise_for_status()
            
            streets = response.json()
            # Filter out the "-Brak-" option
            streets = [s for s in streets if s.get('name', '').strip() != '-Brak-']
            
            self._streets_cache = streets
            print(f"Loaded {len(streets)} streets")
            return streets
            
        except Exception as e:
            print(f"Error fetching streets: {e}")
            return []
    
    def find_street(self, street_name: str) -> Optional[Dict[str, str]]:
        """
        Find street by name (case-insensitive, partial matching)
        Returns: {"id": "39936", "name": "Krakowska"} or None
        """
        streets = self.get_streets()
        street_name = street_name.lower().strip()
        
        # First try exact match
        for street in streets:
            if street['name'].lower() == street_name:
                return street
        
        # Then try partial match
        for street in streets:
            if street_name in street['name'].lower():
                return street
        
        return None
    
    def get_house_numbers(self, street_id: str) -> List[Dict[str, str]]:
        """
        Get house numbers for a specific street
        Args: street_id (e.g., "39936")
        Returns: [{"id": "840531", "name": "1 DJ"}, ...]
        """
        if street_id in self._house_numbers_cache:
            return self._house_numbers_cache[street_id]
        
        try:
            print(f"Fetching house numbers for street ID {street_id}...")
            data = {
                "ulica": street_id,
                "token": self.token
            }
            
            response = requests.post(self.base_url, data=data, headers=self.headers)
            response.raise_for_status()
            
            house_numbers = response.json()
            # Filter out the "-Brak-" option
            house_numbers = [h for h in house_numbers if h.get('name', '').strip() != '-Brak-']
            
            self._house_numbers_cache[street_id] = house_numbers
            print(f"Loaded {len(house_numbers)} house numbers")
            return house_numbers
            
        except Exception as e:
            print(f"Error fetching house numbers: {e}")
            return []
    
    def _calculate_number_match_score(self, user_input: str, house_name: str) -> int:
        """
        Smart matching for house numbers (same logic as the scraper)
        Handles cases like "1" → "1 DJ" 
        """
        user_input = user_input.strip().upper()
        house_name = house_name.strip().upper()
        
        # Perfect exact match
        if user_input == house_name:
            return 100
        
        # Check if user input is at start of house name
        if house_name.startswith(user_input):
            remainder = house_name[len(user_input):].strip()
            
            # If followed immediately by single letter (like "3CA"), highest score
            if remainder and len(remainder) == 1 and remainder[0].isalpha():
                return 97
            # If followed by space and letters/words (like "3C DJ"), high score
            elif remainder.startswith(' ') and len(remainder) > 1 and remainder[1:].isalnum():
                return 95
            # If followed immediately by multiple letters (like "3CAB"), medium-high score
            elif remainder and remainder[0].isalpha():
                return 92
            # If followed by numbers (like "3C1"), lower score
            elif remainder and remainder[0].isdigit():
                return 80
            else:
                return 85
        
        # Check if user input is contained within house name
        if user_input in house_name:
            words = house_name.split()
            for word in words:
                if word.startswith(user_input):
                    return 75
            return 50
        
        return 0
    
    def find_house_number(self, street_id: str, number_input: str) -> Optional[Dict[str, str]]:
        """
        Find best matching house number using smart matching
        Args: street_id, number_input (e.g., "1")
        Returns: {"id": "840531", "name": "1 DJ"} or None
        """
        house_numbers = self.get_house_numbers(street_id)
        
        if not house_numbers:
            return None
        
        best_match = None
        best_score = 0
        
        for house in house_numbers:
            score = self._calculate_number_match_score(number_input, house['name'])
            
            if score > best_score:
                best_match = house
                best_score = score
                
                # Perfect match found
                if score >= 100:
                    break
        
        if best_match and best_score > 0:
            print(f"Found house number: '{number_input}' -> '{best_match['name']}' (score: {best_score})")
            return best_match
        
        print(f"No matching house number found for '{number_input}'")
        return None
    
    def get_schedule_image(self, street_id: str, house_id: str) -> Optional[bytes]:
        """
        Get the waste collection schedule as PNG image
        Args: street_id, house_id
        Returns: PNG image bytes or None
        """
        try:
            print(f"Fetching schedule image for street {street_id}, house {house_id}...")
            data = {
                "ulica": street_id,
                "numer": house_id,
                "token": self.token
            }
            
            response = requests.post(self.base_url, data=data, headers=self.headers)
            response.raise_for_status()
            
            result = response.json()
            
            if result.get('status') == 1 and 'img' in result:
                # Extract base64 image data
                base64_data = result['img']
                
                # Handle both formats: with or without space after comma
                if base64_data.startswith('data:image/png;base64,'):
                    base64_data = base64_data.replace('data:image/png;base64,', '')
                elif base64_data.startswith('data:image/png;base64, '):
                    base64_data = base64_data.replace('data:image/png;base64, ', '')
                
                # Decode image
                image_bytes = base64.b64decode(base64_data)
                print(f"Schedule image received: {len(image_bytes)} bytes")
                return image_bytes
            else:
                print("No valid schedule image in API response")
                return None
                
        except Exception as e:
            print(f"Error fetching schedule image: {e}")
            return None
    
    def get_schedule_for_address(self, street_name: str, house_number: str) -> Tuple[bool, Optional[str], Optional[bytes]]:
        """
        Main method: Get waste collection schedule for an address
        Args: street_name (e.g., "Krakowska"), house_number (e.g., "1")  
        Returns: (success, message, image_bytes)
        """
        try:
            print(f"Looking up schedule for: {street_name} {house_number}")
            
            # Step 1: Find the street
            street = self.find_street(street_name)
            if not street:
                return False, f"Street '{street_name}' not found", None
            
            print(f"Found street: {street['name']} (ID: {street['id']})")
            
            # Step 2: Find the house number
            house = self.find_house_number(street['id'], house_number)
            if not house:
                return False, f"House number '{house_number}' not found on {street['name']}", None
            
            print(f"Found house: {house['name']} (ID: {house['id']})")
            
            # Step 3: Get the schedule image
            image_bytes = self.get_schedule_image(street['id'], house['id'])
            if not image_bytes:
                return False, "Failed to retrieve schedule image", None
            
            success_message = f"Schedule retrieved for {street['name']} {house['name']}"
            return True, success_message, image_bytes
            
        except Exception as e:
            return False, f"Error: {e}", None
    
    def save_schedule_image(self, image_bytes: bytes, street_name: str, house_number: str) -> str:
        """
        Save schedule image to file
        Returns: file path
        """
        filename = f"schedule_{street_name.replace(' ', '_')}_{house_number.replace(' ', '_')}.png"
        
        with open(filename, 'wb') as f:
            f.write(image_bytes)
        
        print(f"Schedule saved to: {filename}")
        return filename


# Convenience functions for backward compatibility
async def download_waste_schedule(street: str, number: str) -> Tuple[bool, str]:
    """
    Compatibility function that works like the old scraper but uses direct API
    """
    client = KrakówWasteAPIClient()
    success, message, image_bytes = client.get_schedule_for_address(street, number)
    
    if success and image_bytes:
        # Save the image
        filename = client.save_schedule_image(image_bytes, street, number)
        return True, f"SUCCESS: {message}\nSaved to: {filename}"
    else:
        return False, f"FAILED: {message}"


async def get_waste_schedule(street: str, number: str) -> Tuple[bool, str]:
    """
    Compatibility function for simplified_gui that expects get_waste_schedule
    """
    client = KrakówWasteAPIClient()
    success, message, image_bytes = client.get_schedule_for_address(street, number)
    
    if success and image_bytes:
        # Save the image
        filename = client.save_schedule_image(image_bytes, street, number)
        
        # Format the response like the old scraper
        formatted_response = f"""Waste Collection Schedule
========================================

Schedule Image Retrieved Successfully!
Address: {street} {number}
Image saved to: {filename}
Image size: {len(image_bytes)} bytes

The schedule data is now available as a PNG image.
This is much faster than the old browser-based method!
        """
        return True, formatted_response
    else:
        return False, f"Failed to retrieve schedule: {message}"


# For direct testing
if __name__ == "__main__":
    def test_api_client():
        print("Testing Krakow Waste API Client...")
        
        client = KrakówWasteAPIClient()
        
        # Test the complete flow
        success, message, image_bytes = client.get_schedule_for_address("Krakowska", "1")
        
        if success and image_bytes:
            # Save the image
            filename = client.save_schedule_image(image_bytes, "Krakowska", "1")
            print(f"SUCCESS: {message}")
            print(f"Image saved to: {filename}")
            print(f"Image size: {len(image_bytes)} bytes")
        else:
            print(f"FAILED: {message}")
    
    test_api_client()