from typing import Optional, Callable
import flet as ft
import asyncio
from frontend.database_connection import DatabaseConnection
from frontend.database_config import DatabaseConfig
import hashlib  # For password hashing

from frontend.auth_server_handler_singleton import AuthServerHandlerSingleton


class LoginScreen:
    def __init__(self, db_config: DatabaseConfig, on_sign_in: Callable):
        self.db_config = db_config
        self.on_sign_in = on_sign_in
        
        # Brand colors
        self.primary_color = ft.Colors.BLUE_600
        self.text_color = ft.Colors.BLUE_GREY_900
        self.error_color = ft.Colors.RED_600
        self.success_color = ft.Colors.GREEN_600
        self.background_color = ft.Colors.WHITE
        self.card_color = "#F5F7FA"  # Light grey for card background
        
        # Create input fields with enhanced styling
        self.username_field = ft.TextField(
            label="Username",
            border=ft.InputBorder.OUTLINE,  # Fixed: OUTLINE instead of OUTLINED
            width=320,
            text_size=16,
            prefix_icon=ft.Icons.PERSON,
            cursor_color=self.primary_color,
            focused_border_color=self.primary_color,
            focused_color=self.primary_color,
        )
        
        self.password_field = ft.TextField(
            label="Password",
            border=ft.InputBorder.OUTLINE,  # Fixed: OUTLINE instead of OUTLINED
            width=320,
            password=True,
            can_reveal_password=True,
            text_size=16,
            prefix_icon=ft.Icons.LOCK_OUTLINE,
            cursor_color=self.primary_color,
            focused_border_color=self.primary_color,
            focused_color=self.primary_color,
        )
        
        self.sign_in_button = ft.ElevatedButton(
            "Sign In",
            on_click=self.handle_sign_in,
            style=ft.ButtonStyle(
                color=ft.Colors.WHITE,
                bgcolor=self.primary_color,
                padding=ft.padding.symmetric(horizontal=30, vertical=15),
                shape=ft.RoundedRectangleBorder(radius=8),
                elevation=2,
            ),
            width=320,
            height=48,
            icon=ft.Icons.LOGIN,
        )
        
        # Add a progress ring (initially hidden)
        self.progress_ring = ft.ProgressRing(
            width=20,
            height=20,
            stroke_width=2,
            color=ft.Colors.WHITE,
            visible=False
        )
        
        
        
        # Forgot password link
        self.forgot_password = ft.TextButton(
            "Forgot password?",
            on_click=self.handle_forgot_password,  # Added click handler
            style=ft.ButtonStyle(
                color=self.primary_color,

            ),
        )

    def handle_email_click(self, e):
        """Handle email click to open default email client"""
        try:
            # This will open the default email client with a new email to the support address
            email_url = "mailto:hello@buildnexai.com?subject=Password Reset Request"
            e.page.launch_url(email_url)
        except Exception as ex:
            print(f"Error opening email client: {ex}")

    async def show_support_dialog(self, page: ft.Page, dialog_type: str = "support"):
      """Show dialog with support information based on dialog type"""
    
    # Set content based on dialog type
      if dialog_type == "forgot_password":
        title = "Password Recovery"
        main_text = "To reset your password, please contact our support team:"
        instruction_text = "Include your username in the email for faster assistance."
      elif dialog_type == "signup":
        title = "Sign Up"
        main_text = "To create a new account, please contact our support team:"
        instruction_text = "Please include your desired username and full name in your email."
      else:
        # Default fallback for "support" or any other type
        title = "Support"
        main_text = "Please contact our support team:"
        instruction_text = "Include relevant details in your email."
    
      dialog = ft.AlertDialog(
        title=ft.Text(title, color=self.primary_color),
        content=ft.Column(
            [
                ft.Text(
                    main_text,
                    size=14,
                ),
                ft.Container(height=10),
                ft.Row(
                    [
                        ft.Icon(ft.Icons.EMAIL, color=self.primary_color, size=20),
                        ft.Container(width=8),
                        # Make the email clickable using TextButton
                        ft.TextButton(
                            "hello@buildnexai.com",
                            on_click=self.handle_email_click,
                            style=ft.ButtonStyle(
                                color=self.primary_color,
                                text_style=ft.TextStyle(
                                    weight=ft.FontWeight.BOLD,
                                    size=16,
                                    decoration=ft.TextDecoration.UNDERLINE,
                                ),
                                padding=ft.padding.all(0),  # Remove button padding
                            ),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                ft.Container(height=10),
                ft.Text(
                    instruction_text,
                    size=12,
                    color=ft.Colors.BLUE_GREY_600,
                ),
                ft.Container(height=5),
                ft.Text(
                    "Click the email address above to open your email client.",
                    size=11,
                    color=ft.Colors.BLUE_GREY_500,
                    style=ft.TextStyle(italic=True),
                ),
            ],
            tight=True,
            spacing=0,
        ),
        actions=[
            ft.TextButton(
                "OK",
                on_click=lambda e: self.close_dialog(e.page),
                style=ft.ButtonStyle(color=self.primary_color),
            )
        ],
    )
      page.dialog = dialog
      dialog.open = True
      page.update()
    async def handle_forgot_password(self, e):
      """Handle forgot password button click"""
      await self.show_support_dialog(e.page, "forgot_password")    

    async def handle_signup(self, e):
      """Handle signup button click"""
      await self.show_support_dialog(e.page, "signup")   
    
    def create_ui(self) -> ft.Container:
        # Create a card-like container for the login form
        login_card = ft.Container(
            content=ft.Column(
                [
                    # Welcome text
                    ft.Container(
                        content=ft.Text(
                            "Welcome",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            color=self.text_color,
                        ),
                        margin=ft.margin.only(bottom=5),
                    ),
                    
                    # Subtitle
                    ft.Container(
                        content=ft.Text(
                            "Please sign in to continue",
                            size=14,
                            color=ft.Colors.BLUE_GREY_400,
                        ),
                        margin=ft.margin.only(bottom=30),
                    ),
                    
                    # Username field
                    self.username_field,
                    ft.Container(height=16),  # Spacing
                    
                    # Password field
                    self.password_field,
                    ft.Container(height=8),  # Spacing
                    
                    # Remember me and forgot password row
                    ft.Row(
                        [
                            self.forgot_password,
                            ft.Container(expand=True),  # Spacer
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        width=320,
                    ),
                    
                    ft.Container(height=32),  # Spacing
                    
                    # Sign in button
                    ft.Stack(
                        [
                            self.sign_in_button,
                            ft.Container(
                                content=self.progress_ring,
                                alignment=ft.alignment.center,
                            ),
                        ],
                    ),
                    
                    ft.Container(height=20),  # Spacing
                    
                    # Sign up option
                    ft.Row(
                        [
                            ft.Text(
                                "Don't have an account?",
                                size=14,
                                color=ft.Colors.BLUE_GREY_400,
                            ),
                            ft.TextButton(
                                "Sign up",
                                on_click=self.handle_signup,  # Added click handler
                                style=ft.ButtonStyle(
                                    color=self.primary_color,
                                ),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=0,
            ),
            width=420,
            height=620,
            padding=40,
            border_radius=12,
            bgcolor=self.card_color,
            shadow=ft.BoxShadow(
                spread_radius=1,
                blur_radius=15,
                color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK),
                offset=ft.Offset(0, 4),
            ),
        )
        
        # Main container with gradient background
        return ft.Container(
            content=ft.Column(
                [login_card],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            expand=True,
            gradient=ft.LinearGradient(
                begin=ft.alignment.top_left,
                end=ft.alignment.bottom_right,
                colors=[
                    "#F0F4F9",  # Light blue-gray
                    "#E6ECFF",  # Light blue
                ],
            ),
            alignment=ft.alignment.center,
        )

    def verify_credentials_db(self, username: str, password: str) -> bool:
        """
        Verify username and password against database
        """
        try:
            with DatabaseConnection(self.db_config) as db:
                # Query to check credentials
                query = "SELECT * FROM userdetails WHERE username = ? AND password = ?"
                
                # In a production environment, you should hash the password
                # hashed_password = hashlib.sha256(password.encode()).hexdigest()
                
                db.cursor.execute(query, (username, password))
                result = db.cursor.fetchone()
                return result is not None
                
        except Exception as e:
            print(f"Database error during authentication: {e}")
            return False

    def verify_credentials_api(self, username: str, password: str) -> bool:
        """
        Verify username and password against API server
        return:
            bool: True if credentials are valid, False otherwise
        """
        ash = AuthServerHandlerSingleton()
        try:
            # Call the login function from auth_server_handler
            ret = ash.login(username, password)
            return ret.get("status_code", False) and ret.get("authenticated", False)
        except Exception as e:
            print(f"API error during authentication: {e}")
            return False
    
    async def show_error_dialog(self, page: ft.Page, message: str):
        dialog = ft.AlertDialog(
            title=ft.Text("Error", color=self.error_color),
            content=ft.Text(message),
            actions=[
                ft.TextButton(
                    "OK",
                    on_click=lambda e: self.close_dialog(e.page),
                    style=ft.ButtonStyle(color=self.primary_color),
                )
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()
        
    def close_dialog(self, page: ft.Page):
        if page.dialog and page.dialog.open:
            page.dialog.open = False
            page.update()

    async def handle_sign_in(self, e):
        # Show progress ring and disable button during authentication
        self.progress_ring.visible = True
        self.sign_in_button.disabled = True
        self.username_field.disabled = True
        self.password_field.disabled = True
        e.page.update()

        # Simulate network delay for visual feedback (can be removed in production)
        await asyncio.sleep(1)

        try:
            username = self.username_field.value
            password = self.password_field.value

            if not username or not password:
                await self.show_error_dialog(e.page, "Please enter both username and password.")
                return

            if self.verify_credentials_api(username, password):
                # Clear the fields
                self.username_field.value = ""
                self.password_field.value = ""
                
                # Show success animation (optional)
                self.sign_in_button.style.bgcolor = self.success_color
                self.sign_in_button.text = "Success!"
                self.sign_in_button.icon = ft.Icons.CHECK_CIRCLE
                e.page.update()
                
                # Add a small delay to show success state
                await asyncio.sleep(0.8)
                
                # Call the callback to proceed to main form
                if asyncio.iscoroutinefunction(self.on_sign_in):
                    await self.on_sign_in(username)  # If async, await it
                else:
                    self.on_sign_in(username)  # If not async, just call it normally
            else:
                await self.show_error_dialog(e.page, "Invalid username or password.")

        except Exception as ex:
            await self.show_error_dialog(e.page, f"An error occurred: {str(ex)}")
            
        finally:
            # Reset UI state
            self.progress_ring.visible = False
            self.sign_in_button.disabled = False
            self.username_field.disabled = False
            self.password_field.disabled = False
            self.sign_in_button.style.bgcolor = self.primary_color
            self.sign_in_button.text = "Sign In"
            self.sign_in_button.icon = ft.Icons.LOGIN
            e.page.update()
    