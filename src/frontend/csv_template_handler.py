import flet as ft
import os
import csv
from typing import Dict, List, Optional, Callable
import tempfile
from datetime import datetime
import io


class CSVTemplateHandler:
    def __init__(self, form_app, page: ft.Page):
        self.form_app = form_app
        self.page = page
        self.templates = self._get_available_templates()
        # Store reference to avoid None issues
        self._page_ref = page
        self._page_getter = None  # Function to get current page
        
        # Initialize file picker for directory selection
        self.directory_picker = ft.FilePicker(
            on_result=self._on_directory_selected
        )
        self._pending_template_key = None  # Store which template is being downloaded
        
        # Add file picker to page if available
        if self.page:
            self.page.overlay.append(self.directory_picker)
    
    def set_page_getter(self, page_getter: Callable[[], ft.Page]):
        """Set a function that returns the current page"""
        self._page_getter = page_getter
    
    def _get_current_page(self) -> Optional[ft.Page]:
        """Get the current page, trying multiple methods"""
        # Try the page getter function first
        if self._page_getter:
            try:
                return self._page_getter()
            except:
                pass
        
        # Try the stored page reference
        if self.page is not None:
            return self.page
        
        # Try the backup reference
        if self._page_ref is not None:
            return self._page_ref
        
        # Try getting from form_app if it has a page attribute
        if hasattr(self.form_app, 'page') and self.form_app.page is not None:
            return self.form_app.page
        
        return None
    
    def _get_available_templates(self) -> Dict[str, Dict]:
        """Define available CSV templates with their structure"""
        return {
            # Original Geotechnical Analysis Templates
            "project_info": {
                "name": "Project Info Template",
                "description": "Template for project information and basic settings",
                "filename": "project_info_template.csv",
                "headers": [
                    "Project Title", "Section", "Model Type", "Element Type", 
                    "Borehole Type", "Borehole", "Design Approach"
                ],
                "sample_data": [
                    ["MyProject", "A", "Plane Strain", "6-Node", "Manual", "BH-1", "SLS"],
                    ["SampleProject", "B", "Axisymmetric", "15-Node", "Auto", "BH-2", "ULS"],
                    ["TestProject", "C", "Plane Strain", "6-Node", "Manual", "BH-3", "SLS"]
                ]
            },
            "geometry": {
                "name": "Geometry Template",
                "description": "Template for excavation geometry and structural elements",
                "filename": "geometry_template.csv",
                "headers": [
                    "Excavation Type", "Over Excavation", "Excavation Below Strut", 
                    "Wall Top Level", "Excavation Depth", "Excavation Width", "Toe Level", 
                    "No of Strut", "Strut Type", "Wall Type", "Material", "Member Size", 
                    "Spacing", "Borehole X Coordinate", "Ground Water Table", "Strut 1 Level", 
                    "Strut 1 Material", "Strut 1 Member Size", "Strut 2 Level", 
                    "Strut 2 Material", "Strut 2 Member Size"
                ],
                "sample_data": [
                    ["Double wall", "0.5", "1", "100", "10", "10", "80", "2", "Node to Node", 
                     "Sheet Pile", "Steel", "762x267x173", "2", "-10", "100", "98", "Steel", 
                     "203x203x71", "95", "Steel", "203x203x86"],
                    ["Single wall", "0.3", "0.5", "105", "8", "12", "85", "1", "Waler to Waler", 
                     "Diaphragm Wall", "Concrete", "800x1000", "3", "-12", "102", "97", "Steel", 
                     "254x254x89", "", "", ""],
                    ["Cantilever", "0", "0", "95", "6", "8", "82", "0", "", 
                     "Bored Pile", "Concrete", "600mm dia", "1.5", "-8", "93", "", "", 
                     "", "", "", ""]
                ]
            },
            "borehole": {
                "name": "Borehole Template",
                "description": "Template for soil borehole data and properties",
                "filename": "borehole_template.csv",
                "headers": [
                    "Soil Type", "SPT", "Top Depth", "Bottom Depth", "Gamma Unsat", 
                    "Gamma Sat", "E ref", "Nu", "C '", "Phi '", "Kx", "Ky", 
                    "R inter", "K0 Primary", "Drain Type"
                ],
                "sample_data": [
                    ["Fill", "10", "100", "97", "16.5", "19.5", "15000", "0.35", "5", "25", 
                     "0.001", "0.001", "0.5", "0.6", "Undrain"],
                    ["Soft Clay", "5", "97", "90", "15.8", "18.8", "8000", "0.40", "10", "20", 
                     "0.0001", "0.0001", "0.4", "0.7", "Drain"],
                    ["Dense Sand", "35", "90", "85", "18.5", "20.5", "45000", "0.30", "0", "38", 
                     "0.01", "0.01", "0.7", "0.4", "Drain"],
                    ["Stiff Clay", "25", "85", "80", "17.2", "19.8", "25000", "0.35", "20", "28", 
                     "0.0005", "0.0005", "0.6", "0.5", "Undrain"]
                ]
            },
            "excavation": {
                "name": "Excavation Stages Template",
                "description": "Template for excavation stages and construction sequence",
                "filename": "excavation_template.csv",
                "headers": [
                    "Stage No", "Stage Name", "From", "To"
                ],
                "sample_data": [
                    ["1", "Excavate to Stage 1", "100.0", "97.5"],
                    ["2", "Install First Strut", "97.5", "97.5"],
                    ["3", "Excavate to Stage 2", "97.5", "95.0"],
                    ["4", "Install Second Strut", "95.0", "95.0"],
                    ["5", "Final Excavation", "95.0", "90.0"]
                ]
            },
            "sequence_construction": {
                "name": "Construct Sequence Template",
                "description": "Template for construction sequence phases and actions",
                "filename": "sequence_construction_template.csv",
                "headers": [
                    "Phase No", "Phase Name", "Element Type", "Element Name", "Action"
                ],
                "sample_data": [
                    ["1", "Activate Live Load", "Line Load", "LL_Left", "Activate"],
                    ["2", "Activate Live Load", "Line Load", "LL_Right", "Activate"],
                    ["3", "Install Wall", "Structural Element", "Retaining_Wall", "Install"],
                    ["4", "First Excavation", "Soil Cluster", "Soil_Layer_1", "Remove"],
                    ["5", "Install First Strut", "Structural Element", "Strut_1", "Install"],
                    ["6", "Second Excavation", "Soil Cluster", "Soil_Layer_2", "Remove"]
                ]
            },
            
                      
        }
    
    def create_template_selection_view(self) -> ft.Container:
        """Create the main template selection interface"""
        template_cards = []
        
        for template_key, template_info in self.templates.items():
            card = ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(
                                self._get_template_icon(template_key),
                                color=ft.colors.BLUE_600,
                                size=24
                            ),
                            ft.Text(
                                template_info["name"],
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.GREY_800
                            )
                        ], spacing=10),
                        ft.Container(height=8),
                        ft.Text(
                            template_info["description"],
                            size=12,
                            color=ft.colors.GREY_600,
                            max_lines=2
                        ),
                        ft.Container(height=10),
                        ft.Text(
                            f"Fields: {len(template_info['headers'])}",
                            size=11,
                            color=ft.colors.GREY_500
                        ),
                        ft.Container(height=15),
                        ft.Row([
                            ft.ElevatedButton(
                                "Download",
                                on_click=lambda e, key=template_key: self.select_download_location(key),
                                icon=ft.icons.DOWNLOAD,
                                style=ft.ButtonStyle(
                                    color=ft.colors.WHITE,
                                    bgcolor=ft.colors.GREEN_600,
                                    padding=ft.padding.symmetric(horizontal=20, vertical=8),
                                    shape=ft.RoundedRectangleBorder(radius=6)
                                )
                            ),
                            ft.TextButton(
                                "Preview",
                                on_click=lambda e, key=template_key: self.preview_template(key),
                                icon=ft.icons.PREVIEW,
                                style=ft.ButtonStyle(
                                    color=ft.colors.BLUE_600
                                )
                            )
                        ], spacing=10)
                    ], spacing=5),
                    padding=20,
                    width=280
                ),
                elevation=2,
                margin=ft.margin.all(10)
            )
            template_cards.append(card)
        
        # Arrange cards in a grid
        card_rows = []
        for i in range(0, len(template_cards), 2):
            row_cards = template_cards[i:i+2]
            card_rows.append(
                ft.Row(
                    row_cards,
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                )
            )
        
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.DOWNLOAD_FOR_OFFLINE, color=ft.colors.GREEN_600, size=24),
                        ft.Text("Download CSV Templates", size=20, weight=ft.FontWeight.BOLD),
                    ], spacing=10),
                    padding=ft.padding.only(bottom=20),
                ),
                ft.Container(
                    content=ft.Text(
                        "Download pre-configured CSV templates for importing data into your projects. "
                        "Each template includes proper headers and sample data to help you get started.",
                        size=14,
                        color=ft.colors.GREY_600,
                        text_align=ft.TextAlign.CENTER
                    ),
                    padding=ft.padding.only(bottom=30),
                    width=600
                ),
                ft.Column(card_rows, spacing=15)
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10),
            padding=20,
            alignment=ft.alignment.center
        )
    
    def _get_template_icon(self, template_key: str) -> str:
        """Get appropriate icon for each template type"""
        icon_map = {
            "soil_parameters": ft.icons.TERRAIN,
            "geometry_points": ft.icons.CONTROL_POINT,
            "load_cases": ft.icons.FITNESS_CENTER,
            "material_properties": ft.icons.SCIENCE
        }
        return icon_map.get(template_key, ft.icons.TABLE_CHART)
    
    def select_download_location(self, template_key: str):
      """Show location selection dialog before downloading"""
      try:
        current_page = self._get_current_page()
        if current_page is None:
            # Fallback to default download
            self.download_template_to_default(template_key)
            return
        
        # Ensure file picker is in overlay
        if self.directory_picker not in current_page.overlay:
            current_page.overlay.append(self.directory_picker)
            current_page.update()
        
        # Store which template we're downloading
        self._pending_template_key = template_key
        
        # Show location selection dialog
        template_info = self.templates[template_key]
        location_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.FOLDER_OPEN, color=ft.colors.BLUE_600, size=20),  # Reduced icon size
                ft.Text("Select Download Location", size=16)  # Reduced title size
            ], spacing=8),  # Reduced spacing
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        f"Select where to save '{template_info['name']}'",
                        size=13,  # Reduced font size
                        color=ft.colors.GREY_700
                    ),
                    ft.Container(height=6),  # Reduced height
                    ft.Row([
                        ft.Icon(ft.icons.INFO_OUTLINE, color=ft.colors.BLUE_500, size=14),  # Reduced icon size
                        ft.Text(
                            f"File: {template_info['filename']}",  # Shortened text
                            size=11,  # Reduced font size
                            color=ft.colors.GREY_600
                        )
                    ], spacing=6)  # Reduced spacing
                ], spacing=0),  # Removed spacing between column items
                width=320,  # Reduced width
                height=60   # Set explicit height to control dialog size
            ),
            actions=[
                ft.ElevatedButton(
                    "Browse",  # Shortened text
                    icon=ft.icons.FOLDER_OPEN,
                    on_click=lambda e: self._open_directory_picker(),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.BLUE_600,
                        padding=ft.padding.symmetric(horizontal=16, vertical=6)  # Reduced padding
                    )
                ),
                ft.TextButton(
                    "Default",  # Shortened text
                    on_click=lambda e: self._use_default_location(location_dialog),
                    style=ft.ButtonStyle(
                        color=ft.colors.GREEN_600,
                        padding=ft.padding.symmetric(horizontal=12, vertical=6)  # Reduced padding
                    )
                ),
                ft.TextButton(
                    "Cancel",
                    on_click=lambda e: self._close_dialog(location_dialog),
                    style=ft.ButtonStyle(
                        padding=ft.padding.symmetric(horizontal=12, vertical=6)  # Reduced padding
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            # Make the overall dialog more compact
            content_padding=ft.padding.all(16),  # Reduced content padding
            actions_padding=ft.padding.only(left=16, right=16, bottom=12, top=8)  # Reduced actions padding
        )
        
        current_page.dialog = location_dialog
        location_dialog.open = True
        current_page.update()
        
      except Exception as e:
        self._show_error(f"Error showing location dialog: {str(e)}")
        # Fallback to default download
        self.download_template_to_default(template_key) 
    def _open_directory_picker(self):
        """Open the directory picker"""
        try:
            self.directory_picker.get_directory_path()
        except Exception as e:
            self._show_error(f"Error opening directory picker: {str(e)}")
            # Fallback to default location
            if self._pending_template_key:
                self.download_template_to_default(self._pending_template_key)
    
    def _use_default_location(self, dialog: ft.AlertDialog):
        """Use default download location"""
        self._close_dialog(dialog)
        if self._pending_template_key:
            self.download_template_to_default(self._pending_template_key)
    
    def _on_directory_selected(self, e: ft.FilePickerResultEvent):
        """Handle directory selection from file picker"""
        try:
            if e.path and self._pending_template_key:
                # Close any open dialogs first
                current_page = self._get_current_page()
                if current_page and current_page.dialog:
                    current_page.dialog.open = False
                    current_page.update()
                
                # Download to selected location
                self.download_template_to_location(self._pending_template_key, e.path)
            else:
                # No path selected or no pending template
                if self._pending_template_key:
                    self._show_error("No location selected. Using default location.")
                    self.download_template_to_default(self._pending_template_key)
        except Exception as ex:
            self._show_error(f"Error processing selected location: {str(ex)}")
            if self._pending_template_key:
                self.download_template_to_default(self._pending_template_key)
        finally:
            self._pending_template_key = None
    
    def download_template_to_location(self, template_key: str, directory_path: str):
        """Download template to specified location"""
        try:
            if template_key not in self.templates:
                self._show_error("Template not found")
                return
            
            template = self.templates[template_key]
            
            # Create full file path
            file_path = os.path.join(directory_path, template["filename"])
            
            # Check if file already exists
            if os.path.exists(file_path):
                self._show_file_exists_dialog(template_key, file_path)
                return
            
            # Write CSV file
            self._write_csv_file(template, file_path)
            
            # Show success message with location
            self._show_download_success(template["name"], file_path)
            
        except Exception as e:
            self._show_error(f"Error downloading template: {str(e)}")
    
    def download_template_to_default(self, template_key: str):
        """Download template to default location (user's Downloads folder or current directory)"""
        try:
            if template_key not in self.templates:
                self._show_error("Template not found")
                return
            
            template = self.templates[template_key]
            
            # Try to get Downloads folder, fallback to current directory
            default_path = self._get_default_download_path()
            file_path = os.path.join(default_path, template["filename"])
            
            # Handle duplicate files
            file_path = self._get_unique_file_path(file_path)
            
            # Write CSV file
            self._write_csv_file(template, file_path)
            
            # Show success message with location
            self._show_download_success(template["name"], file_path)
            
        except Exception as e:
            self._show_error(f"Error downloading template: {str(e)}")
    
    def _get_default_download_path(self) -> str:
        """Get default download path"""
        try:
            # Try to get user's Downloads folder
            home = os.path.expanduser("~")
            downloads_path = os.path.join(home, "Downloads")
            
            if os.path.exists(downloads_path):
                return downloads_path
            else:
                # Fallback to home directory
                return home
        except:
            # Final fallback to current directory
            return os.getcwd()
    
    def _get_unique_file_path(self, file_path: str) -> str:
        """Get unique file path by adding number suffix if file exists"""
        if not os.path.exists(file_path):
            return file_path
        
        base, ext = os.path.splitext(file_path)
        counter = 1
        
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        
        return f"{base}_{counter}{ext}"
    
    def _write_csv_file(self, template: Dict, file_path: str):
        """Write CSV file with proper encoding"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(template["headers"])
            writer.writerows(template["sample_data"])
    
    def _show_file_exists_dialog(self, template_key: str, file_path: str):
        """Show dialog when file already exists"""
        current_page = self._get_current_page()
        if current_page is None:
            # Auto-rename and download
            unique_path = self._get_unique_file_path(file_path)
            template = self.templates[template_key]
            self._write_csv_file(template, unique_path)
            self._show_download_success(template["name"], unique_path)
            return
        
        exists_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.WARNING, color=ft.colors.ORANGE_600),
                ft.Text("File Already Exists")
            ]),
            content=ft.Column([
                ft.Text(f"A file with the name already exists at:"),
                ft.Container(height=5),
                ft.Text(
                    file_path,
                    size=12,
                    color=ft.colors.GREY_600,
                    selectable=True
                ),
                ft.Text("What would you like to do?")
            ]),
            actions=[
                ft.ElevatedButton(
                    "Replace",
                    icon=ft.icons.REFRESH,
                    on_click=lambda e: self._replace_file(template_key, file_path, exists_dialog),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.ORANGE_600
                    )
                ),
                ft.ElevatedButton(
                    "Keep Both",
                    icon=ft.icons.CONTENT_COPY,
                    on_click=lambda e: self._keep_both_files(template_key, file_path, exists_dialog),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.BLUE_600
                    )
                ),
                ft.TextButton(
                    "Cancel",
                    on_click=lambda e: self._close_dialog(exists_dialog)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        current_page.dialog = exists_dialog
        exists_dialog.open = True
        current_page.update()
    
    def _replace_file(self, template_key: str, file_path: str, dialog: ft.AlertDialog):
        """Replace existing file"""
        self._close_dialog(dialog)
        template = self.templates[template_key]
        self._write_csv_file(template, file_path)
        self._show_download_success(template["name"], file_path)
    
    def _keep_both_files(self, template_key: str, file_path: str, dialog: ft.AlertDialog):
        """Keep both files by creating unique name"""
        self._close_dialog(dialog)
        unique_path = self._get_unique_file_path(file_path)
        template = self.templates[template_key]
        self._write_csv_file(template, unique_path)
        self._show_download_success(template["name"], unique_path)
    
    def _show_download_success(self, template_name: str, file_path: str):
      """Show success message with download location - Compact version"""
      try:
        current_page = self._get_current_page()
        if current_page is None:
            print(f"Success: Template '{template_name}' downloaded to: {file_path}")
            return
        
        success_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN_600, size=20),
                ft.Text("Download Successful!", size=16)
            ], spacing=8),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        f"'{template_name}' downloaded successfully.",
                        size=13,
                        max_lines=1
                    ),
                    ft.Container(height=8),  # Reduced spacing
                    ft.Text("Saved to:", size=11, weight=ft.FontWeight.BOLD),
                    ft.Container(height=4),  # Reduced spacing
                    ft.Container(
                        content=ft.Text(
                            file_path,
                            size=10,  # Smaller font
                            color=ft.colors.GREY_600,
                            selectable=True,
                            max_lines=2,  # Limit to 2 lines
                            overflow=ft.TextOverflow.ELLIPSIS
                        ),
                        padding=ft.padding.all(6),  # Reduced padding
                        bgcolor=ft.colors.GREY_100,
                        border_radius=4,
                        border=ft.border.all(1, ft.colors.GREY_300)
                    )
                ], spacing=2),  # Reduced spacing between elements
                width=380,  # Reduced width
                height=90   # Set explicit height
            ),
            actions=[
                ft.ElevatedButton(
                    "Open Folder",
                    icon=ft.icons.FOLDER_OPEN,
                    on_click=lambda e: self._open_file_location(file_path, success_dialog),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.BLUE_600,
                        padding=ft.padding.symmetric(horizontal=14, vertical=6)
                    )
                ),
                ft.TextButton(
                    "OK",
                    on_click=lambda e: self._close_dialog(success_dialog),
                    style=ft.ButtonStyle(
                        padding=ft.padding.symmetric(horizontal=12, vertical=6)
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END,
            content_padding=ft.padding.all(16),
            actions_padding=ft.padding.only(left=16, right=16, bottom=12, top=8)
        )
        
        current_page.dialog = success_dialog
        success_dialog.open = True
        current_page.update()
        
      except Exception as e:
        print(f"Error showing success dialog: {e}")
        print(f"Success: Template '{template_name}' downloaded to: {file_path}")
    def _open_file_location(self, file_path: str, dialog: ft.AlertDialog):
        """Open file location in system file manager"""
        try:
            import platform
            import subprocess
            
            if platform.system() == "Windows":
                subprocess.run(f'explorer /select,"{file_path}"', shell=True)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", "-R", file_path])
            else:  # Linux
                subprocess.run(["xdg-open", os.path.dirname(file_path)])
            
            self._close_dialog(dialog)
            
        except Exception as e:
            print(f"Error opening file location: {e}")
            # Just close the dialog if we can't open the location
            self._close_dialog(dialog)
    
    def download_template(self, template_key: str):
        """Legacy method - redirects to location selection"""
        self.select_download_location(template_key)
    
    def preview_template(self, template_key: str):
      """Show template preview in a dialog with horizontal scrolling"""
      try:
        current_page = self._get_current_page()
        if current_page is None:
            print(f"Cannot show preview - page not available")
            self._show_console_preview(template_key)
            return
            
        if template_key not in self.templates:
            return
        
        template = self.templates[template_key]
        
        # Create preview table with better scrolling
        preview_rows = []
        
        # Header row
        header_cells = []
        for header in template["headers"]:
            header_cells.append(
                ft.Container(
                    content=ft.Text(
                        header, 
                        size=12, 
                        weight=ft.FontWeight.BOLD,
                        color=ft.colors.WHITE
                    ),
                    padding=ft.padding.all(8),
                    bgcolor=ft.colors.BLUE_600,
                    border=ft.border.all(1, ft.colors.BLUE_700),
                    width=120,
                    alignment=ft.alignment.center
                )
            )
        preview_rows.append(ft.Row(header_cells, spacing=1))
        
        # Sample data rows
        for i, row_data in enumerate(template["sample_data"][:5]):  # Show first 5 rows
            data_cells = []
            bg_color = ft.colors.GREY_50 if i % 2 == 0 else ft.colors.WHITE
            
            for cell in row_data:
                data_cells.append(
                    ft.Container(
                        content=ft.Text(
                            str(cell), 
                            size=11,
                            color=ft.colors.GREY_800
                        ),
                        padding=ft.padding.all(8),
                        bgcolor=bg_color,
                        border=ft.border.all(1, ft.colors.GREY_300),
                        width=120,
                        alignment=ft.alignment.center
                    )
                )
            preview_rows.append(ft.Row(data_cells, spacing=1))
        
        # Create the table content with both horizontal and vertical scrolling
        table_content = ft.Column(preview_rows, spacing=1)
        
        # Wrap in a horizontally scrollable container first
        horizontally_scrollable = ft.Row(
            [table_content],
            scroll=ft.ScrollMode.AUTO,  # Enable horizontal scrolling
        )
        
        # Then wrap in a vertically scrollable container
        preview_content = ft.Container(
            content=ft.Column(
                [horizontally_scrollable],
                scroll=ft.ScrollMode.AUTO,  # Enable vertical scrolling
                expand=True
            ),
            padding=10,
            bgcolor=ft.colors.WHITE,
            border_radius=8,
            border=ft.border.all(1, ft.colors.GREY_300),
            width=800,  # Fixed width for the container
            height=300,  # Fixed height for the container
        )
        
        # Create dialog content
        dialog_content = ft.Column([
            ft.Text(
                template["description"],
                size=14,
                color=ft.colors.GREY_600
            ),
            ft.Container(height=10),
            ft.Text(
                f"Template contains {len(template['headers'])} fields and {len(template['sample_data'])} sample records:",
                size=12,
                color=ft.colors.GREY_500
            ),
            ft.Container(height=10),
            ft.Text(
                "💡 Tip: Use mouse wheel or drag to scroll horizontally and vertically",
                size=11,
                color=ft.colors.BLUE_600,
                italic=True
            ),
            ft.Container(height=5),
            preview_content
        ])
        
        preview_dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(self._get_template_icon(template_key), color=ft.colors.BLUE_600),
                ft.Text(f"Preview: {template['name']}")
            ]),
            content=ft.Container(
                content=dialog_content,
                width=850,
                height=450  # Slightly increased height to accommodate the tip
            ),
            actions=[
                ft.ElevatedButton(
                    "Download Template",
                    icon=ft.icons.DOWNLOAD,
                    on_click=lambda e: self._download_from_preview(template_key, preview_dialog),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.GREEN_600
                    )
                ),
                ft.TextButton(
                    "Close",
                    on_click=lambda e: self._close_dialog(preview_dialog)
                )
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )
        
        current_page.dialog = preview_dialog
        preview_dialog.open = True
        current_page.update()
        
      except Exception as e:
        self._show_error(f"Error previewing template: {str(e)}")
        # Fallback to console preview
        self._show_console_preview(template_key)
    
    def _show_console_preview(self, template_key: str):
        """Show preview in console when dialog is not available"""
        if template_key not in self.templates:
            return
        
        template = self.templates[template_key]
        print(f"\n=== Preview: {template['name']} ===")
        print(f"Description: {template['description']}")
        print(f"Fields: {len(template['headers'])}")
        print("\nHeaders:")
        print(" | ".join(template["headers"]))
        print("\nSample Data:")
        for i, row in enumerate(template["sample_data"][:3]):
            print(f"Row {i+1}: {' | '.join(map(str, row))}")
        print("=" * 50)
    
    def _download_from_preview(self, template_key: str, dialog: ft.AlertDialog):
        """Download template from preview dialog"""
        self._close_dialog(dialog)
        self.select_download_location(template_key)
    
    def _close_dialog(self, dialog: ft.AlertDialog):
        """Close dialog safely"""
        try:
            current_page = self._get_current_page()
            if current_page is not None:
                dialog.open = False
                current_page.update()
        except Exception as e:
            print(f"Error closing dialog: {e}")
    
    def _create_csv_content(self, template: Dict) -> str:
        """Create CSV content string"""
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(template["headers"])
        writer.writerows(template["sample_data"])
        return output.getvalue()
    
    def _is_page_available(self) -> bool:
        """Check if page is available and not None"""
        current_page = self._get_current_page()
        return current_page is not None and hasattr(current_page, 'dialog')
    
    def _show_success(self, message: str):
        """Show success message with fallback"""
        try:
            current_page = self._get_current_page()
            if current_page is None:
                print(f"Success: {message}")
                return
                
            success_dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN_600),
                    ft.Text("Success")
                ]),
                content=ft.Text(message),
                actions=[
                    ft.TextButton(
                        "OK",
                        on_click=lambda e: self._close_dialog(success_dialog)
                    )
                ]
            )
            current_page.dialog = success_dialog
            success_dialog.open = True
            current_page.update()
        except Exception as e:
            print(f"Error showing success message: {e}")
            print(f"Success: {message}")
    
    def _show_error(self, message: str):
        """Show error message with fallback"""
        try:
            current_page = self._get_current_page()
            if current_page is None:
                print(f"Error: {message}")
                return
                
            error_dialog = ft.AlertDialog(
                title=ft.Row([
                    ft.Icon(ft.icons.ERROR, color=ft.colors.RED_600),
                    ft.Text("Error")
                ]),
                content=ft.Text(message),
                actions=[
                    ft.TextButton(
                        "OK",
                        on_click=lambda e: self._close_dialog(error_dialog)
                    )
                ]
            )
            current_page.dialog = error_dialog
            error_dialog.open = True
            current_page.update()
        except Exception as e:
            print(f"Error showing error message: {e}")
            print(f"Error: {message}")
    
    def _show_console_message(self, message: str):
        """Show message in console"""
        print(f"[CSV Template Handler] {message}")
    
    def get_template_stats(self) -> Dict:
        """Get statistics about available templates"""
        return {
            "total_templates": len(self.templates),
            "template_names": [template["name"] for template in self.templates.values()],
            "total_fields": sum(len(template["headers"]) for template in self.templates.values())
        }
    
    def update_page_reference(self, page: ft.Page):
        """Update the page reference if it changes"""
        self.page = page
        self._page_ref = page
        
        # Update file picker overlay
        if page and self.directory_picker not in page.overlay:
            page.overlay.append(self.directory_picker)
    
    def refresh_page_reference(self):
        """Refresh page reference from form_app"""
        if hasattr(self.form_app, 'page') and self.form_app.page is not None:
            self.page = self.form_app.page
            self._page_ref = self.form_app.page
            
            # Update file picker overlay
            if self.page and self.directory_picker not in self.page.overlay:
                self.page.overlay.append(self.directory_picker)