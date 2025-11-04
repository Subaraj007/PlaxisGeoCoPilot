import pandas as pd
import flet as ft
from pathlib import Path
import os
from typing import List, Dict, Any, Optional

class SoilDBHandler:
    def __init__(self, form_app):
        self.form_app = form_app
        self.soil_db_path = form_app.soil_db_path
        self.current_sheet_data = {}
        self.current_sheet_name = None
        self.clipboard_data = None
        self.clipboard_sheet_name = None
        self.rows_to_delete = {}

    def show_soil_db(self, e):
      """Show Soil DB management popup with list of databases and action icons"""
      sheet_names = self.load_existing_db_sheets()
    
    # Create clean white background container
      white_bg = ft.Container(
        width=500,
        height=600,
        bgcolor=ft.colors.WHITE,
        border_radius=20,
        padding=ft.padding.all(30),
    )

    # Header with icon and title
      header = ft.Container(
        content=ft.Column([
            ft.Container(height=15),
            ft.Text(
                "Soil Database Management",
                size=24,
                weight=ft.FontWeight.BOLD,
                color=ft.colors.GREY_800,
                text_align=ft.TextAlign.CENTER
            ),
            ft.Container(
                width=80,
                height=3,
                bgcolor=ft.colors.GREEN_400,
                border_radius=2,
                margin=ft.margin.only(top=8)
            )
        ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
        margin=ft.margin.only(bottom=30)
    )

    # Create database list items
      db_list_items = []
    
      if not sheet_names:
        # Show message when no databases exist
        no_db_message = ft.Container(
            content=ft.Column([
                ft.Icon(ft.icons.FOLDER_OPEN, size=60, color=ft.colors.GREY_400),
                ft.Text(
                    "No databases found",
                    size=16,
                    color=ft.colors.GREY_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Text(
                    "Create your first database",
                    size=12,
                    color=ft.colors.GREY_500,
                    text_align=ft.TextAlign.CENTER
                )
            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=40,
            alignment=ft.alignment.center
        )
        db_list_items.append(no_db_message)
      else:
        for sheet_name in sheet_names:
            sheet_info = self.get_sheet_info(sheet_name)
            row_count = sheet_info.get('row_count', 0)
            
            # Create database item with action buttons
            # Create database item with action buttons
            db_item = ft.Container(
                content=ft.Row([
                                # Database info section
                    ft.Container(
                        content=ft.Column([
                            ft.Text(
                                sheet_name,
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.GREY_800
                            ),
                            ft.Text(
                                f"{row_count} rows",
                                size=12,
                                color=ft.colors.GREY_600
                            )
                        ], spacing=2),
                        expand=True
                    ),
                    # Action buttons section
                    ft.Row([
                        ft.IconButton(
                            icon=ft.icons.EDIT,
                            icon_color=ft.colors.BLUE_600,
                            tooltip="Edit Database",
                            on_click=lambda e, name=sheet_name: self.view_sheet_data(name)
                        ),
                        ft.IconButton(
                            icon=ft.icons.COPY,
                            icon_color=ft.colors.GREEN_600,
                            tooltip="Copy Database",
                            on_click=lambda e, name=sheet_name: self.copy_sheet_data(name)
                        ),
                        ft.IconButton(
                            icon=ft.icons.DELETE,
                            icon_color=ft.colors.RED_600,
                            tooltip="Delete Database",
                            on_click=lambda e, name=sheet_name: self.confirm_delete_sheet(name)
                        )
                    ], spacing=5)
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                padding=ft.padding.all(15),
                margin=ft.margin.only(bottom=10),
                bgcolor=ft.colors.WHITE,
                border=ft.border.all(1, ft.colors.GREY_300),
                border_radius=10,
                shadow=ft.BoxShadow(
                    spread_radius=0,
                    blur_radius=3,
                    color=ft.colors.with_opacity(0.1, ft.colors.BLACK),
                    offset=ft.Offset(0, 2),
                )
            )
            db_list_items.append(db_item)

    # Create new database button
      create_new_btn = ft.Container(
        content=ft.ElevatedButton(
            content=ft.Row([
                ft.Icon(ft.icons.ADD, color=ft.colors.WHITE),
                ft.Text("Create New Database", color=ft.colors.WHITE, weight=ft.FontWeight.BOLD)
            ], alignment=ft.MainAxisAlignment.CENTER),
            on_click=lambda e: self.create_new_db_dialog(),
            style=ft.ButtonStyle(
                bgcolor=ft.colors.GREEN_600,
                padding=ft.padding.all(15),
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            width=400
        ),
        margin=ft.margin.only(top=20)
    )

    # Main content layout
      dialog_content = ft.Container(
        content=ft.Column([
            header,
            ft.Container(
                content=ft.Column(
                    db_list_items + [create_new_btn],
                    spacing=5,
                    scroll=ft.ScrollMode.AUTO
                ),
                height=400,
                expand=True
            )
        ]),
        padding=ft.padding.all(0)
    )

    # Enhanced dialog
      dialog = ft.AlertDialog(
        modal=True,
        content=ft.Container(
            content=dialog_content,
            width=500,
            padding=ft.padding.all(30),
            bgcolor=ft.colors.WHITE,
            border_radius=20,
        ),
        actions=[
            ft.Container(
                content=ft.TextButton(
                    "Close",
                    on_click=lambda e: self.form_app.close_dialog(),
                    style=ft.ButtonStyle(
                        color=ft.colors.GREY_600,
                        padding=ft.padding.symmetric(horizontal=20, vertical=10),
                    )
                ),
                margin=ft.margin.only(right=10, bottom=10)
            )
        ],
        actions_alignment=ft.MainAxisAlignment.END,
        bgcolor=ft.colors.WHITE,
    )

      self.form_app.page.dialog = dialog
      dialog.open = True
      self.form_app.page.update()
    def _get_button_subtitle(self, button_text):
        """Get subtitle text for buttons"""
        subtitles = {
            "Open Existing Table": "Browse and load existing soil data",
            "Create New Table": "Start fresh with a new database",
            "Delete Table": "Remove existing soil database"
        }
        return subtitles.get(button_text, "") 
    
    def load_existing_db_sheets(self) -> List[str]:
        try:
            if not os.path.exists(self.soil_db_path):
                return []
            excel_file = pd.ExcelFile(self.soil_db_path)
            return excel_file.sheet_names
        except Exception as e:
            print(f"Error loading existing DB sheets: {e}")
            return []

    def load_sheet_data(self, sheet_name: str) -> pd.DataFrame:
        try:
            if not os.path.exists(self.soil_db_path):
                return pd.DataFrame()
            df = pd.read_excel(self.soil_db_path, sheet_name=sheet_name)
            return df
        except Exception as e:
            print(f"Error loading sheet {sheet_name}: {e}")
            return pd.DataFrame()

    def save_sheet_data(self, sheet_name: str, data: pd.DataFrame):
        try:
            os.makedirs(os.path.dirname(self.soil_db_path), exist_ok=True)
            if os.path.exists(self.soil_db_path):
                with pd.ExcelWriter(self.soil_db_path, mode='a', engine='openpyxl', if_sheet_exists='replace') as writer:
                    data.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                with pd.ExcelWriter(self.soil_db_path, engine='openpyxl') as writer:
                    data.to_excel(writer, sheet_name=sheet_name, index=False)
            return True
        except Exception as e:
            print(f"Error saving sheet {sheet_name}: {e}")
            return False

    def create_new_sheet(self, sheet_name: str, columns: List[str]) -> bool:
        try:
            df = pd.DataFrame(columns=columns)
            return self.save_sheet_data(sheet_name, df)
        except Exception as e:
            print(f"Error creating new sheet {sheet_name}: {e}")
            return False

    def delete_sheet(self, sheet_name: str) -> bool:
        try:
            if not os.path.exists(self.soil_db_path):
                return False
            excel_file = pd.ExcelFile(self.soil_db_path)
            sheets = excel_file.sheet_names
            
            if sheet_name not in sheets:
                return False
            
            if len(sheets) == 1:
                os.remove(self.soil_db_path)
                return True
            
            sheets_data = {}
            for sheet in sheets:
                if sheet != sheet_name:
                    sheets_data[sheet] = pd.read_excel(self.soil_db_path, sheet_name=sheet)
            
            excel_file.close()
            
            with pd.ExcelWriter(self.soil_db_path, engine='openpyxl') as writer:
                for sheet, df in sheets_data.items():
                    df.to_excel(writer, sheet_name=sheet, index=False)
            
            return True
        except Exception as e:
            print(f"Error deleting sheet {sheet_name}: {e}")
            return False

    def delete_entire_db(self) -> bool:
        try:
            if os.path.exists(self.soil_db_path):
                os.remove(self.soil_db_path)
                return True
            return False
        except Exception as e:
            print(f"Error deleting entire DB: {e}")
            return False

    def get_sheet_info(self, sheet_name: str) -> Dict[str, Any]:
        try:
            df = self.load_sheet_data(sheet_name)
            return {
                'columns': list(df.columns),
                'row_count': len(df),
                'column_count': len(df.columns),
                'data_types': df.dtypes.to_dict()
            }
        except Exception as e:
            print(f"Error getting sheet info for {sheet_name}: {e}")
            return {}

    def copy_sheet_data(self, sheet_name: str):
        try:
            df = self.load_sheet_data(sheet_name)
            if not df.empty:
                self.clipboard_data = df.copy()
                self.clipboard_sheet_name = sheet_name
                
                return True
            else:
                
                return False
        except Exception as e:
            print(f"Error copying sheet {sheet_name}: {e}")
            
            return False

    def has_clipboard_data(self) -> bool:
        return self.clipboard_data is not None and not self.clipboard_data.empty

    def create_data_table_from_dataframe(self, df: pd.DataFrame) -> ft.DataTable:
        try:
            columns = [ft.DataColumn(ft.Text(col)) for col in df.columns]
            rows = []
            for index, row in df.iterrows():
                cells = [ft.DataCell(ft.Text(str(value))) for value in row]
                rows.append(ft.DataRow(cells=cells))
            
            return ft.DataTable(
                columns=columns,
                rows=rows,
                column_spacing=100,
                horizontal_lines=ft.border.BorderSide(1, ft.colors.GREY_300),
                vertical_lines=ft.border.BorderSide(1, ft.colors.GREY_300),
            )
        except Exception as e:
            print(f"Error creating data table: {e}")
            return ft.DataTable(columns=[], rows=[])

    def mark_row_for_deletion(self, sheet_name: str, row_index: int):
        try:
            if sheet_name not in self.rows_to_delete:
                self.rows_to_delete[sheet_name] = set()
            
            if row_index in self.rows_to_delete[sheet_name]:
                self.rows_to_delete[sheet_name].remove(row_index)
                
            else:
                self.rows_to_delete[sheet_name].add(row_index)
                
            self.refresh_sheet_view(sheet_name)
        except Exception as e:
            print(f"Error marking row for deletion: {e}")

    def clear_deletion_marks(self, sheet_name: str):
        """Clear all deletion marks for a specific sheet"""
        if sheet_name in self.rows_to_delete:
            self.rows_to_delete[sheet_name] = set()

    def create_editable_data_table(self, df: pd.DataFrame, sheet_name: str) -> ft.Column:
        try:
            self.current_sheet_data[sheet_name] = df.copy()
            self.current_sheet_name = sheet_name
            
            if sheet_name not in self.rows_to_delete:
                self.rows_to_delete[sheet_name] = set()
            
            num_columns = len(df.columns)
            if num_columns <= 5:
                column_width = 180  
            elif num_columns <= 10:
                column_width = 130
            else:
                column_width = 100
            
            table_content = []
            
            # Create header row
            header_controls = []
            for col in df.columns:
                header_controls.append(
                    ft.Container(
                        content=ft.Text(
                            col,
                            weight=ft.FontWeight.BOLD,
                            size=11,
                            text_align=ft.TextAlign.CENTER,
                            color=ft.colors.WHITE
                        ),
                        width=column_width,
                        padding=8,
                        border=ft.border.all(1, ft.colors.GREY_400),
                        bgcolor=ft.colors.BLUE_700,
                    )
                )
            
            header_controls.append(
                ft.Container(
                    content=ft.Text(
                        "Del",
                        weight=ft.FontWeight.BOLD,
                        size=11,
                        text_align=ft.TextAlign.CENTER,
                        color=ft.colors.WHITE
                    ),
                    width=50,
                    padding=8,
                    border=ft.border.all(1, ft.colors.GREY_400),
                    bgcolor=ft.colors.RED_700,
                )
            )
            
            header_row = ft.Row(header_controls, spacing=0)
            table_content.append(header_row)
            
            # Create data rows
            for index, row in df.iterrows():
                row_controls = []
                is_marked_for_deletion = index in self.rows_to_delete[sheet_name]
                
                for col_name, value in row.items():
                    text_field = ft.TextField(
                        value=str(value) if pd.notna(value) else "",
                        width=column_width,
                        height=40,
                        text_size=10,
                        content_padding=ft.padding.all(5),
                        border_color=ft.colors.RED_300 if is_marked_for_deletion else ft.colors.GREY_300,
                        focused_border_color=ft.colors.RED_400 if is_marked_for_deletion else ft.colors.BLUE_400,
                        bgcolor=ft.colors.RED_50 if is_marked_for_deletion else None,
                        on_change=lambda e, r=index, c=col_name: self.update_cell_value(sheet_name, r, c, e.control.value),
                        disabled=is_marked_for_deletion
                    )
                    row_controls.append(text_field)
                
                delete_button = ft.Container(
                    content=ft.IconButton(
                        icon=ft.icons.RESTORE if is_marked_for_deletion else ft.icons.REMOVE,
                        icon_color=ft.colors.BLUE_600 if is_marked_for_deletion else ft.colors.RED_600,
                        icon_size=16,
                        tooltip="Restore row" if is_marked_for_deletion else "Mark for deletion",
                        on_click=lambda e, r=index: self.mark_row_for_deletion(sheet_name, r)
                    ),
                    width=50,
                    height=40,
                    border=ft.border.all(1, ft.colors.GREY_300),
                    bgcolor=ft.colors.BLUE_50 if is_marked_for_deletion else ft.colors.RED_50,
                    alignment=ft.alignment.center
                )
                row_controls.append(delete_button)
                
                data_row = ft.Row(row_controls, spacing=0)
                table_content.append(data_row)
            
            add_row_button = ft.ElevatedButton(
                "Add Row",
                icon=ft.icons.ADD,
                on_click=lambda e: self.add_new_row(sheet_name),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.GREEN_600,
                    padding=15,
                    shape=ft.RoundedRectangleBorder(radius=8)
                )
            )
            
            save_button = ft.ElevatedButton(
                "Save Changes",
                icon=ft.icons.SAVE,
                on_click=lambda e: self.save_current_sheet(sheet_name),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.BLUE_600,
                    padding=15,
                    shape=ft.RoundedRectangleBorder(radius=8)
                )
            )
            
            info_text = None
            if sheet_name in self.rows_to_delete and self.rows_to_delete[sheet_name]:
                marked_count = len(self.rows_to_delete[sheet_name])
                info_text = ft.Container(
                    content=ft.Text(
                        f"{marked_count} row(s) marked for deletion. Click 'Save Changes' to confirm.",
                        color=ft.colors.ORANGE_700,
                        weight=ft.FontWeight.BOLD,
                        size=12
                    ),
                    bgcolor=ft.colors.ORANGE_50,
                    padding=10,
                    border_radius=5,
                    border=ft.border.all(1, ft.colors.ORANGE_300)
                )
            
            table_column = ft.Column(
                table_content,
                spacing=1,
                tight=True
            )
            
            scrollable_container = ft.Container(
                content=ft.Row([
                    table_column
                ], scroll=ft.ScrollMode.ALWAYS),
                expand=True,
                border=ft.border.all(2, ft.colors.BLUE_200),
                border_radius=8,
                padding=10
            )
            
            column_controls = [
                ft.Container(
                    content=scrollable_container,
                    expand=True
                ),
                ft.Container(height=15)
            ]
            
            if info_text:
                column_controls.append(info_text)
                column_controls.append(ft.Container(height=10))
            
            column_controls.append(
                ft.Row([add_row_button, save_button], spacing=15, alignment=ft.MainAxisAlignment.CENTER)
            )
            
            return ft.Column(column_controls, expand=True)
        except Exception as e:
            print(f"Error creating editable data table: {e}")
            return ft.Column([ft.Text(f"Error: {e}")])

    def update_cell_value(self, sheet_name: str, row_index: int, column_name: str, new_value: str):
        try:
            if sheet_name in self.current_sheet_data:
                self.current_sheet_data[sheet_name].at[row_index, column_name] = new_value
        except Exception as e:
            print(f"Error updating cell value: {e}")

    def add_new_row(self, sheet_name: str):
        try:
            if sheet_name in self.current_sheet_data:
                df = self.current_sheet_data[sheet_name]
                new_row = pd.Series([''] * len(df.columns), index=df.columns)
                self.current_sheet_data[sheet_name] = pd.concat([df, new_row.to_frame().T], ignore_index=True)
                self.refresh_sheet_view(sheet_name)
        except Exception as e:
            print(f"Error adding new row: {e}")
            

    def refresh_sheet_view(self, sheet_name: str):
        try:
            if sheet_name in self.current_sheet_data:
                df = self.current_sheet_data[sheet_name]
                content = self.create_editable_data_table(df, sheet_name)
                if self.form_app.page.dialog:
                    self.form_app.page.dialog.content.content = content
                    self.form_app.page.update()
        except Exception as e:
            print(f"Error refreshing sheet view: {e}")

    def save_current_sheet(self, sheet_name: str):
        try:
            if sheet_name in self.current_sheet_data:
                df = self.current_sheet_data[sheet_name].copy()
                
                if sheet_name in self.rows_to_delete and self.rows_to_delete[sheet_name]:
                    all_indices = set(df.index)
                    indices_to_delete = self.rows_to_delete[sheet_name]
                    indices_to_keep = all_indices - indices_to_delete
                    
                    if indices_to_keep:
                        df = df.loc[list(indices_to_keep)].reset_index(drop=True)
                        deleted_count = len(indices_to_delete)
                        self.current_sheet_data[sheet_name] = df
                        self.rows_to_delete[sheet_name] = set()
                        
                        success = self.save_sheet_data(sheet_name, df)
                        if success:
                            
                            self.refresh_sheet_view(sheet_name)
                        else:
                            print(f"Failed to save sheet {sheet_name} after deletion.")
                    else:
                        print(f"All rows marked for deletion in sheet {sheet_name}. No data to save.")
                else:
                    success = self.save_sheet_data(sheet_name, df)
                    if success:
                        print(f"Sheet '{sheet_name}' saved successfully.")
                    else:
                        print(f"Failed to save sheet {sheet_name}.")
        except Exception as e:
            print(f"Error saving current sheet: {e}")
            

    def open_existing_db_dialog(self):
        self.form_app.close_dialog()
        sheet_names = self.load_existing_db_sheets()
        if not sheet_names:
            no_db_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("No Database Found"),
                content=ft.Text("No existing Soil Database found. Would you like to create a new one?"),
                actions=[
                    ft.TextButton("Create New", on_click=lambda e: self.create_new_db_dialog()),
                    ft.TextButton("Cancel", on_click=lambda e: self.form_app.close_dialog())
                ],
            )
            self.form_app.page.dialog = no_db_dialog
            no_db_dialog.open = True
            self.form_app.page.update()
            return

        sheet_buttons = []
        for sheet_name in sheet_names:
            sheet_info = self.get_sheet_info(sheet_name)
            button = ft.ElevatedButton(
                f"{sheet_name} ({sheet_info.get('row_count', 0)} rows)",
                on_click=lambda e, name=sheet_name: self.view_sheet_data(name),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.BLUE_500,
                    padding=ft.padding.all(10),
                ),
                width=400
            )
            sheet_buttons.append(button)

        sheet_content = ft.Column([
            ft.Text(
                "Select a sheet to view:",
                size=16,
                weight=ft.FontWeight.W_500
            ),
            ft.Container(height=10),
            ft.Container(
                content=ft.Column(
                    sheet_buttons,
                    spacing=5,
                    scroll=ft.ScrollMode.AUTO
                ),
                height=300
            )
        ])

        sheets_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Existing Database Sheets"),
            content=sheet_content,
            actions=[
                ft.TextButton("Back", on_click=lambda e: self.show_soil_db(e)),
                ft.TextButton("Cancel", on_click=lambda e: self.form_app.close_dialog())
            ],
        )
        self.form_app.page.dialog = sheets_dialog
        sheets_dialog.open = True
        self.form_app.page.update()

    def view_sheet_data(self, sheet_name: str):
        self.form_app.close_dialog()
        df = self.load_sheet_data(sheet_name)
        
        if df.empty:
            def add_first_row(e):
                sheet_info = self.get_sheet_info(sheet_name)
                columns = sheet_info.get('columns', [])
                if columns:
                    empty_df = pd.DataFrame([[''] * len(columns)], columns=columns)
                    self.form_app.close_dialog()
                    content = self.create_editable_data_table(empty_df, sheet_name)
                    sheet_dialog = ft.AlertDialog(
                        modal=True,
                        title=ft.Text(f"Sheet: {sheet_name}", size=18, weight=ft.FontWeight.BOLD),
                        content=ft.Container(
                            content=content,
                            width=min(1400, self.form_app.page.window_width * 0.9) if hasattr(self.form_app.page, 'window_width') else 1400,
                            height=min(700, self.form_app.page.window_height * 0.8) if hasattr(self.form_app.page, 'window_height') else 700
                        ),
                        actions=[
                            ft.TextButton("Copy Sheet", on_click=lambda e: self.copy_sheet_data(sheet_name)),
                            ft.TextButton("Delete Sheet", on_click=lambda e: self.confirm_delete_sheet(sheet_name)),
                            ft.TextButton("Back", on_click=lambda e: self.show_soil_db(e)),
                            ft.TextButton("Close", on_click=lambda e: self.form_app.close_dialog())
                        ],
                    )
                    self.form_app.page.dialog = sheet_dialog
                    sheet_dialog.open = True
                    self.form_app.page.update()

            content = ft.Column([
                ft.Text(f"Sheet '{sheet_name}' is empty.", size=16),
                ft.Container(height=20),
                ft.ElevatedButton(
                    "Add First Row",
                    icon=ft.icons.ADD,
                    on_click=add_first_row,
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.GREEN_600,
                        padding=ft.padding.all(10),
                    )
                )
            ])
        else:
            content = self.create_editable_data_table(df, sheet_name)

        # Enhanced actions with Copy button
        actions = [
            ft.TextButton("Copy Sheet", on_click=lambda e: self.copy_sheet_data(sheet_name)),
            ft.TextButton("Delete Sheet", on_click=lambda e: self.confirm_delete_sheet(sheet_name)),
            ft.TextButton("Back", on_click=lambda e: self.show_soil_db(e)),
            ft.TextButton("Close", on_click=lambda e: self.form_app.close_dialog())
        ]

        sheet_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text(f"Sheet: {sheet_name}", size=18, weight=ft.FontWeight.BOLD),
            content=ft.Container(
                content=content,
                width=min(1400, self.form_app.page.window_width * 0.9) if hasattr(self.form_app.page, 'window_width') else 1400,
                height=min(700, self.form_app.page.window_height * 0.8) if hasattr(self.form_app.page, 'window_height') else 700
            ),
            actions=actions,
        )
        self.form_app.page.dialog = sheet_dialog
        sheet_dialog.open = True
        self.form_app.page.update()

    def create_new_db_dialog(self):
        self.form_app.close_dialog()
        soil_headers = [
            "MaterialName", "SoilModel", "DrainageType", "gammaUnsat", "gammaSat", "Eref", "nu", "cref", "phi", 
            "kx", "ky", "Strength", "Rinter", "K0Determination", "K0Primary", "Colour"
        ]

        sheet_name_field = ft.TextField(
            label="Sheet Name",
            hint_text="Enter sheet name (e.g., 'Clay_Properties', 'Sand_Data')",
            width=300
        )

        # Create paste option if clipboard has data
        paste_option = None
        if self.has_clipboard_data():
            paste_checkbox = ft.Checkbox(
                label=f"Paste copied data from '{self.clipboard_sheet_name}'",
                value=False
            )
            paste_option = ft.Container(
                content=ft.Column([
                    ft.Text("Paste Options:", weight=ft.FontWeight.BOLD, size=14),
                    paste_checkbox,
                    ft.Text(
                        f"Rows: {len(self.clipboard_data)}, Columns: {len(self.clipboard_data.columns)}",
                        size=12,
                        color=ft.colors.GREY_700
                    )
                ]),
                bgcolor=ft.colors.LIGHT_BLUE_50,
                padding=10,
                border_radius=5,
                border=ft.border.all(1, ft.colors.LIGHT_BLUE_300),
                width=400
            )

        columns_display = ft.Container(
            content=ft.Column([
                ft.Text("Default Columns (if not pasting):", weight=ft.FontWeight.BOLD, size=14),
                ft.Text(", ".join(soil_headers), size=12, color=ft.colors.GREY_700)
            ]),
            bgcolor=ft.colors.GREY_50,
            padding=10,
            border_radius=5,
            border=ft.border.all(1, ft.colors.GREY_300),
            width=400
        )

        def create_sheet(e):
            sheet_name = sheet_name_field.value.strip()
            if not sheet_name:
                
                return

            existing_sheets = self.load_existing_db_sheets()
            if sheet_name in existing_sheets:
                
                return

            # Check if user wants to paste clipboard data
            should_paste = paste_option and paste_checkbox.value if paste_option else False
            
            if should_paste and self.has_clipboard_data():
                # Create sheet with clipboard data
                success = self.save_sheet_data(sheet_name, self.clipboard_data)
                if success:
                    
                    self.form_app.close_dialog()
                    self.view_sheet_data(sheet_name)
                else:
                    print(f"Failed to create sheet '{sheet_name}' with pasted data.")
            else:
                # Create sheet with default columns
                success = self.create_new_sheet(sheet_name, soil_headers)
                if success:
                    
                    self.form_app.close_dialog()
                    self.view_sheet_data(sheet_name)
                else:
                    print(f"Failed to create new sheet '{sheet_name}' with default columns.")

        create_content_controls = [
            ft.Text(
                "Create New Soil Database Sheet",
                size=18,
                weight=ft.FontWeight.BOLD
            ),
            ft.Container(height=20),
            sheet_name_field,
            ft.Container(height=20)
        ]

        # Add paste option if available
        if paste_option:
            create_content_controls.extend([
                paste_option,
                ft.Container(height=20)
            ])

        create_content_controls.extend([
            columns_display,
            ft.Container(height=20),
            ft.ElevatedButton(
                "Create Sheet",
                icon=ft.icons.CREATE,
                on_click=create_sheet,
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.GREEN_600,
                    padding=ft.padding.all(10),
                )
            )
        ])

        create_content = ft.Column(create_content_controls)

        create_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("New Soil Database Sheet"),
            content=create_content,
            actions=[
                ft.TextButton("Back", on_click=lambda e: self.show_soil_db(e)),
                ft.TextButton("Cancel", on_click=lambda e: self.form_app.close_dialog())
            ],
        )
        self.form_app.page.dialog = create_dialog
        create_dialog.open = True
        self.form_app.page.update()
  
    def delete_db_dialog(self):
        self.form_app.close_dialog()
        sheet_names = self.load_existing_db_sheets()
        if not sheet_names:
            no_db_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("No Database Found"),
                content=ft.Text("No existing Soil Database found to delete."),
                actions=[
                    ft.TextButton("OK", on_click=lambda e: self.form_app.close_dialog())
                ],
            )
            self.form_app.page.dialog = no_db_dialog
            no_db_dialog.open = True
            self.form_app.page.update()
            return

        delete_content = ft.Column([
            ft.Text(
                "Delete Options",
                size=18,
                weight=ft.FontWeight.BOLD
            ),
            ft.Container(height=20),
            ft.ElevatedButton(
                "Delete Entire Database",
                icon=ft.icons.DELETE_FOREVER,
                on_click=lambda e: self.confirm_delete_entire_db(),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.RED_700,
                    padding=ft.padding.all(15),
                ),
                width=300
            ),
            ft.Container(height=20),
            ft.Text("Or delete specific sheets:", size=14, weight=ft.FontWeight.W_500),
            ft.Container(height=10),
        ])

        for sheet_name in sheet_names:
            sheet_button = ft.ElevatedButton(
                f"Delete '{sheet_name}'",
                icon=ft.icons.DELETE,
                on_click=lambda e, name=sheet_name: self.confirm_delete_sheet(name),
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.RED_500,
                    padding=ft.padding.all(10),
                ),
                width=300
            )
            delete_content.controls.append(sheet_button)

        delete_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Delete Database"),
            content=ft.Container(
                content=ft.Column(
                    delete_content.controls,
                    scroll=ft.ScrollMode.AUTO
                ),
                height=400
            ),
            actions=[
                ft.TextButton("Back", on_click=lambda e: self.show_soil_db(e)),
                ft.TextButton("Cancel", on_click=lambda e: self.form_app.close_dialog())
            ],
        )
        self.form_app.page.dialog = delete_dialog
        delete_dialog.open = True
        self.form_app.page.update()

    def confirm_delete_entire_db(self):
        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Deletion"),
            content=ft.Text(
                "Are you sure you want to delete the entire Soil Database?\n\n"
                "This action cannot be undone!",
                color=ft.colors.RED_700
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.form_app.close_dialog()),
                ft.ElevatedButton(
                    "Delete",
                    on_click=lambda e: self.execute_delete_entire_db(),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.RED_700,
                    )
                )
            ],
        )
        self.form_app.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.form_app.page.update()

    def execute_delete_entire_db(self):
        success = self.delete_entire_db()
        if success:
            print("Database deleted successfully.")
        else:
            print("Failed to delete the database.")
        self.form_app.close_dialog()

    def confirm_delete_sheet(self, sheet_name: str):
        confirm_dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Confirm Sheet Deletion"),
            content=ft.Text(
                f"Are you sure you want to delete the sheet '{sheet_name}'?\n\n"
                "This action cannot be undone!",
                color=ft.colors.RED_700
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.form_app.close_dialog()),
                ft.ElevatedButton(
                    "Delete",
                    on_click=lambda e: self.execute_delete_sheet(sheet_name),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.RED_700,
                    )
                )
            ],
        )
        self.form_app.page.dialog = confirm_dialog
        confirm_dialog.open = True
        self.form_app.page.update()

    def execute_delete_sheet(self, sheet_name: str):
        success = self.delete_sheet(sheet_name)
        if success:
            print(f"Sheet '{sheet_name}' deleted successfully.")
        else:
            print(f"Failed to delete sheet '{sheet_name}'. It may not exist.")
        self.form_app.close_dialog()