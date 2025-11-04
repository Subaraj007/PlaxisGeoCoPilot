import os
import zipfile
import traceback
from io import BytesIO
import pandas as pd
import flet as ft
from typing import Dict, Optional, List, Any
from frontend.auth_manager import AuthManager
class GCPHandler:
    def __init__(self, form_app):
        self.form_app = form_app
        self.user_selected_save_path = None
        self.save_file_picker = None
        self.open_gcp_picker = None
        self.current_gcp_data = None  # Store the current loaded GCP data
        self.auth_manager = AuthManager(form_app)
    def initialize_file_pickers(self):
        if not self.form_app.page:
            return
        self.save_file_picker = ft.FilePicker(on_result=self.handle_save_path_selection)
        self.open_gcp_picker = ft.FilePicker(on_result=self.handle_open_gcp_selection)
        self.form_app.page.overlay.extend([self.save_file_picker, self.open_gcp_picker])
        self.form_app.page.update()

    def _init_file_pickers(self):
        if not self.form_app.page:
            print("DEBUG: Cannot initialize file pickers - page not available")
            return
        print("DEBUG: Initializing file pickers")
        self.save_file_picker = ft.FilePicker(on_result=self.handle_save_path_selection)
        self.open_gcp_picker = ft.FilePicker(on_result=self.handle_open_gcp_selection)
        self.form_app.page.overlay.append(self.save_file_picker)
        self.form_app.page.overlay.append(self.open_gcp_picker)

    async def _ensure_file_pickers(self):
      if not self.form_app.page:
        print("DEBUG: Page not initialized")
        return False
    
      if self.save_file_picker is None:
        print("DEBUG: Creating save_file_picker")
        self.save_file_picker = ft.FilePicker(on_result=self.handle_save_path_selection)
        self.form_app.page.overlay.append(self.save_file_picker)
    
      if self.open_gcp_picker is None:
        print("DEBUG: Creating open_gcp_picker")
        self.open_gcp_picker = ft.FilePicker(on_result=self.handle_open_gcp_selection)
        self.form_app.page.overlay.append(self.open_gcp_picker)
    
    # CRITICAL: Update page after adding pickers
      await self.form_app.page.update_async()
      return True

    async def handle_save_path_selection(self, e: ft.FilePickerResultEvent):
        if not e.path:
            print("DEBUG: No save path selected")
            return
        try:
            self.user_selected_save_path = e.path
            print(f"DEBUG: Save path selected: {self.user_selected_save_path}")
            await self._actually_save_gcp_data()
        except Exception as ex:
            print(f"DEBUG: Save path selection error: {str(ex)}")
            await self.form_app.show_error_dialog([f"Save path selection error: {str(ex)}"])

    async def _actually_save_gcp_data(self):
        try:
            if not self.user_selected_save_path:
                print("DEBUG: No save path available")
                return
            project_info = self.form_app.form_manager.get_section_data('project_info') or {}
            geometry = self.form_app.form_manager.get_section_data('geometry') or {}
            borehole = self.form_app.form_manager.get_section_data('borehole') or []
            excavation = self.form_app.form_manager.get_section_data('excavation') or []
            sequence_construct = self.form_app.form_manager.get_section_data('sequence_construct') or {}

            data_dict = {
                'project_info': project_info,
                'geometry': geometry,
                'borehole': borehole,
                'excavation': excavation,
                'sequence_construct': sequence_construct
            }

            save_path = self.user_selected_save_path
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            self.save_gcp(save_path, data_dict)
            print(f"DEBUG: GCP file successfully saved to {save_path}")
            await self.form_app.show_success_dialog(f"Data saved successfully to:\n{save_path}")
        except Exception as ex:
            print(f"DEBUG: GCP save error: {str(ex)}")
            await self.form_app.show_error_dialog([
                f"Error saving GCP file: {str(ex)}",
                "Technical details:",
                *traceback.format_exc().split('\n')[-3:]
            ])

    def save_gcp(self, save_path, data_dict):
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        dataframes = {}

        if 'project_info' in data_dict:
            if isinstance(data_dict['project_info'], dict):
                dataframes['project_info'] = pd.DataFrame([data_dict['project_info']])
            elif isinstance(data_dict['project_info'], pd.DataFrame):
                dataframes['project_info'] = data_dict['project_info']
        else:
            dataframes['project_info'] = pd.DataFrame()

        if 'geometry' in data_dict:
            if isinstance(data_dict['geometry'], dict):
                dataframes['geometry'] = pd.DataFrame([data_dict['geometry']])
            elif isinstance(data_dict['geometry'], pd.DataFrame):
                dataframes['geometry'] = data_dict['geometry']
        else:
            dataframes['geometry'] = pd.DataFrame()

        if 'borehole' in data_dict:
            if isinstance(data_dict['borehole'], list):
                dataframes['borehole'] = pd.DataFrame(data_dict['borehole'])
            elif isinstance(data_dict['borehole'], pd.DataFrame):
                dataframes['borehole'] = data_dict['borehole']
        else:
            dataframes['borehole'] = pd.DataFrame()

        if 'excavation' in data_dict:
            if isinstance(data_dict['excavation'], list):
                dataframes['excavation'] = pd.DataFrame(data_dict['excavation'])
            elif isinstance(data_dict['excavation'], pd.DataFrame):
                dataframes['excavation'] = data_dict['excavation']
        else:
            dataframes['excavation'] = pd.DataFrame()

        if 'sequence_construct' in data_dict:
            if isinstance(data_dict['sequence_construct'], dict):
                dataframes['sequence_construct'] = pd.DataFrame(data_dict['sequence_construct'])
            elif isinstance(data_dict['sequence_construct'], pd.DataFrame):
                dataframes['sequence_construct'] = data_dict['sequence_construct']
        else:
            dataframes['sequence_construct'] = pd.DataFrame()

        with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for key, df in dataframes.items():
                self._save_csv_to_gcp(zip_file, df, f"{key}.csv")

    def _save_csv_to_gcp(self, zip_file, df, csv_file_name):
        with zip_file.open(csv_file_name, 'w') as csv_file:
            csv_data = df.to_csv(index=False).encode('utf-8')
            csv_file.write(csv_data)

    async def handle_open_gcp_selection(self, e: ft.FilePickerResultEvent):
      print("DEBUG: GCP file selection event triggered")
      if not e.files:
        print("DEBUG: No GCP file selected")
        return
      if not self.form_app.page:
        raise Exception("Page not initialized")
      if self.open_gcp_picker not in self.form_app.page.overlay:
        self.form_app.page.overlay.append(self.open_gcp_picker)
        await self.form_app.page.update_async()
    
      try:
        gcp_path = e.files[0].path
        if not gcp_path.lower().endswith('.gcp'):
            raise ValueError("Invalid file type. Please select a .gcp file")
        data = self.open_gcp(gcp_path)
        if not data:
            raise ValueError("No data could be extracted from the GCP file")
        
        # Store the loaded data for later use
        self.current_gcp_data = data
        
        # Directly load to tabs instead of showing popup
        await self.load_gcp_data_to_tabs()
        
      except Exception as ex:
        error_msg = f"Failed to open GCP file: {str(ex)}"
        print(f"DEBUG: {error_msg}")
        if hasattr(self.form_app, 'page') and self.form_app.page:
            error_details = [
                error_msg,
                "Technical details:",
                *traceback.format_exc().split('\n')[-3:]
            ]
            try:
                await self.form_app.show_error_dialog(error_details)
            except Exception as dialog_ex:
                print(f"ERROR: Failed to show error dialog: {str(dialog_ex)}")
        else:
            print("ERROR: Cannot show dialog - page not initialized") 
    def open_gcp(self, gcp_file_path):
        dataframes = {}
        expected_csv_files = [
            'project_info.csv',
            'geometry.csv',
            'borehole.csv',
            'excavation.csv',
            'sequence_construct.csv'
        ]

        try:
            with open(gcp_file_path, 'rb') as file:
                zip_data = BytesIO(file.read())
            if not zipfile.is_zipfile(zip_data):
                raise ValueError("The selected file is not a valid ZIP/GCP archive")
            zip_data.seek(0)
            with zipfile.ZipFile(zip_data) as zip_file:
                file_list = zip_file.namelist()
                print(f"DEBUG: Files in GCP: {file_list}")
                for csv_file_name in expected_csv_files:
                    section_name = csv_file_name.split('.')[0]
                    try:
                        dataframes[section_name] = self._open_csv_from_gcp(zip_file, csv_file_name)
                    except Exception as ex:
                        print(f"DEBUG: Error processing {csv_file_name}: {str(ex)}")
                        dataframes[section_name] = pd.DataFrame()
        
        except zipfile.BadZipFile:
            raise ValueError("The selected file is not a valid ZIP/GCP archive")
        except Exception as ex:
            raise ValueError(f"Error opening GCP file: {str(ex)}")

        for section_name in [file.split('.')[0] for file in expected_csv_files]:
            if section_name not in dataframes:
                dataframes[section_name] = pd.DataFrame()

        with pd.option_context('display.max_rows', None, 'display.max_columns', None):
            print("\n=== GCP File Contents ===")
            for name, df in dataframes.items():
                print(f"\nDataFrame for {name}:")
                print("=" * 80)
                print(f"Shape: {df.shape}")
                print(f"Columns: {list(df.columns) if not df.empty else 'None'}")
                if not df.empty and len(df) > 0:
                    print("\nAll Rows:")
                    print(df)
                else:
                    print("\nEmpty DataFrame")
                print("\n" + "-" * 80)

        return dataframes

    def _open_csv_from_gcp(self, zip_file, csv_file_name):
        matching_files = [file_name for file_name in zip_file.namelist() if csv_file_name in file_name]
        if matching_files:
            with zip_file.open(matching_files[0]) as csv_file:
                try:
                    content = csv_file.read()
                    if not content.strip():
                        print(f"DEBUG: Empty CSV file encountered: {csv_file_name}")
                        return pd.DataFrame()
                    
                    csv_data = BytesIO(content)
                    df = pd.read_csv(csv_data)
                    return df
                except pd.errors.EmptyDataError:
                    print(f"DEBUG: Empty data in CSV file: {csv_file_name}")
                    return pd.DataFrame()
                
                except Exception as e:
                    print(f"DEBUG: Error reading CSV {csv_file_name}: {str(e)}")
                    raise
        else:
            print(f"DEBUG: CSV file not found: {csv_file_name}")
            return pd.DataFrame()

    # In the GCPHandler class, modify the load_gcp_data_to_tabs method
    async def load_gcp_data_to_tabs(self):
      """Load the current GCP data to all tabs similar to FullDataImporter"""
      try:
        if not self.current_gcp_data:
            print("DEBUG: No GCP data to load")
            return
        
        print("DEBUG: Starting load_gcp_data_to_tabs")
        success_messages = []
        
        # Convert DataFrame data to appropriate format for each section
        converted_data = self._convert_gcp_data_for_import(self.current_gcp_data)
        
        # Import to each section similar to FullDataImporter
        if converted_data.get('project_info'):
            print("DEBUG: Loading project info to tab")
            await self._import_project_info(converted_data['project_info'])
            success_messages.append("Project Info")
        
        if converted_data.get('geometry'):
            print("DEBUG: Loading geometry to tab")
            await self._import_geometry(converted_data['geometry'])
            success_messages.append("Geometry")
        
        if converted_data.get('borehole'):
            print("DEBUG: Loading borehole to tab")
            await self._import_borehole(converted_data['borehole'])
            success_messages.append("Borehole")
        
        if converted_data.get('excavation'):
            print("DEBUG: Loading excavation to tab")
            await self._import_excavation(converted_data['excavation'])
            success_messages.append("Excavation")
        
        if converted_data.get('sequence_construct'):
            print("DEBUG: Loading sequence construct to tab")
            await self._import_sequence_construction(converted_data['sequence_construct'])
            success_messages.append("Sequence Construction")
        
        # Close the current dialog
        await self.close_dialog_async()
        
        # Show success message
        if success_messages:
            message = f"Successfully loaded GCP data to: {', '.join(success_messages)}"
            await self._show_success_dialog(message)
            
            # NEW: Navigate to the first tab (Project Info)
            self.form_app.rail.selected_index = 0
            self.form_app.current_section = self.form_app.sections[0]
            self.form_app.update_form_content(0)
            
            # Update UI
            self.form_app.rail.update()
            await self.form_app.page.update_async()
        
        print(f"DEBUG: Successfully loaded GCP data to {len(success_messages)} sections")
        
      except Exception as ex:
        print(f"ERROR in load_gcp_data_to_tabs: {str(ex)}")
        await self.form_app.show_error_dialog([f"Error loading GCP data to tabs: {str(ex)}"])
   

    def _convert_gcp_data_for_import(self, gcp_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
      """Convert GCP DataFrame data to format expected by import functions"""
      converted_data = {}
    
      try:
        # Convert project_info DataFrame to dict with string values
        if 'project_info' in gcp_data and not gcp_data['project_info'].empty:
            project_dict = gcp_data['project_info'].iloc[0].to_dict()
            # Convert all values to strings
            converted_data['project_info'] = {k: str(v) if pd.notna(v) else '' for k, v in project_dict.items()}
        
        # Convert geometry DataFrame to dict with string values
        if 'geometry' in gcp_data and not gcp_data['geometry'].empty:
            geometry_dict = gcp_data['geometry'].iloc[0].to_dict()
            # Convert all values to strings - THIS IS THE KEY FIX
            converted_data['geometry'] = {k: str(v) if pd.notna(v) else '' for k, v in geometry_dict.items()}
        
        # Convert borehole DataFrame to list of dicts with string values
        if 'borehole' in gcp_data and not gcp_data['borehole'].empty:
            borehole_records = gcp_data['borehole'].to_dict('records')
            converted_data['borehole'] = [
                {k: str(v) if pd.notna(v) else '' for k, v in record.items()} 
                for record in borehole_records
            ]
        
        # Convert excavation DataFrame to list of dicts with string values
        if 'excavation' in gcp_data and not gcp_data['excavation'].empty:
            excavation_records = gcp_data['excavation'].to_dict('records')
            converted_data['excavation'] = [
                {k: str(v) if pd.notna(v) else '' for k, v in record.items()} 
                for record in excavation_records
            ]
        
        # Convert sequence_construct DataFrame to list of dicts with string values
        if 'sequence_construct' in gcp_data and not gcp_data['sequence_construct'].empty:
            sequence_records = gcp_data['sequence_construct'].to_dict('records')
            converted_data['sequence_construct'] = [
                {k: str(v) if pd.notna(v) else '' for k, v in record.items()} 
                for record in sequence_records
            ]
        
        print(f"DEBUG: Converted GCP data - sections: {list(converted_data.keys())}")
        
        # Debug: Print sample geometry data to verify string conversion
        if 'geometry' in converted_data:
            print("DEBUG: Sample geometry data after conversion:")
            for key, value in list(converted_data['geometry'].items())[:5]:  # First 5 items
                print(f"  {key}: {value} (type: {type(value)})")
        
        return converted_data
        
      except Exception as ex:
        print(f"ERROR in _convert_gcp_data_for_import: {str(ex)}")
        return {}
    # Import functions similar to FullDataImporter
    async def _import_project_info(self, data: Dict[str, str]):
        self.form_app.section_data['project info'] = data
        print(f"Imported Project Info: {data}")

    async def _import_geometry(self, data: Dict[str, str]):
      """Import geometry data from GCP and properly display all frames"""
      geometry_section = self.form_app.sections[1]
    
    # CRITICAL: Initialize form_values with imported data
      if not hasattr(geometry_section, 'form_values'):
        geometry_section.form_values = {}
    
    # Store all imported data in form_values
      geometry_section.form_values = data.copy()
    
    # CRITICAL: Extract and set number of struts
      num_struts = data.get('No of Strut', '0')
      try:
        geometry_section.current_num_struts = int(num_struts)
        print(f"DEBUG: Set current_num_struts to {geometry_section.current_num_struts}")
      except (ValueError, TypeError):
        geometry_section.current_num_struts = 0
        print("DEBUG: Failed to parse num_struts, defaulting to 0")
    
    # CRITICAL: Set strut type
      strut_type = data.get('Strut Type', '')
      if strut_type:
        geometry_section.form_values['Strut Type'] = strut_type
        print(f"DEBUG: Set Strut Type to {strut_type}")
    
    # Store individual strut data in form_values
      for i in range(1, geometry_section.current_num_struts + 1):
        strut_keys = [
            f"Strut {i} Level",
            f"Strut {i} Material", 
            f"Strut {i} Member Size",
            f"Strut {i} Space",
            f"Strut {i} EA",
            f"Strut {i} Stiffness",
            f"Strut {i} Length",
            f"Strut {i} Angle"
        ]
        
        for key in strut_keys:
            if key in data:
                geometry_section.form_values[key] = data[key]
                print(f"DEBUG: Stored {key} = {data[key]}")
    
    # Store in section_data
      self.form_app.section_data['geometry'] = data.copy()
    
    # Store in form_manager
      self.form_app.form_manager.store_section_data('geometry', data)
    
    # CRITICAL: Force UI update to geometry tab with stored data
    # This will trigger _create_geometry_frames with the correct num_struts
      if self.form_app.rail.selected_index == 1:
        # If already on geometry tab, refresh it
        print("DEBUG: Already on geometry tab, refreshing...")
        self.form_app.update_form_content(1, data)
    
      print(f"DEBUG: Successfully imported geometry data with {geometry_section.current_num_struts} struts")
    
      if self.form_app.page:
        await self.form_app.page.update_async()
    
    async def _import_borehole(self, data: List[Dict[str, str]]):
        self.form_app.section_data['borehole'] = data
        if hasattr(self.form_app, 'form_manager') and hasattr(self.form_app.form_manager, 'update_borehole_table'):
            self.form_app.form_manager.update_borehole_table(data)
        print(f"Imported Borehole: {data}")

    async def _import_excavation(self, data: List[Dict[str, str]]):
        self.form_app.section_data['excavation'] = data
        if hasattr(self.form_app, 'form_manager') and hasattr(self.form_app.form_manager, 'update_excavation_table'):
            self.form_app.form_manager.update_excavation_table(data)
        print(f"Imported Excavation: {data}")

    async def _import_sequence_construction(self, data: List[Dict[str, str]]):
        try:
            print("DEBUG: *** ENTERING _import_sequence_construction via GCP ***")
            print(f"DEBUG: Data received: {data}")
            
            self.form_app.section_data['sequence construct'] = data
            print("DEBUG: Stored data in form_app.section_data['sequence construct']")
            
            sequence_section = None
            if hasattr(self.form_app, 'sections') and len(self.form_app.sections) > 4:
                sequence_section = self.form_app.sections[4]
                print("DEBUG: Found sequence section via sections array")
            
            if sequence_section:
                print("DEBUG: Attempting to import data into sequence section")
                if hasattr(sequence_section, 'import_from_list'):
                    print("DEBUG: Using import_from_list method")
                    sequence_section.import_from_list(data)
                elif hasattr(sequence_section, 'load_data'):
                    print("DEBUG: Using load_data method")
                    sequence_section.load_data(data)
                elif hasattr(sequence_section, 'populate_table'):
                    print("DEBUG: Using populate_table method")
                    sequence_section.populate_table(data)
                
                if hasattr(sequence_section, 'section_data'):
                    sequence_section.section_data = data
                    print("DEBUG: Stored data in section's section_data")
                
                print(f"DEBUG: Successfully processed {len(data)} sequence construction records")
            else:
                print("WARNING: Could not find sequence construction section for import")
            
            if (hasattr(self.form_app, 'form_manager') and 
                hasattr(self.form_app.form_manager, 'update_sequence_table')):
                print("DEBUG: Updating sequence table via form_manager")
                self.form_app.form_manager.update_sequence_table(data)
            
            if hasattr(self.form_app, 'page') and self.form_app.page:
                print("DEBUG: Updating UI page")
                self.form_app.page.update()
            
            print(f"DEBUG: *** COMPLETED _import_sequence_construction *** - Imported {len(data)} records")
            
        except Exception as e:
            print(f"ERROR in _import_sequence_construction: {e}")
            import traceback
            traceback.print_exc()

    async def save_gcp_handler(self, e):
        if not self.auth_manager.ensure_authenticated():
            return
        print("DEBUG: User authenticated, proceeding with save handler")
        try:
            if not await self._ensure_file_pickers():
                return
            current_section_name = self.form_app.rail.destinations[
                self.form_app.rail.selected_index
            ].label.lower()
            current_data = self.form_app.collect_form_data()
            if current_data:
                normalized_name = self.form_app.normalize_section_name(current_section_name)
                self.form_app.form_manager.store_section_data(normalized_name, current_data)
            self.save_file_picker.save_file(
                allowed_extensions=["gcp"],
                file_name="geo_design_project.gcp"
            )
        except Exception as ex:
            await self.form_app.show_error_dialog([f"Save error: {str(ex)}"])

    async def open_gcp_handler(self, e):
      if not self.auth_manager.ensure_authenticated():
        return
      print("DEBUG: User authenticated, proceeding with open GCP handler")
      try:
        print("DEBUG: Open GCP handler called")
        
        # CRITICAL FIX: Ensure page is available
        if not self.form_app.page:
            print("ERROR: Page not initialized")
            return
        
        # Ensure file pickers are initialized
        await self._ensure_file_pickers()
        
        if self.open_gcp_picker is None:
            print("DEBUG: File picker is still None after initialization attempt")
            await self.form_app.show_error_dialog(["Cannot open: File picker initialization failed"])
            return
        
        # CRITICAL FIX: Check if picker is in overlay, add if not
        if self.open_gcp_picker not in self.form_app.page.overlay:
            print("DEBUG: Adding file picker to page overlay")
            self.form_app.page.overlay.append(self.open_gcp_picker)
            await self.form_app.page.update_async()
        
        print(f"DEBUG: Page overlay contains {len(self.form_app.page.overlay)} items")
        for i, item in enumerate(self.form_app.page.overlay):
            print(f"DEBUG: Overlay item {i}: {type(item).__name__}")
        
        print("DEBUG: Calling pick_files on file picker")
        self.open_gcp_picker.pick_files(
            allowed_extensions=["gcp"],
            dialog_title="Open GCP File"
        )
        
        # No need to update page again immediately after pick_files
        
      except Exception as ex:
        error_msg = f"Open handler error: {str(ex)}"
        print(f"DEBUG: {error_msg}")
        import traceback
        traceback.print_exc()
        if hasattr(self.form_app, 'show_error_dialog'):
            await self.form_app.show_error_dialog([
                error_msg,
                "Technical details:",
                *traceback.format_exc().split('\n')[-3:]
            ])
    
    async def close_dialog_async(self, e=None):
        if hasattr(self.form_app, 'page') and self.form_app.page and self.form_app.page.dialog:
            self.form_app.page.dialog.open = False
            await self.form_app.page.update_async()

    async def refresh_current_view(self):
        current_section_index = self.form_app.rail.selected_index
        print(f"DEBUG: Refreshing view for section index: {current_section_index}")
        self.form_app.update_form_content(current_section_index)
        await self.form_app.page.update_async()

    async def _show_success_dialog(self, message: str):
        async def close_success_dialog(e):
            await self._close_success_dialog()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Load Successful"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=close_success_dialog)
            ],
        )
        self.form_app.page.dialog = dialog
        dialog.open = True
        await self.form_app.page.update_async()

    async def _close_success_dialog(self):
        if self.form_app.page.dialog:
            self.form_app.page.dialog.open = False
            await self.form_app.page.update_async()