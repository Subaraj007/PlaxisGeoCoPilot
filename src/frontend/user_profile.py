import flet as ft
from dataclasses import dataclass
from typing import Optional, Dict, Callable
from frontend.database_config import DatabaseConfig
from frontend.database_connection import DatabaseConnection
from frontend.auth_server_handler_singleton import AuthServerHandlerSingleton
import time
from datetime import datetime
from frontend.auth_manager import AuthManager
from frontend.csv_template_handler import CSVTemplateHandler

class UserProfile:
    def __init__(self, form_app, db_config: DatabaseConfig, current_username: str, page: ft.Page, model_creator):
        self.form_app = form_app
        self.db_config = db_config
        self.model_creator = model_creator
        self.page = page
        self.profile_content = None
        self.edit_form = None
        self.password_form = None
        self.auth_manager = AuthManager(self)
        self.feature_usage_recorded = False
        
        self.csv_handler = self._create_template_handler_with_proper_page_management()
        self._initialize_components()

    def _create_template_handler_with_proper_page_management(self):
        """Create the CSV template handler with proper page management"""
        handler = CSVTemplateHandler(self.form_app, self.page)
        
        def get_current_page():
            if hasattr(self.form_app, 'page') and self.form_app.page is not None:
                return self.form_app.page
            return self.page
        
        handler.set_page_getter(get_current_page)
        return handler

    
    def _create_feature_usage_section(self) -> ft.Container:
      """Create a section to display feature usage with tier limits from auth server"""
      try:
        auth_handler = AuthServerHandlerSingleton()
        license_info = auth_handler.get_license()
        
        if not license_info.get("status_code", False):
            return ft.Container(
                content=ft.Text("Error loading feature usage information", color=ft.colors.RED),
                padding=10
            )
        
        features = license_info.get("license_data", {}).get("features", [])
        if not features:
            return ft.Container(
                content=ft.Text("No features available in your license", color=ft.colors.GREY),
                padding=10
            )
        
        feature_cards = []
        
        feature_display_names = {
            'feature_1': 'Create Model',
            'feature_2': 'Feature 2 (Reserved)',
            'feature_3': 'Feature 3 (Reserved)'
        }
        
        for feature in features:
            server_feature_name = feature.get("feature_name", "Unknown Feature")
            remaining_usage = feature.get("remaining_usage", 0)
            
            display_name = feature_display_names.get(server_feature_name, server_feature_name)
            app_feature_name = auth_handler._translate_feature_name(server_feature_name)
            tier_limit = auth_handler.get_feature_limit(app_feature_name)
            is_unlimited = auth_handler.is_feature_unlimited(app_feature_name)
            
            if is_unlimited:
                limit_text = "Unlimited"
                progress_value = 1.0
                progress_color = ft.colors.GREEN
            else:
                limit_text = f"{remaining_usage}/{tier_limit}"
                progress_value = remaining_usage / tier_limit if tier_limit > 0 else 0
                
                if progress_value > 0.5:
                    progress_color = ft.colors.GREEN
                elif progress_value > 0.2:
                    progress_color = ft.colors.ORANGE
                else:
                    progress_color = ft.colors.RED
            
            if server_feature_name == 'feature_1':
                feature_icon = ft.icons.BUILD_CIRCLE
            else:
                feature_icon = ft.icons.FEATURED_PLAY_LIST
            
            feature_cards.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(feature_icon, color=ft.colors.PURPLE_600, size=20),
                                ft.Text(display_name, 
                                       size=16, weight=ft.FontWeight.BOLD),
                                ft.Icon(
                                    ft.icons.ALL_INCLUSIVE if is_unlimited else 
                                    (ft.icons.LOCK_OPEN if remaining_usage > 0 else ft.icons.LOCK),
                                    color=ft.colors.GREEN if (is_unlimited or remaining_usage > 0) else ft.colors.RED,
                                    size=20
                                )
                            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                            ft.Container(height=5),
                            ft.Text(
                                limit_text if not is_unlimited else "Unlimited Usage",
                                size=14,
                                color=ft.colors.GREY_700
                            ),
                            ft.ProgressBar(
                                value=progress_value,
                                width=300,
                                color=progress_color,
                                bgcolor=ft.colors.GREY_300
                            ) if not is_unlimited else ft.Container()
                        ], spacing=5),
                        padding=15,
                        width=350
                    ),
                    elevation=3,
                    margin=ft.margin.only(bottom=15)
                ))
        
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.FEATURED_PLAY_LIST, color=ft.colors.PURPLE_600, size=24),
                        ft.Text("Feature Usage", size=20, weight=ft.FontWeight.BOLD),
                    ], spacing=10),
                    padding=ft.padding.only(bottom=15),
                ),
                ft.Column(feature_cards, spacing=10)
            ]),
            padding=20,
            margin=ft.margin.only(top=10),
            border_radius=10,
            bgcolor=ft.colors.WHITE,
            border=ft.border.all(1, ft.colors.GREY_300)
        )
      except Exception as e:
        print(f"Error creating feature usage section: {e}")
        return ft.Container()

    
    def _initialize_components(self):
        self.profile_content = ft.Column()
        self.edit_form = ft.Column(visible=False)
        self.password_form = ft.Column(visible=False)
        
        self.plaxis_path_field = ft.TextField(
            label="Plaxis Path", width=400, border=ft.InputBorder.UNDERLINE)
        self.port_i_field = ft.TextField(
            label="Input Port (PORT_i)", width=200, border=ft.InputBorder.UNDERLINE)
        self.port_o_field = ft.TextField(
            label="Output Port (PORT_o)", width=200, border=ft.InputBorder.UNDERLINE)
        self.plaxis_password_field = ft.TextField(
            label="Plaxis Password", password=True, can_reveal_password=True,
            width=400, border=ft.InputBorder.UNDERLINE)
        
        self.version_dropdown = ft.Dropdown(
            label="Plaxis Version",
            width=200,
            options=[
                ft.dropdown.Option("before_22", "Before 2022"),
                ft.dropdown.Option("after_22", "2022 and Later")
            ],
            border=ft.InputBorder.UNDERLINE
        )
            
        self.current_password_field = ft.TextField(
            label="Current Password", password=True, can_reveal_password=True,
            width=400, border=ft.InputBorder.UNDERLINE)
        self.new_password_field = ft.TextField(
            label="New Password", password=True, can_reveal_password=True,
            width=400, border=ft.InputBorder.UNDERLINE)
        self.confirm_password_field = ft.TextField(
            label="Confirm New Password", password=True, can_reveal_password=True,
            width=400, border=ft.InputBorder.UNDERLINE)

    def show_signout_confirmation(self, e=None):
      """Show confirmation dialog before signing out"""
      def handle_signout_confirm(e):
        dialog.open = False
        self.form_app.page.update()
        self.handle_signout()
    
      def handle_signout_cancel(e):
        dialog.open = False
        self.form_app.page.update()
    
      dialog = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon(ft.icons.LOGOUT, color=ft.colors.ORANGE_600, size=20),
            ft.Text("Sign Out", size=18, weight=ft.FontWeight.BOLD)
        ], spacing=8),
        content=ft.Container(
            content=ft.Text(
                "Are you sure you want to sign out?",
                size=14,
                text_align=ft.TextAlign.CENTER
            ),
            width=280,
            padding=5
        ),
        actions=[
            ft.TextButton(
                "Cancel",
                on_click=handle_signout_cancel,
                style=ft.ButtonStyle(
                    color=ft.colors.GREY_700,
                    padding=10
                )
            ),
            ft.ElevatedButton(
                "Sign Out",
                on_click=handle_signout_confirm,
                style=ft.ButtonStyle(
                    color=ft.colors.WHITE,
                    bgcolor=ft.colors.RED_600,
                    padding=10,
                    shape=ft.RoundedRectangleBorder(radius=6)
                ),
                icon=ft.icons.LOGOUT
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
      )
    
      self.form_app.page.dialog = dialog
      dialog.open = True
      self.form_app.page.update()

    def handle_signout(self):
      """Handle the actual sign out process"""
      try:
        self.clear_password_fields()
        
        if hasattr(self.form_app, 'section_data'):
            self.form_app.section_data.clear()
        
        if hasattr(self.form_app, 'form_manager'):
            self.form_app.form_manager.clear_all_data()
        
        self.form_app.is_signed_in = False
        self.form_app.current_username = None
        self.form_app.submission_successful = False
        self.form_app.viewing_profile = False
        
        try:
            auth_handler = AuthServerHandlerSingleton()
            if hasattr(auth_handler, 'clear_session'):
                auth_handler.clear_session()
        except Exception as e:
            print(f"Warning: Could not clear auth session: {e}")
        
        self.show_signout_progress()
        
      except Exception as e:
        print(f"Error during signout: {e}")
        self.form_app.reset_to_login()

    def show_signout_progress(self):
      """Show a brief 'Signing out...' message before redirecting"""
      self.form_app.page.controls.clear()
    
      signout_container = ft.Container(
        content=ft.Column([
            ft.Icon(ft.icons.LOGOUT, size=64, color=ft.colors.BLUE_600),
            ft.Text("Signing out...", size=24, weight=ft.FontWeight.BOLD),
            ft.ProgressRing(color=ft.colors.BLUE_600),
        ], 
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        spacing=20),
        alignment=ft.alignment.center,
        expand=True
      )
    
      self.form_app.page.add(signout_container)
      self.form_app.page.update()
    
      import threading
      import time
    
      def delayed_redirect():
        time.sleep(1.5)
        self.form_app.page.run_task(self.complete_signout)
    
      thread = threading.Thread(target=delayed_redirect)
      thread.daemon = True
      thread.start()

    async def complete_signout(self):
      """Complete the signout process by redirecting to login"""
      self.form_app.reset_to_login()

    def get_license_info(self) -> Dict:
        """Get license information from AuthServerHandlerSingleton"""
        try:
            auth_handler = AuthServerHandlerSingleton()
            license_result = auth_handler.get_license()
            
            if not license_result.get("status_code", False):
                return {
                    "valid": False,
                    "error": license_result.get("message", "Failed to retrieve license"),
                    "expiry_date": None,
                    "features": []
                }
            
            license_data = license_result.get("license_data", {})
            expiry_date = license_data.get("expiry_date", None)
            features = license_data.get("features", [])
            
            is_valid = auth_handler.is_license_valid()
            expiry_info = self._parse_expiry_date(expiry_date)
            
            return {
                "valid": is_valid,
                "expiry_date": expiry_date,
                "expiry_info": expiry_info,
                "features": features,
                "error": None
            }
            
        except Exception as e:
            return {
                "valid": False,
                "error": f"Error retrieving license: {str(e)}",
                "expiry_date": None,
                "features": []
            }

    def _parse_expiry_date(self, expiry_date: str) -> Dict:
        """Parse expiry date and calculate remaining time"""
        if not expiry_date:
            return {"formatted": "Not available", "remaining": "Unknown", "expired": True}
        
        try:
            expiry_timestamp = int(time.mktime(time.strptime(expiry_date, "%a, %d %b %Y %H:%M:%S %Z")))
            current_timestamp = int(time.time())
            
            expiry_dt = datetime.fromtimestamp(expiry_timestamp)
            formatted_date = expiry_dt.strftime("%B %d, %Y at %I:%M %p")
            
            if expiry_timestamp <= current_timestamp:
                return {
                    "formatted": formatted_date,
                    "remaining": "Expired",
                    "expired": True
                }
            
            remaining_seconds = expiry_timestamp - current_timestamp
            remaining_days = remaining_seconds // (24 * 3600)
            remaining_hours = (remaining_seconds % (24 * 3600)) // 3600
            
            if remaining_days > 0:
                remaining_text = f"{remaining_days} days, {remaining_hours} hours"
            else:
                remaining_minutes = (remaining_seconds % 3600) // 60
                remaining_text = f"{remaining_hours} hours, {remaining_minutes} minutes"
            
            return {
                "formatted": formatted_date,
                "remaining": remaining_text,
                "expired": False
            }
            
        except ValueError as e:
            return {
                "formatted": expiry_date,
                "remaining": "Invalid date format",
                "expired": True
            }

    def _create_license_section(self) -> ft.Container:
        """Create the license information section"""
        license_info = self.get_license_info()
        auth_handler = AuthServerHandlerSingleton()
        tier = auth_handler.get_license_tier()
        
        if license_info.get("error"):
            return ft.Container(
                content=ft.Column([
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.ERROR, color=ft.colors.RED_600, size=24),
                            ft.Text("License Information", size=20, weight=ft.FontWeight.BOLD),
                        ], spacing=10),
                        padding=ft.padding.only(bottom=15),
                    ),
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.WARNING, color=ft.colors.ORANGE_600, size=20),
                            ft.Text(
                                license_info["error"], 
                                size=14, 
                                color=ft.colors.RED_600
                            )
                        ], spacing=10),
                        padding=ft.padding.all(10),
                        border_radius=8,
                        bgcolor=ft.colors.RED_50,
                        border=ft.border.all(1, ft.colors.RED_200),
                    )
                ]),
                padding=20,
                margin=ft.margin.only(top=10),
            )

        status_color = ft.colors.GREEN_600 if license_info["valid"] else ft.colors.RED_600
        status_text = "Active" if license_info["valid"] else "Inactive/Expired"
        status_icon = ft.icons.CHECK_CIRCLE if license_info["valid"] else ft.icons.CANCEL

        license_controls = [
            # License header
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.CARD_MEMBERSHIP, color=ft.colors.PURPLE_600, size=24),
                    ft.Text("License Information", size=20, weight=ft.FontWeight.BOLD),
                ], spacing=10),
                padding=ft.padding.only(bottom=15),
            ),
        
            # License Tier Badge
            ft.Container(
                content=ft.Row([
                    ft.Icon(ft.icons.WORKSPACE_PREMIUM, color=ft.colors.AMBER_600, size=20),
                    ft.Column([
                        ft.Text("License Tier", size=14, color=ft.colors.GREY_700),
                        ft.Container(
                            content=ft.Text(
                                tier.upper() if tier else "UNKNOWN",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.WHITE
                            ),
                            bgcolor=self._get_tier_color(tier),
                            padding=ft.padding.symmetric(horizontal=15, vertical=5),
                            border_radius=15
                        )
                    ], spacing=5)
                ], spacing=15),
                padding=ft.padding.all(10),
                border_radius=8,
                bgcolor=ft.colors.GREY_50,
                margin=ft.margin.only(bottom=10)
            ),
            
            # License status
            ft.Container(
                content=ft.Row([
                    ft.Icon(status_icon, color=status_color, size=20),
                    ft.Column([
                        ft.Text("License Status", size=14, color=ft.colors.GREY_700),
                        ft.Text(status_text, size=16, color=status_color, weight=ft.FontWeight.W_500)
                    ], spacing=2)
                ], spacing=15),
                padding=ft.padding.all(10),
                border_radius=8,
                bgcolor=ft.colors.GREY_50,
            ),
        ]

        # Expiry information
        if license_info.get("expiry_info"):
            expiry_info = license_info["expiry_info"]
            expiry_color = ft.colors.RED_600 if expiry_info["expired"] else ft.colors.GREEN_600
            
            license_controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Icon(ft.icons.SCHEDULE, color=ft.colors.BLUE_600, size=20),
                        ft.Column([
                            ft.Text("Expiry Date", size=14, color=ft.colors.GREY_700),
                            ft.Text(expiry_info["formatted"], size=16, weight=ft.FontWeight.W_500),
                            ft.Text(
                                f"Time remaining: {expiry_info['remaining']}", 
                                size=14, 
                                color=expiry_color,
                                weight=ft.FontWeight.W_500
                            )
                        ], spacing=2)
                    ], spacing=15),
                    padding=ft.padding.all(10),
                    border_radius=8,
                    bgcolor=ft.colors.GREY_50,
                    margin=ft.margin.only(top=10),
                )
            )
        
        return ft.Container(
            content=ft.Column(license_controls, spacing=5),
            padding=20,
            margin=ft.margin.only(top=10),
        )
  
  
    def _get_tier_color(self, tier: str) -> str:
        """Get color based on license tier"""
        colors = {
            'trial': ft.colors.GREY_600,
            'basic': ft.colors.BLUE_600,
            'premium': ft.colors.PURPLE_600,
            'enterprise': ft.colors.AMBER_700
        }
        return colors.get(tier, ft.colors.GREY_500)

    def show_user_profile(self):
        self.form_app.hide_import_buttons()
        self.form_app.form_content.controls.clear()
    
        main_cards = self._create_main_dashboard_cards()
    
        self.profile_content.controls = [main_cards]
        self.edit_form = self.create_edit_form({})
        self.password_form = self.create_password_form()
    
        self.form_app.form_content.controls.extend([self.profile_content, self.edit_form, self.password_form])
        self.form_app.form_content.update()

    def _create_main_dashboard_cards(self) -> ft.Container:
        """Create the main dashboard with 3 cards - REMOVED create_model usage display"""
        
        # Get license tier for display only
        auth_handler = AuthServerHandlerSingleton()
        tier = 'trial'
        
        try:
            license_result = auth_handler.get_license()
            if license_result.get("status_code", False):
                tier = license_result.get("license_data", {}).get("license_level", "trial")
        except Exception as e:
            print(f"Error getting license tier: {e}")
    
        cards = [
            # User Details Card
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.PERSON, color=ft.colors.BLUE_600, size=32),
                            ft.Text("User Details", size=18, weight=ft.FontWeight.BOLD)
                        ], spacing=15),
                        ft.Container(height=10),
                        ft.Text(
                            "View and edit your profile information and Plaxis configuration settings",
                            size=14,
                            color=ft.colors.GREY_600
                        ),
                        ft.Container(height=20),
                        ft.ElevatedButton(
                            "View Details",
                            on_click=lambda e: self._show_user_details_section(),
                            style=ft.ButtonStyle(
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.BLUE_600,
                                padding=15,
                                shape=ft.RoundedRectangleBorder(radius=8)
                            )
                        )
                    ], spacing=5),
                    padding=25,
                    width=300,
                    height=200
                ),
                elevation=3,
                margin=ft.margin.all(15)
            ),
            
            # License Management Card - SIMPLIFIED (removed usage display)
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.CARD_MEMBERSHIP, color=ft.colors.PURPLE_600, size=32),
                            ft.Text("License Management", size=18, weight=ft.FontWeight.BOLD)
                        ], spacing=15),
                        ft.Container(height=10),
                        ft.Text(
                            "View your license details, tier information, and feature access",
                            size=14,
                            color=ft.colors.GREY_600
                        ),
                        ft.Container(
                            content=ft.Text(
                                f"Current Tier: {tier.upper()}",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.PURPLE_600
                            ),
                            padding=10,
                            border_radius=6,
                            bgcolor=ft.colors.GREY_50,
                            border=ft.border.all(1, ft.colors.GREY_300)
                        ),
                        ft.Container(height=10),
                        ft.Container(
                            content=ft.Row([
                                ft.ElevatedButton(
                                    "View License",
                                    on_click=lambda e: self._handle_license_click(e),
                                    style=ft.ButtonStyle(
                                        color=ft.colors.WHITE,
                                        bgcolor=ft.colors.PURPLE_600,
                                        padding=15,
                                        shape=ft.RoundedRectangleBorder(radius=8)
                                    )
                                ),
                                ft.Container(
                                    content=ft.ProgressRing(
                                        width=20,
                                        height=20,
                                        stroke_width=2,
                                        color=ft.colors.PURPLE_600
                                    ),
                                    visible=False
                                )
                            ], spacing=10, alignment=ft.MainAxisAlignment.START)
                        )
                    ], spacing=5),
                    padding=25,
                    width=300,
                    height=220
                ),
                elevation=3,
                margin=ft.margin.all(15)
            ),
            
            # Download Templates Card
            ft.Card(
                content=ft.Container(
                    content=ft.Column([
                        ft.Row([
                            ft.Icon(ft.icons.DOWNLOAD_FOR_OFFLINE, color=ft.colors.GREEN_600, size=32),
                            ft.Text("Download Templates", size=18, weight=ft.FontWeight.BOLD)
                        ], spacing=15),
                        ft.Container(height=10),
                        ft.Text(
                            "Download CSV templates for importing data into your projects",
                            size=14,
                            color=ft.colors.GREY_600
                        ),
                        ft.Container(height=20),
                        ft.ElevatedButton(
                            "View Templates",
                            on_click=lambda e: self._show_template_section(),
                            style=ft.ButtonStyle(
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.GREEN_600,
                                padding=15,
                                shape=ft.RoundedRectangleBorder(radius=8)
                            )
                        )
                    ], spacing=5),
                    padding=25,
                    width=300,
                    height=200
                ),
                elevation=3,
                margin=ft.margin.all(15)
            )
        ]
        
        # Store reference to the loading indicator
        self.license_loading_indicator = cards[1].content.content.controls[5].content.controls[1]
        
        # Arrange cards in rows
        card_rows = []
        for i in range(0, len(cards), 2):
            row_cards = cards[i:i+2]
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
                        ft.Container(
                            content=ft.Text(
                                self.form_app.current_username[0].upper(),
                                size=24,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.WHITE,
                            ),
                            width=60,
                            height=60,
                            border_radius=30,
                            alignment=ft.alignment.center,
                            bgcolor=ft.colors.BLUE_600,
                        ),
                        ft.Column([
                            ft.Text(
                                f"Welcome, {self.form_app.current_username}",
                                size=24,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                "Choose a section to manage your account",
                                size=16,
                                color=ft.colors.GREY_700
                            )
                        ], spacing=5)
                    ], alignment=ft.MainAxisAlignment.START, spacing=20),
                    padding=ft.padding.all(30),
                ),
                ft.Column(card_rows, spacing=20),
                self._create_contact_section()

            ], spacing=20),
            padding=20,
            alignment=ft.alignment.center
        )
    
    def _show_user_details_section(self):
        config_data = self.model_creator.load_config()
        user_details = self.get_user_details()
        plaxis_config = config_data.get('plaxis', {})
        user_profile_data = {
            'username': self.form_app.current_username,
            'plaxis_path': plaxis_config.get('plaxis_path') or user_details.get('plaxis_path', ''),
            'port_i': plaxis_config.get('port_i') or user_details.get('port_i', ''),
            'port_o': plaxis_config.get('port_o') or user_details.get('port_o', ''),
            'plaxis_password': plaxis_config.get('password') or user_details.get('plaxis_password', ''),
            'version': plaxis_config.get('version') or user_details.get('version', 'after_22')
        }
        
        profile_card = ft.Container(
            content=ft.Column([
                self._create_back_button(),
                ft.Container(
                    content=ft.Row([
                        ft.Container(
                            content=ft.Text(
                                user_profile_data['username'][0].upper(),
                                size=32,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.WHITE,
                            ),
                            width=80,
                            height=80,
                            border_radius=40,
                            alignment=ft.alignment.center,
                            bgcolor=ft.colors.BLUE_600,
                        ),
                        ft.Column([
                            ft.Text(
                                user_profile_data['username'],
                                size=28,
                                weight=ft.FontWeight.BOLD
                            ),
                            ft.Text(
                                "User Account Details",
                                size=16,
                                color=ft.colors.GREY_700
                            )
                        ], spacing=5)
                    ], alignment=ft.MainAxisAlignment.START, spacing=20),
                    padding=ft.padding.only(left=20, top=20, right=20, bottom=10),
                ),
                ft.Divider(height=1, thickness=1, color=ft.colors.GREY_300),
                ft.Container(
                    content=ft.Column([
                        self._create_detail_item("Username", user_profile_data['username'], ft.icons.PERSON),
                        self._create_detail_item("Plaxis Path", user_profile_data['plaxis_path'], ft.icons.FOLDER),
                        self._create_detail_item("Input Port", user_profile_data['port_i'], ft.icons.INPUT),
                        self._create_detail_item("Output Port", user_profile_data['port_o'], ft.icons.OUTPUT),
                        self._create_detail_item(
                            "Plaxis Version", 
                            "Before 2022" if user_profile_data['version'] == 'before_22' else "2022 and Later", 
                            ft.icons.INFO
                        ),
                        self._create_detail_item(
                            "Plaxis Password",
                            "••••••" if user_profile_data['plaxis_password'] else 'Not configured',
                            ft.icons.PASSWORD,
                            is_password=True
                        ),
                    ], spacing=10),
                    padding=20,
                ),
                ft.Container(
                    content=ft.Row([
                        ft.ElevatedButton(
                            "Edit Configuration",
                            on_click=lambda e: self.toggle_forms(show_edit=True),
                            icon=ft.icons.EDIT,
                            style=ft.ButtonStyle(
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.BLUE_600,
                                padding=15
                            )
                        ),
                        ft.ElevatedButton(
                            "Change Password",
                            on_click=lambda e: self.toggle_forms(show_password=True),
                            icon=ft.icons.LOCK_RESET,
                            style=ft.ButtonStyle(
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.ORANGE_600,
                                padding=15
                            )
                        )
                    ], spacing=15, alignment=ft.MainAxisAlignment.CENTER),
                    padding=20
                )
            ]),
            border_radius=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            bgcolor=ft.colors.WHITE,
            margin=ft.margin.all(20),
        )
        
        self.edit_form = self.create_edit_form(user_profile_data)
        self.password_form = self.create_password_form()
        
        self.form_app.form_content.controls.clear()
        self.profile_content.controls = [profile_card]
        
        self.form_app.form_content.controls.extend([
            self.profile_content, 
            self.edit_form, 
            self.password_form
        ])
        self.form_app.form_content.update()
    
    def _handle_license_click(self, e):
        """Handle license button click with loading indicator"""
        self.license_loading_indicator.visible = True
        self.form_app.form_content.update()
        
        try:
            self._show_license_section()
        finally:
            self.license_loading_indicator.visible = False
            self.form_app.form_content.update()

    def _show_license_section(self):
        """Show the license management section"""
        license_section = self._create_license_section()
        feature_usage_section = self._create_feature_usage_section()

        license_card = ft.Container(
            content=ft.Column([
                self._create_back_button(),
                license_section,
                ft.Divider(height=1, thickness=1, color=ft.colors.GREY_300),
                feature_usage_section,
                ft.Container(
                    content=ft.Row([
                        ft.ElevatedButton(
                            "Refresh License",
                            on_click=lambda e: self.refresh_license_info(),
                            icon=ft.icons.REFRESH,
                            style=ft.ButtonStyle(
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.PURPLE_600,
                                padding=15
                            )
                        )
                    ], alignment=ft.MainAxisAlignment.CENTER),
                    padding=20
                )
            ]),
            border_radius=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            bgcolor=ft.colors.WHITE,
            margin=ft.margin.all(20),
        )

        self.profile_content.controls = [license_card]
        self.form_app.form_content.update()

    def _show_template_section(self):
        """Show the CSV template download section"""
        template_view = self.csv_handler.create_template_selection_view()
    
        template_card = ft.Container(
            content=ft.Column([
                self._create_back_button(),
                template_view
            ]),
            border_radius=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            bgcolor=ft.colors.WHITE,
            margin=ft.margin.all(20),
        )
    
        self.profile_content.controls = [template_card]
        self.form_app.form_content.update()

    def _create_back_button(self) -> ft.Container:
        """Create a back button to return to main dashboard"""
        return ft.Container(
            content=ft.Row([
                ft.IconButton(
                    icon=ft.icons.ARROW_BACK,
                    icon_color=ft.colors.BLUE_600,
                    on_click=lambda e: self.show_user_profile(),
                    tooltip="Back to Dashboard"
                ),
                ft.Text("Back to Dashboard", size=20, color=ft.colors.BLUE_600)
            ], spacing=5),
            padding=ft.padding.only(left=10, top=10)
        )

    def _create_contact_section(self) -> ft.Container:
        """Create a contact section at the bottom of the dashboard"""
        return ft.Container(
            content=ft.Column([
                ft.Divider(height=1, thickness=1, color=ft.colors.GREY_300),
                ft.Container(
                    content=ft.Column([
                        ft.Text(
                            "Need Help?",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color=ft.colors.GREY_700,
                            text_align=ft.TextAlign.CENTER
                        ),
                        ft.Container(height=8),
                        ft.Row([
                            ft.Icon(ft.icons.EMAIL, color=ft.colors.BLUE_600, size=20),
                            ft.Text(
                                "Contact us at: ",
                                size=14,
                                color=ft.colors.GREY_600
                            ),
                            ft.TextButton(
                                "hello@buildnexai.com",
                                on_click=self.handle_contact_email_click,
                                style=ft.ButtonStyle(
                                    color=ft.colors.BLUE_600,
                                    padding=ft.padding.symmetric(horizontal=0, vertical=5)
                                )
                            )
                        ], alignment=ft.MainAxisAlignment.CENTER, spacing=5),
                        ft.Text(
                            "We're here to help with any questions or technical support!",
                            size=12,
                            color=ft.colors.GREY_500,
                            text_align=ft.TextAlign.CENTER,
                            italic=True
                        )
                    ], 
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=5
                    ),
                    padding=ft.padding.all(20),
                    border_radius=8,
                    bgcolor=ft.colors.GREY_50,
                )
            ], spacing=10),
            margin=ft.margin.only(top=30, bottom=20),
        )

    def handle_contact_email_click(self, e):
        """Handle contact email click to open default email client"""
        try:
            email_url = "mailto:hello@buildnexai.com?subject=Support Request - User Dashboard"
            e.page.launch_url(email_url)
        except Exception as ex:
            print(f"Error opening email client: {ex}")
            try:
                dialog = ft.AlertDialog(
                    title=ft.Text("Contact Information"),
                    content=ft.Column([
                        ft.Text("Please contact us at:"),
                        ft.SelectionArea(
                            content=ft.Text(
                                "hello@buildnexai.com",
                                size=16,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.BLUE_600
                            )
                        )
                    ], tight=True, spacing=10),
                    actions=[
                        ft.TextButton("Close", on_click=lambda _: self._close_dialog(e.page))
                    ]
                )
                e.page.dialog = dialog
                dialog.open = True
                e.page.update()
            except:
                pass

    def _close_dialog(self, page):
        """Helper method to close dialog"""
        if page.dialog:
            page.dialog.open = False
            page.update()

    def refresh_license_info(self):
        """Refresh license information by clearing cached data and reloading the profile"""
        try:
            auth_handler = AuthServerHandlerSingleton()
            auth_handler.license_data = None
            self.show_user_profile()
        except Exception as e:
            print(f"Error refreshing license info: {e}")
        
    def _create_detail_item(self, label, value, icon, is_password=False):
        """Helper method to create consistently styled detail items"""
        text_color = ft.colors.GREY_800 if not is_password else ft.colors.ORANGE_800
        
        return ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Icon(icon, color=ft.colors.BLUE_600, size=20),
                    width=40,
                ),
                ft.Column([
                    ft.Text(label, size=14, color=ft.colors.GREY_700),
                    ft.Text(
                        value or "Not provided", 
                        size=16, 
                        color=text_color,
                        weight=ft.FontWeight.W_500
                    )
                ], spacing=2, expand=True)
            ]),
            padding=ft.padding.all(10),
            border_radius=8,
            bgcolor=ft.colors.GREY_50,
        )

    def create_edit_form(self, user_details: Dict) -> ft.Container:
        self.plaxis_path_field.value = user_details.get('plaxis_path', '')
        self.port_i_field.value = user_details.get('port_i', '')
        self.port_o_field.value = user_details.get('port_o', '')
        self.plaxis_password_field.value = user_details.get('plaxis_password', '')
        self.version_dropdown.value = user_details.get('version', 'after_22')
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Text("Edit Plaxis Configuration", size=22, weight=ft.FontWeight.BOLD),
                        padding=ft.padding.only(bottom=20),
                    ),
                    ft.Container(
                        content=self.plaxis_path_field,
                        padding=ft.padding.only(bottom=15),
                    ),
                    ft.Container(
                        content=ft.Row([self.port_i_field, self.port_o_field], spacing=20),
                        padding=ft.padding.only(bottom=15),
                    ),
                    ft.Container(
                        content=self.version_dropdown,
                        padding=ft.padding.only(bottom=15),
                    ),
                    ft.Container(
                        content=self.plaxis_password_field,
                        padding=ft.padding.only(bottom=25),
                    ),
                    ft.Row([
                        ft.ElevatedButton(
                            "Save",
                            on_click=self.save_configuration_changes,
                            icon=ft.icons.SAVE,
                            style=ft.ButtonStyle(
                                color=ft.colors.WHITE,
                                bgcolor=ft.colors.GREEN_600,
                                padding=15,
                                shape=ft.RoundedRectangleBorder(radius=8)
                            )
                        ),
                        ft.OutlinedButton(
                            "Cancel",
                            on_click=lambda e: self.toggle_forms(show_profile=True),
                            icon=ft.icons.CANCEL,
                            style=ft.ButtonStyle(
                                color=ft.colors.RED_600,
                                padding=15,
                                shape=ft.RoundedRectangleBorder(radius=8)
                            )
                        )
                    ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)
                ],
                spacing=10,
            ),
            width=600,
            border_radius=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            bgcolor=ft.colors.WHITE,
            padding=30,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.colors.with_opacity(0.2, ft.colors.BLACK),
                offset=ft.Offset(0, 2)
            ),
            margin=ft.margin.all(20),
            visible=False
        )
 
    def create_password_form(self) -> ft.Column:
        self.clear_password_fields()
        
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(
                        content=ft.Row([
                            ft.Icon(ft.icons.SECURITY, color=ft.colors.ORANGE_600, size=24),
                            ft.Text("Change Password", size=22, weight=ft.FontWeight.BOLD),
                        ], spacing=10),
                        padding=ft.padding.only(bottom=20),
                    ),
                    ft.Container(
                        content=self.current_password_field,
                        padding=ft.padding.only(bottom=15),
                    ),
                    ft.Container(
                        content=self.new_password_field,
                        padding=ft.padding.only(bottom=15),
                    ),
                    ft.Container(
                        content=self.confirm_password_field,
                        padding=ft.padding.only(bottom=25),
                    ),
                    ft.Container(
                        content=ft.Text(
                            "Password requirements:",
                            size=14,
                            color=ft.colors.GREY_700,
                            weight=ft.FontWeight.BOLD
                        ),
                        padding=ft.padding.only(bottom=5),
                    ),
                    ft.Container(
                        content=ft.Text(
                            "• At least 8 characters\n• Include numbers and special characters\n• Mix of uppercase and lowercase letters",
                            size=12,
                            color=ft.colors.GREY_700,
                        ),
                        padding=ft.padding.only(bottom=20),
                    ),
                    ft.Row([
                        ft.ElevatedButton(
                            "Save", 
                            on_click=self.handle_password_change,
                            icon=ft.icons.SAVE,
                            style=ft.ButtonStyle(
                                color=ft.colors.WHITE, 
                                bgcolor=ft.colors.GREEN_600, 
                                padding=15,
                                shape=ft.RoundedRectangleBorder(radius=8)
                            )
                        ),
                        ft.OutlinedButton(
                            "Cancel", 
                            on_click=lambda e: self.toggle_forms(show_profile=True),
                            icon=ft.icons.CANCEL,
                            style=ft.ButtonStyle(
                                color=ft.colors.RED_600, 
                                padding=15,
                                shape=ft.RoundedRectangleBorder(radius=8)
                            )
                        )
                    ], spacing=20, alignment=ft.MainAxisAlignment.CENTER)
                ],
                spacing=10,
            ),
            width=600,
            border_radius=10,
            border=ft.border.all(1, ft.colors.GREY_300),
            bgcolor=ft.colors.WHITE,
            padding=30,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=10,
                color=ft.colors.with_opacity(0.2, ft.colors.BLACK),
                offset=ft.Offset(0, 2)
            ),
            margin=ft.margin.all(20),
            visible=False
        )

    def clear_password_fields(self):
        """Clear all password fields for security"""
        self.current_password_field.value = ""
        self.new_password_field.value = ""
        self.confirm_password_field.value = ""
        if self.current_password_field.page:
            self.current_password_field.update()
            self.new_password_field.update()
            self.confirm_password_field.update()

    def toggle_forms(self, show_profile=False, show_edit=False, show_password=False):
        if show_password:
            self.clear_password_fields()
    
        self.profile_content.visible = show_profile
        self.edit_form.visible = show_edit
        self.password_form.visible = show_password
    
        if not (show_profile or show_edit or show_password):
            self.profile_content.visible = True
    
        self.form_app.form_content.update()

    async def handle_password_change(self, e):
        """Handle password change submission using AuthServerHandlerSingleton"""
        current = self.current_password_field.value
        new = self.new_password_field.value
        confirm = self.confirm_password_field.value

        errors = []
        if not current:
            errors.append("Current password is required")
        if not new:
            errors.append("New password is required")
        if new != confirm:
            errors.append("New passwords don't match")
        if current == new:
            errors.append("New password must be different from current password")

        if errors:
            await self.form_app.show_error_dialog(errors)
            return

        try:
            auth_handler = AuthServerHandlerSingleton()
            result = auth_handler.change_password(current, new)
            
            if result and result.get("status_code"):
                self.clear_password_fields()
                self.toggle_forms(show_profile=True)
                
                message = result.get("message", "Password changed successfully! Please log in again.")
                dialog = ft.AlertDialog(
                    title=ft.Text("Success"),
                    content=ft.Text(message),
                    on_dismiss=lambda _: self.form_app.reset_to_login()
                )
                self.form_app.page.dialog = dialog
                dialog.open = True
                self.form_app.page.update()
            else:
                error_message = result.get("message", "Failed to change password") if result else "Failed to change password"
                await self.form_app.show_error_dialog([error_message])
            
            self.clear_password_fields()
            
        except Exception as ex:
            await self.form_app.show_error_dialog([f"Error changing password: {str(ex)}"])
            self.clear_password_fields()

    async def show_success_dialog(self, message: str, on_dismiss: Optional[Callable] = None):
        """Show success dialog with optional dismiss callback"""
        dialog = ft.AlertDialog(
            title=ft.Text("Success"),
            content=ft.Text(message),
            on_dismiss=on_dismiss
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    async def save_configuration_changes(self, e):
        errors = []
        if not self.plaxis_path_field.value:
            errors.append("Plaxis path is required")
        if not self.port_i_field.value.isdigit():
            errors.append("Input port must be a number")
        if not self.port_o_field.value.isdigit():
            errors.append("Output port must be a number")
        if not self.version_dropdown.value:
            errors.append("Please select a Plaxis version")

        if errors:
            await self.form_app.show_error_dialog(errors)
            return

        try:
            self.model_creator.save_config(
                self.plaxis_path_field.value,
                self.port_i_field.value,
                self.port_o_field.value,
                self.plaxis_password_field.value,
                self.version_dropdown.value
            )
            self.toggle_forms(show_profile=True)
            self.show_user_profile()
            await self.form_app.show_success_dialog("Configuration updated successfully!")
        except Exception as ex:
            await self.form_app.show_error_dialog([f"Failed to save changes: {str(ex)}"])

    def get_user_details(self) -> Dict:
        try:
            with DatabaseConnection(self.db_config) as db:
                db.cursor.execute('''SELECT password, plaxis_path, port_i, port_o, plaxis_password, version 
                                  FROM userdetails WHERE username = ?''',
                               (self.form_app.current_username,))
                result = db.cursor.fetchone()
                return dict(result) if result else {}
        except Exception as e:
            print(f"Error fetching user details: {e}")
            return {}

    def show_user_profile_with_loading(self):
        """Show loading message and then load user profile"""
        try:
            if not self.auth_manager.ensure_authenticated():
                return
            
            self.show_loading_message("Loading user profile, please wait...")
            
            import threading
            import time
            
            def load_profile_async():
                try:
                    time.sleep(0.5)
                    self.form_app.page.run_task(self.complete_profile_loading)
                except Exception as e:
                    print(f"Error in profile loading thread: {e}")
                    self.form_app.page.run_task(lambda: self.show_profile_error(str(e)))
            
            thread = threading.Thread(target=load_profile_async)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            print(f"Error starting profile load: {e}")
            self.show_profile_error(str(e))

    async def complete_profile_loading(self):
        """Complete the profile loading process"""
        try:
            self.show_user_profile()
        except Exception as e:
            print(f"Error completing profile load: {e}")
            self.show_profile_error(str(e))

    def show_loading_message(self, message="Loading profile data..."):
        """Show a loading message in the form content area"""
        self.form_app.hide_import_buttons()
        self.form_app.form_content.controls.clear()
    
        loading_container = ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.ProgressRing(
                        width=60, 
                        height=60, 
                        stroke_width=4,
                        color=ft.colors.BLUE_600
                    ),
                    alignment=ft.alignment.center,
                    padding=20
                ),
                ft.Text(
                    "Loading User Profile",
                    size=20,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.BLUE_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=10),
                ft.Text(
                    message,
                    size=14,
                    color=ft.colors.GREY_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=15),
                ft.Container(
                    content=ft.ProgressBar(
                        color=ft.colors.BLUE_600,
                        bgcolor=ft.colors.GREY_300,
                        width=300
                    ),
                    alignment=ft.alignment.center
                )
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=10),
            alignment=ft.alignment.center,
            expand=True,
            padding=50,
            bgcolor=ft.colors.WHITE
        )
    
        self.form_app.form_content.controls.append(loading_container)
        self.form_app.form_content.update()

    def show_profile_error(self, error_message):
        """Show error message when profile fails to load"""
        self.form_app.form_content.controls.clear()
    
        error_container = ft.Container(
            content=ft.Column([
                ft.Icon(
                    ft.icons.ERROR_OUTLINE,
                    size=64,
                    color=ft.colors.RED_600
                ),
                ft.Text(
                    "Failed to Load Profile",
                    size=24,
                    weight=ft.FontWeight.BOLD,
                    color=ft.colors.RED_600,
                    text_align=ft.TextAlign.CENTER
                ),
                ft.Container(height=15),
                ft.Container(
                    content=ft.Text(
                        error_message,
                        size=14,
                        color=ft.colors.GREY_700,
                        text_align=ft.TextAlign.CENTER
                    ),
                    width=400,
                    padding=10,
                    border_radius=8,
                    bgcolor=ft.colors.GREY_100
                ),
                ft.Container(height=25),
                ft.Row([
                    ft.ElevatedButton(
                        "Try Again",
                        on_click=lambda e: self.show_user_profile_with_loading(),
                        icon=ft.icons.REFRESH,
                        style=ft.ButtonStyle(
                            color=ft.colors.WHITE,
                            bgcolor=ft.colors.BLUE_600,
                            padding=15
                        )
                    ),
                    ft.OutlinedButton(
                        "Go Back",
                        on_click=lambda e: self.form_app.show_main_content(),
                        icon=ft.icons.ARROW_BACK,
                        style=ft.ButtonStyle(
                            color=ft.colors.GREY_600,
                            padding=15
                        )
                    )
                ], spacing=15, alignment=ft.MainAxisAlignment.CENTER)
            ], 
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=15),
            alignment=ft.alignment.center,
            expand=True,
            padding=50,
            bgcolor=ft.colors.WHITE
        )
    
        self.form_app.form_content.controls.append(error_container)
        self.form_app.form_content.update()