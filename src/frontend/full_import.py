import csv
import flet as ft
from typing import Dict, List, Any
from pathlib import Path

class FullDataImporter:
    def __init__(self, form_app):
        self.form_app = form_app
        self.imported_data = {}

    def parse_csv_file(self, file_path: str) -> Dict[str, List[Dict[str, Any]]]:
        sections_data = {
            'project_info': [],
            'geometry': [],
            'borehole': [],
            'excavation': [],
            'sequence_construction': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            lines = content.strip().split('\n')
            current_section = None
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Check for section headers - make detection more robust
                if "Project Info Data" in line:
                    current_section = 'project_info'
                    print(f"DEBUG: Found Project Info section at line {i}")
                    i += 1
                    continue
                elif "Geometry Data" in line:
                    current_section = 'geometry'
                    print(f"DEBUG: Found Geometry section at line {i}")
                    i += 1
                    continue
                elif "Borehole Data" in line:
                    current_section = 'borehole'
                    print(f"DEBUG: Found Borehole section at line {i}")
                    i += 1
                    continue
                elif "Excavation Data" in line:
                    current_section = 'excavation'
                    print(f"DEBUG: Found Excavation section at line {i}")
                    i += 1
                    continue
                elif "Sequence Construction Data" in line or "Sequence Data" in line:
                    current_section = 'sequence_construction'
                    print(f"DEBUG: Found Sequence Construction section at line {i}")
                    i += 1
                    continue
                
                # Process data lines
                if current_section and line and not line.startswith('#') and line.strip():
                    print(f"DEBUG: Processing line in {current_section}: {line[:50]}...")
                    
                    if current_section == 'project_info':
                        sections_data[current_section] = self._parse_project_info(line)
                    elif current_section == 'geometry':
                        sections_data[current_section] = self._parse_geometry(line)
                    elif current_section == 'borehole':
                        if i + 1 < len(lines):
                            header_line = line
                            data_lines = []
                            i += 1
                            while i < len(lines) and lines[i].strip() and not self._is_section_header(lines[i]):
                                data_lines.append(lines[i].strip())
                                i += 1
                            sections_data[current_section] = self._parse_borehole(header_line, data_lines)
                            i -= 1
                    elif current_section == 'excavation':
                        if i + 1 < len(lines):
                            header_line = line
                            data_lines = []
                            i += 1
                            while i < len(lines) and lines[i].strip() and not self._is_section_header(lines[i]):
                                data_lines.append(lines[i].strip())
                                i += 1
                            sections_data[current_section] = self._parse_excavation(header_line, data_lines)
                            i -= 1
                    elif current_section == 'sequence_construction':
                        if i + 1 < len(lines):
                            header_line = line
                            data_lines = []
                            i += 1
                            # Collect all data lines for this section
                            while i < len(lines) and lines[i].strip() and not self._is_section_header(lines[i]):
                                data_lines.append(lines[i].strip())
                                i += 1
                            print(f"DEBUG: Found {len(data_lines)} sequence construction data lines")
                            sections_data[current_section] = self._parse_sequence_construction(header_line, data_lines)
                            i -= 1
                
                i += 1
                
        except Exception as e:
            print(f"Error parsing CSV file: {e}")
            import traceback
            traceback.print_exc()
            raise e
        
        # Debug: Print final sections data
        print("DEBUG: Final sections data summary:")
        for section, data in sections_data.items():
            if isinstance(data, list):
                print(f"  {section}: {len(data)} items")
            else:
                print(f"  {section}: {type(data)} - {bool(data)}")
        
        return sections_data
    
    def _is_section_header(self, line: str) -> bool:
        """Check if a line is a section header"""
        section_keywords = [
            "Project Info Data", "Geometry Data", "Borehole Data", 
            "Excavation Data", "Sequence Construction Data", "Sequence Data"
        ]
        return any(keyword in line for keyword in section_keywords)
    
    def _parse_project_info(self, line: str) -> Dict[str, str]:
        values = [v.strip() for v in line.split(',')]
        return {
            'Project Title': values[0] if len(values) > 0 else '',
            'Section': values[1] if len(values) > 1 else '',
            'Model Type': values[2] if len(values) > 2 else '',
            'Element Type': values[3] if len(values) > 3 else '',
            'Borehole Type': values[4] if len(values) > 4 else '',
            'Borehole': values[5] if len(values) > 5 else '',
            'Design Approach': values[6] if len(values) > 6 else ''
        }

    def _parse_geometry(self, line: str) -> Dict[str, str]:
        values = [v.strip() for v in line.split(',')]
        geometry_fields = [
            'Excavation Type', 'Over Excavation', 'Excavation Below Strut', 'Wall Top Level',
            'Excavation Depth', 'Excavation Width', 'Toe Level', 'No of Strut', 'Strut Type',
            'Wall Type', 'Material', 'Member Size', 'Spacing', 'Borehole X Coordinate',
            'Ground Water Table', 'Strut 1 Level', 'Strut 1 Material', 'Strut 1 Member Size',
            'Strut 2 Level', 'Strut 2 Material', 'Strut 2 Member Size'
        ]
        
        geometry_data = {}
        for i, field in enumerate(geometry_fields):
            geometry_data[field] = values[i] if i < len(values) else ''
        
        return geometry_data

    def _parse_borehole(self, header_line: str, data_lines: List[str]) -> List[Dict[str, str]]:
        headers = [h.strip() for h in header_line.split(',')]
        borehole_data = []
        
        for line in data_lines:
            values = [v.strip() for v in line.split(',')]
            row_data = {}
            for i, header in enumerate(headers):
                row_data[header] = values[i] if i < len(values) else ''
            borehole_data.append(row_data)
        
        return borehole_data

    def _parse_excavation(self, header_line: str, data_lines: List[str]) -> List[Dict[str, str]]:
        headers = [h.strip() for h in header_line.split(',')]
        excavation_data = []
        
        for line in data_lines:
            values = [v.strip() for v in line.split(',')]
            row_data = {}
            for i, header in enumerate(headers):
                row_data[header] = values[i] if i < len(values) else ''
            excavation_data.append(row_data)
        
        return excavation_data

    def _parse_sequence_construction(self, header_line: str, data_lines: List[str]) -> List[Dict[str, str]]:
        print(f"DEBUG: Parsing sequence construction with header: {header_line}")
        print(f"DEBUG: Data lines count: {len(data_lines)}")
        
        headers = [h.strip() for h in header_line.split(',')]
        sequence_data = []
        
        for line_num, line in enumerate(data_lines):
            print(f"DEBUG: Processing sequence data line {line_num + 1}: {line}")
            values = [v.strip() for v in line.split(',')]
            row_data = {}
            for i, header in enumerate(headers):
                row_data[header] = values[i] if i < len(values) else ''
            sequence_data.append(row_data)
        
        print(f"DEBUG: Final parsed sequence construction data: {sequence_data}")
        return sequence_data

    def _create_geometry_csv_file(self, geometry_data: Dict[str, str], temp_file_path: str):
        """Create a temporary CSV file with geometry data for import_from_csv function"""
        try:
            with open(temp_file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header row
                headers = list(geometry_data.keys())
                writer.writerow(headers)
                
                # Write data row
                values = list(geometry_data.values())
                writer.writerow(values)
                
            print(f"DEBUG: Created temporary geometry CSV file at {temp_file_path}")
            
        except Exception as e:
            print(f"Error creating geometry CSV file: {e}")
            raise e

    async def import_all_data(self, file_path: str):
        try:
            print("DEBUG: Starting import_all_data")
            sections_data = self.parse_csv_file(file_path)
            success_messages = []
            
            print("DEBUG: Checking sections for import...")
            
            if sections_data['project_info']:
                print("DEBUG: Importing project info")
                await self._import_project_info(sections_data['project_info'])
                success_messages.append("Project Info")
            
            if sections_data['geometry']:
                print("DEBUG: Importing geometry")
                await self._import_geometry(sections_data['geometry'])
                success_messages.append("Geometry")
            
            if sections_data['borehole']:
                print("DEBUG: Importing borehole")
                await self._import_borehole(sections_data['borehole'])
                success_messages.append("Borehole")
            
            if sections_data['excavation']:
                print("DEBUG: Importing excavation")
                await self._import_excavation(sections_data['excavation'])
                success_messages.append("Excavation")
            
            # Fixed: Check for sequence construction data properly
            if sections_data['sequence_construction'] and len(sections_data['sequence_construction']) > 0:
                print("DEBUG: Starting sequence construction import")
                print(f"DEBUG: Sequence construction data to import: {sections_data['sequence_construction']}")
                await self._import_sequence_construction(sections_data['sequence_construction'])
                success_messages.append("Sequence Construction")
            else:
                print("DEBUG: No sequence construction data found or data is empty")
                print(f"DEBUG: sequence_construction content: {sections_data['sequence_construction']}")
            
            if success_messages:
                message = f"Successfully imported data for: {', '.join(success_messages)}"
                await self._show_success_dialog(message)
            else:
                print("WARNING: No data was imported")
            
            # Update current tab content
            current_tab = self.form_app.rail.selected_index
            self.form_app.update_form_content(current_tab)
            
        except Exception as e:
            print(f"ERROR in import_all_data: {e}")
            import traceback
            traceback.print_exc()
            await self.form_app.show_error_dialog([f"Error importing data: {str(e)}"])

    async def _import_project_info(self, data: Dict[str, str]):
        self.form_app.section_data['project info'] = data
        print(f"Imported Project Info: {data}")

    async def _import_geometry(self, data: Dict[str, str]):
        # Ensure geometry section is initialized
        geometry_section = self.form_app.sections[1]  # Geometry section index
        
        # Create the geometry UI if it doesn't exist
        if not hasattr(geometry_section, 'form_content') or geometry_section.form_content is None:
            geometry_section.form_content = geometry_section.build_section_ui()
        
        # Now import using the direct method
        geometry_section.import_from_dict(data)
        print(f"Imported Geometry: {data}")
        # Update the UI
        if self.form_app.page:
            self.form_app.page.update()

    async def _update_geometry_ui_fields(self, data: Dict[str, str]):
        """Update geometry UI fields directly"""
        try:
            print("DEBUG: Starting geometry UI field update")
            
            # Method 1: Try to access through form_manager
            if (hasattr(self.form_app, 'form_manager') and 
                hasattr(self.form_app.form_manager, 'geometry_section')):
                
                geometry_section = self.form_app.form_manager.geometry_section
                
                # Look for field controls in the geometry section
                if hasattr(geometry_section, 'controls'):
                    self._update_controls_with_data(geometry_section.controls, data)
                    print("DEBUG: Updated geometry fields via form_manager.geometry_section.controls")
                
                # Try to access individual field attributes
                field_mapping = {
                    'Excavation Type': 'excavation_type_dropdown',
                    'Over Excavation': 'over_excavation_field',
                    'Excavation Below Strut': 'excavation_below_strut_field',
                    'Wall Top Level': 'wall_top_level_field',
                    'Excavation Depth': 'excavation_depth_field',
                    'Excavation Width': 'excavation_width_field',
                    'Toe Level': 'toe_level_field',
                    'No of Strut': 'no_of_strut_field',
                    'Strut Type': 'strut_type_dropdown',
                    'Wall Type': 'wall_type_dropdown',
                    'Material': 'material_dropdown',
                    'Member Size': 'member_size_dropdown',
                    'Spacing': 'spacing_field',
                    'Borehole X Coordinate': 'borehole_x_coordinate_field',
                    'Ground Water Table': 'ground_water_table_field',
                    'Strut 1 Level': 'strut_1_level_field',
                    'Strut 1 Material': 'strut_1_material_dropdown',
                    'Strut 1 Member Size': 'strut_1_member_size_dropdown',
                    'Strut 2 Level': 'strut_2_level_field',
                    'Strut 2 Material': 'strut_2_material_dropdown',
                    'Strut 2 Member Size': 'strut_2_member_size_dropdown'
                }
                
                for field_label, field_attr in field_mapping.items():
                    if field_label in data and hasattr(geometry_section, field_attr):
                        field_control = getattr(geometry_section, field_attr)
                        if field_control:
                            field_control.value = data[field_label]
                            print(f"DEBUG: Updated {field_label} = {data[field_label]}")
                
            # Method 2: Try to access through the current form content
            elif hasattr(self.form_app, 'current_form_content'):
                self._update_controls_with_data([self.form_app.current_form_content], data)
                print("DEBUG: Updated geometry fields via current_form_content")
            
            # Method 3: Force update by switching to geometry tab and back
            current_tab = self.form_app.rail.selected_index
            self.form_app.rail.selected_index = 1  # Geometry tab
            self.form_app.update_form_content(1)
            
            # Update the form content with imported data
            if hasattr(self.form_app, 'current_form_content'):
                self._update_controls_with_data([self.form_app.current_form_content], data)
            
            # Update the UI
            self.form_app.page.update()
            
            print("DEBUG: Completed geometry UI field update")
            
        except Exception as e:
            print(f"Error updating geometry UI fields: {e}")

    def _update_controls_with_data(self, controls, data: Dict[str, str]):
        """Recursively update form controls with imported data"""
        try:
            for control in controls:
                if isinstance(control, ft.TextField):
                    # Check label or hint_text to match with data
                    field_key = None
                    if hasattr(control, 'label') and control.label:
                        field_key = control.label
                    elif hasattr(control, 'hint_text') and control.hint_text:
                        field_key = control.hint_text
                    
                    if field_key and field_key in data:
                        control.value = data[field_key]
                        print(f"DEBUG: Updated TextField {field_key} = {data[field_key]}")
                        
                elif isinstance(control, ft.Dropdown):
                    # Check label to match with data
                    field_key = None
                    if hasattr(control, 'label') and control.label:
                        field_key = control.label
                    
                    if field_key and field_key in data:
                        control.value = data[field_key]
                        print(f"DEBUG: Updated Dropdown {field_key} = {data[field_key]}")
                        
                elif hasattr(control, 'controls') and control.controls:
                    # Recursively check child controls
                    self._update_controls_with_data(control.controls, data)
                    
                elif hasattr(control, 'content') and hasattr(control.content, 'controls'):
                    # Check content controls
                    self._update_controls_with_data(control.content.controls, data)
                    
        except Exception as e:
            print(f"Error in _update_controls_with_data: {e}")

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
        """Import sequence construction data into the sequence construction section"""
        try:
            print("DEBUG: *** ENTERING _import_sequence_construction ***")
            print(f"DEBUG: Data received: {data}")
            print(f"DEBUG: Data type: {type(data)}")
            print(f"DEBUG: Data length: {len(data)}")
            
            # Store data in section_data
            self.form_app.section_data['sequence construct'] = data
            print("DEBUG: Stored data in form_app.section_data['sequence construct']")
            
            # Method 1: Try to access sequence construction section directly through sections array
            sequence_section = None
            if hasattr(self.form_app, 'sections') and len(self.form_app.sections) > 4:
                sequence_section = self.form_app.sections[4]  # Sequence construction is typically index 4
                print("DEBUG: Found sequence section via sections array")
                print(f"DEBUG: Sequence section type: {type(sequence_section)}")
                print(f"DEBUG: Sequence section class: {sequence_section.__class__.__name__ if hasattr(sequence_section, '__class__') else 'No class'}")
            
            # Method 2: Try to access through form_manager
            elif (hasattr(self.form_app, 'form_manager') and 
                  hasattr(self.form_app.form_manager, 'sequence_construct_section')):
                sequence_section = self.form_app.form_manager.sequence_construct_section
                print("DEBUG: Found sequence section via form_manager")
            
            # Method 3: Search through all sections to find the sequence construction section
            elif hasattr(self.form_app, 'sections'):
                print(f"DEBUG: Searching through {len(self.form_app.sections)} sections")
                for i, section in enumerate(self.form_app.sections):
                    print(f"DEBUG: Section {i}: {section.__class__.__name__ if hasattr(section, '__class__') else 'No class'}")
                    if hasattr(section, '__class__') and 'Sequence' in section.__class__.__name__:
                        sequence_section = section
                        print(f"DEBUG: Found sequence section by class name: {section.__class__.__name__}")
                        break
            
            if sequence_section:
                print("DEBUG: Attempting to import data into sequence section")
                
                # Use the import_from_list method if available
                if hasattr(sequence_section, 'import_from_list'):
                    print("DEBUG: Using import_from_list method")
                    sequence_section.import_from_list(data)
                    print("DEBUG: import_from_list method completed")
                
                # Alternative: Try to update table directly
                elif hasattr(sequence_section, 'update_form_content'):
                    print("DEBUG: Using update_form_content method")
                    # Convert list of dicts to column format
                    column_data = {}
                    for item in data:
                        for key, value in item.items():
                            if key not in column_data:
                                column_data[key] = []
                            column_data[key].append(value)
                    
                    sequence_section.update_form_content(0, column_data)
                    print("DEBUG: update_form_content method completed")
                
                # Store in section's internal data structure if available
                if hasattr(sequence_section, 'section_data'):
                    sequence_section.section_data = data
                    print("DEBUG: Stored data in section's section_data")
                
                # Try additional methods
                if hasattr(sequence_section, 'load_data'):
                    print("DEBUG: Using load_data method")
                    sequence_section.load_data(data)
                
                if hasattr(sequence_section, 'populate_table'):
                    print("DEBUG: Using populate_table method")
                    sequence_section.populate_table(data)
                
                print(f"DEBUG: Successfully processed {len(data)} sequence construction records")
            else:
                print("WARNING: Could not find sequence construction section for import")
                # Try to find any section containing sequence-related functionality
                if hasattr(self.form_app, 'sections'):
                    print("DEBUG: Available sections:")
                    for i, section in enumerate(self.form_app.sections):
                        section_name = section.__class__.__name__ if hasattr(section, '__class__') else str(type(section))
                        print(f"  Section {i}: {section_name}")
                        
                        # Check for any sequence-related attributes or methods
                        if hasattr(section, '__dict__'):
                            attrs = [attr for attr in dir(section) if 'sequence' in attr.lower()]
                            if attrs:
                                print(f"    Sequence-related attributes: {attrs}")
            
            # Try to update via form_manager if available
            if (hasattr(self.form_app, 'form_manager') and 
                hasattr(self.form_app.form_manager, 'update_sequence_table')):
                print("DEBUG: Updating sequence table via form_manager")
                self.form_app.form_manager.update_sequence_table(data)
            
            # Force UI update
            if hasattr(self.form_app, 'page') and self.form_app.page:
                print("DEBUG: Updating UI page")
                self.form_app.page.update()
            
            print(f"DEBUG: *** COMPLETED _import_sequence_construction *** - Imported {len(data)} records")
            
        except Exception as e:
            print(f"ERROR in _import_sequence_construction: {e}")
            import traceback
            traceback.print_exc()

    async def _show_success_dialog(self, message: str):
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Import Successful"),
            content=ft.Text(message),
            actions=[
                ft.TextButton("OK", on_click=lambda e: self._close_dialog())
            ],
        )
        self.form_app.page.dialog = dialog
        dialog.open = True
        self.form_app.page.update()

    def _close_dialog(self):
        if self.form_app.page.dialog:
            self.form_app.page.dialog.open = False
            self.form_app.page.update()