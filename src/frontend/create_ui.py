import flet as ft
import asyncio
from frontend.soil_db_handler import SoilDBHandler
class UICreator:
    def __init__(self, form_app):
        """
        Initialize UICreator with a reference to the FormApp instance
        
        Args:
            form_app: The FormApp instance that contains all the necessary data and methods
        """
        self.form_app = form_app
        self.soil_db_handler = SoilDBHandler(form_app)
    
    def create_ui(self):
        """
        Create the main UI for the application
        """
        if not self.form_app.is_signed_in:
            return

        self._create_navigation_rail()
        self._create_form_content()
        self._create_stage_components()
        self._populate_form_sections()
        self._create_buttons()
        self._create_import_buttons()
        self._create_main_layout()
        
        self.form_app.update_form_content(0)

    def _create_navigation_rail(self):
        """Create the navigation rail with all destinations"""
        self.form_app.rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            min_width=120,
            min_extended_width=150,
            extended=True,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.icons.INFO),
                    label="Project Info",
                    label_content=ft.Container(
                        content=ft.Text(
                            "Project Info",
                            size=14,
                            weight=ft.FontWeight.BOLD
                        ),
                        margin=ft.margin.only(right=20)
                    ),
                    disabled=False
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.icons.ARCHITECTURE),
                    label="Geometry",
                    label_content=ft.Container(
                        content=ft.Text(
                            "Geometry",
                            size=14,
                            weight=ft.FontWeight.BOLD
                        ),
                        margin=ft.margin.only(right=20)
                    ),
                    disabled=True
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.icons.LAYERS),
                    label="Borehole",
                    label_content=ft.Container(
                        content=ft.Text(
                            "Borehole",
                            size=14,
                            weight=ft.FontWeight.BOLD
                        ),
                        margin=ft.margin.only(right=20)
                    ),
                    disabled=True
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.OPEN_WITH,
                    label="Excavation",
                    label_content=ft.Container(
                        content=ft.Text(
                            "Excavation",
                            size=14,
                            weight=ft.FontWeight.BOLD
                        ),
                        margin=ft.margin.only(right=20)
                    ),
                    disabled=True
                ),
                ft.NavigationRailDestination(
                    icon=ft.icons.BUILD,
                    label="Sequence Construct",
                    label_content=ft.Container(
                        content=ft.Text(
                            "Construct Sequence ",
                            size=14,
                            weight=ft.FontWeight.BOLD
                        ),
                        margin=ft.margin.only(right=20)
                    ),
                    disabled=True
                ),
            ],
            trailing=self._create_trailing_buttons(),
            on_change=self.form_app.on_tab_change,
        )

    def _create_trailing_buttons(self):
        """Create the trailing buttons for the navigation rail"""
        return ft.Container(
            content=ft.Column(
                [
                    ft.ElevatedButton(
                        "Save Project",
                        icon=ft.icons.SAVE,
                        on_click=self.form_app._handle_save_click,
                        style=ft.ButtonStyle(
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.BLUE_300,
                            padding=10
                        ),
                        width=140
                    ),
                    ft.ElevatedButton(
                        "Open Project",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=self.form_app._handle_open_click,
                        style=ft.ButtonStyle(
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.BLUE_500,
                            padding=10
                        ),
                        width=140
                    ),
                    ft.Container(height=100),
                    ft.ElevatedButton(
                        "Soil DB",
                        icon=ft.icons.UPLOAD_FILE,
                        on_click=self.soil_db_handler.show_soil_db,
                        style=ft.ButtonStyle(
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.BLUE_500,
                            padding=10
                        ),
                        width=140
                    ),
                    ft.Container(height=100),
                    ft.ElevatedButton(
                        "User Profile",
                        icon=ft.icons.PERSON,
                        on_click=lambda e: self.form_app.user_profile.show_user_profile_with_loading(),
                        style=ft.ButtonStyle(
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.BLUE_700,
                            padding=10
                        ),
                        width=140
                    ),
                    ft.ElevatedButton(
                        "Sign Out",
                        icon=ft.icons.PERSON,
                        on_click=lambda e: self.form_app.show_signout(),
                        style=ft.ButtonStyle(
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.BLUE_900,
                            padding=10
                        ),
                        width=140
                    )
                ],
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            margin=ft.margin.only(top=20),
            alignment=ft.alignment.center
        )

    def _create_form_content(self):
        """Create the main form content column"""
        self.form_app.form_content = ft.Column(
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _create_stage_components(self):
        """Create stage-related UI components"""
        self.form_app.stage_buttons = ft.Row(
            controls=[
                ft.ElevatedButton(
                    "Add Stage",
                    icon=ft.icons.ADD,
                    on_click=self.form_app.excavation_section.add_stage,
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.BLUE_600,
                        padding=10,
                    )
                ),
            ],
            visible=False
        )

        self.form_app.stages_content = ft.Column(
            controls=[],
            spacing=20,
            visible=False
        )

    def _populate_form_sections(self):
        """Populate the form content with sections"""
        for section_index, section in self.form_app.sections.items():
            section_title = ft.Text(
                f"Section {section_index + 1}: {section.__class__.__name__}",
                size=24,
                weight=ft.FontWeight.BOLD,
            )
            section_content = self.form_app.create_form_section(section)
            self.form_app.form_content.controls.extend([
                section_title,
                section_content
            ])

    def _create_buttons(self):
        """Create navigation and action buttons"""
        self.form_app.prev_button = ft.ElevatedButton(
            "Previous",
            on_click=self.form_app.on_previous,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.BLUE_600,
                padding=20,
            ),
            visible=False
        )

        self.form_app.next_button = ft.ElevatedButton(
            "Next",
            on_click=self.form_app.on_submit,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=ft.Colors.GREEN_600,
                padding=20,
            ),
        )

        self.form_app.create_model_button = ft.ElevatedButton(
            "Create Model",
            on_click=self.form_app.handle_create_model_click,
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.ORANGE_600,
                padding=20,
            ),
            visible=False,
            disabled=True
        )

    def _create_import_buttons(self):
        """Create import buttons for different sections"""
        self.form_app.geological_import_button = ft.ElevatedButton(
            "Import Data",
            on_click=lambda e: self.form_app.import_data_handler.open_file_picker(e, section_index=0),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_600,
                padding=10,
            ),
            visible=False
        )

        self.form_app.geometry_import_button = ft.ElevatedButton(
            "Import Data",
            on_click=lambda e: self.form_app.import_data_handler.open_file_picker(e, section_index=1),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_600,
                padding=10,
            ),
            visible=False
        )

        self.form_app.borehole_import_button = ft.ElevatedButton(
            "Import Data",
            on_click=lambda e: self.form_app.import_data_handler.open_file_picker(e, section_index=2),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_600,
                padding=10,
            ),
            visible=False
        )

        self.form_app.excavation_import_button = ft.ElevatedButton(
            "Import Data",
            on_click=lambda e: self.form_app.import_data_handler.open_file_picker(e, section_index=3),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_600,
                padding=10,
            ),
            visible=False
        )

        self.form_app.sequence_import_button = ft.ElevatedButton(
            "Import Data",
            on_click=lambda e: self.form_app.import_data_handler.open_file_picker(e, section_index=4),
            style=ft.ButtonStyle(
                color=ft.colors.WHITE,
                bgcolor=ft.colors.BLUE_600,
                padding=10,
            ),
            visible=False
        )

        self.form_app.import_buttons_row = ft.Row(
            controls=[
                self.form_app.geological_import_button,
                self.form_app.geometry_import_button,
                self.form_app.borehole_import_button,
                self.form_app.excavation_import_button,
                self.form_app.sequence_import_button
            ],
            alignment=ft.MainAxisAlignment.END,
        )

    def _create_main_layout(self):
        """Create the main layout and add it to the page"""
        buttons_row = ft.Row(
            [
                ft.Container(
                    content=self.form_app.prev_button,
                    width=120,
                ),
                ft.Container(
                    content=ft.Row(
                        [self.form_app.next_button, self.form_app.create_model_button],
                        spacing=10,
                        alignment=ft.MainAxisAlignment.END
                    ),
                    expand=True,
                    alignment=ft.alignment.center_right
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )

        main_content = ft.Container(
            content=ft.Column(
                [
                    ft.Text("BuildNex AI Geo Copilot", size=32, weight=ft.FontWeight.BOLD),
                    self.form_app.import_buttons_row,
                    self.form_app.stage_buttons,
                    ft.Container(
                        content=ft.Column(
                            [
                                self.form_app.form_content,
                                self.form_app.stages_content
                            ],
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        ),
                        border=ft.border.all(1, ft.colors.GREY_300),
                        border_radius=10,
                        padding=10,
                        height=500,
                        expand=True,
                    ),
                    buttons_row,
                ],
                spacing=20,
                expand=True,
            ),
            padding=ft.padding.only(left=30, right=30, top=30, bottom=30),
            expand=True,
        )

        self.form_app.page.add(
            ft.Row(
                [
                    self.form_app.rail,
                    ft.VerticalDivider(width=1),
                    ft.Container(
                        content=main_content,
                        expand=True,
                        padding=ft.padding.symmetric(horizontal=20),
                    ),
                ],
                expand=True,
                vertical_alignment=ft.CrossAxisAlignment.START
            )
        )