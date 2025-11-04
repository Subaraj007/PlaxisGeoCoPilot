# Standard Library 
from typing import Optional, List, Dict, Tuple
from dataclasses import dataclass

# Third-Party Library 
import flet as ft
import asyncio
import sys
import os
from io import BytesIO
import zipfile
# Import the AGS reading functions
from pathlib import Path
import pandas as pd
import re
import traceback
import subprocess
from datetime import datetime
import csv
import json
from pathlib import Path
# Local Module 
from frontend.database_config import DatabaseConfig
from frontend.database_connection import DatabaseConnection
from frontend.form_manager import FormManager
from frontend.form_section import FormSection, FormField
from frontend.project_info_section import ProjectInfoSection
from frontend.geometry_section import GeometrySection
from frontend.borehole_section import BoreholeSection
from frontend.excavation_section import ExcavationSection
from frontend.sequence_construct_section import SequenceConstructSection
from frontend.login_screen import LoginScreen
from frontend.database_operations import DatabaseOperations
from pathlib import Path  # Move this import to top instead of inside method
from frontend.gcp_file_handler import GCPHandler
from frontend.create_model import ModelCreator
from frontend.user_profile import UserProfile
from frontend.full_import import FullDataImporter
from frontend.auth_server_handler_singleton import AuthServerHandlerSingleton
from frontend.soil_db_handler import SoilDBHandler  # Import at the top of your file
from frontend.auth_manager import AuthManager
from frontend.ags_data_handler import AGSDataHandler
from frontend.import_data_handler import ImportDataHandler
from frontend.create_ui import UICreator
class FormApp:
    def __init__(self, db_config: DatabaseConfig):
        self.form_manager = FormManager(db_config)
        self.db_config = db_config  
        self.db_ops=DatabaseOperations(db_config)
        self.current_file_section_index=None  
        self.file_picker = None
        self.ags_file_picker = None
        self.page = None
        self.section_data = {}
        self.is_signed_in = False
        self.sign_in_page = None
        self.submission_successful = False
        self.data_modified_after_submission = False
        self.current_username = None  # Add this line
        if getattr(sys, 'frozen', False):
            # Running as exe - use internal/data directory
            self.BASE_DIR = Path(sys.executable).parent / "_internal"
        else:
            # Running as script - use original path
            self.BASE_DIR = Path(__file__).resolve().parent.parent.parent
    
        self.export_dir = self.BASE_DIR / "data"
        self.input_data_path = self.export_dir / "Input_Data.xlsx"
        self.soil_db_path = self.export_dir / "Soil_DB.xlsx"
        self.gcp_handler = GCPHandler(self)
        self.model_creator = ModelCreator(self)
        self.full_data_importer = FullDataImporter(self)
        self.auth_manager = AuthManager(self)   
        self.ags_data_handler = AGSDataHandler(self) 
        self.create_ui_handler = UICreator(self)
        self.import_data_handler = ImportDataHandler(self)   
        self.user_profile = UserProfile(
            form_app=self,
            db_config=self.db_config,
            current_username=self.current_username,
            page=self.page,
            model_creator=self.model_creator
        )
        self.auth_handler = AuthServerHandlerSingleton()

        
        self.sections = {
            0: ProjectInfoSection(self.db_ops),
            1: GeometrySection(db_config).set_parent(self),
            2: BoreholeSection(self.db_ops,form_content=ft.Column(), form_manager=self.form_manager),  # Pass form_manager
            3: ExcavationSection(self.db_ops,db_config, self.form_manager, form_content=ft.Column()),  # Pass form_content
            4: SequenceConstructSection(db_config),  # Add new section

            }
        self.excavation_section = self.sections[3] 
        self.current_section = self.sections[0]
        self.form_content = ft.Column()
        self.rail = None
        self.prev_button = None
        self.next_button = None
        self.page = None
        self.form_values = {}  # Initialize form_values dictionary
        self.viewing_profile = False  # Track if user is viewing profile

        # Create file pickers

        self.open_csv_picker = None
        self.user_selected_save_path = None
        # Initialize the borehole section's material names
        borehole_section = self.sections[2]
        if isinstance(borehole_section, BoreholeSection):
            borehole_section.material_names = borehole_section.load_material_names()
    def mark_data_as_modified(self):
        """Mark that data has been modified after submission"""
        if self.submission_successful:
            self.data_modified_after_submission = True
            print("DEBUG: Data modified after submission - Submit button will show on last tab")
            
            # Update button visibility based on current tab
            current_index = self.rail.selected_index
            is_last_tab = current_index == len(self.sections) - 1
            
            if is_last_tab:
                # If currently on last tab, show submit button and hide create model
                self.next_button.visible = True
                self.next_button.text = "Submit"
                self.next_button.disabled = False
                self.create_model_button.visible = False
                self.create_model_button.disabled = True
                
                # Update UI
                self.next_button.update()
                self.create_model_button.update()
            # If not on last tab, don't change anything - submit will appear when they reach last tab
    
    def create_field_change_handler(self, control):
        """Create a change handler that marks data as modified"""
        original_on_change = control.on_change if hasattr(control, 'on_change') else None
        
        def combined_handler(e):
            # Mark data as modified
            self.mark_data_as_modified()
            # Call original handler if it exists
            if original_on_change:
                if asyncio.iscoroutinefunction(original_on_change):
                    asyncio.create_task(original_on_change(e))
                else:
                    original_on_change(e)
        
        return combined_handler
    
    def attach_change_handlers_to_controls(self, controls):
        """Recursively attach change handlers to all form controls"""
        for control in controls:
            # Handle TextField and Dropdown
            if isinstance(control, (ft.TextField, ft.Dropdown)):
                control.on_change = self.create_field_change_handler(control)
            
            # Handle containers recursively
            elif isinstance(control, ft.Container) and hasattr(control, 'content'):
                if isinstance(control.content, (ft.Column, ft.Row)):
                    self.attach_change_handlers_to_controls(control.content.controls)
            
            # Handle Row and Column
            elif isinstance(control, (ft.Row, ft.Column)) and hasattr(control, 'controls'):
                self.attach_change_handlers_to_controls(control.controls)
            
            # Handle DataTable
            elif isinstance(control, ft.DataTable):
                for row in control.rows:
                    for cell in row.cells:
                        cell_control = cell.content
                        if isinstance(cell_control, ft.Container):
                            cell_control = cell_control.content
                        if isinstance(cell_control, (ft.TextField, ft.Dropdown)):
                            cell_control.on_change = self.create_field_change_handler(cell_control)
    # Replace the old AGS functions with simple delegate methods
    async def handle_borehole_type_change(self, e):
        """Delegate to AGS data handler"""
        await self.ags_data_handler.handle_borehole_type_change(e)

    async def handle_ags_file_selection(self, e: ft.FilePickerResultEvent):
        """Delegate to AGS data handler"""
        await self.ags_data_handler.handle_ags_file_selection(e)

    def extract_borehole_ids_from_ags(self, ags_file_path):
        """Delegate to AGS data handler"""
        return self.ags_data_handler.extract_borehole_ids_from_ags(ags_file_path)

    def update_borehole_field_to_dropdown(self, borehole_options):
        """Delegate to AGS data handler"""
        self.ags_data_handler.update_borehole_field_to_dropdown(borehole_options)

    def update_borehole_field_to_text(self):
        """Delegate to AGS data handler"""
        self.ags_data_handler.update_borehole_field_to_text()

    def update_borehole_control_in_ui(self, borehole_options):
        """Delegate to AGS data handler"""
        self.ags_data_handler.update_borehole_control_in_ui(borehole_options)

    def handle_borehole_selection(self, e):
        """Delegate to AGS data handler"""
        self.ags_data_handler.handle_borehole_selection(e)

    def update_borehole_control_to_text(self):
        """Delegate to AGS data handler"""
        self.ags_data_handler.update_borehole_control_to_text()      
    def create_form_section(self, section: FormSection, set_number: Optional[int] = None) -> ft.Column:
      fields = section.get_fields()
      form_rows = []
    
      for i in range(0, len(fields), 2):
        row_fields = []
        for j in range(2):
            if i + j < len(fields):
                field = fields[i + j]
                control = field.create_control(
                    width=300,
                    set_number=set_number,
                    on_change=None
                )
                
                # Add special handlers for specific fields
                if field.label == "Borehole Type":
                    control.on_change = self.handle_borehole_type_change
                
                # Store field data attribute for easier identification later
                control.data = field.label
                
                row_fields.append(control)
        
        form_rows.append(
            ft.Row(
                row_fields,
                alignment=ft.MainAxisAlignment.START,
                spacing=20
            )
        )
    
      return ft.Column(form_rows, spacing=20)

    def _handle_save_click(self, e):
        """Synchronous handler that properly schedules the async operation"""
        asyncio.run_coroutine_threadsafe(
            self.gcp_handler.save_gcp_handler(e),
            self.page.loop
        )
    
    def _handle_open_click(self, e):
        """Synchronous handler that properly schedules the async operation"""
        asyncio.run_coroutine_threadsafe(
            self.gcp_handler.open_gcp_handler(e),
            self.page.loop
        )
    async def handle_create_model_click(self, e):
      if not self.auth_manager.ensure_authenticated():
        print("User is not authenticated. Cannot create model.")
        return
      await self.model_creator.on_create_model(e)
    def close_dialog(self):
      """Close the currently open dialog"""
      if hasattr(self, 'page') and self.page and self.page.dialog:
        self.page.dialog.open = False
        self.page.update()
    
    def enable_next_tab(self):
        """Enable the next tab in sequence"""
        current_index = self.rail.selected_index
        if current_index < len(self.rail.destinations) - 1:
            self.rail.destinations[current_index + 1].disabled = False
            self.rail.update()
    
    async def on_previous(self, e):
      """Handle Previous button click"""
      if not self.auth_manager.ensure_authenticated():
        print("DEBUG: User not authenticated, cannot navigate")
        return
        
      current_index = self.rail.selected_index
      if self.viewing_profile:
        # Handle back from profile view
        self.viewing_profile = False
        self.rail.selected_index = self.pre_profile_section
        self.current_section = self.sections[self.pre_profile_section]
        self.update_form_content(self.pre_profile_section)
        self.prev_button.visible = self.pre_profile_section > 0
        self.prev_button.update()
        return
    
      if current_index > 0:
        # Store current section's data
        current_section_name = self.rail.destinations[current_index].label.lower()
        current_data = self.collect_form_data()
        if current_data:
            # ✅ FIX: Store in BOTH section_data AND form_manager
            self.section_data[current_section_name] = current_data
            
            # ✅ CRITICAL: Also store in form_manager so it persists
            normalized_name = self.normalize_section_name(current_section_name)
            self.form_manager.store_section_data(normalized_name, current_data)
            print(f"DEBUG: Stored {current_section_name} data in form_manager: {current_data}")

        # Navigate to the previous tab
        self.rail.selected_index = current_index - 1
        self.current_section = self.sections[current_index - 1]

        # Load stored data for the previous section
        previous_section_name = self.rail.destinations[current_index - 1].label.lower()
        stored_data = self.section_data.get(previous_section_name, {})
        self.update_form_content(current_index - 1, stored_data)

        # Update button visibility
        self.prev_button.visible = current_index - 1 > 0
        self.prev_button.update()
        self.rail.update()
        self.form_content.update()
        
    def setup_page(self):
        self.page.title = "GeoCoPilot"
        self.page.padding = 0
        self.page.spacing = 0
        self.page.window_width = 1000
        self.page.window_height = 800
        self.page.window_resizable = True
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.update()
    def handle_sign_in(self, username: str):  # Modify this method
        """Handle successful sign in"""
        self.is_signed_in = True
        self.current_username = username
        self.page.controls.clear()
        self.create_ui_handler.create_ui()
        self.page.update()
    def initialize(self, page: ft.Page):
        self.page = page
        self.setup_page()
        self.gcp_handler.initialize_file_pickers()
        
        self.file_picker = self.import_data_handler.get_file_picker()
        self.ags_file_picker = ft.FilePicker(on_result=self.handle_ags_file_selection)
        page.overlay.extend([
            self.file_picker,
            self.ags_file_picker,
        ])
        self.sign_in_page = LoginScreen(self.db_config, self.handle_sign_in)
        page.add(self.sign_in_page.create_ui())
        page.update()
    

    def collect_section_data(self, section_index):
      """Collect data from the current section for storage and UI updates."""
      self.current_section = self.sections[section_index]
      return self.collect_form_data()
    def has_geometry_changed_for_excavation(self, current_geometry: Dict) -> Tuple[bool, List[int]]:

      if not hasattr(self, '_last_excavation_geometry'):
        self._last_excavation_geometry = None
    
      if not current_geometry:
        return False, []
    
      # Extract relevant fields
      relevant_fields = [
        'No of Strut',
        'Wall Top Level', 
        'Excavation Depth',
        'Excavation Below Strut',
        'Over Excavation'
    ]
    
      n_struts = int(current_geometry.get('No of Strut', 0))
      for i in range(1, n_struts + 1):
        relevant_fields.append(f'Strut {i} Level')
    
      current_relevant = {k: current_geometry.get(k) for k in relevant_fields}
    
      if self._last_excavation_geometry is None:
        self._last_excavation_geometry = current_relevant.copy()
        return False, []
    
    # Check WHICH struts changed
      affected_struts = []
      for i in range(1, n_struts + 1):
        strut_key = f'Strut {i} Level'
        if current_relevant.get(strut_key) != self._last_excavation_geometry.get(strut_key):
            affected_struts.append(i)
            print(f"DEBUG: Strut {i} level changed from {self._last_excavation_geometry.get(strut_key)} to {current_relevant.get(strut_key)}")
    
    # Check if other critical fields changed
      critical_changed = any(
        current_relevant.get(field) != self._last_excavation_geometry.get(field)
        for field in ['No of Strut', 'Wall Top Level', 'Excavation Depth']
      )
    
      if affected_struts or critical_changed:
        self._last_excavation_geometry = current_relevant.copy()
        return True, affected_struts
    
      return False, []
    def update_form_content(self, tab_index: int, stored_data: Dict = None):
        self.geological_import_button.visible = False
        self.geometry_import_button.visible = False
        self.borehole_import_button.visible = False
        self.excavation_import_button.visible = False
        self.sequence_import_button.visible = False

        if tab_index == 4:  
          geometry_data = self.form_manager.get_section_data('geometry')
          excavation_data = self.form_manager.get_section_data('excavation')

          if not geometry_data:
            self.show_error_dialog(["Please complete Geometry section first!"])
            self.rail.selected_index = 1  
            self.rail.update()
            return

          if not excavation_data:
            self.show_error_dialog(["Please complete Excavation section first!"])
            self.rail.selected_index = 3  
            self.rail.update()
            return

        if tab_index == 0:
            self.geological_import_button.visible = True
        elif tab_index == 1:  
          self.geometry_import_button.visible = True
          try:
                self.export_dir.mkdir(parents=True, exist_ok=True)
                self.db_ops.ensure_input_data_sheets(str(self.input_data_path))
          except Exception as e:
                print(f"Error creating Excel sheets: {e}")
        elif tab_index == 2:
            self.borehole_import_button.visible = True
            has_pending_data = hasattr(self, 'pending_geology_data') and self.pending_geology_data
            
            if has_pending_data:
                print(f"Processing {len(self.pending_geology_data)} pending geology layers")
        
                # Process all pending geology data
                for layer_data in self.pending_geology_data:
                    print(f"Processing layer: {layer_data}")
                    
                    asyncio.create_task(self.current_section.populate_from_ags_data(layer_data))
        
                # Clear the pending data after processing
                self.pending_geology_data = []
                
            # Only fetch stored data if we're not processing pending data
            if not has_pending_data:
                # Fetch the stored borehole data explicitly
                section_name = self.rail.destinations[tab_index].label.lower()
                stored_data = self.form_manager.get_section_data(section_name) or {}
                # Only clear the table if there's no stored data
                if not stored_data:
                  # Use the borehole section's method to check for data instead of direct access
                  if not self.current_section.has_data_in_table():
                    if hasattr(self.current_section, 'data_table') and self.current_section.data_table:
                      self.current_section.data_table.rows.clear()
            self.form_content.update()
        elif tab_index == 3:  # Excavation section
            self.excavation_import_button.visible = True
            self.current_section.page = self.page

            if not hasattr(self.current_section, 'user_modified'):
                self.current_section.user_modified = False

            fields = self.current_section.get_fields()
            headers = [
                ft.DataColumn(ft.Text("Actions", size=16, weight=ft.FontWeight.BOLD))
            ]
            for field in fields[:4]:
                header = ft.DataColumn(
                    ft.Text(field.label, size=16, weight=ft.FontWeight.BOLD)
                )
                headers.append(header)
        
            if not hasattr(self.current_section, 'data_table') or not self.current_section.data_table:
                self.current_section.data_table = ft.DataTable(
                    columns=headers,
                    rows=[],
                    border=ft.border.all(2, ft.colors.GREY_400),
                    border_radius=10,
                    divider_thickness=2,
                    heading_row_height=50,
                    data_row_min_height=80,
                    data_row_max_height=80,
                    column_spacing=20,
                    width=max(1000, 120 * len(headers)),
                )
        
            # ✅ Get current geometry data
            current_geometry_data = self.form_manager.get_section_data('geometry')
            
            # ✅ Check if geometry has changed and which struts were affected
            geometry_changed, affected_struts = self.has_geometry_changed_for_excavation(current_geometry_data)
            
            # ✅ Get stored excavation data
            stored_excavation_data = self.form_manager.get_section_data('excavation')
            
            print(f"DEBUG: Excavation tab - geometry_changed={geometry_changed}, affected_struts={affected_struts}")
            print(f"DEBUG: Stored excavation data: {stored_excavation_data}")
            
            # ✅ SCENARIO 1: Geometry changed AND we have existing data
            if geometry_changed and stored_excavation_data and len(stored_excavation_data) > 0:
                print(f"DEBUG: Loading {len(stored_excavation_data)} stored stages and applying geometry updates")
                self.current_section.data_table.rows.clear()
                
                # Load existing data into table
                for stage_data in stored_excavation_data:
                    stage_number = int(stage_data.get('Stage No', '1'))
                    row = self.current_section.create_excavation_set(
                        stage_number, 
                        stage_data.get('From'),
                        initial_data=stage_data
                    )
                    self.current_section.data_table.rows.append(row)
                
                self.current_section.visible_sets = len(stored_excavation_data)
                self.current_section.initial_row_added = True
                
                # ✅ NOW apply selective updates
                if affected_struts:
                    all_affected_stages = []
                    for strut_num in affected_struts:
                        stages = self.current_section.get_affected_stages_by_strut_change(
                            strut_num, current_geometry_data
                        )
                        all_affected_stages.extend(stages)
                    
                    # Remove duplicates and sort
                    all_affected_stages = sorted(list(set(all_affected_stages)))
                    
                    print(f"DEBUG: Will update stages: {all_affected_stages}")
                    
                    # Update only these stages
                    self.current_section.update_specific_stages(
                        all_affected_stages, 
                        current_geometry_data
                    )
                    
                    # ✅ CRITICAL: Collect the UPDATED data and save it back
                    updated_excavation_data = self.collect_form_data()
                    if updated_excavation_data:
                        self.form_manager.store_section_data('excavation', updated_excavation_data)
                        print(f"DEBUG: Saved updated excavation data after geometry changes: {updated_excavation_data}")
                    
                    # Mark as user modified to preserve these changes
                    self.current_section.user_modified = True
                    
                    print(f"DEBUG: Completed selective update of stages {all_affected_stages}")
            
            # ✅ SCENARIO 2: No geometry changes - use stored data as-is
            elif not geometry_changed and stored_excavation_data and len(stored_excavation_data) > 0:
                print(f"DEBUG: Using stored excavation data (no changes) - {len(stored_excavation_data)} stages")
                self.current_section.data_table.rows.clear()
                
                for stage_data in stored_excavation_data:
                    stage_number = int(stage_data.get('Stage No', '1'))
                    row = self.current_section.create_excavation_set(
                        stage_number, 
                        stage_data.get('From'),
                        initial_data=stage_data
                    )
                    self.current_section.data_table.rows.append(row)
                
                self.current_section.visible_sets = len(stored_excavation_data)
                self.current_section.initial_row_added = True
                self.current_section.user_modified = True
                
                print("DEBUG: Loaded stored excavation data without changes")
            
            # ✅ SCENARIO 3: No stored data - generate from geometry
            elif current_geometry_data:
                print("DEBUG: No stored data - generating excavation stages from geometry")
                
                try:
                    n_struts = int(current_geometry_data.get('No of Strut', 0))
                    wall_top_level = float(current_geometry_data.get('Wall Top Level', 0))
            
                    print(f"DEBUG: Generating excavation stages: {n_struts} struts, wall_top_level: {wall_top_level}")
                    
                    self.current_section.data_table.rows.clear()
                    
                    current_from = wall_top_level
                    for stage_no in range(1, n_struts + 1):
                        calculated_to = self.current_section.calculate_to_value(stage_no)
                        row = self.current_section.create_excavation_set(
                            stage_no, 
                            str(current_from),
                            initial_data=None
                        )
                        self.current_section.data_table.rows.append(row)
                        current_from = calculated_to
        
                    # Final stage
                    final_stage_no = n_struts + 1
                    calculated_final_to = self.current_section.calculate_to_value(final_stage_no)
                    row = self.current_section.create_excavation_set(
                        final_stage_no, 
                        str(current_from),
                        initial_data=None
                    )
                    self.current_section.data_table.rows.append(row)
                    
                    self.current_section.visible_sets = n_struts + 1
                    self.current_section.initial_row_added = True
                    self.current_section.user_modified = False
                            
                    print("DEBUG: Finished generating excavation stages from geometry")
                    
                except Exception as e:
                    print(f"DEBUG: Error generating excavation stages: {e}")
                    if not self.current_section.initial_row_added:
                        initial_row = self.current_section.create_excavation_set(1, None)
                        self.current_section.data_table.rows.append(initial_row)
                        self.current_section.visible_sets = 1
                        self.current_section.initial_row_added = True
            else:
                # No data at all - create default
                if not self.current_section.initial_row_added:
                    print("DEBUG: Adding default initial row to table")
                    initial_row = self.current_section.create_excavation_set(1, None)
                    self.current_section.data_table.rows.append(initial_row)
                    self.current_section.visible_sets = 1
                    self.current_section.initial_row_added = True
                         
        elif tab_index == 4:
            self.sequence_import_button.visible = True

        self.import_buttons_row.update()
        self.current_section = self.sections[tab_index]
        self.form_content.controls.clear()

        section_name = self.rail.destinations[tab_index].label.lower()
        stored_data = self.section_data.get(section_name, {})

        if isinstance(self.current_section, ExcavationSection):
            print("DEBUG: Updating excavation section form content")
            self.current_section.page = self.page
    
            # Initialize user_modified flag if not exists
            if not hasattr(self.current_section, 'user_modified'):
                self.current_section.user_modified = False

            fields = self.current_section.get_fields()
            headers = [
                ft.DataColumn(ft.Text("Actions", size=16, weight=ft.FontWeight.BOLD))
            ]
            for field in fields[:4]:
                header = ft.DataColumn(
                    ft.Text(field.label, size=16, weight=ft.FontWeight.BOLD)
                )
                headers.append(header)
        
            if not hasattr(self.current_section, 'data_table') or not self.current_section.data_table:
                self.current_section.data_table = ft.DataTable(
                    columns=headers,
                    rows=[],
                    border=ft.border.all(2, ft.colors.GREY_400),
                    border_radius=10,
                    divider_thickness=2,
                    heading_row_height=50,
                    data_row_min_height=80,
                    data_row_max_height=80,
                    column_spacing=20,
                    width=max(1000, 120 * len(headers)),
                )

            # ✅ FIX: ALWAYS get stored excavation data FIRST
            stored_excavation_data = self.form_manager.get_section_data('excavation')
            
            # ✅ FIX: Check if user has modified the data before
            has_user_modifications = (
                self.current_section.user_modified or 
                (stored_excavation_data and len(stored_excavation_data) > 0)
            )
            
            # ✅ FIX: If user has made modifications, ALWAYS use stored data - DO NOT recalculate
            if has_user_modifications and stored_excavation_data and len(stored_excavation_data) > 0:
                print(f"DEBUG: Using stored excavation data (user modified) - {len(stored_excavation_data)} stages")
                self.current_section.data_table.rows.clear()
                
                for stage_data in stored_excavation_data:
                    stage_number = int(stage_data.get('Stage No', '1'))
                    # ✅ CRITICAL: Pass stored data to preserve user changes
                    row = self.current_section.create_excavation_set(
                        stage_number, 
                        stage_data.get('From'),  # Use stored 'From' value
                        initial_data=stage_data  # ✅ Pass all stored data
                    )
                    self.current_section.data_table.rows.append(row)
                
                self.current_section.visible_sets = len(stored_excavation_data)
                self.current_section.initial_row_added = True
                self.current_section.user_modified = True  # Mark as modified
                
                print("DEBUG: Finished loading stored excavation data - USER MODIFICATIONS PRESERVED")
                
            else:
                # NO stored data OR user hasn't modified - generate from geometry
                geometry_data = self.form_manager.get_section_data('geometry')
                print(f"DEBUG: [Excavation] No user modifications - generating from geometry")
                
                if geometry_data:
                    try:
                        n_struts = int(geometry_data.get('No of Strut', 0))
                        wall_top_level = float(geometry_data.get('Wall Top Level', 0))
                
                        print(f"DEBUG: Generating excavation stages: {n_struts} struts")
                        
                        # Clear and regenerate
                        self.current_section.data_table.rows.clear()
                        
                        current_from = wall_top_level
                        for stage_no in range(1, n_struts + 1):
                            row = self.current_section.create_excavation_set(stage_no, current_from)
                            self.current_section.data_table.rows.append(row)
                            current_from = self.current_section.calculate_to_value(stage_no)

                        # Final stage
                        final_stage_no = n_struts + 1
                        row = self.current_section.create_excavation_set(final_stage_no, current_from)
                        self.current_section.data_table.rows.append(row)
                        
                        self.current_section.visible_sets = n_struts + 1
                        self.current_section.initial_row_added = True
                        self.current_section.user_modified = False
                                
                        print("DEBUG: Finished generating excavation stages from geometry")
                        
                    except Exception as e:
                        print(f"DEBUG: Error generating excavation stages: {e}")
                        if not self.current_section.initial_row_added:
                            initial_row = self.current_section.create_excavation_set(1, None)
                            self.current_section.data_table.rows.append(initial_row)
                            self.current_section.visible_sets = 1
                            self.current_section.initial_row_added = True
                else:
                    # No geometry data and no stored data - create default row
                    if not self.current_section.initial_row_added:
                        print("DEBUG: Adding default initial row to table")
                        initial_row = self.current_section.create_excavation_set(1, None)
                        self.current_section.data_table.rows.append(initial_row)
                        self.current_section.visible_sets = 1
                        self.current_section.initial_row_added = True
                    
            # Rest of the excavation section setup (buttons, containers, etc.)
            # Rest of the excavation section setup (buttons, containers, etc.)
            buttons_row = self.current_section.create_buttons_row()
            self.current_section.page = self.page
        
            scrollable_row = ft.Row(
                controls=[self.current_section.data_table],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )
        
            self.current_section.scrollable_row = scrollable_row
        
            table_container = ft.Container(
                content=ft.Column(
                    [scrollable_row],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                margin=ft.margin.only(top=20),
                expand=True,
                height=400,
            )
        
            self.current_section.table_container = table_container
            self.current_section.page = self.page
            self.current_section.form_content = self.form_content
            self.current_section.form_manager = self.form_manager
        
            self.form_content.controls.extend([
                ft.Container(content=buttons_row, margin=ft.margin.only(top=10, bottom=10)),
                table_container
            ])
            
            self.form_content.update()
        
            print("DEBUG: Finished updating excavation section form content")
        
        elif isinstance(self.current_section, SequenceConstructSection):
          print("DEBUG: Creating SequenceConstructSection table form")
          try:
            # ALWAYS get fresh geometry and excavation data - don't rely on stored_data
            geometry_data = self.form_manager.get_section_data('geometry')
            excavation_data = self.form_manager.get_section_data('excavation')
            print(f"DEBUG: [Sequence] Fresh Geometry data: {geometry_data}")
            print(f"DEBUG: [Sequence] Fresh Excavation data: {excavation_data}")

            # Check if geometry/excavation data has changed
            geometry_changed = self.current_section.has_geometry_changed(geometry_data or {}, excavation_data or [])
            
            # If geometry changed, force fresh calculation and ignore stored sequence data
            if geometry_changed:
                print("DEBUG: Geometry/excavation data changed - forcing fresh calculation")
                stored_data = None  # Ignore any stored sequence data
                self.current_section.force_recalculation()

            # CRITICAL: Always recalculate rows based on fresh data
            previous_data = {
                'geometry': geometry_data,
                'excavation': excavation_data
            }
            
            # Force recalculation of rows - this is key for auto-refresh
            print("DEBUG: Force recalculating sequence rows based on latest data...")
            self.current_section.calculate_rows_and_options(previous_data)
            num_rows = self.current_section.get_total_rows()
            print(f"DEBUG: Recalculated number of sequence rows: {num_rows}")

            # Check if we have imported data that should override defaults (only if geometry hasn't changed)
            use_stored_data = False
            if not geometry_changed and stored_data and isinstance(stored_data, dict):
                # Only use stored data if it's not empty and contains actual user modifications
                has_meaningful_data = any(
                    stored_data.get(field) and 
                    any(val for val in (stored_data[field] if isinstance(stored_data[field], list) else [stored_data[field]]))
                    for field in ['PhaseName', 'ElementType', 'ElementName', 'Action']
                )
                if has_meaningful_data:
                    use_stored_data = True
                    print(f"DEBUG: Using meaningful stored data: {stored_data}")
                else:
                    print("DEBUG: Stored data is empty or meaningless, using defaults")
            elif geometry_changed:
                print("DEBUG: Geometry changed - ignoring stored data and using fresh defaults")

            # Convert list data to dictionary format if needed
            if stored_data and isinstance(stored_data, list) and stored_data:
                print(f"DEBUG: Converting list data to dictionary format")
                converted_data = {}
                if stored_data:
                    keys = stored_data[0].keys()
                    for key in keys:
                        converted_data[key] = [item.get(key, "") for item in stored_data]
                    num_rows = max(num_rows, len(stored_data))
                    print(f"DEBUG: Adjusted rows to {num_rows} based on imported data")
                    stored_data = converted_data
                    use_stored_data = True and not geometry_changed

            # Create headers based on recalculated number of rows
            headers = [
                ft.DataColumn(
                    ft.Text("Field", weight=ft.FontWeight.BOLD, size=16)
                ),
                *[ft.DataColumn(
                    ft.Text(f"Row {i+1}", weight=ft.FontWeight.BOLD, size=16)
                ) for i in range(num_rows)]
            ]

            rows = []
            fields = self.current_section.get_fields(previous_data)

            # Store references to dropdowns for dynamic updates
            dropdown_refs = {}

            for field in fields:
                cells = [
                    ft.DataCell(
                        ft.Container(
                            content=ft.Text(field.label, weight=ft.FontWeight.BOLD),
                            width=100
                        )
                    )
                ]

                for row_num in range(num_rows):
                    # Initialize dropdown references for this row if not exists
                    if row_num not in dropdown_refs:
                        dropdown_refs[row_num] = {}
                    
                    # Get field value - prioritize stored data if meaningful, otherwise use defaults
                    field_value = None
                    
                    if use_stored_data and isinstance(stored_data, dict) and field.label in stored_data:
                        if isinstance(stored_data[field.label], list) and row_num < len(stored_data[field.label]):
                            field_value = stored_data[field.label][row_num]
                            print(f"DEBUG: Using stored value '{field_value}' for {field.label} at row {row_num}")
                    
                    # If no meaningful stored value, use fresh default based on recalculated configuration
                    if not field_value:
                        default_value = self.current_section.get_default_value_for_field(row_num, field.label)
                        if default_value:
                            field_value = default_value
                            print(f"DEBUG: Using fresh default value '{field_value}' for {field.label} at row {row_num}")

                    # Create input controls based on field type
                    if field.label == "PhaseNo":
                        input_control = ft.TextField(
                            value=field_value or str(row_num + 1),
                            width=100,
                            border=ft.InputBorder.UNDERLINE,
                            read_only=True,
                            disabled=True,
                            bgcolor=ft.colors.GREY_100,
                        )
                        
                    elif field.label == "PhaseName":
                        # Get all possible phase names based on fresh data
                        all_phase_options = self.current_section.get_filtered_field_options(field.label, row_num)
                        print(f"DEBUG: *** ROW {row_num} Phase Name OPTIONS (Fresh): {all_phase_options} ***")
                        
                        def create_phase_change_handler(current_row_num):
                            def on_phase_change(e):
                                selected_phase = e.control.value
                                print(f"DEBUG: *** Phase changed in row {current_row_num} to: {selected_phase} ***")
                                
                                # Update Element Type dropdown for this row
                                if current_row_num in dropdown_refs and 'element_type' in dropdown_refs[current_row_num]:
                                    element_type_options = self.current_section.get_filtered_field_options(
                                        'ElementType', current_row_num, selected_phase
                                    )
                                    element_type_dropdown = dropdown_refs[current_row_num]['element_type']
                                    element_type_dropdown.options = [ft.dropdown.Option(opt) for opt in element_type_options]
                                    element_type_dropdown.value = element_type_options[0] if element_type_options else None
                                    element_type_dropdown.disabled = len(element_type_options) == 0
                                    element_type_dropdown.update()
                                
                                # Update Element Name dropdown for this row
                                if current_row_num in dropdown_refs and 'element_name' in dropdown_refs[current_row_num]:
                                    element_name_options = self.current_section.get_filtered_field_options(
                                        'ElementName', current_row_num, selected_phase
                                    )
                                    element_name_dropdown = dropdown_refs[current_row_num]['element_name']
                                    element_name_dropdown.options = [ft.dropdown.Option(opt) for opt in element_name_options]
                                    element_name_dropdown.value = element_name_options[0] if element_name_options else None
                                    element_name_dropdown.disabled = len(element_name_options) == 0
                                    element_name_dropdown.update()
                                    
                                    # Confirm the phase selection to increment usage counter
                                    if element_type_options and element_name_options:
                                        actual_element_name = self.current_section.confirm_phase_selection(
                                            selected_phase, element_type_options[0]
                                        )
                                        if actual_element_name != element_name_options[0]:
                                            element_name_dropdown.value = actual_element_name
                                            element_name_dropdown.update()
                            
                            return on_phase_change

                        input_control = ft.Dropdown(
                            options=[ft.dropdown.Option(opt) for opt in all_phase_options],
                            width=100,
                            border=ft.InputBorder.UNDERLINE,
                            filled=True,
                            value=field_value,
                            on_change=create_phase_change_handler(row_num)
                        )
                        dropdown_refs[row_num]['phase_name'] = input_control
                        
                    elif field.label == "ElementType":
                        # Get element type options based on the selected/default phase
                        selected_phase = field_value if field.label == "PhaseName" else None
                        if not selected_phase and use_stored_data and 'PhaseName' in stored_data:
                            if isinstance(stored_data['PhaseName'], list) and row_num < len(stored_data['PhaseName']):
                                selected_phase = stored_data['PhaseName'][row_num]
                        
                        if not selected_phase:
                            # Use default phase from fresh configuration
                            default_phase = self.current_section.get_default_value_for_field(row_num, "PhaseName")
                            selected_phase = default_phase

                        element_type_options = self.current_section.get_filtered_field_options(
                            field.label, row_num, selected_phase
                        ) if selected_phase else []
                        
                        input_control = ft.Dropdown(
                            options=[ft.dropdown.Option(opt) for opt in element_type_options],
                            width=100,
                            border=ft.InputBorder.UNDERLINE,
                            filled=True,
                            value=field_value,
                            disabled=len(element_type_options) == 0
                        )
                        dropdown_refs[row_num]['element_type'] = input_control

                    elif field.label == "ElementName":
                        # Get element name options based on the selected/default phase
                        selected_phase = None
                        if use_stored_data and 'PhaseName' in stored_data:
                            if isinstance(stored_data['PhaseName'], list) and row_num < len(stored_data['PhaseName']):
                                selected_phase = stored_data['PhaseName'][row_num]
                        
                        if not selected_phase:
                            # Use default phase from fresh configuration
                            default_phase = self.current_section.get_default_value_for_field(row_num, "PhaseName")
                            selected_phase = default_phase

                        element_name_options = self.current_section.get_filtered_field_options(
                            field.label, row_num, selected_phase
                        ) if selected_phase else []

                        # Ensure field_value is in options, if not add it
                        if field_value and field_value not in element_name_options:
                            element_name_options.append(field_value)
                        
                        input_control = ft.Dropdown(
                            options=[ft.dropdown.Option(opt) for opt in element_name_options],
                            width=100,
                            border=ft.InputBorder.UNDERLINE,
                            filled=True,
                            value=field_value,
                            disabled=len(element_name_options) == 0
                        )
                        dropdown_refs[row_num]['element_name'] = input_control

                    elif field.field_type == "dropdown":
                        # Other dropdown fields (like Action)
                        row_specific_options = self.current_section.get_filtered_field_options(field.label, row_num)
                        
                        input_control = ft.Dropdown(
                            options=[ft.dropdown.Option(opt) for opt in row_specific_options],
                            width=100,
                            border=ft.InputBorder.UNDERLINE,
                            filled=True,
                            value=field_value
                        )
                    else:
                        input_control = ft.TextField(
                            width=100,
                            border=ft.InputBorder.UNDERLINE,
                            multiline=True,
                            min_lines=2,
                            value=field_value
                        )

                    cells.append(ft.DataCell(
                        ft.Container(
                            content=input_control,
                            padding=ft.padding.all(5),
                            width=150,
                            visible=True,
                            alignment=ft.alignment.center_left
                        )
                    ))

                rows.append(ft.DataRow(cells=cells))

            # Create the data table with fresh data
            data_table = ft.DataTable(
                columns=headers,
                rows=rows,
                border=ft.border.all(2, ft.colors.GREY_400),
                border_radius=10,
                divider_thickness=2,
                column_spacing=10,
                horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_400),
                heading_row_height=50,
                data_row_min_height=60,
                data_row_max_height=90,
                width=max(2000, 150 * (num_rows + 1)),
            )

            self.current_section.data_table = data_table

            scrollable_row = ft.Row(
                controls=[data_table],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            )

            table_container = ft.Container(
                content=ft.Column(
                    [scrollable_row],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
                margin=ft.margin.only(top=20),
                expand=True,
                height=500,
            )

            self.form_content.controls.extend([
                table_container
            ])

            self.form_content.update()
            print("DEBUG: Successfully refreshed sequence construct section with latest data")
            
            # CRITICAL: Reset usage tracking after fresh data load
            if not use_stored_data:
                self.current_section.reset_phase_usage_tracking()
            
            # Trigger initial phase updates for default values
            if not use_stored_data:
                print("DEBUG: *** TRIGGERING INITIAL UPDATES FOR DEFAULT PHASE DATA ***")
                for row_idx in range(num_rows):
                    if row_idx in dropdown_refs and 'phase_name' in dropdown_refs[row_idx]:
                        default_phase = self.current_section.get_default_value_for_field(row_idx, "PhaseName")
                        if default_phase:
                            print(f"DEBUG: Setting up default phase '{default_phase}' for row {row_idx}")
                            
                            # Update Element Type
                            if 'element_type' in dropdown_refs[row_idx]:
                                element_type_options = self.current_section.get_filtered_field_options(
                                    'ElementType', row_idx, default_phase
                                )
                                element_type_dropdown = dropdown_refs[row_idx]['element_type']
                                element_type_dropdown.options = [ft.dropdown.Option(opt) for opt in element_type_options]
                                element_type_dropdown.disabled = len(element_type_options) == 0
                                element_type_dropdown.update()
                            
                            # Update Element Name
                            if 'element_name' in dropdown_refs[row_idx]:
                                element_name_options = self.current_section.get_filtered_field_options(
                                    'ElementName', row_idx, default_phase
                                )
                                element_name_dropdown = dropdown_refs[row_idx]['element_name']
                                element_name_dropdown.options = [ft.dropdown.Option(opt) for opt in element_name_options]
                                element_name_dropdown.disabled = len(element_name_options) == 0
                                element_name_dropdown.update()

          except Exception as ex:
            print(f"DEBUG: Error creating SequenceConstructSection table: {str(ex)}")
            import traceback
            traceback.print_exc() 
        elif isinstance(self.current_section, BoreholeSection):
          print("DEBUG: Updating borehole section form content")
          self.current_section.set_page_reference(self.page)
        
        # Get existing borehole data
          borehole_data = self.form_manager.get_section_data('borehole')
          print(f"DEBUG: Retrieved borehole data from form manager: {borehole_data}")

        # Create formation dropdown
          formation_dropdown = ft.Dropdown(
            label="Select Formation",
            options=[
                ft.dropdown.Option("Bukit Timah Granite"),
                ft.dropdown.Option("Jurong Formation"),
                ft.dropdown.Option("Kallang Formation"),
                ft.dropdown.Option("Old Alluvium"),
                ft.dropdown.Option("Others"),
            ],
            value=None,
            border=ft.InputBorder.UNDERLINE,
            filled=True,
            expand=True,
            label_style=ft.TextStyle(
                color=ft.colors.BLACK,
                size=16,
                weight=ft.FontWeight.W_300,
                decoration=ft.TextDecoration.UNDERLINE
            ),
            on_change=self.current_section.on_formation_change
        )

        # Create soil DB button
          soil_db_button = ft.ElevatedButton(
            text="Select Soil DB",
            icon=ft.icons.STORAGE,
            on_click=self.current_section.open_soil_db_popup,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.PURPLE_600,
                padding=10,
            ),
            tooltip="Load soil properties from Soil Database"
        )

        # Create data table headers
          fields = self.current_section.get_fields()
          headers = [ft.DataColumn(ft.Text("Actions", size=16, weight=ft.FontWeight.BOLD))]
          for field in fields:
            headers.append(ft.DataColumn(
                ft.Text(field.label, size=16, weight=ft.FontWeight.BOLD)
            ))

        # Create data table
          data_table = ft.DataTable(
            columns=headers,
            rows=[],
            border=ft.border.all(2, ft.colors.GREY_400),
            border_radius=10,
            divider_thickness=2,
            heading_row_height=50,
            data_row_min_height=80,
            data_row_max_height=80,
            column_spacing=8,
            width=max(900, 90 * len(headers)),
        )

          self.current_section.data_table = data_table

        # Check for pending geology data
          has_pending_geology = tab_index == 2 and hasattr(self, 'pending_geology_data') and self.pending_geology_data

        # Populate table with data
          if borehole_data:
            print(f"DEBUG: Adding stored borehole data to table: {borehole_data}")
            self.current_section.data_table.rows.clear()
            self.current_section.current_material_index = 0
            
            for idx, material_data in enumerate(borehole_data):
                material_index = self.current_section.current_material_index
                material_name = None
                
                if 'Material' in material_data and material_data['Material']:
                    material_name = material_data['Material']
                elif material_index < len(self.current_section.material_names):
                    material_name = self.current_section.material_names[material_index]

                if material_name:
                    row = self.current_section.create_borehole_row(
                        material_name,
                        material_data,
                        row_index=idx
                    )
                    data_table.rows.append(row)
                    self.current_section.current_material_index += 1
                    
            self.current_section.visible_sets = len(borehole_data)
            
          elif stored_data:
            print(f"DEBUG: Using passed stored_data for table: {stored_data}")
            self.current_section.data_table.rows.clear()
            self.current_section.current_material_index = 0
            
            for idx, material_data in enumerate(stored_data):
                material_index = self.current_section.current_material_index
                if material_index < len(self.current_section.material_names):
                    material_name = self.current_section.material_names[material_index]
                    row = self.current_section.create_borehole_row(
                        material_name,
                        material_data,
                        row_index=idx
                    )
                    data_table.rows.append(row)
                    self.current_section.current_material_index += 1
                    
            self.current_section.visible_sets = len(stored_data)
            
          elif not has_pending_geology:
            # FIXED: Use safer method to determine if initial row should be added
            if self.current_section.should_add_initial_row(stored_data):
                print("DEBUG: Adding initial row to table")
                if self.current_section.material_names:
                    material_name = self.current_section.material_names[0]
                    initial_row = self.current_section.create_borehole_row(
                        material_name,
                        row_index=0
                    )
                    data_table.rows.append(initial_row)
                    self.current_section.visible_sets = 1
                    self.current_section.current_material_index = 1

        # Create scrollable container for the table
          scrollable_row = ft.Row(
            controls=[data_table],
            scroll=ft.ScrollMode.AUTO,
            expand=True,
          )
          self.current_section.scrollable_row = scrollable_row

          table_container = ft.Container(
            content=ft.Column(
                [scrollable_row],
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            margin=ft.margin.only(top=10),
            expand=True,
            height=350,
        )
          self.current_section.table_container = table_container

        # Create action buttons
          add_button = ft.ElevatedButton(
            text="Insert",
            icon=ft.icons.ADD,
            on_click=self.current_section.add_borehole_set,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_600,
                padding=10,
            )
        )

          current_row_count = len(self.current_section.data_table.rows) if self.current_section.data_table.rows else 0
          delete_button = ft.ElevatedButton(
            text="Delete",
            icon=ft.icons.DELETE,
            on_click=self.current_section.delete_last_row,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.RED_600,
                padding=10,
            ),
            disabled=current_row_count <= 1
        )

          self.current_section.delete_button = delete_button

          buttons_row = ft.Row(
            controls=[add_button, delete_button],
            spacing=20
          )

        # Update form content
          self.current_section.form_content = self.form_content
          self.form_content.controls.extend([
            ft.Container(content=formation_dropdown, margin=ft.margin.only(bottom=10)),
            ft.Container(content=soil_db_button, margin=ft.margin.only(bottom=10)),
            ft.Container(content=buttons_row, margin=ft.margin.only(bottom=10)),
            table_container
          ])

          print("DEBUG: Finished updating borehole section form content")  
        elif isinstance(self.current_section, GeometrySection):
            print("DEBUG: Updating geometry section form content")
            all_fields = self.current_section.get_fields()
    
    # Initialize form_values if not exists
            if not hasattr(self.current_section, 'form_values'):
                self.current_section.form_values = {}
    
            if stored_data:
                print(f"DEBUG: Found stored geometry data: {stored_data}")
                self.current_section.form_values = stored_data.copy()
        
                # ✅ CRITICAL FIX: Handle Wall Type restoration FIRST
                wall_type = stored_data.get("Wall Type")
                if wall_type:
                    print(f"DEBUG: Restoring Wall Type: {wall_type}")
                    # Trigger wall type change to regenerate correct fields
                    self.current_section.form_values["Wall Type"] = wall_type
                    
                # Handle number of struts restoration
                num_struts = stored_data.get("No of Strut", 0)
                if num_struts and isinstance(num_struts, (int, str)):
                    try:
                        self.current_section.current_num_struts = int(num_struts)
                        print(f"DEBUG: Restored num_struts to: {self.current_section.current_num_struts}")
                    except (ValueError, TypeError):
                        self.current_section.current_num_struts = 0
                
                # Handle strut type restoration
                strut_type = stored_data.get("Strut Type")
                if strut_type:
                    self.current_section.form_values["Strut Type"] = strut_type
                    
                # Restore individual strut data
                for i in range(1, self.current_section.current_num_struts + 1):
                    strut_level_key = f"Strut {i} Level"
                    strut_material_key = f"Strut {i} Material"
                    strut_member_size_key = f"Strut {i} Member Size"
                    strut_ea_key = f"Strut {i} EA"
                    strut_stiffness_key = f"Strut {i} Stiffness"
                    strut_space_key = f"Strut {i} Space"
                    strut_length_key = f"Strut {i} Length"
                    strut_angle_key = f"Strut {i} Angle"
                    
                    if strut_level_key in stored_data:
                        self.current_section.form_values[strut_level_key] = stored_data[strut_level_key]
                    if strut_material_key in stored_data:
                        self.current_section.form_values[strut_material_key] = stored_data[strut_material_key]
                    if strut_member_size_key in stored_data:
                        self.current_section.form_values[strut_member_size_key] = stored_data[strut_member_size_key]
                    if strut_ea_key in stored_data:
                        self.current_section.form_values[strut_ea_key] = stored_data[strut_ea_key]
                    if strut_stiffness_key in stored_data:
                        self.current_section.form_values[strut_stiffness_key] = stored_data[strut_stiffness_key]
                    if strut_space_key in stored_data:
                        self.current_section.form_values[strut_space_key] = stored_data[strut_space_key]
                    if strut_length_key in stored_data:
                        self.current_section.form_values[strut_length_key] = stored_data[strut_length_key]
                    if strut_angle_key in stored_data:
                        self.current_section.form_values[strut_angle_key] = stored_data[strut_angle_key]
                        
                # ✅ NEW: Restore ALL wall-specific fields based on wall type
                if wall_type == "Steel Pipe":
                    for field_name in ["Diameter", "Spacing", "Pipe Type", "Grade"]:
                        if field_name in stored_data:
                            self.current_section.form_values[field_name] = stored_data[field_name]
                            print(f"DEBUG: Restored {field_name}: {stored_data[field_name]}")
                elif wall_type in ["Sheet Pile", "Soldier Pile"]:
                    for field_name in ["Material", "Member Size", "Spacing", "Connection Type", "Grade", "Shape", "Width", "Depth", "Diameter"]:
                        if field_name in stored_data:
                            self.current_section.form_values[field_name] = stored_data[field_name]
                            print(f"DEBUG: Restored {field_name}: {stored_data[field_name]}")
                elif wall_type in ["Contiguous Bored Pile", "Secant Bored Pile"]:
                    for field_name in ["Material", "Grade", "Diameter", "Spacing"]:
                        if field_name in stored_data:
                            self.current_section.form_values[field_name] = stored_data[field_name]
                            print(f"DEBUG: Restored {field_name}: {stored_data[field_name]}")
                elif wall_type == "Diaphragm Wall":
                    for field_name in ["Material", "Grade", "Thickness"]:
                        if field_name in stored_data:
                            self.current_section.form_values[field_name] = stored_data[field_name]
                            print(f"DEBUG: Restored {field_name}: {stored_data[field_name]}")
            else:
                # Reset to default state if no stored data
                if not hasattr(self.current_section, 'current_num_struts'):
                    self.current_section.current_num_struts = 0
            
            # ✅ CRITICAL: Regenerate fields AFTER restoring all form_values
            # This ensures get_fields() returns the correct wall-specific fields
            all_fields = self.current_section.get_fields()
            
            # Create frames with the restored data
            frames = self.current_section._create_geometry_frames(all_fields, stored_data)
            print(f"DEBUG: Created {len(frames)} geometry frames with wall type: {self.current_section.form_values.get('Wall Type')}")
            self.form_content.controls.extend(frames)
        else:

            form_section = self.create_form_section(self.current_section)
            if stored_data:
                self._populate_form_fields(form_section, stored_data)
            self.form_content.controls.extend(form_section.controls)

        is_first_tab = tab_index == 0
        is_last_tab = tab_index == len(self.sections) - 1
        self.prev_button.visible = not is_first_tab

        if is_last_tab:
            # Check if data was modified after submission
            if self.submission_successful and self.data_modified_after_submission:
                # Show submit button to allow re-submission
                self.next_button.visible = True
                self.next_button.text = "Submit"
                self.next_button.disabled = False
                self.create_model_button.visible = False
                self.create_model_button.disabled = True
            elif self.submission_successful and not self.data_modified_after_submission:
                # Show create model button (no modifications made)
                self.next_button.visible = False
                self.next_button.disabled = True
                self.create_model_button.visible = True
                self.create_model_button.disabled = False
            else:
                # Not yet submitted - show submit button
                self.next_button.visible = True
                self.next_button.text = "Submit"
                self.next_button.disabled = False
                self.create_model_button.visible = False
        else:
            # Not on last tab - always show "Next" button
            self.next_button.visible = True
            self.next_button.text = "Next"
            self.next_button.disabled = False
            self.create_model_button.visible = False

        self.prev_button.update()
        self.next_button.update()
        self.create_model_button.update()
        self.form_content.update()
        
        # CRITICAL: Attach change handlers AFTER all controls are created and updated
        # This must be the LAST operation in this method
        if self.submission_successful:
            print("DEBUG: Attaching change handlers to detect modifications")
            self.attach_change_handlers_to_controls(self.form_content.controls)
    def show_user_profile(self):
      if not self.auth_manager.ensure_authenticated():
        print("DEBUG: User not authenticated, cannot show profile")
        return
      self.viewing_profile = True
      self.user_profile.show_user_profile()
    # Store current section before showing profile
      self.pre_profile_section = self.rail.selected_index 

    def show_signout(self):
      if not self.auth_manager.ensure_authenticated():
        print("DEBUG: User not authenticated, cannot show profile")
        return
      try:
        self.user_profile.show_signout_confirmation()
        print("DEBUG: Signout confirmation dialog shown")
      except Exception as ex:
        print(f"DEBUG: Error showing signout confirmation dialog: {ex}")

# Add this new method to handle token refresh in UI context
    async def refresh_authentication(self):
      """
      Method to handle authentication refresh in async UI contexts
      """
      if self.auth_manager.attempt_token_refresh():
        print("Authentication refreshed successfully")
        return True
      else:
        print("Authentication refresh failed, redirecting to login")
        self.auth_manager.redirect_to_login()
        return False
    def reset_to_login(self):
      """Reset the application to login state"""
    # Clear all stored data
      self.section_data.clear()
      self.form_manager.clear_all_data()
    
    # Reset application state
      self.is_signed_in = False
      self.current_username = None
      self.submission_successful = False
    
    # Clear page controls and recreate login screen
      self.page.controls.clear()
      self.sign_in_page = LoginScreen(self.db_config, self.handle_sign_in)
      self.page.add(self.sign_in_page.create_ui())
    
    # Force page update
      self.page.update()
      print("DEBUG: Application reset to login screen")
    # In FormApp class
    def hide_import_buttons(self):
      """Hide all import buttons"""
      self.geological_import_button.visible = False
      self.prev_button.visible = False
      self.next_button.visible = False
      self.geometry_import_button.visible = False
      self.borehole_import_button.visible = False
      self.excavation_import_button.visible = False
      self.sequence_import_button.visible = False
      self.create_model_button.visible = False
      self.create_model_button.update()
      self.import_buttons_row.update()
      self.next_button.update()
    async def show_edit_configuration(self, e):
      self.toggle_edit_form(True)
    
    def _calculate_sequence_rows(self, geometry_data: Dict, excavation_data: List) -> int:
      """Calculate the number of sequence rows based on wall type and other parameters"""
      try:
        if not geometry_data or not excavation_data:
            return 2  # Default fallback
        
        wall_type = geometry_data.get('Excavation Type', '')
        num_struts = int(geometry_data.get('No of Strut', 0))
        num_stages = len(excavation_data)
        print(f"DEBUG: Calculating sequence rows for wall type {wall_type}, struts {num_struts}, stages {num_stages}")
        if wall_type == 'Single wall':
            return 2 + num_struts + num_stages + 1
        elif wall_type == 'Double wall':
            return 4 + num_struts + num_stages + 1
        else:
            return 2  # Default fallback
            
      except Exception as ex:
        print(f"Error calculating sequence rows: {ex}")
        return 2  # Default fallback
    
    async def on_tab_change(self, e):
      if not self.auth_manager.ensure_authenticated(): 
        print("DEBUG: User not authenticated, cannot change tab")
        return
        
      if e.control.destinations[e.control.selected_index].disabled:
        e.control.selected_index = self.rail.selected_index
        e.control.update()
        return
        
    # CRITICAL: Store current section data before switching tabs
      current_index = self.rail.selected_index
      current_section_name = self.rail.destinations[current_index].label.lower()
      current_data = self.collect_form_data()
    
      if current_data:
        print(f"DEBUG: Storing data for section '{current_section_name}': {current_data}")
        self.section_data[current_section_name] = current_data
        normalized_name = self.normalize_section_name(current_section_name)
        self.form_manager.store_section_data(normalized_name, current_data)  # ✅ This saves your changes

    # CRITICAL: If coming from geometry tab, clear dependent sections' stored data
    # This ensures excavation and sequence tabs will regenerate based on new geometry data
      if current_section_name == 'geometry':
        print("DEBUG: Coming from geometry tab - clearing dependent sections")
        # Clear excavation and sequence stored data so they regenerate
        if 'excavation' in self.section_data:
            del self.section_data['excavation']
        if 'sequence construct' in self.section_data:
            del self.section_data['sequence construct']
        # Also clear from form manager
        self.form_manager.clear_section_data('excavation')
        self.form_manager.clear_section_data('sequence_construct')
        
        # IMPORTANT: Force sequence section to recalculate on next visit
        if isinstance(self.sections.get(4), SequenceConstructSection):
            self.sections[4].force_recalculation()
            print("DEBUG: Forced sequence section recalculation")

      if e.control.selected_index != len(self.sections) - 1:
        self.submission_successful = False
    
      self.current_section = self.sections[e.control.selected_index]
      self.update_form_content(e.control.selected_index)
    def get_space_value_from_ui(self, strut_num):
      """Directly read Space value from UI control as fallback"""
      space_field_name = f"Strut {strut_num} Space"
    
    # Try to find the control recursively
      control = self.find_field_control_recursive(space_field_name)
      if control and hasattr(control, 'value'):
        value = control.value
        print(f"DEBUG: *** DIRECT UI READ - {space_field_name}: {value} ***")
        return value
    
      print(f"DEBUG: *** Could not find UI control for {space_field_name} ***")
      return None    
    def collect_form_data(self) -> Dict:
      try:
       """Collect form data based on the current section"""
       if isinstance(self.current_section, BoreholeSection):
        borehole_data = []
        data_table = self.current_section.data_table

        print("DEBUG: Collecting borehole data from scrollable table")
        
        if data_table and data_table.rows:
            for row in data_table.rows:
                row_data = {}
                for cell in row.cells:
                    # Extract control from cell content (which might be inside a container)
                    control = cell.content
                    if isinstance(control, ft.Container) and hasattr(control, 'content'):
                        control = control.content
                    
                    if isinstance(control, (ft.TextField, ft.Dropdown)) and hasattr(control, 'label'):
                        label = control.label.split(" (Set")[0].split(" *")[0]
                        row_data[label] = control.value
                        
                if row_data:
                    borehole_data.append(row_data)
                    print(f"DEBUG: Collected borehole row data: {row_data}")
                    
        return borehole_data if borehole_data else None

       elif isinstance(self.current_section, ExcavationSection):
        excavation_data = []
        data_table = self.current_section.data_table

        print("DEBUG: Collecting excavation data from scrollable table")

        if data_table and data_table.rows:
            for row in data_table.rows:
                stage_data = {}
                for cell in row.cells:
                    control = cell.content
                    if isinstance(control, ft.Container) and hasattr(control, 'content'):
                        control = control.content
                    
                    if isinstance(control, (ft.TextField, ft.Dropdown)) and hasattr(control, 'label'):
                        label = control.label.split(" (Set")[0].split(" *")[0]
                        stage_data[label] = control.value
                        
                if stage_data:
                    excavation_data.append(stage_data)
                    print(f"DEBUG: Collected excavation row data: {stage_data}")
                    
        return excavation_data if excavation_data else None
    
       elif isinstance(self.current_section, SequenceConstructSection):

            data = {
                "PhaseNo": [],
                "PhaseName": [],
                "ElementType": [],
                "ElementName": [],
                "Action": []
            }

            data_table = None

            print("DEBUG: Looking for sequence table in form controls")

            for control in self.form_content.controls:

                if isinstance(control, ft.Container):
                    print(f"DEBUG: Found container: {type(control.content)}")

                    if isinstance(control.content, ft.Column):
                        for row_control in control.content.controls:
                            if isinstance(row_control, ft.Row):
                                for row_item in row_control.controls:
                                    if isinstance(row_item, ft.DataTable):
                                        print("DEBUG: Found DataTable inside Row inside Column")
                                        data_table = row_item
                                        break

            if data_table:
                print(f"DEBUG: Found sequence data table with {len(data_table.rows)} rows")

                for row in data_table.rows:

                    if len(row.cells) > 0:
                        field_name = None

                        first_cell = row.cells[0]
                        if isinstance(first_cell.content, ft.Container) and hasattr(first_cell.content, 'content'):
                            if isinstance(first_cell.content.content, ft.Text):
                                field_name = first_cell.content.content.value

                        if field_name and field_name in data:
                            print(f"DEBUG: Processing row for field: {field_name}")

                            for i, cell in enumerate(row.cells[1:], 1):
                                value = None

                                if isinstance(cell.content, ft.Container) and hasattr(cell.content, 'content'):
                                    input_control = cell.content.content

                                    if isinstance(input_control, ft.TextField):
                                        value = input_control.value
                                    elif isinstance(input_control, ft.Dropdown):
                                        value = input_control.value

                                while len(data[field_name]) < i:
                                    data[field_name].append(None)

                                if i-1 < len(data[field_name]):
                                    data[field_name][i-1] = value
                                else:
                                    data[field_name].append(value)

            print(f"DEBUG: Data collected for storage: {data}")
            return data
       elif isinstance(self.current_section, GeometrySection):
           # FORCE CAPTURE OF ALL CURRENT UI VALUES BEFORE COLLECTION
           self.current_section.capture_all_ui_values()
           
           data = {}
           for field in self.current_section.get_fields():
               if field.label in ["No of Strut", "Strut Type"]:
                   continue  
               data[field.label] = self.current_section.form_values.get(field.label)
       
           if hasattr(self.current_section, 'current_num_struts'):
               for i in range(1, self.current_section.current_num_struts + 1):
                   data[f"Strut {i} Level"] = self.current_section.form_values.get(f"Strut {i} Level")
                   data[f"Strut {i} Material"] = self.current_section.form_values.get(f"Strut {i} Material")
                   data[f"Strut {i} Member Size"] = self.current_section.form_values.get(f"Strut {i} Member Size")  
                          
                   # Collect Space for each strut
                   space_value = self.current_section.form_values.get(f"Strut {i} Space")
                   if space_value is None:
                      space_value = self.get_space_value_from_ui(i)
                      if space_value is not None:
                          self.current_section.form_values[f"Strut {i} Space"] = space_value
       
                   print(f"DEBUG: *** Collecting Strut {i} Space: {space_value} ***")
                   data[f"Strut {i} Space"] = space_value
                   
                   # Collect Length and Angle for Fixed struts
                   current_strut_type = self.current_section.form_values.get("Strut Type")
                   if current_strut_type == "Fixed":
                       data[f"Strut {i} Length"] = self.current_section.form_values.get(f"Strut {i} Length")
                       data[f"Strut {i} Angle"] = self.current_section.form_values.get(f"Strut {i} Angle")
                       print(f"DEBUG: *** Collecting Fixed Strut {i} - Length: {data[f'Strut {i} Length']}, Angle: {data[f'Strut {i} Angle']} ***")
            
                   if data[f"Strut {i} Material"] == "Steel":
                       data[f"Strut {i} Member Size"] = self.current_section.form_values.get(f"Strut {i} Member Size")
                   elif data[f"Strut {i} Material"] == "Concrete":
                       data[f"Strut {i} EA"] = self.current_section.form_values.get(f"Strut {i} EA")
                       data[f"Strut {i} Stiffness"] = self.current_section.form_values.get(f"Strut {i} Stiffness")

           data["No of Strut"] = self.current_section.current_num_struts
           data["Strut Type"] = self.current_section.form_values.get("Strut Type")
       
    # ✅ ADD THIS: Collect line load data based on excavation type
           excavation_type = self.current_section.form_values.get("Excavation Type", "Single wall")
    
           if excavation_type == "Single wall":
               line_load_fields = [
                   "Distance from the wall",
                   "Length of the load",
                   "Magnitude of the load"
               ]
               for field in line_load_fields:
                   data[field] = self.current_section.form_values.get(field)
                   print(f"DEBUG: Collected {field} = {data[field]}")
                   
           elif excavation_type == "Double wall":
               line_load_fields = [
                   "Distance from the left wall",
                   "Length of the left load",
                   "Magnitude of the left load",
                   "Distance from the Right wall",
                   "Length of the Right load",
                   "Magnitude of the Right load"
               ]
               for field in line_load_fields:
                   data[field] = self.current_section.form_values.get(field)
                   print(f"DEBUG: Collected {field} = {data[field]}")
       
           # DEBUG: Print all collected data
           print(f"DEBUG: *** FINAL COLLECTED GEOMETRY DATA: ***")
           for key, value in data.items():
               print(f"DEBUG: {key}: {value}")
        
           return data if any(data.values()) else None
       else:
    
        data = {}
        for control in self.form_content.controls:
                if isinstance(control, ft.Row):
                    for field in control.controls:
                        if isinstance(field, (ft.TextField, ft.Dropdown)):
                            label = field.label
                            if " (Set" in label:
                                label = label.split(" (Set")[0]
                            if " *" in label:
                                label = label.split(" *")[0]
                            data[label] = field.value
                            print(f"DEBUG: Collected field {label}: {field.value}")  

        return data if any(data.values()) else None
      except Exception as ex:
        print(f"DEBUG: Error in collect_form_data: {str(ex)}")
        import traceback
        traceback.print_exc()
        return None
    def validate_current_form(self) -> List[str]:
      """Validate all fields in the current form"""
      errors = []
      try:
        if isinstance(self.current_section, BoreholeSection):
            # Borehole section validation
            data_table = None
            for control in self.form_content.controls:
                if isinstance(control, ft.DataTable):
                    data_table = control
                    break
                elif isinstance(control, ft.Container) and isinstance(control.content, ft.DataTable):
                    data_table = control.content
                    break
            
            if data_table:
                for row_index, row in enumerate(data_table.rows):
                    for cell in row.cells:
                        if isinstance(cell.content, ft.TextField):
                            control = cell.content
                            if control.label in ["Top Depth", "Bottom Depth"]:
                                if not control.value or control.value.strip() == "":
                                    errors.append(f"Row {row_index + 1}: {control.label} is required")
                                elif control.error_text:
                                    errors.append(f"Row {row_index + 1}: {control.label} - {control.error_text}")

        elif isinstance(self.current_section, ExcavationSection):
            # Excavation section validation
            for control in self.form_content.controls:
                if isinstance(control, ft.DataTable):
                    for row in control.rows:
                        for cell in row.cells:
                            if isinstance(cell.content, (ft.TextField, ft.Dropdown)) and cell.content.error_text:
                                errors.append(f"{cell.content.label}: {cell.content.error_text}")

        elif isinstance(self.current_section, GeometrySection):
            # Geometry section validation (including strut fields)
            # Validate base fields
            for field in self.current_section.get_fields():
                if field.required and not self.current_section.form_values.get(field.label):
                    errors.append(f"{field.label} is required")

            # Validate strut fields
            if hasattr(self.current_section, 'current_num_struts'):
                for i in range(1, self.current_section.current_num_struts + 1):
                    if not self.current_section.form_values.get(f"Strut {i} Level"):
                        errors.append(f"Strut {i} Level is required")
                    if not self.current_section.form_values.get(f"Strut {i} Material"):
                        errors.append(f"Strut {i} Material is required")

        else:
            # Validation for other sections (Project Info, etc.)
            for row in self.form_content.controls:
                if isinstance(row, ft.Row):
                    for control in row.controls:
                        if isinstance(control, (ft.TextField, ft.Dropdown)):
                            field_label = control.label.split(" (Set")[0].split(" *")[0]
                            for field in self.current_section.get_fields():
                                if field.label == field_label:
                                    is_valid = field.validate_input(control.value)
                                    if not is_valid and field.error_text:
                                        errors.append(f"{field_label}: {field.error_text}")

      except Exception as ex:
        print(f"DEBUG: Error in validate_current_form: {str(ex)}")
        errors.append(f"Validation error: {str(ex)}")
    
      return errors
    def normalize_section_name(self, name: str) -> str:
      """Normalize section names by replacing spaces with underscores and converting to lowercase"""
      return name.lower().replace(" ", "_")
    async def on_submit(self, e):
      if not self.auth_manager.ensure_authenticated():
        print("DEBUG: User not authenticated, cannot submit form")
        return
    
      print("DEBUG: User Authenticated successfully. Start Submitting......")
    
    # Rest of the on_submit method remains the same...
      try:
        print("DEBUG: Submit button clicked")
        print(f"DEBUG: Total sections: {len(self.sections)}, Current index: {self.rail.selected_index}")
        # Validate current form
        validation_errors = self.validate_current_form()
        print(f"DEBUG: Validation errors: {validation_errors}")  # Debug print

        if validation_errors:
            await self.show_error_dialog(validation_errors)
            return

        # Collect form data
        data = self.collect_form_data()
        print(f"DEBUG: Data collected for storage: {data}")

        # Modified validation logic for different section types
        if isinstance(self.current_section, (ExcavationSection, BoreholeSection)):
            if not data or (isinstance(data, list) and len(data) == 0):
                await self.show_error_dialog(["Please enter at least one set of data."])
                return
        else:
            if not data:
                await self.show_error_dialog(["Please fill out the required fields."])
                return

        # Validate data with section-specific validation
        errors = self.current_section.validate(data)
        if errors:
            await self.show_error_dialog(errors)
            return

        # Store the current section's data
        current_section_name = self.rail.destinations[self.rail.selected_index].label.lower()
        normalized_name = self.normalize_section_name(current_section_name)
        current_data = self.collect_form_data()
        if current_data:
            self.section_data[current_section_name] = current_data
        print(f"DEBUG: Current section name before normalization: {current_section_name}")
        print(f"DEBUG: Normalized section name: {normalized_name}")

        # Store data in form manager
        self.form_manager.store_section_data(normalized_name, data)
        print(f"DEBUG: Stored data for section {current_section_name}")

        current_index = self.rail.selected_index
        is_last_tab = current_index >= len(self.sections) - 1  # Use >= instead of == for safety


        if is_last_tab:
            # Final submission logic
            try:
                with DatabaseConnection(self.db_config) as db:
                    from datetime import datetime
                    import random

                    # Enhanced common_id with milliseconds
                    common_id = (
                        f"{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}_"
                        f"{random.randint(1000, 9999)}"
                    )

                    # Retrieve all section data
                    sections_data = {
                        'project_info': self.form_manager.get_section_data('project_info'),
                        'geometry': self.form_manager.get_section_data('geometry'),
                        'borehole': self.form_manager.get_section_data('borehole'),
                        'excavation': self.form_manager.get_section_data('excavation'),
                        'sequence_construct': self.form_manager.get_section_data('sequence_construct')
                    }

                    print("DEBUG: Retrieved sections_data:", sections_data)

                    # Add common_id to all sections
                    for section_data in sections_data.values():
                        if isinstance(section_data, dict):
                            section_data['common_id'] = common_id
                        elif isinstance(section_data, list):
                            for item in section_data:
                                item['common_id'] = common_id

                    # Save each section with debug prints
                    print("DEBUG: Saving project info...")
                    self.sections[0].save(db.cursor, sections_data['project_info'])
                    print("DEBUG: Saving geometry...")
                    self.sections[1].save(db.cursor, sections_data['geometry'])
                    print("DEBUG: Saving borehole...")
                    self.sections[2].save(db.cursor, sections_data['borehole'])
                    print("DEBUG: Saving excavation...")
                    self.sections[3].save(db.cursor, sections_data['excavation'], sections_data['geometry'])
                    # Add enhanced error logging here
                    try:
                        print("DEBUG: About to save sequence construct...")
                        print("DEBUG: Sequence construct data:", sections_data['sequence_construct'])
                        if len(self.sections) > 4:
                           print(f"DEBUG: About to save sequence construct with section {self.sections[4].__class__.__name__}")
                           self.sections[4].save(db.cursor, sections_data['sequence_construct'])
                        else:
                           print(f"ERROR: Cannot access section at index 4. Total sections: {len(self.sections)}")
                        print("DEBUG: Finished saving sequence construct")
                    except Exception as ex:
                        import traceback
                        print(f"ERROR: Failed to save sequence construct: {str(ex)}")
                        print(f"ERROR: Traceback: {traceback.format_exc()}")
                        raise
                    db.connection.commit()  # Explicit commit

                    # Clear stored data after successful save
                    
                    self.submission_successful = True
                    self.data_modified_after_submission = False  # Reset modification flag
                
                # Hide submit button, show create model button
                    self.next_button.visible = False
                    self.next_button.disabled = True
                    self.create_model_button.visible = True
                    self.create_model_button.disabled = False
                
                # Update UI
                    self.next_button.update()
                    self.create_model_button.update()
                
                # Attach change handlers to all controls
                    self.attach_change_handlers_to_controls(self.form_content.controls)
                
                    await self.show_success_dialog("All form data has been saved successfully!")
                
            except Exception as ex:
                print(f"Error saving data: {str(ex)}")
                error_msg = f"Database error: {str(ex)}"
                if "NOT NULL constraint" in str(ex):
                    error_msg += "\nMissing required data. Please check all fields are filled correctly."
                await self.show_error_dialog([error_msg])
                return
        else:
            # Move to next tab
            self.enable_next_tab()

            if current_index + 1 < len(self.sections):
                # ✅ CRITICAL: Save current excavation data before leaving
                if current_index == 3:  # If leaving excavation tab
                    excavation_data = self.collect_form_data()
                    if excavation_data:
                        self.form_manager.store_section_data('excavation', excavation_data)
                        print(f"DEBUG: Saved excavation data before leaving: {excavation_data}")
                
                self.rail.selected_index = current_index + 1
                self.current_section = self.sections[current_index + 1]
        
                self.update_form_content(current_index + 1)

                # Enable Previous button
                self.prev_button.visible = True
                self.prev_button.disabled = False
                self.prev_button.update()
            else:
                # Handle the case when there's no next section
                await self.show_error_dialog(["This is the last section. Please submit the form."])
        # Final UI update
        self.page.update()

      except Exception as ex:
        import traceback
        print(f"Error in form submission: {str(ex)}")
        print(f"Detailed traceback: {traceback.format_exc()}")
        await self.show_error_dialog([f"Error: {str(ex)}"])

    def _populate_form_fields(self, form_section: ft.Column, data: Dict):
        """Helper method to populate form fields with stored data"""
        for row in form_section.controls:
            if isinstance(row, ft.Row):
                for control in row.controls:
                    if isinstance(control, (ft.TextField, ft.Dropdown)):
                        label = control.label.split(" (Set")[0].split(" *")[0]
                        if label in data:
                            control.value = data[label]
    
    async def show_success_dialog(self, message: str):
        """Show success dialog with provided message"""
        dialog = ft.AlertDialog(
            title=ft.Text("Success"),
            content=ft.Text(message),
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()

    async def show_error_dialog(self, errors: List[str]):
        """Show error dialog with provided error messages"""
        dialog = ft.AlertDialog(
            title=ft.Text("Validation Errors"),
            content=ft.Column([ft.Text(error) for error in errors], tight=True),
        )
        self.page.overlay.append(dialog)
        dialog.open = True
        self.page.update()
                 
    def clear_form(self):
        """Clear form fields based on section type"""
        if isinstance(self.current_section, BoreholeSection):
            for container in self.form_content.controls:
                if isinstance(container, ft.Container):
                    form_section = container.content.controls[-1]
                    for row in form_section.controls:
                        if isinstance(row, ft.Row):
                            for field in row.controls:
                                if isinstance(field, (ft.TextField, ft.Dropdown)):
                                    field.value = None
        elif isinstance(self.current_section, ExcavationSection):
            # Reset to initial state with exactly one container
            self.excavation_section.visible_sets = 1
            # Clear all controls except the add button
            add_button = self.form_content.controls[0]
            self.form_content.controls.clear()
            self.form_content.controls.append(add_button)
            # Add single initial set
            initial_set = self.current_section.create_excavation_set(1, str(self.current_section.get_initial_wall_top_level()))
            self.form_content.controls.append(initial_set)
        else:
            for row in self.form_content.controls:
                if isinstance(row, ft.Row):
                    for control in row.controls:
                        if isinstance(control, (ft.TextField, ft.Dropdown)):
                            control.value = None
        
        self.form_content.update()
    