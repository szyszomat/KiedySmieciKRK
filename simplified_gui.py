"""
Simplified GUI that scrapes schedule directly from webpage
No PDF download or parsing needed
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import asyncio
from typing import Optional

try:
    from api_client import get_waste_schedule
    SCRAPER_AVAILABLE = True
    print("Using fast API client (20x faster than browser automation!)")
except ImportError:
    SCRAPER_AVAILABLE = False
    print("Error: API client not available")

try:
    from ocr_parser import WasteCollectionParser
    PARSER_AVAILABLE = True
    print("OCR parser available for data extraction")
except ImportError:
    PARSER_AVAILABLE = False
    print("Warning: OCR parser not available - install easyocr and Pillow")


class SimplifiedWasteGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Kiedy Śmieci Kraków - Direct Web Scraper")
        self.root.geometry("700x500")
        self.root.resizable(True, True)
        
        # Variables
        self.street_var = tk.StringVar(value="Krakowska")
        self.number_var = tk.StringVar(value="1")
        self.is_loading = False
        
        # Initialize parser if available
        if PARSER_AVAILABLE:
            self.parser = WasteCollectionParser()
        else:
            self.parser = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Create the user interface"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, 
                               text="Harmonogram Wywozu Śmieci - Kraków", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Input section
        input_frame = ttk.LabelFrame(main_frame, text="Adres", padding="15")
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Street input
        street_frame = ttk.Frame(input_frame)
        street_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(street_frame, text="Ulica (Street):").pack(anchor=tk.W)
        self.street_entry = ttk.Entry(street_frame, textvariable=self.street_var, 
                                     font=("Arial", 11))
        self.street_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Number input
        number_frame = ttk.Frame(input_frame)
        number_frame.pack(fill=tk.X, pady=(0, 15))
        
        ttk.Label(number_frame, text="Numer (House Number):").pack(anchor=tk.W)
        self.number_entry = ttk.Entry(number_frame, textvariable=self.number_var,
                                     font=("Arial", 11))
        self.number_entry.pack(fill=tk.X, pady=(5, 0))
        
        # Get schedule button
        self.get_schedule_btn = ttk.Button(input_frame, 
                                          text="Pobierz Harmonogram", 
                                          command=self.on_get_schedule_click)
        self.get_schedule_btn.pack(pady=(10, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(main_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=(0, 10))
        
        # Status label
        self.status_label = ttk.Label(main_frame, 
                                     text="Wprowadź adres i kliknij 'Pobierz Harmonogram'", 
                                     foreground="gray")
        self.status_label.pack(pady=(0, 15))
        
        # Results section
        results_frame = ttk.LabelFrame(main_frame, text="Harmonogram Odbioru", padding="15")
        results_frame.pack(fill=tk.BOTH, expand=True)
        
        # Schedule display
        self.schedule_text = scrolledtext.ScrolledText(results_frame, 
                                                      wrap=tk.WORD,
                                                      font=("Consolas", 10),
                                                      height=15,
                                                      state=tk.DISABLED)
        self.schedule_text.pack(fill=tk.BOTH, expand=True)
        
        # Instructions
        instructions = ttk.Label(main_frame, 
                               text="Przykład: Ulica: 'Krakowska', Numer: '1'\n" +
                               "Dane pobierane bezpośrednio ze strony MPO Kraków",
                               font=("Arial", 9),
                               foreground="gray",
                               justify=tk.CENTER)
        instructions.pack(pady=(10, 0))
        
        # Bind Enter key
        self.root.bind('<Return>', lambda e: self.on_get_schedule_click())
        
        # Check if scraper is available
        if not SCRAPER_AVAILABLE:
            self.status_label.configure(
                text="Web scraper niedostępny - sprawdź instalację Playwright", 
                foreground="red"
            )
            self.get_schedule_btn.configure(state='disabled')
        
        # Focus on street entry
        self.street_entry.focus()
    
    def validate_input(self) -> bool:
        """Validate user input"""
        street = self.street_var.get().strip()
        number = self.number_var.get().strip()
        
        if not street:
            messagebox.showerror("Błąd", "Proszę wprowadzić nazwę ulicy")
            self.street_entry.focus()
            return False
            
        if not number:
            messagebox.showerror("Błąd", "Proszę wprowadzić numer domu")
            self.number_entry.focus()
            return False
            
        return True
    
    def set_loading_state(self, is_loading: bool, message: str = ""):
        """Update UI state during operations"""
        self.is_loading = is_loading
        
        if is_loading:
            self.get_schedule_btn.configure(state='disabled', text="Pobieranie...")
            self.progress.start(10)
            self.status_label.configure(text=message or "Pobieranie harmonogramu...", 
                                      foreground="blue")
        else:
            self.get_schedule_btn.configure(state='normal', text="Pobierz Harmonogram")
            self.progress.stop()
    
    def update_schedule_display(self, schedule_text: str):
        """Update the schedule display"""
        self.schedule_text.configure(state=tk.NORMAL)
        self.schedule_text.delete(1.0, tk.END)
        self.schedule_text.insert(1.0, schedule_text)
        self.schedule_text.configure(state=tk.DISABLED)
    
    def on_get_schedule_click(self):
        """Handle get schedule button click"""
        if self.is_loading or not SCRAPER_AVAILABLE:
            return
            
        if not self.validate_input():
            return
        
        street = self.street_var.get().strip()
        number = self.number_var.get().strip()
        
        # Run in background thread
        thread = threading.Thread(target=self.get_schedule_in_background, 
                                 args=(street, number))
        thread.daemon = True
        thread.start()
    
    def get_schedule_in_background(self, street: str, number: str):
        """Get schedule in background thread"""
        self.root.after(0, lambda: self.set_loading_state(True, 
                                   f"Pobieranie harmonogramu dla {street} {number}..."))
        
        try:
            # Run async function in new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            success, result = loop.run_until_complete(
                get_waste_schedule(street, number)
            )
            
            loop.close()
            
            # Update UI on main thread
            self.root.after(0, lambda: self.schedule_complete(success, result))
            
        except Exception as e:
            self.root.after(0, lambda: self.schedule_complete(False, f"Błąd: {e}"))
    
    def schedule_complete(self, success: bool, result: str):
        """Handle schedule retrieval completion"""
        self.set_loading_state(False)
        
        if success:
            self.status_label.configure(text="Harmonogram pobrany pomyślnie!", 
                                      foreground="green")
            
            # Try to extract structured data from the saved PNG
            if self.parser and ("Saved to: " in result or "Image saved to: " in result):
                self.extract_and_display_data(result)
            else:
                self.update_schedule_display(result)
        else:
            self.status_label.configure(text="Błąd podczas pobierania harmonogramu", 
                                      foreground="red")
            error_message = f"Błąd pobierania harmonogramu:\n{result}\n\n"
            error_message += "Sprawdź czy:\n"
            error_message += "• Nazwa ulicy jest poprawna\n"
            error_message += "• Numer domu istnieje\n"
            error_message += "• Połączenie internetowe działa"
            
            self.update_schedule_display(error_message)
            messagebox.showerror("Błąd", result)
    
    def extract_and_display_data(self, result: str):
        """Extract structured data from saved PNG image"""
        try:
            # Parse the result to find the saved PNG file path
            lines = result.split('\n')
            png_path = None
            
            for line in lines:
                if "Saved to: " in line:
                    png_path = line.split("Saved to: ")[1].strip()
                    break
                elif "Image saved to: " in line:
                    png_path = line.split("Image saved to: ")[1].strip()
                    break
            
            if not png_path:
                self.update_schedule_display(result + "\n\nWarning: Could not find saved image path for OCR processing")
                return
            
            print(f"Extracting data from: {png_path}")
            
            # Parse the image using OCR (additional safety check)
            if not self.parser:
                self.update_schedule_display(result + "\n\nWarning: OCR parser not available")
                return

            schedule_info = self.parser.parse_schedule_file(png_path)

            if 'error' in schedule_info:
                display_text = result + f"\n\nWarning OCR Error: {schedule_info['error']}"
                print(f"OCR Error: {schedule_info['error']}")
            else:
                # Format the extracted data (additional safety check)
                if not self.parser:
                    display_text = result + "\n\nWarning: OCR parser not available for formatting"
                    print("OCR parser became unavailable during formatting")
                else:
                    formatted_data = self.parser.format_schedule_for_display(schedule_info)
                display_text = f"EXTRACTED SCHEDULE DATA:\n{'-'*50}\n{formatted_data}\n\n"
                display_text += f"Original API Response:\n{'-'*30}\n{result}"
                
                # Print to terminal as well
                print("\n" + "="*60)
                print("EXTRACTED SCHEDULE DATA:")
                print("="*60)
                print(formatted_data)
                print("="*60)
            
            self.update_schedule_display(display_text)
            
        except Exception as e:
            error_text = result + f"\n\nError: Data extraction failed: {e}"
            print(f"Data extraction error: {e}")
            self.update_schedule_display(error_text)
    
    def run(self):
        """Start the GUI application"""
        self.root.mainloop()


def main():
    """Main function to run the simplified application"""
    app = SimplifiedWasteGUI()
    app.run()


if __name__ == "__main__":
    main()