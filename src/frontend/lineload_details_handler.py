"""
line_load.py - Handles line load data operations for geometry section
Modified to use user-entered distances, lengths, and magnitudes
Fixed to use separate wall coordinates for double wall excavations
"""

import csv
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import openpyxl
import flet as ft
from frontend.form_section import FormField


class LineLoadHandler:
    """Handles creation, UI, and saving of line load data for excavation analysis."""
    
    def __init__(self, geometry_section):
        """
        Initialize LineLoadHandler with reference to geometry section.
        
        Args:
            geometry_section: Reference to GeometrySection instance
        """
        self.geometry_section = geometry_section
        self.export_dir = geometry_section.export_dir
    
    def get_line_load_fields(self) -> List[FormField]:
        """Get line load fields based on excavation type"""
        excavation_type = self.geometry_section.form_values.get("Excavation Type", "Single wall")
        
        if excavation_type == "Single wall":
            return [
                FormField("Distance from the wall", "number", "e.g: 5",
                         value=self.geometry_section.form_values.get("Distance from the wall")),
                FormField("Length of the load", "number", "e.g: 10",
                         value=self.geometry_section.form_values.get("Length of the load")),
                FormField("Magnitude of the load", "number", "e.g: 100",
                         value=self.geometry_section.form_values.get("Magnitude of the load"))
            ]
        elif excavation_type == "Double wall":
            return [
                # Left Side fields
                FormField("Distance from the left wall", "number", "e.g: 5",
                         value=self.geometry_section.form_values.get("Distance from the left wall")),
                FormField("Length of the left load", "number", "e.g: 10",
                         value=self.geometry_section.form_values.get("Length of the left load")),
                FormField("Magnitude of the left load", "number", "e.g: 100",
                         value=self.geometry_section.form_values.get("Magnitude of the left load")),
                # Right Side fields
                FormField("Distance from the Right wall", "number", "e.g: 5",
                         value=self.geometry_section.form_values.get("Distance from the Right wall")),
                FormField("Length of the Right load", "number", "e.g: 10",
                         value=self.geometry_section.form_values.get("Length of the Right load")),
                FormField("Magnitude of the Right load", "number", "e.g: 100",
                         value=self.geometry_section.form_values.get("Magnitude of the Right load"))
            ]
        else:
            return []
    
    def create_line_load_controls(self, stored_data: Dict = None) -> ft.Column:
        """Create line load controls with proper section headers for double wall"""
        # Use stored_data if provided, otherwise use form_values
        data_source = stored_data if stored_data else self.geometry_section.form_values
        excavation_type = data_source.get("Excavation Type", "Single wall")
        
        # Update form_values with stored data for line load fields
        if stored_data:
            line_load_fields = [
                "Distance from the wall", "Length of the load", "Magnitude of the load",
                "Distance from the left wall", "Length of the left load", "Magnitude of the left load",
                "Distance from the Right wall", "Length of the Right load", "Magnitude of the Right load"
            ]
            for field in line_load_fields:
                if field in stored_data:
                    self.geometry_section.form_values[field] = stored_data[field]
                    print(f"DEBUG: Restored line load field '{field}' = {stored_data[field]}")
        
        fields = self.get_line_load_fields()
        
        if not fields:
            return ft.Column([ft.Text("Please select an excavation type first", size=14)])
        
        controls = []
        
        if excavation_type == "Single wall":
            # Simple 3-field layout for single wall
            form_rows = []
            for i in range(0, len(fields), 3):
                row_fields = []
                for j in range(3):
                    if i + j < len(fields):
                        field = fields[i + j]
                        control = field.create_control(
                            width=280,
                            on_change=self.geometry_section.handle_field_change
                        )
                        # Explicitly set the value from data source
                        if field.label in data_source:
                            control.value = data_source[field.label]
                            print(f"DEBUG: Set control value for '{field.label}' = {control.value}")
                        row_fields.append(control)
                
                form_rows.append(
                    ft.Row(
                        row_fields,
                        alignment=ft.MainAxisAlignment.START,
                        spacing=20
                    )
                )
            controls = form_rows
            
        elif excavation_type == "Double wall":
            # Separate sections for left and right with headers
            controls.append(
                ft.Text("Left Side", size=16, weight=ft.FontWeight.BOLD, 
                       color=ft.colors.BLUE_700)
            )
            
            # Left side fields (first 3)
            left_fields = fields[:3]
            for i in range(0, len(left_fields), 3):
                row_fields = []
                for j in range(3):
                    if i + j < len(left_fields):
                        field = left_fields[i + j]
                        control = field.create_control(
                            width=280,
                            on_change=self.geometry_section.handle_field_change
                        )
                        # Explicitly set the value from data source
                        if field.label in data_source:
                            control.value = data_source[field.label]
                            print(f"DEBUG: Set control value for '{field.label}' = {control.value}")
                        row_fields.append(control)
                
                controls.append(
                    ft.Row(
                        row_fields,
                        alignment=ft.MainAxisAlignment.START,
                        spacing=20
                    )
                )
            
            # Spacer between sections
            controls.append(ft.Container(height=20))
            
            # Right side header
            controls.append(
                ft.Text("Right Side", size=16, weight=ft.FontWeight.BOLD,
                       color=ft.colors.BLUE_700)
            )
            
            # Right side fields (last 3)
            right_fields = fields[3:]
            for i in range(0, len(right_fields), 3):
                row_fields = []
                for j in range(3):
                    if i + j < len(right_fields):
                        field = right_fields[i + j]
                        control = field.create_control(
                            width=280,
                            on_change=self.geometry_section.handle_field_change
                        )
                        # Explicitly set the value from data source
                        if field.label in data_source:
                            control.value = data_source[field.label]
                            print(f"DEBUG: Set control value for '{field.label}' = {control.value}")
                        row_fields.append(control)
                
                controls.append(
                    ft.Row(
                        row_fields,
                        alignment=ft.MainAxisAlignment.START,
                        spacing=20
                    )
                )
        
        return ft.Column(controls, spacing=15)
    
    def update_line_load_frame(self):
        """Update the Line Load Details frame when excavation type changes"""
        try:
            if not self.geometry_section.parent_form or not self.geometry_section.parent_form.form_content:
                return
            
            # Find the Line Load Details frame
            line_load_frame = None
            for container in self.geometry_section.parent_form.form_content.controls:
                if (isinstance(container, ft.Container) and 
                    hasattr(container, 'content') and 
                    isinstance(container.content, ft.Column) and
                    container.content.controls and 
                    isinstance(container.content.controls[0], ft.Text) and
                    container.content.controls[0].value == "Line Load Details"):
                    line_load_frame = container
                    break
            
            if not line_load_frame:
                print("DEBUG: Line Load Details frame not found")
                return
            
            # Regenerate line load controls based on current form_values
            line_load_controls = self.create_line_load_controls(self.geometry_section.form_values)
            
            # Update the frame content
            line_load_frame.content.controls[1] = line_load_controls
            line_load_frame.update()
            
            print("DEBUG: Successfully updated Line Load Details frame")
            
        except Exception as ex:
            print(f"ERROR in update_line_load_frame: {str(ex)}")
            import traceback
            traceback.print_exc()
    
    def get_wall_top_coordinates(self, cursor, common_id: str, wall_position: str = None) -> Tuple[float, float]:
        """
        Get x_top and y_top from ERSS Wall Details sheet.
        
        Args:
            cursor: Database cursor
            common_id: Common identifier for related data
            wall_position: For double wall, specify "left" or "right" to get specific wall coordinates
            
        Returns:
            Tuple of (x_top, y_top) coordinates
        """
        try:
            if wall_position:
                # For double wall, get specific wall based on position
                # Assuming the first row is left wall and second row is right wall
                if wall_position.lower() == "left":
                    query = """
                        SELECT x_Top, y_Top 
                        FROM erss_wall_details 
                        WHERE common_id = ? 
                        ORDER BY rowid
                        LIMIT 1
                    """
                elif wall_position.lower() == "right":
                    query = """
                        SELECT x_Top, y_Top 
                        FROM erss_wall_details 
                        WHERE common_id = ? 
                        ORDER BY rowid
                        LIMIT 1 OFFSET 1
                    """
                else:
                    print(f"WARNING: Invalid wall_position '{wall_position}', defaulting to first row")
                    query = """
                        SELECT x_Top, y_Top 
                        FROM erss_wall_details 
                        WHERE common_id = ? 
                        LIMIT 1
                    """
            else:
                # For single wall, just get the first row
                query = """
                    SELECT x_Top, y_Top 
                    FROM erss_wall_details 
                    WHERE common_id = ? 
                    LIMIT 1
                """
            
            cursor.execute(query, [common_id])
            result = cursor.fetchone()
            
            if result:
                x_top = float(result[0])
                y_top = float(result[1])
                position_str = f" ({wall_position})" if wall_position else ""
                print(f"DEBUG: Retrieved wall top coordinates{position_str} - x_top: {x_top}, y_top: {y_top}")
                return x_top, y_top
            else:
                position_str = f" for {wall_position} wall" if wall_position else ""
                print(f"WARNING: No wall details found{position_str} for common_id: {common_id}")
                return 0.0, 0.0
                
        except Exception as e:
            print(f"ERROR: Failed to get wall top coordinates: {e}")
            import traceback
            traceback.print_exc()
            return 0.0, 0.0
    
    def save_lineload_data(self, cursor, common_id: str, load_name: str, 
                          x_start: float, y_start: float, x_end: float, y_end: float,
                          qy_start: float, sheets_config: Dict, excel_sheets: Dict) -> None:
        """
        Save line load data to database, CSV, and Excel.
        
        Args:
            cursor: Database cursor
            common_id: Common identifier for related data
            load_name: Name of the line load (e.g., "LL_Left", "LL_Right")
            x_start: Starting X coordinate
            y_start: Starting Y coordinate
            x_end: Ending X coordinate
            y_end: Ending Y coordinate
            qy_start: Vertical load magnitude (from user input)
            sheets_config: Configuration for sheets
            excel_sheets: Dictionary of Excel worksheet objects
        """
        try:
            # Create lineload data array
            lineload_data = [
                load_name,           # LoadName
                x_start,             # x_start
                y_start,             # y_start
                x_end,               # x_end
                y_end,               # y_end
                0,                   # qx_start (horizontal load component)
                qy_start,            # qy_start (use user-entered value as-is)
                "Uniform"            # Distribution type
            ]
            
            print(f"DEBUG: Saving lineload data: {lineload_data}")
            
            # Save to database
            self._save_to_database(cursor, common_id, lineload_data, sheets_config)
            
            # Save to Excel
            self._save_to_excel(excel_sheets, lineload_data)
            
            # Save to CSV
            self._save_to_csv(common_id, lineload_data, sheets_config)
            
            print(f"DEBUG: Successfully saved lineload data for {load_name}")
            
        except Exception as e:
            print(f"ERROR: Failed to save lineload data for {load_name}: {e}")
            raise
    
    def _save_to_database(self, cursor, common_id: str, lineload_data: list,
                         sheets_config: Dict) -> None:
        """Save lineload data to database."""
        headers = sheets_config['Line Load']['headers']
        columns = ', '.join(headers)
        placeholders = ', '.join(['?'] * len(headers))
        
        query = (f"INSERT INTO {sheets_config['Line Load']['db_table']} "
                f"(common_id, {columns}) VALUES (?, {placeholders})")
        
        cursor.execute(query, [common_id] + lineload_data)
        print(f"DEBUG: Inserted lineload data into database")
    
    def _save_to_excel(self, excel_sheets: Dict, lineload_data: list) -> None:
        """Save lineload data to Excel sheet."""
        excel_sheets["Line Load"].append(lineload_data)
        print(f"DEBUG: Appended lineload data to Excel sheet")
    
    def _save_to_csv(self, common_id: str, lineload_data: list, 
                    sheets_config: Dict) -> None:
        """Save lineload data to CSV file."""
        csv_file = sheets_config["Line Load"]["csv_file"]
        
        with open(csv_file, 'a', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([common_id] + lineload_data)
        
        print(f"DEBUG: Wrote lineload data to CSV: {csv_file}")
    
    def save_all_lineloads(self, cursor, data: Dict, common_id: str,
                          sheets_config: Dict, excel_sheets: Dict) -> None:
        """
        Save all line loads based on excavation type and user-entered data.
        
        Args:
            cursor: Database cursor
            data: Dictionary containing geometry and line load data
            common_id: Common identifier for related data
            sheets_config: Configuration for sheets
            excel_sheets: Dictionary of Excel worksheet objects
        """
        try:
            # Get excavation type
            excavation_type = data.get("Excavation Type", "Single wall")
            
            if excavation_type == "Single wall":
                # Get wall top coordinates (single wall - first row only)
                x_top, y_top = self.get_wall_top_coordinates(cursor, common_id)
                
                if x_top == 0.0 and y_top == 0.0:
                    print("WARNING: Wall coordinates are zero, line loads may be incorrect")
                
                # Get user-entered values
                d = float(data.get("Distance from the wall", 0))
                l = float(data.get("Length of the load", 0))
                q_left = float(data.get("Magnitude of the load", 0))
                
                print(f"DEBUG: Single wall - d={d}, l={l}, q_left={q_left}")
                
                # Calculate coordinates
                x_start = x_top - d
                x_end = x_start - l
                
                # Save left side line load
                self.save_lineload_data(
                    cursor=cursor,
                    common_id=common_id,
                    load_name="LL_Left",
                    x_start=x_start,
                    y_start=y_top,
                    x_end=x_end,
                    y_end=y_top,
                    qy_start=-q_left,
                    sheets_config=sheets_config,
                    excel_sheets=excel_sheets
                )
                
            elif excavation_type == "Double wall":
                # Get left wall coordinates (first row)
                x_top_left, y_top_left = self.get_wall_top_coordinates(cursor, common_id, "left")
                
                # Get right wall coordinates (second row)
                x_top_right, y_top_right = self.get_wall_top_coordinates(cursor, common_id, "right")
                
                if (x_top_left == 0.0 and y_top_left == 0.0) or (x_top_right == 0.0 and y_top_right == 0.0):
                    print("WARNING: Wall coordinates are zero, line loads may be incorrect")
                
                # Get left side user-entered values
                d_left = float(data.get("Distance from the left wall", 0))
                l_left = float(data.get("Length of the left load", 0))
                q_left = float(data.get("Magnitude of the left load", 0))
                
                # Get right side user-entered values
                d_right = float(data.get("Distance from the Right wall", 0))
                l_right = float(data.get("Length of the Right load", 0))
                q_right = float(data.get("Magnitude of the Right load", 0))
                
                print(f"DEBUG: Double wall - Left: d={d_left}, l={l_left}, q={q_left}, x_top={x_top_left}, y_top={y_top_left}")
                print(f"DEBUG: Double wall - Right: d={d_right}, l={l_right}, q={q_right}, x_top={x_top_right}, y_top={y_top_right}")
                
                # Calculate left side coordinates using LEFT wall coordinates
                x_start_left = x_top_left - d_left
                x_end_left = x_start_left - l_left
                
                # Save left side line load
                self.save_lineload_data(
                    cursor=cursor,
                    common_id=common_id,
                    load_name="LL_Left",
                    x_start=x_start_left,
                    y_start=y_top_left,
                    x_end=x_end_left,
                    y_end=y_top_left,
                    qy_start=-q_left,
                    sheets_config=sheets_config,
                    excel_sheets=excel_sheets
                )
                
                # Calculate right side coordinates using RIGHT wall coordinates
                x_start_right = x_top_right + d_right
                x_end_right = x_start_right + l_right
                
                # Save right side line load
                self.save_lineload_data(
                    cursor=cursor,
                    common_id=common_id,
                    load_name="LL_Right",
                    x_start=x_start_right,
                    y_start=y_top_right,
                    x_end=x_end_right,
                    y_end=y_top_right,
                    qy_start=-q_right,
                    sheets_config=sheets_config,
                    excel_sheets=excel_sheets
                )
                
                print("DEBUG: Saved both left and right lineloads for double wall")
            
            print(f"DEBUG: Successfully saved all lineloads for {excavation_type}")
            
        except Exception as e:
            print(f"ERROR: Failed to save lineloads: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def initialize_csv_file(self, sheets_config: Dict) -> None:
        """
        Initialize the CSV file with headers if it doesn't exist.
        
        Args:
            sheets_config: Configuration for sheets including CSV file path and headers
        """
        csv_file = sheets_config["Line Load"]["csv_file"]
        
        if not csv_file.exists():
            with open(csv_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["common_id"] + sheets_config["Line Load"]["headers"])
            print(f"DEBUG: Initialized lineload CSV file: {csv_file}")