import flet as ft
import asyncio
from frontend.auth_server_handler_singleton import AuthServerHandlerSingleton

class AuthManager:
    def __init__(self, form_app):
        self.form_app = form_app
        self.auth_handler = AuthServerHandlerSingleton()
        self.is_refreshing = False  # Prevent multiple simultaneous refresh attempts
        
    def ensure_authenticated(self) -> bool:
        """
        Enhanced authentication check that attempts token refresh before redirecting to login
        Returns True if user is authenticated (either originally or after refresh)
        """
        # Check if we're currently in the middle of a refresh to avoid infinite loops
        if self.is_refreshing:
            return False
            
        # First, check current authentication status
        auth_result = self.auth_handler.is_authenticated()
        
        if auth_result.get("status_code", False):
            # User is already authenticated
            return True
        
        # Token might be expired, try to refresh it
        print("Access token expired or invalid. Attempting to refresh...")
        
        if self.attempt_token_refresh():
            print("Token refresh successful. User remains authenticated.")
            return True
        else:
            print("Token refresh failed. Redirecting to login.")
            self.redirect_to_login()
            return False
    
    def attempt_token_refresh(self) -> bool:
        """
        Attempt to refresh the access token using the refresh token
        Returns True if refresh was successful, False otherwise
        """
        if self.is_refreshing:
            return False
            
        try:
            self.is_refreshing = True
            
            # Check if we have a refresh token
            if not self.auth_handler.refresh_token:
                print("No refresh token available. Cannot refresh.")
                return False
            
            # Attempt to refresh the token
            refresh_result = self.auth_handler.refresh_access_token()
            
            if refresh_result.get("status_code", False):
                print("Access token refreshed successfully.")
                # Clear any cached license data to force re-fetch with new token
                self.auth_handler.license_data = None
                return True
            else:
                print(f"Token refresh failed: {refresh_result.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"Error during token refresh: {str(e)}")
            return False
        finally:
            self.is_refreshing = False
    
    def redirect_to_login(self):
        """Redirect user to login screen and clear authentication state"""
        try:
            # Clear authentication tokens
            self.auth_handler.access_token = None
            self.auth_handler.refresh_token = None
            self.auth_handler.license_data = None
            
            # Reset form app state
            self.form_app.reset_to_login()
            
        except Exception as e:
            print(f"Error during login redirect: {str(e)}")
    
    async def ensure_authenticated_async(self) -> bool:
        """
        Async version of ensure_authenticated for use in async contexts
        """
        return await asyncio.get_event_loop().run_in_executor(
            None, self.ensure_authenticated
        )
    
    def logout(self):
        """
        Perform logout - clear tokens and redirect to login
        """
        try:
            # Attempt to logout on server
            logout_result = self.auth_handler.logout()
            print(f"Logout result: {logout_result.get('message', 'Logout completed')}")
        except Exception as e:
            print(f"Error during server logout: {str(e)}")
        finally:
            # Always clear local state and redirect to login regardless of server response
            self.redirect_to_login()
    
    def check_license_validity(self) -> bool:
        """
        Check if user has valid license, with automatic token refresh if needed
        """
        if not self.ensure_authenticated():
            return False
            
        return self.auth_handler.is_license_valid()
    
    def can_use_feature(self, feature_name: str) -> bool:
        """
        Check if user can use a specific feature, with automatic token refresh if needed
        """
        if not self.ensure_authenticated():
            return False
            
        return self.auth_handler.can_use_feature(feature_name)
    
    def record_feature_usage(self, feature_name: str) -> dict:
        """
        Record feature usage, with automatic token refresh if needed
        """
        if not self.ensure_authenticated():
            return {"status_code": False, "message": "User not authenticated"}
            
        return self.auth_handler.record_license_usage(feature_name)
        
    def handle_sign_in(self, username: str):
        self.is_signed_in = True
        self.current_username = username
        self.form_app.page.controls.clear()
        self.form_app.create_ui()
        self.form_app.page.update()
        
    def show_signout_confirmation(self):
        # Implementation for signout confirmation
        pass
        
