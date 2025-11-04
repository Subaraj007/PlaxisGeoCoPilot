from typing import Callable, Union, Optional, List, Dict, Tuple
from frontend.database_config import DatabaseConfig

class FormManager:
    """Manages form data storage and submission across multiple sections"""
    def __init__(self, db_config: DatabaseConfig):
        self.db_config = db_config
        self.stored_data = {
            'project_info': None,
            'geometry': None,
            'borehole': None,
            'excavation': None,
            'sequence_construct': None
        }
    
    def store_section_data(self, section_name: str, data: Dict) -> None:
        """Store form data for a section temporarily"""
        # Normalize section name
        section_name = section_name.lower().replace(" ", "_")
        print(f"DEBUG: Storing data for section {section_name}: {data}")
        
        if section_name in self.stored_data:
            self.stored_data[section_name] = data
            print(f"DEBUG: After storing, stored_data is: {self.stored_data}")
        else:
            print(f"DEBUG: Warning - Attempted to store data for unknown section: {section_name}")
    
    def get_section_data(self, section_name: str) -> Dict:
        """Retrieve stored data for a section"""
        # Normalize section name
        section_name = section_name.lower().replace(" ", "_")
        print(f"DEBUG: Retrieving data for section {section_name}")
        print(f"DEBUG: Current stored data: {self.stored_data}")
        
        data = self.stored_data.get(section_name)
        print(f"DEBUG: Retrieved data: {data}")
        return data
    
    def clear_section_data(self, section_name: str) -> None:
        """Clear stored data for a specific section"""
        # Normalize section name
        section_name = section_name.lower().replace(" ", "_")
        
        if section_name in self.stored_data:
            self.stored_data[section_name] = None
            print(f"DEBUG: Cleared data for section {section_name}")
        else:
            print(f"DEBUG: Warning - Attempted to clear data for unknown section: {section_name}")
    
    def clear_all_data(self) -> None:
        """Clear all stored form data"""
        for key in self.stored_data:
            self.stored_data[key] = None
        print("DEBUG: Cleared all stored data")
            
    def all_sections_filled(self) -> bool:
        """Check if all sections have data stored"""
        filled = all(data is not None for data in self.stored_data.values())
        print(f"DEBUG: All sections filled: {filled}")
        return filled