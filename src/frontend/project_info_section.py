# Standard Library 
import os
import re
import csv
import logging
from pathlib import Path
from typing import List, Dict, Optional
import sys

# Third-Party Library 
import mysql.connector
import openpyxl
from openpyxl.utils import get_column_letter

# Local Module 
from frontend.form_section import FormSection, FormField
from frontend.database_operations import DatabaseOperations
class ProjectInfoSection(FormSection):
    """Manages project information form fields and validation for construction projects."""
    UNIT_FORCE = "kN"
    UNIT_LENGTH = "m"
    UNIT_TIME = "s"
    ELEMENT_TYPE = "Plane Strain"
    
    BOREHOLE_OPTIONS = ["Manual", "Ags file"]
    DESIGN_APPROACH_OPTIONS = ["SLS", "DA1-C1", "DA1-C2"]
    ELEMENT_OPTIONS =["6-Node","15-Node"]
    MODEL_OPTIONS=["Plane Strain","Axisymmetry"]
    CSV_FILENAME = "project_data.csv"

    # Validation constants
    MAX_TITLE_LENGTH = 100
    MAX_SECTION_LENGTH = 50
    MAX_BOREHOLE_LENGTH = 50
    TITLE_PATTERN = r'^[a-zA-Z0-9_-]+$'
    SECTION_PATTERN = r'^[A-Z0-9]+$'

    def __init__(self, db_ops: DatabaseOperations):
        """Initialize ProjectInfoSection with a logger."""
        self.db_ops = db_ops

        self.logger = logging.getLogger(__name__)
    def import_from_dict(self, data):
      for field in self.get_fields():
        if field.label in data:
            field.control.value = data[field.label]   
    
    def get_fields(self) -> List[FormField]:
      """Returns list of form fields for project information."""

      return [
        FormField("Project Title", "text", "e.g: Project_01", required=True),
        FormField("Section", "text", "e.g: A", required=True),
        FormField("Unit Force", "constant", value=self.UNIT_FORCE),
        FormField("Unit Length", "constant", value=self.UNIT_LENGTH),
        FormField("Unit Time", "constant", value=self.UNIT_TIME),
        FormField("Model Type", "dropdown", options=self.MODEL_OPTIONS, value="Plane Strain"),
        FormField("Element Type", "dropdown", options=self.ELEMENT_OPTIONS, value="15-Node"),
        FormField("Borehole Type", "dropdown", options=self.BOREHOLE_OPTIONS, required=True),
        FormField("Borehole", "text", "e.g: BH_01", required=True),
        FormField("Design Approach", "dropdown", options=self.DESIGN_APPROACH_OPTIONS, required=True)
    ]
    def validate_project_title(self, title: str) -> List[str]:
        """Validate project title with specific rules."""
        errors = []
        if not title:
            errors.append("Project Title is required")
        elif len(title) > self.MAX_TITLE_LENGTH:
            errors.append(f"Project Title must be less than {self.MAX_TITLE_LENGTH} characters")
        elif not re.match(self.TITLE_PATTERN, title):
            errors.append("Project Title can only contain letters, numbers, underscores, and hyphens")
        return errors

    def validate_section(self, section: str) -> List[str]:
        """Validate section with specific rules."""
        errors = []
        if section:  # Section is optional, but if provided must meet criteria
            if len(section) > self.MAX_SECTION_LENGTH:
                errors.append(f"Section must be less than {self.MAX_SECTION_LENGTH} characters")
        return errors

    def validate_borehole(self, borehole_type: str, borehole: str) -> List[str]:
        """Validate borehole information."""
        errors = []
        if borehole_type:
            if borehole_type not in self.BOREHOLE_OPTIONS:
                errors.append("Invalid Borehole Type selected")
            
            # If borehole type is selected, borehole ID is required
            if not borehole:
                errors.append("Borehole ID is required when Borehole Type is selected")
            # Pattern validation removed - accepting any user input for borehole
            elif len(borehole) > self.MAX_BOREHOLE_LENGTH:
                errors.append(f"Borehole ID must be less than {self.MAX_BOREHOLE_LENGTH} characters")
        return errors

    def validate_constant_fields(self, data: Dict) -> List[str]:
        """Validate that constant fields haven't been modified."""
        errors = []
        if data.get("Unit Force") != self.UNIT_FORCE:
            errors.append("Unit Force cannot be modified")
        if data.get("Unit Length") != self.UNIT_LENGTH:
            errors.append("Unit Length cannot be modified")
        if data.get("Unit Time") != self.UNIT_TIME:
            errors.append("Unit Time cannot be modified")
        return errors

    def validate(self, data: Dict) -> List[str]:
        """Comprehensive validation of all fields."""
        errors = []
        
        # Validate project title
        errors.extend(self.validate_project_title(data.get("Project Title", "")))
        
        # Validate section if provided
        errors.extend(self.validate_section(data.get("Section", "")))
        
        # Validate borehole information
        errors.extend(self.validate_borehole(
            data.get("Borehole Type"),
            data.get("Borehole")
        ))
        
        
        
        # Validate design approach
        if data.get("Design Approach"):
            if data["Design Approach"] not in self.DESIGN_APPROACH_OPTIONS:
                errors.append("Invalid Design Approach selected")

        return errors

    def read_from_csv(self, csv_file_path: str) -> Optional[Dict]:
        """
        Read project information from a CSV file.
        The CSV file must have headers matching the form field names.
        """
        try:
            with open(csv_file_path, mode='r') as file:
                reader = csv.DictReader(file)
                data = next(reader)  # Assumes only one row of data
                
                # Ensure all required fields are present
                required_fields = {
                    "Project Title",
                    "Section",
                    "Model Type",
                    "Element Type",
                    "Borehole Type",
                    "Borehole",
                    "Design Approach"
                }
                
                missing_fields = required_fields - set(data.keys())
                if missing_fields:
                    raise ValueError(f"Missing required fields in CSV: {', '.join(missing_fields)}")
                
                return data
                
        except StopIteration:
            raise ValueError("CSV file is empty")
        except Exception as e:
            self.logger.error(f"Error reading CSV file: {str(e)}")
            raise ValueError(f"Error reading CSV file: {str(e)}")

    # New method to import data from a CSV file
    def import_from_csv(self, csv_file_path: str, cursor) -> None:
        """
        Import project information from a CSV file and save it to the database.
        """
        try:
            # Step 1: Read data from the CSV file
            data = self.read_from_csv(csv_file_path)
            if not data:
                raise ValueError("No data found in CSV file or file is improperly formatted.")

            # Step 2: Validate the data
            validation_errors = self.validate(data)
            if validation_errors:
                error_msg = "; ".join(validation_errors)
                raise ValueError(f"Validation errors in CSV data: {error_msg}")

            

        except Exception as e:
            error_msg = f"Error importing CSV data: {str(e)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
 
    def save(self, cursor, data: Dict) -> int:
      """Save project information using DatabaseOperations."""
      # Ensure constants are in the data dictionary
      data["Unit Force"] = self.UNIT_FORCE
      data["Unit Length"] = self.UNIT_LENGTH
      data["Unit Time"] = self.UNIT_TIME
    
      common_id = data.get('common_id')
      inserted_id = self.db_ops.save_project_info(cursor, data, common_id)
    
    # Save to files
      # Get the base directory of the script
      # Check if running as executable
      if getattr(sys, 'frozen', False):
          # Running as exe - use internal/data directory
          BASE_DIR = Path(sys.executable).parent / "_internal"
      else:
          # Running as script - use original path
          BASE_DIR = Path(__file__).resolve().parent.parent.parent

      # Define the export directory relative to the project root
      export_dir = BASE_DIR / "data"
      self.db_ops.save_to_csv([data], export_dir/"project_data.csv", data.keys())
      self.db_ops.update_excel(export_dir/"Input_Data.xlsx", "Project Info", [data])
    
      return inserted_id