#!/usr/bin/env python3
"""
Krakow Waste Collection Schedule Downloader
Main entry point for the application

Usage: 
    python main.py              # GUI mode (default)
    python main.py --gui        # GUI mode (explicit)
    python main.py --cli        # CLI mode (interactive)
    python main.py --cli --street "Krakowska" --number "1"  # CLI mode (direct)
"""

import sys
import os
import traceback
import argparse
import asyncio
try:
    from simplified_gui import SimplifiedWasteGUI as WasteScheduleGUI
    print("Using fast API-based GUI")
except ImportError:
    print("Error: simplified_gui.py not found")
    print("Make sure all required files are present")
    sys.exit(1)


def check_dependencies():
    """Check if all required dependencies are installed"""
    missing = []
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    # Check OCR dependencies (optional but recommended)
    try:
        import easyocr
        import PIL
        print("OK: OCR dependencies found - EasyOCR ready for data extraction")
    except ImportError:
        print("Warning: OCR dependencies not found")
        print("   For data extraction from images, install:")
        print("   pip install easyocr Pillow")
        print("   Or with pip: pip install easyocr Pillow")
    
    try:
        from dateutil import parser
    except ImportError:
        missing.append("python-dateutil")
    
    if missing:
        print(f"❌ Missing required dependencies: {', '.join(missing)}")
        print("\nPlease install:")
        print("pip install -r requirements.txt")
        return False
    
    return True


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Krakow Waste Collection Schedule Downloader",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                                    # GUI mode (default)
  python main.py --gui                             # GUI mode (explicit)
  python main.py --cli                             # CLI interactive mode
  python main.py --cli --street "Krakowska" --number "1"  # CLI direct mode
  python main.py --cli --street "Krakowska" --number "1" --json  # JSON output
        """
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--gui', action='store_true', 
                           help='Run in GUI mode (default)')
    mode_group.add_argument('--cli', action='store_true',
                           help='Run in command-line interface mode')
    
    # CLI-specific options
    parser.add_argument('--street', metavar='NAME',
                       help='Street name (for CLI mode)')
    parser.add_argument('--number', metavar='NUM', 
                       help='House number (for CLI mode)')
    parser.add_argument('--json', action='store_true',
                       help='Output results in JSON format (CLI mode only)')
    parser.add_argument('--quiet', action='store_true',
                       help='Suppress non-essential output (CLI mode only)')
    parser.add_argument('--no-color', action='store_true',
                       help='Disable colored output (CLI mode only)')
    
    return parser.parse_args()


async def run_cli_mode(args):
    """Run the application in CLI mode"""
    try:
        from cli import run_cli
    except ImportError:
        print("Error: CLI module not available")
        print("Make sure cli.py is present in the application directory")
        return 1
    
    return await run_cli(
        street=args.street,
        number=args.number,
        quiet=args.quiet,
        json_output=args.json,
        no_color=args.no_color
    )


def run_gui_mode():
    """Run the application in GUI mode"""
    try:
        # Create and run the GUI application
        app = WasteScheduleGUI()
        print("Starting GUI application...")
        app.run()
        return 0
        
    except KeyboardInterrupt:
        print("\nGUI application interrupted by user")
        return 0
        
    except Exception as e:
        print(f"\nUnexpected error in GUI mode: {e}")
        print("\nFull traceback:")
        traceback.print_exc()
        
        # Show error dialog if possible
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Critical Error", 
                               f"Application crashed:\n{e}\n\nCheck console for details.")
        except:
            pass
        
        return 1


def main():
    """Main entry point with CLI/GUI mode selection"""
    # Parse command line arguments
    args = parse_arguments()
    
    print("Kiedy Smieci Krakow - Waste Collection Schedule Downloader")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Determine mode
    if args.cli:
        print("Starting in CLI mode...")
        try:
            exit_code = asyncio.run(run_cli_mode(args))
            sys.exit(exit_code)
        except KeyboardInterrupt:
            print("\nCLI application interrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"\nUnexpected error in CLI mode: {e}")
            traceback.print_exc()
            sys.exit(1)
    else:
        # Default to GUI mode
        print("Starting in GUI mode...")
        exit_code = run_gui_mode()
        sys.exit(exit_code)


if __name__ == "__main__":
    main()