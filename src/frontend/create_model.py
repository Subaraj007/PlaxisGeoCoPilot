import asyncio
import json
import sys
import os
from typing import Dict
from pathlib import Path
import flet as ft
import yaml
from datetime import datetime
import random
from frontend.auth_server_handler_singleton import AuthServerHandlerSingleton

import plaxis.Main as plaxis_main

# Safe print function that handles Unicode characters
def safe_print(message):
    """Print message with fallback for Unicode characters on Windows"""
    try:
        print(message)
    except UnicodeEncodeError:
        ascii_message = message.encode('ascii', 'ignore').decode('ascii')
        print(ascii_message)

class ModelCreator:
    def __init__(self, app):
        self.app = app
        self.is_model_running = False
        self.plaxis_versions = ["Before V22", "V22 and after"]
        
        if getattr(sys, 'frozen', False):
            temp_dir = Path(sys._MEIPASS)
            if (temp_dir / "plaxis").exists() and (temp_dir / "frontend").exists():
                self.BASE_DIR = temp_dir.parent if temp_dir.name == 'src' else temp_dir
            else:
                self.BASE_DIR = temp_dir
        else:
            self.BASE_DIR = Path(__file__).resolve().parent.parent.parent
        
        safe_print(f"ModelCreator BASE_DIR: {self.BASE_DIR}")
    
    async def on_create_model(self, e):
        """Handle create model button click with auth server feature tracking"""
        if self.is_model_running:
            await self.app.show_error_dialog(["A model is already running. Please wait for the current process to complete."])
            return
        
        # CHECK AUTH SERVER FEATURE USAGE (feature_1 = create_model)
        auth_handler = AuthServerHandlerSingleton()
        
        safe_print(f"[DEBUG] Checking if user can use 'create_model' feature...")
        
        # Check if user can use the create_model feature
        can_create = auth_handler.can_use_feature('create_model')
        
        safe_print(f"[DEBUG] can_use_feature('create_model') returned: {can_create}")
        
        if not can_create:
            # Get tier info for better error message
            tier = auth_handler.get_license_tier()
            tier_limit = auth_handler.get_feature_limit('create_model')
            
            safe_print(f"[DEBUG] User cannot create model. Tier: {tier}, Limit: {tier_limit}")
            
            # Show limit reached dialog
            await self._show_limit_reached_dialog(tier, tier_limit)
            return
        
        # Get remaining count for display
        remaining = self._get_remaining_create_model_count()
        if remaining != -1:  # Not unlimited
            safe_print(f"[OK] You have {remaining} model creations remaining")
        
        # Continue with normal model creation flow
        config = self.load_config()
        plaxis_config = config.get("plaxis", {})
        
        has_complete_config = self._has_valid_plaxis_config(plaxis_config)
        
        if has_complete_config:
            await self.run_model_with_config(
                plaxis_path=plaxis_config["plaxis_path"],
                port_i=plaxis_config["port_i"],
                port_o=plaxis_config["port_o"],
                password=plaxis_config["password"],
                version=plaxis_config["version"]
            )
            return

        await self._show_config_dialog(plaxis_config)
    
    def _get_remaining_create_model_count(self) -> int:
        """Get remaining create_model usage from auth server"""
        try:
            auth_handler = AuthServerHandlerSingleton()
            license_result = auth_handler.get_license()
            
            if not license_result.get("status_code", False):
                return 0
            
            features = license_result.get("license_data", {}).get("features", [])
            
            # Find feature_1 (create_model)
            for feature in features:
                if feature.get("feature_name") == "feature_1":
                    remaining = feature.get("remaining_usage", 0)
                    # Check if unlimited in tier using SERVER feature name
                    tier = auth_handler.get_license_tier()
                    tier_limits = auth_handler.LICENSE_TIER_LIMITS.get(tier, {})
                    # FIXED: Use 'feature_1' not 'create_model'
                    if tier_limits.get('feature_1', 0) == -1:
                        return -1  # Unlimited
                    return remaining
            
            return 0
        except Exception as e:
            safe_print(f"Error getting remaining count: {e}")
            return 0
    
    async def _show_limit_reached_dialog(self, tier: str, tier_limit: int):
        """Show dialog when create model limit is reached"""
        remaining = self._get_remaining_create_model_count()
        
        if tier_limit == -1:
            message = "Unlimited model creations available in your tier"
        else:
            message = f"You have reached your model creation limit ({remaining} of {tier_limit} models remaining) in the {tier.upper()} tier"
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Row([
                ft.Icon(ft.icons.WARNING, color=ft.colors.ORANGE_600, size=32),
                ft.Text("Model Creation Limit Reached", size=20, weight=ft.FontWeight.BOLD)
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        message,
                        size=16,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=15),
                    ft.Container(
                        content=ft.Column([
                            ft.Text("To create more models:", weight=ft.FontWeight.BOLD),
                            ft.Text("- Upgrade to a higher license tier", size=14),
                            ft.Text("- Contact support for assistance", size=14),
                        ], spacing=5),
                        padding=10,
                        border_radius=8,
                        bgcolor=ft.colors.GREY_100
                    )
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=400,
                padding=20
            ),
            actions=[
                ft.TextButton(
                    "View License",
                    on_click=lambda e: self._handle_view_license_click(dialog),
                    style=ft.ButtonStyle(
                        color=ft.colors.BLUE_600
                    )
                ),
                ft.ElevatedButton(
                    "OK",
                    on_click=lambda e: self._close_dialog(dialog),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.ORANGE_600
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        )
        
        self.app.page.dialog = dialog
        dialog.open = True
        await self.app.page.update_async()
    
    def _handle_view_license_click(self, dialog):
        """Navigate to license section from limit dialog"""
        dialog.open = False
        self.app.page.update()
        if hasattr(self.app, 'user_profile'):
            self.app.user_profile.show_user_profile()
    
    def _close_dialog(self, dialog):
        """Close the dialog"""
        dialog.open = False
        self.app.page.update()

    def _has_valid_plaxis_config(self, plaxis_config):
        """Check if plaxis config has all required fields with non-empty values."""
        required_fields = ["plaxis_path", "port_i", "port_o", "password", "version"]
        return all(
            field in plaxis_config and 
            plaxis_config[field] is not None and 
            str(plaxis_config[field]).strip() != ""
            for field in required_fields
        )

    async def _show_config_dialog(self, plaxis_config):
        """Show the configuration dialog with pre-filled values."""
        path_input = ft.TextField(
            label="Plaxis 2D Input Path",
            hint_text="Path to Plaxis2DXInput.exe",
            width=600,
            value=plaxis_config.get("plaxis_path", "") or ""
        )
        port_i_input = ft.TextField(
            label="Input Port (PORT_i)",
            hint_text="e.g. 10000",
            width=300,
            value=plaxis_config.get("port_i", "") or ""
        )
        port_o_input = ft.TextField(
            label="Output Port (PORT_o)",
            hint_text="e.g. 10001",
            width=300,
            value=plaxis_config.get("port_o", "") or ""
        )
        password_input = ft.TextField(
            label="Password",
            password=True,
            width=600,
            value=plaxis_config.get("password", "") or "",
            can_reveal_password=True,
            disabled=False
        )
        version_dropdown = ft.Dropdown(
            label="Plaxis Version",
            options=[ft.dropdown.Option(v) for v in self.plaxis_versions],
            width=300,
            value=plaxis_config.get("version", "") or "Before V22"
        )

        async def run_model(e):
            plaxis_path = path_input.value.strip()
            port_i = port_i_input.value.strip()
            port_o = port_o_input.value.strip()
            password = password_input.value.strip()
            version = version_dropdown.value.strip()
        
            errors = []
            if not plaxis_path:
                errors.append("Plaxis Path is required.")
            if not port_i or not port_i.isdigit():
                errors.append("Input Port must be a valid number.")
            if not port_o or not port_o.isdigit():
                errors.append("Output Port must be a valid number.")
            if not password:
                errors.append("Password is required.")
            if not version:
                errors.append("Plaxis Version is required.")
        
            if errors:
                await self.app.show_error_dialog(errors)
                return
        
            self.save_config(plaxis_path, port_i, port_o, password, version)
            self.app.close_dialog()
            await self.app.page.update_async()
            await asyncio.sleep(0.1)
            await self.run_model_with_config(plaxis_path, port_i, port_o, password, version)

        dialog = ft.AlertDialog(
            title=ft.Text("Configure Plaxis Settings"),
            content=ft.Container(
                content=ft.Column([
                    ft.Text("Please provide the Plaxis application path and connection settings:"),
                    path_input,
                    ft.Row([port_i_input, port_o_input], spacing=20),
                    version_dropdown,
                    password_input
                ], spacing=20, scroll=ft.ScrollMode.AUTO),
                width=650,
                height=350,
                padding=20
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: self.app.close_dialog()),
                ft.TextButton("Save & Run Model", on_click=run_model)
            ],
            actions_alignment=ft.MainAxisAlignment.END
        )

        self.app.page.dialog = dialog
        dialog.open = True
        await self.app.page.update_async()

    def save_plaxis_config(self, plaxis_path: str, port_i: str, port_o: str, password: str, version: str):
        """Save Plaxis configuration to the unified YAML config file."""
        config_path = self.get_config_path()
        config = {}
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
        except Exception as e:
            safe_print(f"Error reading existing config: {e}")

        if 'plaxis' not in config:
            config['plaxis'] = {}

        config['plaxis'].update({
            "plaxis_path": plaxis_path,
            "port_i": port_i,
            "port_o": port_o,
            "password": password,
            "version": version
        })

        try:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            safe_print(f"Config saved to {config_path}")
        except Exception as e:
            safe_print(f"Error saving config: {e}")
    
    def is_license_valid(self) -> bool:
        """Check if license is valid"""
        try:
            auth_handler = AuthServerHandlerSingleton()
            return auth_handler.is_license_valid()
        except Exception as e:
            safe_print(f"Error checking license: {str(e)}")
            return False

    def _ensure_data_directory(self):
        """Ensure the data directory exists where the script expects it."""
        if getattr(sys, 'frozen', False):
            data_dir = self.BASE_DIR / "data"
        else:
            data_dir = self.BASE_DIR / "data"
            
        data_dir.mkdir(exist_ok=True)
        safe_print(f"Ensured data directory at: {data_dir}")
        return data_dir

    async def run_model_with_config(self, plaxis_path, port_i, port_o, password, version):
        """Run the model and record usage via auth server"""
        if self.is_model_running:
            await self.app.show_error_dialog(["A model is already running. Please wait for the current process to complete."])
            return

        if not all([plaxis_path, port_i, port_o, password, version]):
            await self.app.show_error_dialog(["Invalid configuration. Please check all parameters are set."])
            return

        try:
            self.is_model_running = True
            self.save_config(plaxis_path, port_i, port_o, password, version)

            # Generate common_id for this project
            common_id = f"{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}_{random.randint(1000, 9999)}"

            # RECORD USAGE VIA AUTH SERVER (feature_1 = create_model)
            auth_handler = AuthServerHandlerSingleton()
            usage_result = auth_handler.record_license_usage('create_model')
            
            if usage_result.get("status_code", False):
                safe_print(f"[OK] Model creation recorded via auth server")
            else:
                error_msg = usage_result.get("message", "Failed to record usage")
                safe_print(f"[WARNING] Usage recording failed: {error_msg}")
                # Continue anyway - don't block model creation

            # Ensure data directory exists where the script expects it
            self._ensure_data_directory()
            
            # Run the actual Plaxis model creation with Unicode error protection
            try:
                plaxis_main.create_model()
            except UnicodeEncodeError as ue:
                safe_print(f"[WARNING] Unicode encoding error during model creation: {ue}")
                safe_print("[INFO] Model may have been created successfully despite the encoding error")
            
            # Get updated remaining count for display
            remaining = self._get_remaining_create_model_count()
            tier = auth_handler.get_license_tier()
            
            # Show success message with updated usage info
            await self._show_model_success_with_usage(remaining, tier)
            
        except Exception as ex:
            await self.app.show_error_dialog([f"Failed to run script: {str(ex)}"])
        finally:
            self.is_model_running = False
    
    async def _show_model_success_with_usage(self, remaining: int, tier: str):
        """Show success dialog with updated usage information from auth server"""
        
        # Determine display text and color based on remaining count
        if remaining == -1:  # Unlimited
            color = ft.colors.GREEN_600
            usage_text = "Unlimited model creations available"
            progress_value = 1.0
        else:
            # Get tier limit to calculate progress
            auth_handler = AuthServerHandlerSingleton()
            tier_limit = auth_handler.get_feature_limit('create_model')
            
            if tier_limit > 0:
                progress_value = remaining / tier_limit
            else:
                progress_value = 0
            
            if remaining > tier_limit * 0.5:
                color = ft.colors.GREEN_600
            elif remaining > tier_limit * 0.2:
                color = ft.colors.ORANGE_600
            else:
                color = ft.colors.RED_600
            
            usage_text = f"{remaining} model creations remaining"
        
        dialog = ft.AlertDialog(
            title=ft.Row([
                ft.Icon(ft.icons.CHECK_CIRCLE, color=ft.colors.GREEN_600, size=32),
                ft.Text("Model Created Successfully", size=20, weight=ft.FontWeight.BOLD)
            ], spacing=10),
            content=ft.Container(
                content=ft.Column([
                    ft.Text(
                        "Your Plaxis model has been created successfully!",
                        size=16,
                        text_align=ft.TextAlign.CENTER
                    ),
                    ft.Container(height=15),
                    ft.Container(
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.icons.WORKSPACE_PREMIUM, color=color, size=20),
                                ft.Text(
                                    f"License Tier: {tier.upper()}",
                                    size=14,
                                    weight=ft.FontWeight.BOLD
                                )
                            ], spacing=10),
                            ft.Container(height=5),
                            ft.Row([
                                ft.Icon(ft.icons.BUILD_CIRCLE, color=color, size=20),
                                ft.Text(
                                    usage_text,
                                    size=14,
                                    color=color,
                                    weight=ft.FontWeight.BOLD
                                )
                            ], spacing=10),
                            ft.ProgressBar(
                                value=progress_value,
                                color=color,
                                bgcolor=ft.colors.GREY_300,
                                width=300
                            ) if remaining != -1 else ft.Container()
                        ], spacing=8),
                        padding=15,
                        border_radius=8,
                        bgcolor=ft.colors.GREY_50,
                        border=ft.border.all(1, ft.colors.GREY_300)
                    )
                ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                width=400,
                padding=20
            ),
            actions=[
                ft.ElevatedButton(
                    "OK",
                    on_click=lambda e: self._close_dialog(dialog),
                    style=ft.ButtonStyle(
                        color=ft.colors.WHITE,
                        bgcolor=ft.colors.GREEN_600
                    )
                )
            ],
            actions_alignment=ft.MainAxisAlignment.CENTER
        )
        
        self.app.page.dialog = dialog
        dialog.open = True
        await self.app.page.update_async()
      
    def get_config_path(self) -> Path:
        """Return the path to the unified YAML configuration file."""
        config_path = Path(__file__).resolve().parent.parent / "config.yaml"
        return config_path

    def load_config(self) -> dict:
        """Load configuration from the unified YAML file and database."""
        config_path = self.get_config_path()
        config_data = {}

        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config_data = yaml.safe_load(f) or {}
            except Exception as e:
                safe_print(f"Error loading config from file: {e}")

        plaxis_config = config_data.get("plaxis", {})

        if not self._has_valid_plaxis_config(plaxis_config):
            try:
                if hasattr(self.app, 'current_username') and self.app.current_username:
                    from frontend.database_connection import DatabaseConnection
                    with DatabaseConnection(self.app.db_config) as db:
                        db.cursor.execute("""
                            SELECT plaxis_path, port_i, port_o, plaxis_password, plaxis_version
                            FROM user_plaxis_config 
                            WHERE username = ?
                        """, (self.app.current_username,))
                        result = db.cursor.fetchone()
                        
                        if result:
                            db_config = {
                                "plaxis_path": result['plaxis_path'],
                                "port_i": result['port_i'],
                                "port_o": result['port_o'],
                                "password": result['plaxis_password'],
                                "version": result['plaxis_version']
                            }
                            
                            if self._has_valid_plaxis_config(db_config):
                                for key, value in db_config.items():
                                    if not plaxis_config.get(key) or str(plaxis_config.get(key)).strip() == "":
                                        plaxis_config[key] = value
                                
                                if self._has_valid_plaxis_config(plaxis_config):
                                    self.save_config(
                                        plaxis_config["plaxis_path"],
                                        plaxis_config["port_i"],
                                        plaxis_config["port_o"],
                                        plaxis_config["password"],
                                        plaxis_config["version"]
                                    )
                                
                                config_data["plaxis"] = plaxis_config
                        
            except Exception as e:
                safe_print(f"Error loading config from database: {e}")

        return config_data

    def save_config(self, plaxis_path: str, port_i: str, port_o: str, password: str, version: str):
        """Save Plaxis configuration to both YAML file and database."""
        # Save to YAML file
        config_path = self.get_config_path()
        config = {}
        
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
        except Exception as e:
            safe_print(f"Error reading existing config: {e}")

        if 'plaxis' not in config:
            config['plaxis'] = {}

        config['plaxis'].update({
            "plaxis_path": plaxis_path,
            "port_i": port_i,
            "port_o": port_o,
            "password": password,
            "version": version
        })

        try:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            safe_print(f"Config saved to {config_path}")
        except Exception as e:
            safe_print(f"Error saving config: {e}")

        # Save to database if user is logged in
        if hasattr(self.app, 'current_username') and self.app.current_username:
            try:
                from frontend.database_connection import DatabaseConnection
                with DatabaseConnection(self.app.db_config) as db:
                    db.cursor.execute("""
                        INSERT OR REPLACE INTO user_plaxis_config 
                        (plaxis_path, port_i, port_o, plaxis_password, plaxis_version, username) 
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        plaxis_path, 
                        port_i, 
                        port_o, 
                        password, 
                        version,
                        self.app.current_username
                    ))
                    db.connection.commit()
                    safe_print(f"Config saved to database for user: {self.app.current_username}")
            except Exception as e:
                safe_print(f"Error saving config to database: {e}")