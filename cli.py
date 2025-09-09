"""
Command Line Interface for Krakow Waste Collection Schedule
Provides terminal-based access to waste schedule functionality
"""

import sys
import asyncio
import json
from typing import Optional, Tuple
from datetime import datetime

try:
    from api_client import KrakówWasteAPIClient
    API_AVAILABLE = True
except ImportError:
    API_AVAILABLE = False
    print("Error: API client not available")

try:
    from ocr_parser import WasteCollectionParser
    PARSER_AVAILABLE = True
except ImportError:
    PARSER_AVAILABLE = False
    print("Warning: OCR parser not available - install easyocr and Pillow")


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    @classmethod
    def disable(cls):
        """Disable colors for non-interactive terminals"""
        cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = ''
        cls.MAGENTA = cls.CYAN = cls.WHITE = cls.BOLD = ''
        cls.UNDERLINE = cls.END = ''


class WasteCLI:
    """Command Line Interface for waste collection schedule"""
    
    def __init__(self, quiet: bool = False, json_output: bool = False, no_color: bool = False):
        self.quiet = quiet
        self.json_output = json_output
        
        if no_color or not sys.stdout.isatty():
            Colors.disable()
            
        self.client = KrakówWasteAPIClient() if API_AVAILABLE else None
        self.parser = WasteCollectionParser() if PARSER_AVAILABLE else None
        
    def print_info(self, message: str):
        """Print info message (unless quiet mode)"""
        if not self.quiet and not self.json_output:
            print(f"{Colors.BLUE}ℹ{Colors.END} {message}")
    
    def print_success(self, message: str):
        """Print success message (unless quiet mode)"""
        if not self.quiet and not self.json_output:
            print(f"{Colors.GREEN}✓{Colors.END} {message}")
    
    def print_error(self, message: str):
        """Print error message"""
        if not self.json_output:
            print(f"{Colors.RED}✗{Colors.END} {message}", file=sys.stderr)
    
    def print_warning(self, message: str):
        """Print warning message (unless quiet mode)"""
        if not self.quiet and not self.json_output:
            print(f"{Colors.YELLOW}⚠{Colors.END} {message}")
    
    def print_header(self, title: str):
        """Print formatted header"""
        if not self.quiet and not self.json_output:
            print(f"\n{Colors.BOLD}{Colors.CYAN}{title}{Colors.END}")
            print(f"{Colors.CYAN}{'=' * len(title)}{Colors.END}")
    
    def get_user_input(self, prompt: str, default: str = "") -> str:
        """Get user input with optional default"""
        try:
            if default:
                full_prompt = f"{prompt} [{default}]: "
            else:
                full_prompt = f"{prompt}: "
            
            result = input(full_prompt).strip()
            return result if result else default
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Colors.YELLOW}Operation cancelled by user{Colors.END}")
            sys.exit(0)
    
    def validate_input(self, street: str, number: str) -> bool:
        """Validate user input"""
        if not street.strip():
            self.print_error("Street name cannot be empty")
            return False
            
        if not number.strip():
            self.print_error("House number cannot be empty")
            return False
            
        return True
    
    def interactive_mode(self) -> Tuple[str, str]:
        """Interactive mode - prompt user for input"""
        self.print_header("Krakow Waste Collection Schedule - Interactive Mode")
        
        print(f"{Colors.WHITE}Enter your address details:{Colors.END}")
        street = self.get_user_input("Street name (ulica)", "Krakowska")
        number = self.get_user_input("House number (numer)", "1")
        
        return street.strip(), number.strip()
    
    def format_schedule_output(self, success: bool, message: str, image_path: Optional[str] = None, 
                             parsed_data: Optional[dict] = None) -> dict:
        """Format output for display or JSON"""
        result = {
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        if image_path:
            result['image_path'] = image_path
            
        if parsed_data and 'error' not in parsed_data:
            result['schedule'] = {
                'address': f"{parsed_data.get('address', 'Unknown')} {parsed_data.get('house_number', 'Unknown')}",
                'total_collections': parsed_data.get('total_collections', 0),
                'waste_types': [wt.get('polish', '') for wt in parsed_data.get('waste_types', [])],
                'collections': []
            }
            
            # Format categorized schedule
            if parsed_data.get('categorized_schedule'):
                all_collections = []
                for waste_type, dates in parsed_data['categorized_schedule'].items():
                    for date_info in dates:
                        all_collections.append({
                            'date': date_info['date'],
                            'formatted_date': date_info['formatted'],
                            'weekday': date_info['weekday'],
                            'waste_type': waste_type
                        })
                
                # Sort by date
                all_collections.sort(key=lambda x: x['date'])
                result['schedule']['collections'] = all_collections
        
        return result
    
    def display_schedule_result(self, result: dict):
        """Display schedule result in terminal format"""
        if self.json_output:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return
        
        if not result['success']:
            self.print_error(f"Failed to retrieve schedule: {result['message']}")
            return
        
        self.print_success("Schedule retrieved successfully!")
        
        if 'schedule' in result:
            schedule = result['schedule']
            
            self.print_header(f"Schedule for {schedule['address']}")
            
            if schedule.get('waste_types'):
                print(f"{Colors.WHITE}Waste types found:{Colors.END}")
                for waste_type in schedule['waste_types']:
                    print(f"  • {waste_type}")
                print()
            
            if schedule.get('collections'):
                print(f"{Colors.WHITE}Collection Dates:{Colors.END}")
                print(f"{Colors.WHITE}Total: {schedule['total_collections']} collections{Colors.END}\n")
                
                for collection in schedule['collections']:
                    waste_color = Colors.GREEN if 'Bio' in collection['waste_type'] or 'Garden' in collection['waste_type'] else Colors.BLUE
                    print(f"  {Colors.CYAN}{collection['formatted_date']}{Colors.END} "
                          f"({collection['weekday']}) - "
                          f"{waste_color}{collection['waste_type']}{Colors.END}")
            else:
                print(f"{Colors.YELLOW}No detailed schedule information extracted{Colors.END}")
        
        if result.get('image_path'):
            print(f"\n{Colors.WHITE}Schedule image saved to: {Colors.UNDERLINE}{result['image_path']}{Colors.END}")
    
    async def get_schedule(self, street: str, number: str) -> dict:
        """Get waste collection schedule"""
        if not API_AVAILABLE:
            return self.format_schedule_output(False, "API client not available")
        
        self.print_info(f"Looking up schedule for: {street} {number}")
        
        try:
            # Get schedule from API
            success, message, image_bytes = self.client.get_schedule_for_address(street, number)
            
            if not success or not image_bytes:
                return self.format_schedule_output(False, message)
            
            # Save image
            image_path = self.client.save_schedule_image(image_bytes, street, number)
            self.print_success(f"Schedule image saved: {image_path}")
            
            # Parse image if OCR is available
            parsed_data = None
            if self.parser:
                self.print_info("Extracting schedule data using OCR...")
                parsed_data = self.parser.parse_schedule_file(image_path)
                
                if 'error' in parsed_data:
                    self.print_warning(f"OCR parsing failed: {parsed_data['error']}")
                    parsed_data = None
                else:
                    self.print_success("Schedule data extracted successfully")
            
            return self.format_schedule_output(True, message, image_path, parsed_data)
            
        except Exception as e:
            return self.format_schedule_output(False, f"Error: {str(e)}")
    
    async def run(self, street: Optional[str] = None, number: Optional[str] = None) -> int:
        """Main CLI execution"""
        try:
            # Check if API is available
            if not API_AVAILABLE:
                self.print_error("API client not available. Please check installation.")
                return 1
            
            # Get input parameters
            if street and number:
                # Direct mode - use provided arguments
                if not self.validate_input(street, number):
                    return 1
            else:
                # Interactive mode - prompt user
                street, number = self.interactive_mode()
                if not self.validate_input(street, number):
                    return 1
            
            # Get and display schedule
            result = await self.get_schedule(street, number)
            self.display_schedule_result(result)
            
            return 0 if result['success'] else 1
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Operation cancelled by user{Colors.END}")
            return 130  # Standard exit code for SIGINT
        except Exception as e:
            self.print_error(f"Unexpected error: {str(e)}")
            return 1


def print_help():
    """Print CLI help information"""
    help_text = f"""
{Colors.BOLD}{Colors.CYAN}Krakow Waste Collection Schedule - CLI{Colors.END}

{Colors.BOLD}USAGE:{Colors.END}
    python main.py --cli                    # Interactive mode
    python main.py --cli --street "Krakowska" --number "1"  # Direct mode
    
{Colors.BOLD}OPTIONS:{Colors.END}
    --cli                   Run in command-line mode instead of GUI
    --gui                   Run in GUI mode (default)
    --street <name>         Street name (e.g., "Krakowska")
    --number <num>          House number (e.g., "1", "3c")
    --json                  Output results in JSON format
    --quiet                 Suppress non-essential output
    --no-color              Disable colored output
    --help                  Show this help message

{Colors.BOLD}EXAMPLES:{Colors.END}
    python main.py --cli
    python main.py --cli --street "Krakowska" --number "1"
    python main.py --cli --street "Aleja Pokoju" --number "5" --json
    python main.py --cli --street "Krakowska" --number "1" --quiet --no-color

{Colors.BOLD}FEATURES:{Colors.END}
    • Direct API access to Krakow waste collection data
    • OCR parsing of schedule images for structured data
    • Colored terminal output with progress indicators
    • JSON output for scripting and automation
    • Interactive and direct command-line modes
    • Compatible with existing GUI functionality
"""
    print(help_text)


async def run_cli(street: Optional[str] = None, number: Optional[str] = None, 
                  quiet: bool = False, json_output: bool = False, no_color: bool = False) -> int:
    """Main CLI entry point"""
    cli = WasteCLI(quiet=quiet, json_output=json_output, no_color=no_color)
    return await cli.run(street, number)


if __name__ == "__main__":
    # Direct CLI testing
    import argparse
    
    parser = argparse.ArgumentParser(description="Krakow Waste Collection Schedule CLI")
    parser.add_argument('--street', help='Street name')
    parser.add_argument('--number', help='House number') 
    parser.add_argument('--json', action='store_true', help='JSON output')
    parser.add_argument('--quiet', action='store_true', help='Quiet mode')
    parser.add_argument('--no-color', action='store_true', help='Disable colors')
    
    args = parser.parse_args()
    
    exit_code = asyncio.run(run_cli(
        street=args.street,
        number=args.number,
        quiet=args.quiet,
        json_output=args.json,
        no_color=args.no_color
    ))
    
    sys.exit(exit_code)