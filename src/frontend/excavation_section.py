import csv
import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Union
import sys

import mysql.connector
import openpyxl
from openpyxl.utils import get_column_letter
import flet as ft

from frontend.database_config import DatabaseConfig
from frontend.database_connection import DatabaseConnection
from frontend.form_section import FormSection, FormField
from frontend.form_manager import FormManager
from frontend.database_operations import DatabaseOperations

class ExcavationSection(FormSection):
    """Manages excavation stages in a form, including stage data and visualization."""

    def __init__(self, db_ops: DatabaseOperations, db_config: DatabaseConfig, form_manager=None, form_content=None):
        """Initialize excavation section with database config and form components."""
        super().__init__()
        self.db_config = db_config
        self.db_ops = db_ops
        self.form_manager = form_manager  # Save the form manager for later use
        self.visible_sets = 1
        self.form_content = form_content  
        self.page = None
        self.data_table = None  # Initialize the data_table attribute
        self.add_button = None  #
        self.delete_button = None  # Add this new line
        self.initial_row_added = False  # Flag to track if the initial row has been added
        self.initialized = False
    def import_from_list(self, data):
        self.data_table.rows.clear()
        for idx, item in enumerate(data):
            self.add_stage(None, initial_data=item)
    
    def get_initial_wall_top_level(self) -> float:
        """Retrieve initial wall top level from geometry table."""
        with DatabaseConnection(self.db_config) as db:
            db.cursor.execute("""
                SELECT wall_top_level 
                FROM geometry 
                ORDER BY id DESC 
                LIMIT 1
            """)
            result = db.cursor.fetchone()
            return float(result['wall_top_level']) if result else 0.0

    def get_fields(self) -> List[FormField]:
        """Return list of form fields for excavation stages."""
        return [
            FormField("Stage No", "number", required=True),
            FormField("Stage Name", "text", required=True),
            FormField("From", "number", required=True),
            FormField("To", "number", required=True)
        ]

    def validate(self, data: Dict) -> List[str]:
        """Validate excavation stage data and return list of errors."""
        errors = []
        if not data:
            return ["No excavation stages provided"]

        for stage in data:
            # Check if all required fields exist
            if not all(key in stage for key in ["Stage No", "Stage Name", "From", "To"]):
                errors.append("All fields are required for each stage")
                continue  # Skip further validation for this stage if fields are missing
            
            # Check if all fields have values
            if not all(stage[key] for key in ["Stage No", "Stage Name", "From", "To"]):
                errors.append("All fields must have values")
                continue  # Skip further validation for this stage if values are missing
            
            try:
                # Convert From and To values to float for comparison
                from_value = float(stage["From"])
                to_value = float(stage["To"])
                
                # Check if From is greater than To
                if from_value <= to_value:
                    errors.append(f"Stage {stage['Stage No']}: 'From' value ({from_value}) must be greater than 'To' value ({to_value})")
            except ValueError:
                errors.append(f"Stage {stage['Stage No']}: 'From' and 'To' values must be valid numbers")

        return errors  

    def save(self, cursor, data: List[Dict], geometry_data: Dict = None) -> None:
        """Save excavation data using DatabaseOperations."""
        try:
            db_ops = DatabaseOperations(self.db_config)
            common_id = data[0].get('common_id') if data else None
            
            # Get over-excavation from geometry data
            over_excavation = None
            excavation_width = None
            excavation_depth = None
            excavation_type = None
            if geometry_data:
                if isinstance(geometry_data, dict):
                    over_excavation = geometry_data.get('Over Excavation')
                    excavation_width = geometry_data.get('Excavation Width')
                    excavation_depth = geometry_data.get('Excavation Depth')
                    excavation_type = geometry_data.get('Excavation Type')
                elif isinstance(geometry_data, list) and len(geometry_data) > 0:
                    over_excavation = geometry_data[0].get('Over Excavation')
                    excavation_width = geometry_data[0].get('Excavation Width')
                    excavation_depth = geometry_data[0].get('Excavation Depth')
                    excavation_type = geometry_data[0].get('Excavation Type')
            # Calculate x value (half of excavation width)
            x = float(excavation_width) / 2 if excavation_width else None
           
            x_max = float(excavation_width)/2 + 4*float(excavation_depth)
            # Determine x_Right based on excavation type
            if excavation_type == "Double wall":
                x_right_value = x
            else:  # Single wall or any other type
                x_right_value = x_max
            # Save excavation data
            db_ops.save_excavation_data(
                cursor,
                common_id,
                data,
                float(over_excavation) if over_excavation else None
            )

            # Save to files using DatabaseOperations
            # Get the base directory of the script
            if getattr(sys, 'frozen', False):
                # Running as exe - use internal/data directory
                BASE_DIR = Path(sys.executable).parent / "_internal"
            else:
                # Running as script - use original path
                BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Define the export directory relative to the project root
            export_dir = BASE_DIR / "data"    
            # Updated headers with new column names
            headers = ['StageNo', 'StageName', 'y_start_Left', 'y_end_Left', 'x_Left', 'y_start_Right', 'y_end_Right', 'x_Right']
            
            # CSV data with renamed columns and new columns
            csv_data = []
            for stage in data:
                stage_data = {
                    'StageNo': stage["Stage No"],
                    'StageName': stage["Stage Name"],
                    'y_start_Left': stage["From"],  # renamed from "From"
                    'y_end_Left': stage["To"],      # renamed from "To"
                    'x_Left': -x if x is not None else None,  # new column
                    'y_start_Right': stage["From"],  # new column, same as y_start_Left
                    'y_end_Right': stage["To"],      # new column, same as y_end_Left
                    'x_Right': x_right_value                     # new column
                }
                csv_data.append(stage_data)
            
            if over_excavation:
                last_to = float(data[-1]["To"])
                over_ex_to = last_to - float(over_excavation)
                csv_data.append({
                    'StageNo': len(data) + 1,
                    'StageName': "Over Excavation",
                    'y_start_Left': last_to,
                    'y_end_Left': over_ex_to,
                    'x_Left': -x if x is not None else None,
                    'y_start_Right': last_to,
                    'y_end_Right': over_ex_to,
                    'x_Right': x_right_value
                })
            
            db_ops.save_to_csv(
                csv_data,
                export_dir / "excavation_stages.csv",
                headers
            )

            # Excel data with updated column names and new columns
            db_ops.update_excel(
                export_dir / "Input_Data.xlsx",
                "Excavation Details",
                csv_data
            )

        except Exception as e:
            print(f"Error saving excavation data: {str(e)}")
            raise
    
    def reset_initial_row_flag(self):
        self.initial_row_added = False
    
    def validate_to_value(self, e, control):
        """Validate the To value and show error immediately (used for next button validation)."""
        try:
            # Get the current value from the TextField
            to_value = control.value
            
            # If empty, don't validate yet
            if not to_value:
                return True
                
            # Convert to float for comparison
            to_float = float(to_value)
            
            # Get Toe Level from geometry data
            geometry_data = self.form_manager.get_section_data('geometry')
            toe_level = float(geometry_data.get('Toe Level', 0))
            
            # Check if To value is less than Toe Level
            if to_float < toe_level:
                # Show error message
                self._show_error_dialog(
                    f"Invalid 'To' value: The value ({to_float}) cannot be less than Toe Level ({toe_level})"
                )
                return False
                
            return True
                
        except ValueError:
            # Handle case where value can't be converted to float
            self._show_error_dialog("'To' value must be a valid number")
            return False

    def validate_all_to_values(self):
        """Validate all To values when user clicks next button."""
        if not hasattr(self, 'data_table') or not self.data_table:
            return True
            
        validation_errors = []
    
        try:
            # Get geometry data once
            geometry_data = self.form_manager.get_section_data('geometry')
            toe_level = float(geometry_data.get('Toe Level', 0))
            
            # Check each row in the data table
            for row in self.data_table.rows:
                # Find the "To" field in this row (should be the 4th cell, index 3)
                if len(row.cells) >= 4:
                    to_cell = row.cells[3]  # "To" field is the 4th column
                    if hasattr(to_cell.content, 'content') and hasattr(to_cell.content.content, 'value'):
                        to_control = to_cell.content.content
                        to_value = to_control.value
                        
                        if to_value:
                            try:
                                to_float = float(to_value)
                                if to_float < toe_level:
                                    # Get stage number from first cell
                                    stage_no = row.cells[0].content.content.value if len(row.cells) > 0 else "Unknown"
                                    validation_errors.append(
                                        f"Stage {stage_no}: 'To' value ({to_float}) cannot be less than Toe Level ({toe_level})"
                                    )
                            except ValueError:
                                stage_no = row.cells[0].content.content.value if len(row.cells) > 0 else "Unknown"
                                validation_errors.append(f"Stage {stage_no}: 'To' value must be a valid number")
    
            # Show all validation errors at once
            if validation_errors:
                error_message = "Please fix the following errors:\n\n" + "\n".join(validation_errors)
                self._show_error_dialog(error_message)
                return False
                
            return True
            
        except Exception as e:
            print(f"Error validating To values: {str(e)}")
            return False

    def set_page_reference(self, page):
        """Set the page reference for immediate updates."""
        self.page = page

    def update_next_stage_from_value(self, current_stage_number: int, new_to_value: str):
      """Update the next stage's 'From' value when current stage's 'To' value changes."""
      try:
        if not self.data_table or not self.data_table.rows:
            return
        
        next_stage_number = current_stage_number + 1
        
        # Find the next stage row
        for row in self.data_table.rows:
            if len(row.cells) >= 5:  # Ensure we have all required cells
                # Get stage number from cell index 1 (after Actions at index 0)
                stage_no_cell = row.cells[1]
                if (hasattr(stage_no_cell.content, 'content') and 
                    hasattr(stage_no_cell.content.content, 'value')):
                    
                    stage_no = stage_no_cell.content.content.value
                    if stage_no and int(stage_no) == next_stage_number:
                        # Update "From" value in cell index 3
                        from_cell = row.cells[3]
                        if (hasattr(from_cell.content, 'content') and 
                            hasattr(from_cell.content.content, 'value')):
                            from_control = from_cell.content.content
                            from_control.value = new_to_value
                            from_control.update()
                            
                            # Force page update
                            if self.page:
                                self.page.update()
                            break
                            
      except Exception as e:
        print(f"Error updating next stage From value: {e}")
    def create_excavation_set(self, set_number: int, initial_from: str = None, initial_data: Dict = None) -> ft.DataRow:
      fields = self.get_fields()
      cells = []
      column_widths = {
        "Actions": 50,  # Add this new line
        "Stage No": 150,
        "Stage Name": 300,
        "From": 200,
        "To": 200
    }
      stage_name_control = None
      to_control = None
    
    # Calculate values (only used if no stored data available)
      calculated_to_value = self.calculate_to_value(set_number)
      if set_number == 1:
        geometry_data = self.form_manager.get_section_data('geometry')
        calculated_from_value = geometry_data.get('Wall Top Level', '')
      else:
        calculated_from_value = self.get_previous_stage_to_value(set_number - 1)
        if not calculated_from_value:
            calculated_from_value = initial_from if initial_from else ""
      # Add delete icon button for each row
      delete_icon = ft.IconButton(
          icon=ft.icons.REMOVE_CIRCLE_OUTLINE,
          icon_color=ft.colors.RED_400,
          icon_size=20,
          tooltip="Delete this stage",
          on_click=lambda e, set_num=set_number: self.delete_row(set_num)
      )
      actions_cell = ft.DataCell(
          content=ft.Container(
              content=delete_icon,
              width=column_widths["Actions"],
              height=50,
              padding=ft.padding.all(0)
          )
      )
      cells.append(actions_cell) 
      for field in fields:
        width = column_widths.get(field.label, 200)
        
        # VALUE ASSIGNMENT LOGIC - Prefer initial_data (stored values), then calculate
        value = None
        read_only = False  # default
        
        # Check if we have initial_data for this field
        if initial_data and field.label in initial_data and initial_data[field.label] is not None:
            value = str(initial_data[field.label])
        else:
            # Only calculate if we don't have initial_data
            if field.label == "To":
                value = calculated_to_value
            elif field.label == "From":
                value = str(calculated_from_value) if calculated_from_value else ""
            elif field.label == "Stage No":
                value = str(set_number)
            elif field.label == "Stage Name":
                # Create default name using calculated "To" value if available
                value = f"Excavate to {calculated_to_value}" if calculated_to_value else "Excavate to"
        
        # Set read-only for Stage No, From, and Stage Name
        if field.label in ["Stage No", "From", "Stage Name"]:
            read_only = True
        elif field.label == "To":
            read_only = False

        control = field.create_control(
            width=width,
            value=value,
            set_number=set_number
        )
        
        if isinstance(control, ft.TextField):
            control.height = 40
            control.text_size = 14
            control.content_padding = 5
            control.value = value
            control.read_only = read_only
            
            if field.label == "Stage Name":
                stage_name_control = control
            elif field.label == "To":
                to_control = control

            if field.label == "To" and not read_only:
                def create_comprehensive_update_handler(stage_name_ctrl, to_ctrl, stage_num):
                    def handle_comprehensive_update(e):
                        # Mark as user modified when To value changes
                        self.user_modified = True
                        self.update_stage_name(stage_name_ctrl, to_ctrl)
                        self.update_next_stage_from_value(stage_num, to_ctrl.value)
                        if self.page:
                            self.page.update()
                    return handle_comprehensive_update

                def create_validation_handler(to_ctrl):
                    def handle_validation(e):
                        self.store_validation_result(to_ctrl)
                    return handle_validation

                comprehensive_handler = create_comprehensive_update_handler(stage_name_control, to_control, set_number)
                validation_handler = create_validation_handler(to_control)
                
                control.on_change = comprehensive_handler
                control.on_blur = validation_handler
                control.on_submit = validation_handler

            if read_only:
                control.bgcolor = ft.colors.GREY_200
                control.cursor_color = ft.colors.TRANSPARENT
                control.selection_color = ft.colors.TRANSPARENT

        cell = ft.DataCell(
            content=ft.Container(
                content=control,
                width=width,
                height=50,
                padding=ft.padding.all(0)
            )
        )
        cells.append(cell)

      return ft.DataRow(cells=cells)
    def get_previous_stage_to_value(self, previous_stage_number: int) -> str:
      """Get the 'To' value from the previous stage in the DataTable."""
      try:
        if not self.data_table or not self.data_table.rows:
            return ""
        
        # Look for the row with the previous stage number
        for row in self.data_table.rows:
            if len(row.cells) >= 5:  # Ensure we have all required cells
                # Get stage number from cell index 1 (after Actions at index 0)
                stage_no_cell = row.cells[1]
                if (hasattr(stage_no_cell.content, 'content') and 
                    hasattr(stage_no_cell.content.content, 'value')):
                    
                    stage_no = stage_no_cell.content.content.value
                    if stage_no and int(stage_no) == previous_stage_number:
                        # Get "To" value from cell index 4
                        to_cell = row.cells[4]
                        if (hasattr(to_cell.content, 'content') and 
                            hasattr(to_cell.content.content,'value')):
                            to_value = to_cell.content.content.value
                            return str(to_value) if to_value else ""
        
        # If we can't find it in the DataTable, calculate it
        return self.calculate_to_value(previous_stage_number)
        
      except Exception as e:
        print(f"Error getting previous stage To value: {e}")
        # Fallback to calculation
        return self.calculate_to_value(previous_stage_number)
    def calculate_to_value(self, stage_number: int) -> str:
      print(f"DEBUG: calculate_to_value called for stage {stage_number}")
      try:
        geometry_data = self.form_manager.get_section_data('geometry')
        wall_top_level = float(geometry_data.get('Wall Top Level', 0))
        excavation_depth = float(geometry_data.get('Excavation Depth', 0))
        excavation_below_strut = float(geometry_data.get('Excavation Below Strut', 0))
        over_excavation = float(geometry_data.get('Over Excavation', 0))
        no_of_struts = int(geometry_data.get('No of Strut', 0))
        
        print(f"DEBUG calculate_to_value: stage_number={stage_number}, no_of_struts={no_of_struts}")
        print(f"DEBUG: wall_top_level={wall_top_level}, excavation_depth={excavation_depth}")
        print(f"DEBUG: excavation_below_strut={excavation_below_strut}, over_excavation={over_excavation}")

        # Stage calculations based on strut levels
        if stage_number <= no_of_struts:
            strut_level_key = f'Strut {stage_number} Level'
            if strut_level_key in geometry_data:
                strut_level = float(geometry_data.get(strut_level_key, 0))
                result = strut_level - excavation_below_strut
                print(f"DEBUG: Stage {stage_number} = {strut_level} - {excavation_below_strut} = {result}")
                return str(result)
        
        # Final stage (no_of_struts + 1)
        elif stage_number == no_of_struts + 1:
            result = wall_top_level - excavation_depth
            print(f"DEBUG: Final stage = {wall_top_level} - {excavation_depth} = {result}")
            return str(result)
        
        # Over excavation stage (not displayed but calculated)
        elif stage_number == no_of_struts + 2:
            result = wall_top_level - excavation_depth - over_excavation
            print(f"DEBUG: Over excavation = {wall_top_level} - {excavation_depth} - {over_excavation} = {result}")
            return str(result)
        
        else:
            print(f"DEBUG: No calculation rule for stage {stage_number}")
            return ""
            
      except (ValueError, KeyError) as e:
        print(f"Error calculating To value: {e}")
        return "" 
    def update_stage_name(self, stage_name_control, to_control):
        """Update the stage name based on the To field value."""
        try:
            to_value = to_control.value.strip() if to_control.value else ""
            
            if to_value:
                # Update stage name to include the To value
                stage_name_control.value = f"Excavate to {to_value}"
            else:
                # Reset to default if To field is empty
                stage_name_control.value = "Excavate to"
            
            # Force immediate update of the control
            stage_name_control.update()
            
            # Also update the page if available
            if hasattr(self, 'page') and self.page:
                self.page.update()
            
        except Exception as e:
            print(f"Error updating stage name: {str(e)}")

    def store_validation_result(self, control):
        """Store validation result for later use when user clicks next button."""
        try:
            # Get the current value from the TextField
            to_value = control.value
            
            # If empty, no validation needed
            if not to_value:
                return
                
            # Convert to float for comparison
            to_float = float(to_value)
            
            # Get Toe Level from geometry data
            geometry_data = self.form_manager.get_section_data('geometry')
            toe_level = float(geometry_data.get('Toe Level', 0))
            
            # Store validation result in the control for later use
            if to_float < toe_level:
                control.error_text = f"Value ({to_float}) cannot be less than Toe Level ({toe_level})"
                control.has_validation_error = True
            else:
                control.error_text = None
                control.has_validation_error = False
                
        except ValueError:
            # Handle case where value can't be converted to float
            control.error_text = "Must be a valid number"
            control.has_validation_error = True
    
    def add_stage(self, e, initial_data: Dict = None):
      """Add a new stage with proper UI updates."""
      try:
        if not self.data_table:
            print("ERROR: data_table not initialized")
            return

        # CHECK MAXIMUM STAGES LIMIT FIRST - SHOW ERROR IF EXCEEDED
        max_allowed = self.get_max_allowed_stages()
        current_stages = len(self.data_table.rows)
        
        if current_stages >= max_allowed:
            geometry_data = self.form_manager.get_section_data('geometry')
            no_of_struts = int(geometry_data.get('No of Strut', 0))
            error_msg = (
                f"Cannot add more stages!\n\n"
                f"Maximum allowed stages: {max_allowed}\n"
                f"Based on {no_of_struts} strut level(s) + 1 final stage\n\n"
                f"Current stages: {current_stages}\n"
                f"(Note: Over excavation stage exists but is not displayed)"
            )
            self._show_error_dialog(error_msg)
            return  # EXIT HERE - DON'T ADD THE STAGE

        self.user_modified = True
        next_stage_number = self.visible_sets + 1
        from_value = None
        
        # Get the 'To' value from the last row to use as 'From' value for new row
        if self.data_table.rows:
            last_row = self.data_table.rows[-1]
            if len(last_row.cells) >= 5:  # Ensure we have all cells [Actions, Stage No, Stage Name, From, To]
                to_cell = last_row.cells[4]  # 'To' cell is at index 4
                if (hasattr(to_cell.content, 'content') and
                     hasattr(to_cell.content.content, 'value')):
                    from_value = to_cell.content.content.value

        # Validate that the previous stage's 'To' value is greater than Toe Level
        if from_value:
            try:
                geometry_data = self.form_manager.get_section_data('geometry')
                toe_level = float(geometry_data.get('Toe Level', 0))
                from_float = float(from_value)
                if from_float <= toe_level:
                    self._show_error_dialog(
                        f"Cannot add new stage: Previous stage's 'To' value ({from_float}) "
                        f"must be greater than Toe Level ({toe_level})"
                    )
                    return
            except (ValueError, TypeError) as e:
                self._show_error_dialog(f"Invalid previous stage 'To' value: {e}")
                return

        # Create and add the new row
        new_row = self.create_excavation_set(
            next_stage_number,
            from_value,
            initial_data
        )
        self.data_table.rows.append(new_row)
        self.visible_sets += 1

        # Update delete button state - only disable if we have 1 or fewer rows
        if hasattr(self, 'delete_button') and self.delete_button:
            current_row_count = len(self.data_table.rows)
            self.delete_button.disabled = current_row_count <= 1
            self.delete_button.update()

        # FIXED: Update parent containers instead of data_table directly
        if hasattr(self, 'table_container') and self.table_container:
            self.table_container.update()
        
        if hasattr(self, 'scrollable_row') and self.scrollable_row:
            self.scrollable_row.update()
            
        if self.form_content:
            self.form_content.update()
            
        if self.page:
            self.page.update()

        print(f"DEBUG: Successfully added stage {next_stage_number}")

      except Exception as ex:
        print(f"Error in add_stage: {str(ex)}")
        import traceback
        traceback.print_exc()
        if hasattr(self, 'page') and self.page:
            self._show_error_dialog(f"Failed to add stage: {str(ex)}")
    def is_ui_ready(self):
      """Check if the UI components are properly initialized and added to page"""
      return (hasattr(self, 'page') and self.page and 
            hasattr(self, 'data_table') and self.data_table and
            hasattr(self.data_table, 'page') and self.data_table.page)
    def delete_row(self, set_number: int):
      """Delete a specific row and properly adjust remaining rows."""
      if not self.data_table or len(self.data_table.rows) <= 1:
        return

      try:
        self.user_modified = True
        deleted_index = None
        
        # Find and delete the row with the specified set_number
        for i, row in enumerate(self.data_table.rows):
            if len(row.cells) > 1:  # Ensure we have at least the stage number cell
                # Cell index 1 is Stage No (after Actions at index 0)
                stage_no_cell = row.cells[1]
                if (hasattr(stage_no_cell.content, 'content') and
                    hasattr(stage_no_cell.content.content, 'value')):
                    stage_no_value = stage_no_cell.content.content.value
                    if stage_no_value and int(stage_no_value) == set_number:
                        deleted_index = i
                        break

        if deleted_index is None:
            print(f"Row with stage number {set_number} not found")
            return

        # Remove the row
        del self.data_table.rows[deleted_index]
        self.visible_sets -= 1

        # Re-number all remaining stages and update their values
        for j, row in enumerate(self.data_table.rows):
            new_stage_number = j + 1
            
            if len(row.cells) >= 5:  # Ensure we have all required cells [Actions, Stage No, Stage Name, From, To]
                # Update Stage No (cell index 1)
                stage_no_cell = row.cells[1]
                if (hasattr(stage_no_cell.content, 'content') and
                    hasattr(stage_no_cell.content.content, 'value')):
                    stage_no_cell.content.content.value = str(new_stage_number)

                # Update From value (cell index 3)
                from_cell = row.cells[3]
                if (hasattr(from_cell.content, 'content') and
                    hasattr(from_cell.content.content, 'value')):
                    
                    if j == 0:
                        # First row: From = Wall Top Level
                        geometry_data = self.form_manager.get_section_data('geometry')
                        wall_top_level = geometry_data.get('Wall Top Level', '')
                        from_cell.content.content.value = str(wall_top_level)
                    else:
                        # Other rows: From = previous row's To value
                        prev_row = self.data_table.rows[j-1]
                        if len(prev_row.cells) >= 5:
                            prev_to_cell = prev_row.cells[4]  # To cell is at index 4
                            if (hasattr(prev_to_cell.content, 'content') and
                                hasattr(prev_to_cell.content.content, 'value')):
                                prev_to_value = prev_to_cell.content.content.value
                                from_cell.content.content.value = str(prev_to_value) if prev_to_value else ""

                # Update To value (cell index 4) - recalculate based on new stage number
                to_cell = row.cells[4]
                if (hasattr(to_cell.content, 'content') and
                    hasattr(to_cell.content.content, 'value')):
                    # Only recalculate if this row was affected by the deletion
                    if j >= deleted_index:
                        calculated_to = self.calculate_to_value(new_stage_number)
                        if calculated_to:
                            to_cell.content.content.value = calculated_to

                # Update Stage Name (cell index 2) based on To value
                stage_name_cell = row.cells[2]
                if (hasattr(stage_name_cell.content, 'content') and
                    hasattr(stage_name_cell.content.content, 'value')):
                    to_value = to_cell.content.content.value if (
                        hasattr(to_cell.content, 'content') and
                        hasattr(to_cell.content.content, 'value')
                    ) else ""
                    stage_name_cell.content.content.value = f"Excavate to {to_value}" if to_value else "Excavate to"

                # Update the delete button's onclick handler for the new stage number
                if len(row.cells) >= 1:  # Actions cell at index 0
                    actions_cell = row.cells[0]
                    if (hasattr(actions_cell.content, 'content') and
                        hasattr(actions_cell.content.content, 'on_click')):
                        # Update the onclick handler with the new stage number
                        actions_cell.content.content.on_click = lambda e, set_num=new_stage_number: self.delete_row(set_num)

        # Update delete button state - only disable if we have 1 or fewer rows
        current_row_count = len(self.data_table.rows)
        if hasattr(self, 'delete_button') and self.delete_button:
            self.delete_button.disabled = current_row_count <= 1
            self.delete_button.update()

        # FIXED: Update the UI properly - don't call data_table.update() directly
        # Instead, update the parent containers that contain the data_table
        
        # Update parent containers in order of hierarchy
        if hasattr(self, 'table_container') and self.table_container:
            self.table_container.update()
        
        if hasattr(self, 'scrollable_row') and self.scrollable_row:
            self.scrollable_row.update()
            
        # Update form content if available
        if self.form_content:
            self.form_content.update()
            
        # Finally update the page
        if self.page:
            self.page.update()

        print(f"DEBUG: Successfully deleted stage {set_number}, renumbered remaining stages")

      except Exception as e:
        print(f"Error deleting row: {e}")
        import traceback
        traceback.print_exc()
        if hasattr(self, 'page') and self.page:
            self._show_error_dialog(f"Failed to delete stage: {str(e)}")


    def delete_last_stage(self, e):
      """Delete the last stage with proper UI updates."""
      if not self.data_table or len(self.data_table.rows) <= 1:
        return

      try:
        self.user_modified = True
        self.data_table.rows.pop()
        self.visible_sets -= 1

        # Update delete button state
        current_row_count = len(self.data_table.rows)
        
        if hasattr(self, 'delete_button') and self.delete_button:
            self.delete_button.disabled = current_row_count <= 1
            self.delete_button.update()

        # FIXED: Update parent containers instead of data_table directly
        if hasattr(self, 'table_container') and self.table_container:
            self.table_container.update()
        
        if hasattr(self, 'scrollable_row') and self.scrollable_row:
            self.scrollable_row.update()
            
        if self.form_content:
            self.form_content.update()
            
        if self.page:
            self.page.update()

        print(f"DEBUG: Successfully deleted last stage, {self.visible_sets} stages remaining")

      except Exception as e:
        print(f"Error deleting last stage: {e}")
        import traceback
        traceback.print_exc()
        if hasattr(self, 'page') and self.page:
            self._show_error_dialog(f"Failed to delete stage: {str(e)}")
  
    def refresh_table_ui(self):
      if hasattr(self, 'page') and self.page:
        self.page.update()
    def create_buttons_row(self):
      self.add_button = ft.ElevatedButton(
        "Add Stage",
        icon=ft.icons.ADD,
        on_click=self.add_stage,
        style=ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor=ft.colors.BLUE_600,
            padding=10,
        )
        # REMOVED: disabled parameter - keep button always enabled
      )

      current_row_count = len(self.data_table.rows) if hasattr(self, 'data_table') and self.data_table else 0
    
      self.delete_button = ft.ElevatedButton(
        "Delete Last Stage",
        icon=ft.icons.DELETE,
        on_click=self.delete_last_stage,
        style=ft.ButtonStyle(
            color=ft.colors.WHITE,
            bgcolor=ft.colors.RED_600,
            padding=10,
        ),
        disabled=current_row_count <= 1  # Only delete button gets disabled
    )

      return ft.Row(controls=[self.add_button, self.delete_button], spacing=20) 
    async def _show_error_dialog_async(self, message: str):
        """Display error dialog with the specified message asynchronously."""
        if self.page:
            dialog = ft.AlertDialog(
                title=ft.Text("Validation Error"),
                content=ft.Text(message)
            )
            self.page.dialog = dialog
            dialog.open = True
            await self.page.update_async()
        else:
            print(f"ERROR: Cannot show dialog - {message}")

    # Keep the original _show_error_dialog for backward compatibility
    def _show_error_dialog(self, message: str):
        """Display error dialog with the specified message."""
        if self.page:
            dialog = ft.AlertDialog(
                title=ft.Text("Validation Error"),
                content=ft.Text(message)
            )
            self.page.dialog = dialog
            dialog.open = True
            self.page.update()
        else:
            print(f"ERROR: Cannot show dialog - {message}")
    
    def import_from_csv(self, csv_file_path: str, cursor) -> None:
        """Import excavation data from CSV file and populate the DataTable."""
        try:
            # Read CSV file
            with open(csv_file_path, mode='r') as file:
                reader = csv.DictReader(file)  # Reads the CSV into a list of dictionaries
                csv_data = [row for row in reader]  # Convert CSV rows to a list of dictionaries

            # Clear existing rows in the DataTable
            self.data_table.rows.clear()

            # Populate the DataTable with CSV data
            for row_data in csv_data:
                # Map CSV columns to the expected field names
                initial_data = {
                    "Stage No": row_data.get("Stage No", ""),
                    "Stage Name": row_data.get("Stage Name", ""),
                    "From": row_data.get("From", ""),
                    "To": row_data.get("To", "")
                }

                # Create a new row and add it to the DataTable
                new_row = self.create_excavation_set(
                    int(initial_data["Stage No"]),  # Stage number
                    initial_data["From"],           # From value
                    initial_data                    # Pass the entire initial_data dictionary
                )
                self.data_table.rows.append(new_row)

            # Update the UI
            self.data_table.update()
            print("DEBUG: DataTable populated with CSV data.")

        except Exception as e:
            print(f"Error importing CSV: {e}")
    
    # 1. UPDATE: Add method to calculate maximum allowed stages
    def get_max_allowed_stages(self) -> int:
        """Calculate maximum allowed stages based on number of struts"""
        try:
            geometry_data = self.form_manager.get_section_data('geometry')
            no_of_struts = int(geometry_data.get('No of Strut', 0))
            # Formula: no_of_struts + 1 (final stage) 
            # Note: over excavation stage exists but is not displayed as a row
            max_stages = no_of_struts + 1
            print(f"DEBUG: Max allowed stages = {no_of_struts} struts + 1 final = {max_stages}")
            return max_stages
        except (ValueError, KeyError, TypeError) as e:
            print(f"Error calculating max stages: {e}")
            return 1
    def get_affected_stages_by_strut_change(self, changed_strut_num: int, geometry_data: Dict) -> List[int]:
      affected_stages = []
      n_struts = int(geometry_data.get('No of Strut', 0))
    
      if changed_strut_num > 0 and changed_strut_num <= n_struts:
        # The stage that excavates TO this strut level
        affected_stages.append(changed_strut_num)
        
        # The next stage that starts FROM this strut level
        # This will be either the next strut stage or the final stage
        if changed_strut_num < n_struts:
            affected_stages.append(changed_strut_num + 1)
        elif changed_strut_num == n_struts:
            # Last strut affects the final excavation stage
            affected_stages.append(n_struts + 1)
    
      print(f"DEBUG: Strut {changed_strut_num} change affects stages: {affected_stages}")
      return affected_stages

    def update_specific_stages(self, affected_stages: List[int], geometry_data: Dict):
      """
      Update only specific excavation stages based on geometry changes.
      Preserves user's manual edits to unaffected stages.
      """
      if not self.data_table or not self.data_table.rows:
        print("DEBUG: No data table or rows to update")
        return
    
      n_struts = int(geometry_data.get('No of Strut', 0))
      wall_top_level = float(geometry_data.get('Wall Top Level', 0))
      excavation_depth = float(geometry_data.get('Excavation Depth', 0))
      excavation_below_strut = float(geometry_data.get('Excavation Below Strut', 1))
      final_level = wall_top_level - excavation_depth
      
      print(f"DEBUG: update_specific_stages called for stages {affected_stages}")
      print(f"DEBUG: Current data table has {len(self.data_table.rows)} rows")
      
      for stage_num in affected_stages:
        row_index = stage_num - 1
        
        if row_index >= len(self.data_table.rows):
            print(f"DEBUG: Stage {stage_num} out of range")
            continue
            
        row = self.data_table.rows[row_index]
        
        # Find the "From" and "To" fields in this row
        from_control = None
        to_control = None
        
        for cell in row.cells:
            control = cell.content
            if isinstance(control, ft.Container):
                control = control.content
            
            if isinstance(control, ft.TextField) and hasattr(control, 'label'):
                if 'From' in control.label:
                    from_control = control
                elif 'To' in control.label:
                    to_control = control
        
        # Calculate and apply new values
        if stage_num <= n_struts:
            # Regular strut stage: excavate TO (strut level - excavation_below_strut)
            strut_level = float(geometry_data.get(f'Strut {stage_num} Level', 0))
            new_to_value = strut_level - excavation_below_strut
            
            # Update "To" value for this stage
            if to_control:
                old_value = to_control.value
                to_control.value = str(new_to_value)
                
                # Also update stage name
                for cell in row.cells:
                    control = cell.content
                    if isinstance(control, ft.Container):
                        control = control.content
                    if isinstance(control, ft.TextField) and hasattr(control, 'label'):
                        if 'Stage Name' in control.label:
                            control.value = f"Excavate to {new_to_value}"
                            break
            
            # Update "From" value of NEXT stage
            next_stage_num = stage_num + 1
            next_row_index = next_stage_num - 1
            
            if next_row_index < len(self.data_table.rows):
                next_row = self.data_table.rows[next_row_index]
                for cell in next_row.cells:
                    control = cell.content
                    if isinstance(control, ft.Container):
                        control = control.content
                    
                    if isinstance(control, ft.TextField) and hasattr(control, 'label'):
                        if 'From' in control.label:
                            old_value = control.value
                            control.value = str(new_to_value)
                            print(f"DEBUG: Stage {next_stage_num} From: {old_value} -> {new_to_value}")
                            break
        
        elif stage_num == n_struts + 1:
            # Final stage - update "To" to match final excavation level
            if to_control:
                old_value = to_control.value
                to_control.value = str(final_level)
                print(f"DEBUG:  Final Stage {stage_num} To: {old_value} -> {final_level}")
                
                # Update stage name
                for cell in row.cells:
                    control = cell.content
                    if isinstance(control, ft.Container):
                        control = control.content
                    if isinstance(control, ft.TextField) and hasattr(control, 'label'):
                        if 'Stage Name' in control.label:
                            control.value = f"Excavate to {final_level}"
                            print(f"DEBUG:  Final Stage Name updated")
                            break
    
        print(f"DEBUG: Completed updating {len(affected_stages)} stages")