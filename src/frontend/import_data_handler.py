import flet as ft
from typing import Dict
from frontend.database_connection import DatabaseConnection


class ImportDataHandler:
    def __init__(self, form_app):
        self.form_app = form_app
        self.db_config = form_app.db_config
        self.current_file_section_index = None
        
        # Initialize file picker
        self.file_picker = ft.FilePicker(on_result=self.handle_csv_file_selection)
    
    def get_file_picker(self):
        """Return the file picker for adding to page overlay"""
        return self.file_picker
    
    def open_file_picker(self, e, section_index: int):
        """Open file picker for CSV import"""
        self.current_file_section_index = section_index
        self.file_picker.pick_files(
            allowed_extensions=["csv"],
            dialog_title="Select a CSV file",
        )
    
    async def handle_csv_file_selection(self, e: ft.FilePickerResultEvent):
      """Handle CSV file selection and import data"""
      if e.files:
        csv_file_path = e.files[0].path
        section_index = self.current_file_section_index
        try:
            with DatabaseConnection(self.db_config) as db:
                if section_index == 0:
                    self.form_app.sections[0].import_from_csv(csv_file_path, db.cursor)
                    db.connection.commit()
                    print("Geological data imported successfully!")
                    self.update_form_with_csv_data(csv_file_path)
                elif section_index == 1:
                    # **IMPORTANT**: Import geometry data and store it
                    self.form_app.sections[1].import_from_csv(csv_file_path, db.cursor)
                    db.connection.commit()
                    
                    # **STORE THE IMPORTED DATA** in section_data
                    imported_data = self.form_app.sections[1].form_values.copy()
                    self.form_app.section_data['geometry'] = imported_data
                    
                    # **FORCE UI UPDATE** with the imported data
                    self.form_app.update_form_content(1, imported_data)
                    
                    print("Geometry data imported successfully!")
                elif section_index == 2:
                    self.form_app.sections[2].import_from_csv(csv_file_path, db.cursor)
                    db.connection.commit()
                    print("Borehole data imported successfully!")
                elif section_index == 3:
                    self.form_app.sections[3].import_from_csv(csv_file_path, db.cursor)
                    db.connection.commit()
                    imported_data = self.form_app.collect_section_data(3)
                    self.form_app.section_data['excavation'] = imported_data
                    self.form_app.update_form_content(3, imported_data)
                    print("Excavation data imported successfully!")
                elif section_index == 4:
                    imported_data = self.form_app.sections[4].import_from_csv(csv_file_path, db.cursor)
                    self.form_app.section_data['sequence construct'] = imported_data
                    self.form_app.update_form_content(4, imported_data)
                    print("Sequence data imported successfully!")
                else:
                    raise ValueError(f"Invalid section index: {section_index}")
        except Exception as ex:
            print(f"Error importing CSV data: {ex}")
            await self.form_app.show_error_dialog([f"Error importing CSV data: {ex}"])
      else:
          print("No file selected.")
    
    def update_form_with_csv_data(self, csv_file_path: str):
        """Update form with CSV data for geological section"""
        data = self.form_app.sections[0].read_from_csv(csv_file_path)
        if data:
            self._populate_form_fields(self.form_app.form_content, data)
            self.form_app.form_content.update()
    
    def _populate_form_fields(self, form_section: ft.Column, data: Dict):
        """Populate form fields with imported data"""
        for row in form_section.controls:
            if isinstance(row, ft.Row):
                for control in row.controls:
                    if isinstance(control, (ft.TextField, ft.Dropdown)):
                        label = control.label.split(" (Set")[0].split(" *")[0]
                        if label in data:
                            control.value = data[label]