from pathlib import Path
import requests
import yaml
import time
import os
import sys
from datetime import datetime
import jwt  # PyJWT

class AuthServerHandlerSingleton:
    _instance = None
    LICENSE_TIER_LIMITS = {
        'trial': {
            'feature_1': 10,  # create_model
            'feature_2': 5,
            'feature_3': 20,
            'max_projects': 100,
            'export_enabled': False
        },
        'basic': {
            'feature_1': 50,  # create_model
            'feature_2': 25,
            'feature_3': 100,
            'max_projects': 150,
            'export_enabled': True
        },
        'standard': {
            'feature_1': 100,  # create_model
            'feature_2': 50,
            'feature_3': 200,
            'max_projects': 150,
            'export_enabled': True
        },
        'premium': {
            'feature_1': -1,  # create_model - unlimited
            'feature_2': -1,
            'feature_3': -1,
            'max_projects': 200,
            'export_enabled': True
        },
        'enterprise': {
            'feature_1': -1,  # create_model - unlimited
            'feature_2': -1,
            'feature_3': -1,
            'max_projects': -1,
            'export_enabled': True,
            'priority_support': True
        }
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.base_url = None
            cls._instance.access_token = None
            cls._instance.refresh_token = None
            cls._instance.license_data = None
            cls._instance.get_auth_server_config()
        return cls._instance

    def get_auth_server_config(self):
        try:
            try:
                from config_encoded import get_config
                config_content = get_config()
                config = yaml.safe_load(config_content)
                print("Loaded config from encoded module")
            except ImportError:
                BASE_DIR = Path(__file__).resolve().parent.parent
                config_file_path = BASE_DIR / "config.yaml"
                with open(config_file_path, "r") as config_file:
                    config = yaml.safe_load(config_file)
                print("Loaded config from YAML file")

            auth_server_config = config.get("auth_server", {})
            host = auth_server_config.get("host", "127.0.0.1")
            port = auth_server_config.get("port", 5000)
            if port is not None:
                self.base_url = f"https://{host}:{port}"
            else:
                self.base_url = f"https://{host}"
            print(f"Auth server URL: {self.base_url}")

        except FileNotFoundError:
            print("Configuration file not found.")
            self.base_url = None
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file: {e}")
            self.base_url = None
        except Exception as e:
            print(f"Error loading auth config: {str(e)}")
            self.base_url = None

    def login(self, username: str, password: str) -> dict:
        if not self.base_url:
            return {"status_code": False, "message": "Auth server configuration not loaded", "authenticated": False}
        
        login_url = f"{self.base_url}/user/login"
        try:
            payload = {"username": username, "password": password}
            response = requests.post(login_url, json=payload)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.refresh_token = data.get("refresh_token")
                self.license_data = None
                return {"status_code": True, "message": "Login successful.", "authenticated": data.get("authenticated", False)}
            else:
                print(f"Authentication failed with status code: {response.status_code}")
                return {"status_code": False, "message": f"Authentication failed with status code: {response.status_code}", "authenticated": False}
        except requests.RequestException as e:
            print(f"Error contacting the authentication server: {e}")
            return {"status_code": False, "message": str(e), "authenticated": False}

    def logout(self) -> dict:
        if not self.access_token:
            print("No access token found.")
            return {"status_code": False, "message": "No access token found."}
        if not self.base_url:
            return {"status_code": False, "message": "Auth server configuration not loaded"}
            
        logout_url = f"{self.base_url}/user/logout"
        headers = {"Authorization": f"Bearer {self.access_token}"}
        try:
            response = requests.post(logout_url, headers=headers)
            if response.status_code == 200:
                print("Logout successful.")
                self.access_token = None
                self.refresh_token = None
                self.license_data = None
                return {"status_code": True, "message": response.json().get("msg", "Logout successful.")}
            else:
                print(f"Logout failed: {response.status_code}")
                self.access_token = None
                self.refresh_token = None
                self.license_data = None
                return {"status_code": False, "message": f"Logout failed: {response.status_code}"}
        except requests.RequestException as e:
            print(f"Error contacting the authentication server: {e}")
            self.access_token = None
            self.refresh_token = None
            self.license_data = None
            return {"status_code": False, "message": str(e)}

    def _make_authenticated_request(self, method, url, **kwargs):
        """Helper method to make authenticated requests with automatic token refresh"""
        headers = kwargs.get('headers', {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        kwargs['headers'] = headers
        
        try:
            if method.upper() == 'GET':
                response = requests.get(url, **kwargs)
            elif method.upper() == 'POST':
                response = requests.post(url, **kwargs)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            if response.status_code == 401 and self.refresh_token:
                print("Access token expired, attempting to refresh...")
                refresh_result = self.refresh_access_token()
                
                if refresh_result.get("status_code", False):
                    print("Token refreshed successfully, retrying request...")
                    headers["Authorization"] = f"Bearer {self.access_token}"
                    kwargs['headers'] = headers
                    
                    if method.upper() == 'GET':
                        response = requests.get(url, **kwargs)
                    elif method.upper() == 'POST':
                        response = requests.post(url, **kwargs)
                else:
                    print("Token refresh failed")
            
            return response
            
        except requests.RequestException as e:
            raise e

    def get_fullname(self) -> dict:
        if not self.access_token:
            print("No access token found.")
            return {"status_code": False, "message": "No access token found."}
        if not self.base_url:
            return {"status_code": False, "message": "Auth server configuration not loaded"}
            
        fullname_url = f"{self.base_url}/user/get_fullname"
        try:
            response = self._make_authenticated_request('GET', fullname_url)
            
            if response.status_code == 200:
                data = response.json()
                return {"status_code": True, "message": "Full name retrieved successfully.", "fullname": data.get("full_name")}
            else:
                print(f"Failed to get full name: {response.status_code}")
                return {"status_code": False, "message": f"Failed to get full name: {response.status_code}"}
        except requests.RequestException as e:
            print(f"Error contacting the authentication server: {e}")
            return {"status_code": False, "message": str(e)}

    def refresh_access_token(self) -> dict:
        if not self.refresh_token:
            print("No refresh token found.")
            return {"status_code": False, "message": "No refresh token found."}
        if not self.base_url:
            return {"status_code": False, "message": "Auth server configuration not loaded"}
            
        refresh_url = f"{self.base_url}/user/refresh_token"
        headers = {"Authorization": f"Bearer {self.refresh_token}"}
        try:
            response = requests.post(refresh_url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("access_token")
                self.license_data = None
                print("Access token refreshed.")
                return {"status_code": True, "message": "Access token refreshed."}
            else:
                print(f"Failed to refresh token: {response.status_code}")
                if response.status_code == 401:
                    print("Refresh token expired or invalid, clearing all tokens")
                    self.access_token = None
                    self.refresh_token = None
                    self.license_data = None
                return {"status_code": False, "message": f"Failed to refresh token: {response.status_code}"}
        except requests.RequestException as e:
            print(f"Error contacting the authentication server: {e}")
            return {"status_code": False, "message": str(e)}

    def change_password(self, old_password: str, new_password: str) -> dict:
        if not self.access_token:
            print("No access token found.")
            return {"status_code": False, "message": "No access token found."}
        if not self.base_url:
            return {"status_code": False, "message": "Auth server configuration not loaded"}
            
        if not old_password or not new_password:
            print("Old password and new password must be provided.")
            return {"status_code": False, "message": "Old password and new password must be provided."}
        if old_password == new_password:
            print("Old password and new password cannot be the same.")
            return {"status_code": False, "message": "Old password and new password cannot be the same."}
        
        change_url = f"{self.base_url}/user/change_password"
        payload = {"old_password": old_password, "new_password": new_password}
        try:
            response = self._make_authenticated_request('POST', change_url, json=payload)
            
            if response.status_code == 200:
                print("Password changed successfully.")
                return {"status_code": True, "message": response.json().get("msg", "Password changed successfully. Please log in again.")}
            else:
                print(f"Failed to change password: {response.status_code}")
                return {"status_code": False, "message": f"Failed to change password: {response.status_code}"}
        except requests.RequestException as e:
            print(f"Error contacting the authentication server: {e}")
            return {"status_code": False, "message": str(e)}

    def is_authenticated(self) -> dict:
        if not self.access_token:
            return {"status_code": False, "message": "No access token found."}
        try:
            payload = jwt.decode(self.access_token, options={"verify_signature": False})
            exp = payload.get("exp")
            if exp and exp > int(time.time()):
                return {"status_code": True, "message": "User is authenticated."}
            else:
                print("Access token expired.")
                return {"status_code": False, "message": "Access token expired."}
        except Exception as e:
            print(f"Error decoding access token: {e}")
            return {"status_code": False, "message": str(e)}

    def get_license(self) -> dict:
        if self.license_data:
            print("\n" + "=" * 70)
            print("RETURNING CACHED LICENSE DATA")
            print("=" * 70)
            import json
            print(json.dumps(self.license_data, indent=2))
            print("=" * 70 + "\n")
            return {"status_code": True, "license_data": self.license_data}
    
        if not self.access_token:
            return {"status_code": False, "message": "No access token found."}
        if not self.base_url:
            return {"status_code": False, "message": "Auth server configuration not loaded"}
        
        license_url = f"{self.base_url}/license/get_license"
        try:
            print("\n" + "=" * 70)
            print("FETCHING LICENSE FROM SERVER")
            print("=" * 70)
            
            response = self._make_authenticated_request('GET', license_url)
            
            print(f"Response Status: {response.status_code}")
            print("-" * 70)
            
            if response.status_code == 200:
                response_json = response.json()
                
                import json
                print("SERVER RESPONSE FORMAT:")
                print(json.dumps(response_json, indent=2))
                print("=" * 70 + "\n")
                
                self.license_data = dict(response_json)
                
                return {"status_code": True, "license_data": self.license_data}
                
            elif response.status_code == 404:
                print("LICENSE NOT FOUND (404)")
                print("=" * 70 + "\n")
                return {"status_code": False, "message": "License not found."}
            else:
                print(f"FAILED TO GET LICENSE: Status {response.status_code}")
                print(f"Response body: {response.text}")
                print("=" * 70 + "\n")
                return {"status_code": False, "message": f"Failed to get license: {response.status_code}"}
                
        except requests.RequestException as e:
            print(f"REQUEST EXCEPTION: {str(e)}")
            print("=" * 70 + "\n")
            return {"status_code": False, "message": str(e)}

    def is_license_valid(self) -> dict:
        """
        Enhanced validation that returns detailed status information
        Returns: dict with keys:
            - valid: bool - overall validity
            - error_type: str - 'expired', 'inactive', 'no_features', 'not_found', etc.
            - message: str - detailed error message
            - expiry_date: str - expiry date if available
        """
        l = self.get_license()
        
        if not l.get("status_code", False):
            print("License retrieval failed.")
            return {
                "valid": False,
                "error_type": "not_found",
                "message": "License not found or could not be retrieved."
            }
        
        license_data = l.get("license_data", {})
        
        # ✅ Check license status (active/inactive)
        license_status = license_data.get("status", "").lower()
        print(f"[DEBUG] License status: {license_status}")
        
        if license_status == "inactive":
            return {
                "valid": False,
                "error_type": "inactive",
                "message": "Your license is inactive. Please contact support to activate your license."
            }
        
        # Check expiry date
        expiry_date = license_data.get("expiry_date", None)
        if expiry_date:
            try:
                expiry_timestamp = int(time.mktime(time.strptime(expiry_date, "%a, %d %b %Y %H:%M:%S %Z")))
                current_timestamp = int(time.time())
                print("expiry_timestamp:", expiry_timestamp)
                print("current_timestamp:", current_timestamp)
                if expiry_timestamp < current_timestamp:
                    print("License has expired.")
                    return {
                        "valid": False,
                        "error_type": "expired",
                        "message": f"Your license expired on {expiry_date}. Please renew your license to continue using this feature.",
                        "expiry_date": expiry_date
                    }
            except ValueError:
                print("Invalid date format in license data.")
                return {
                    "valid": False,
                    "error_type": "invalid_date",
                    "message": "Invalid expiry date format in license data."
                }
        else:
            print("No expiry date found in license data.")
            return {
                "valid": False,
                "error_type": "no_expiry",
                "message": "No expiry date found in license data."
            }
        
        # Check if there are any features with remaining usage
        features = license_data.get("features", [])
        has_valid_features = False
        
        for feature in features:
            if feature.get("remaining_usage", 0) > 0:
                print(f"Feature '{feature.get('feature_name')}' is available with {feature.get('remaining_usage')} usages remaining.")
                has_valid_features = True
                break
        
        if not has_valid_features:
            print("No valid features available in the license.")
            return {
                "valid": False,
                "error_type": "no_features",
                "message": "No features with remaining usage available in your license. Please upgrade or contact support."
            }
        
        return {
            "valid": True,
            "error_type": None,
            "message": "License is valid.",
            "expiry_date": expiry_date
        }

    def get_license_tier(self) -> str:
        """Get the current license tier - with proper normalization"""
        license_result = self.get_license()
        if not license_result.get("status_code", False):
            return None
    
        license_data = license_result.get("license_data", {})
        tier = license_data.get("license_level", "trial")
        
        # ✅ Normalize tier name to lowercase for consistency
        tier_normalized = tier.lower().strip()
        
        # ✅ Validate against known tiers
        if tier_normalized not in self.LICENSE_TIER_LIMITS:
            print(f"[WARNING] Unknown license tier '{tier}', defaulting to 'trial'")
            return "trial"
        
        print(f"[DEBUG] License tier: {tier_normalized}")
        return tier_normalized

    def get_feature_limit(self, feature_name: str) -> int:
        """Get the limit for a specific feature based on license tier"""
        tier = self.get_license_tier()
        if not tier or tier not in self.LICENSE_TIER_LIMITS:
            return 0
    
        # Translate app feature name to server feature name for lookup
        server_feature_name = self._reverse_translate_feature_name(feature_name)
        tier_limits = self.LICENSE_TIER_LIMITS[tier]
        return tier_limits.get(server_feature_name, 0)

    def is_feature_unlimited(self, feature_name: str) -> bool:
        """Check if a feature has unlimited usage in current tier"""
        limit = self.get_feature_limit(feature_name)
        return limit == -1

    def force_refresh_license(self):
        """Force refresh license data from server (clear cache)"""
        print("[DEBUG] Forcing license refresh - clearing cached data")
        self.license_data = None
        return self.get_license()

    def _translate_feature_name(self, server_feature_name: str) -> str:
        """Translate server feature names (feature_1, feature_2) to app feature names"""
        feature_map = {
            'feature_1': 'create_model',
            'feature_2': 'feature_2',  # Reserved for future use
            'feature_3': 'feature_3'   # Reserved for future use
        }
        return feature_map.get(server_feature_name, server_feature_name)
    
    def _reverse_translate_feature_name(self, app_feature_name: str) -> str:
        """Translate app feature names to server feature names"""
        reverse_map = {
            'create_model': 'feature_1',
            'feature_2': 'feature_2',
            'feature_3': 'feature_3'
        }
        return reverse_map.get(app_feature_name, app_feature_name)

    def can_use_feature(self, feature_name: str) -> dict:
        """
        Enhanced: Check both tier limits and remaining usage, with detailed error info
        Returns: dict with keys:
            - allowed: bool
            - reason: str - reason for denial if not allowed
            - error_type: str - type of error (expired, inactive, no_usage, etc.)
        """
        print(f"\n{'='*70}")
        print(f"[DEBUG] can_use_feature called with: '{feature_name}'")
        print(f"{'='*70}")
    
        if not feature_name:
            print(f"[DEBUG] Feature name is empty, returning False")
            return {
                "allowed": False,
                "reason": "Feature name not provided.",
                "error_type": "invalid_input"
            }
        
        # First check if license is valid (not expired, not inactive)
        license_validity = self.is_license_valid()
        if not license_validity.get("valid", False):
            error_type = license_validity.get("error_type")
            message = license_validity.get("message")
            print(f"[DEBUG] License invalid: {error_type} - {message}")
            return {
                "allowed": False,
                "reason": message,
                "error_type": error_type
            }
  
        # Translate app feature name to server feature name
        server_feature_name = self._reverse_translate_feature_name(feature_name)
        print(f"[DEBUG] Translated '{feature_name}' to server name '{server_feature_name}'")
  
        # Check if feature exists in current tier (using server name)
        tier = self.get_license_tier()
        print(f"[DEBUG] Current tier: {tier}")
    
        if not tier or tier not in self.LICENSE_TIER_LIMITS:
            print(f"[DEBUG] Tier invalid or not in LICENSE_TIER_LIMITS")
            return {
                "allowed": False,
                "reason": "Invalid license tier.",
                "error_type": "invalid_tier"
            }
  
        tier_limits = self.LICENSE_TIER_LIMITS[tier]
        print(f"[DEBUG] Tier limits for '{tier}': {tier_limits}")
    
        # Check using server feature name (feature_1 instead of create_model)
        if server_feature_name not in tier_limits:
            print(f"[DEBUG] Feature '{server_feature_name}' not in tier_limits keys: {list(tier_limits.keys())}")
            return {
                "allowed": False,
                "reason": f"Feature '{feature_name}' is not available in your current license tier.",
                "error_type": "feature_not_in_tier"
            }
  
        # If unlimited in tier, allow usage
        tier_limit_value = tier_limits[server_feature_name]
        print(f"[DEBUG] Tier limit value for '{server_feature_name}': {tier_limit_value}")
    
        if tier_limit_value == -1:
            print(f"[DEBUG] Feature is unlimited in tier, returning True")
            return {
                "allowed": True,
                "reason": "Unlimited usage",
                "error_type": None
            }
  
        # Otherwise check remaining usage from server
        license_result = self.get_license()
        print(f"[DEBUG] License result status: {license_result.get('status_code', False)}")
    
        if not license_result.get("status_code", False):
            print(f"[DEBUG] Failed to get license")
            return {
                "allowed": False,
                "reason": "Failed to retrieve license information.",
                "error_type": "license_fetch_failed"
            }
  
        license_data = license_result.get("license_data", {})
        features = license_data.get("features", [])
        print(f"[DEBUG] Number of features from server: {len(features)}")
        print(f"[DEBUG] Features from server: {features}")
      
        for idx, feature in enumerate(features):
            feature_server_name = feature.get("feature_name")
            remaining = feature.get("remaining_usage", 0)
            print(f"[DEBUG] Feature {idx}: name='{feature_server_name}', remaining={remaining}")
        
            # Compare server names directly
            if feature_server_name == server_feature_name:
                print("[DEBUG] MATCH FOUND!")
                print(f"[DEBUG] Remaining usage: {remaining}")
                
                if remaining > 0:
                    print(f"[DEBUG] Usage allowed, {remaining} remaining")
                    return {
                        "allowed": True,
                        "reason": f"{remaining} uses remaining",
                        "error_type": None,
                        "remaining_usage": remaining
                    }
                else:
                    print(f"[DEBUG] No remaining usage")
                    return {
                        "allowed": False,
                        "reason": f"You have exhausted your usage limit for '{feature_name}'. Please upgrade your license for additional usage.",
                        "error_type": "no_usage_remaining"
                    }
  
        print(f"[DEBUG] NO MATCH - Feature '{server_feature_name}' not found in server response")
        print("=" * 70 + "\n")
        return {
            "allowed": False,
            "reason": f"Feature '{feature_name}' not found in license data.",
            "error_type": "feature_not_found"
        }
   
    def get_tier_capabilities(self) -> dict:
        """Get all capabilities for the current license tier"""
        tier = self.get_license_tier()
        if not tier or tier not in self.LICENSE_TIER_LIMITS:
            return {}
    
        return self.LICENSE_TIER_LIMITS[tier].copy()

    def record_license_usage(self, feature_name: str) -> dict:
        if not feature_name:
            return {"status_code": False, "message": "Feature name must be provided."}
        
        # Translate app feature name to server feature name
        server_feature_name = self._reverse_translate_feature_name(feature_name)
        print(f"[DEBUG] Recording usage for '{feature_name}' -> '{server_feature_name}'")
        
        if not self._rerecord_license_usage_local(server_feature_name):
            return {"status_code": False, "message": "Local usage recording failed."}
        if not self.access_token:
            return {"status_code": False, "message": "No access token found."}
        if not self.base_url:
            return {"status_code": False, "message": "Auth server configuration not loaded"}
            
        usage_url = f"{self.base_url}/license/record_usage"
        payload = {"feature_name": server_feature_name}
        try:
            response = self._make_authenticated_request('POST', usage_url, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                return {"status_code": True, "message": data.get("msg", "Usage recorded.")}
            elif response.status_code == 400:
                data = response.json()
                return {"status_code": False, "message": data.get("msg", "Invalid usage.")}
            else:
                return {"status_code": False, "message": f"Failed to record usage: {response.status_code}"}
        except requests.RequestException as e:
            return {"status_code": False, "message": str(e)}

    def _rerecord_license_usage_local(self, server_feature_name: str) -> bool:
        """Decrease local cached usage count"""
        l = self.get_license()
        print(f"License data from _rerecord_license_usage_local: {l}")
        if not l.get("status_code", False):
            return False
        license_data = l.get("license_data", {})
        features = license_data.get("features", [])
        for feature in features:
            if feature.get("feature_name") == server_feature_name:
                remaining_usage = feature.get("remaining_usage", 0)
                if remaining_usage > 0:
                    print(f"Feature '{server_feature_name}' has {remaining_usage} usages remaining.")
                    remaining_usage -= 1
                    print(f"Usage recorded for feature '{server_feature_name}'. Remaining usage: {remaining_usage}")
                    feature["remaining_usage"] = remaining_usage
                    return True
        return False