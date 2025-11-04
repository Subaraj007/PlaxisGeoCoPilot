from pathlib import Path
import requests
import yaml

import time
from datetime import datetime
import jwt  # PyJWT

base_url = None

# TODO: Need to handle token expiration and refresh logic.
# Global variables to store access and refresh tokens.
# These should be replaced with a more secure storage mechanism in production.

# TODO: Ideally, this should be converted to a class to encapsulate the state
# and methods (e.g., AuthServerHandler).

# TODO: Need to persist these tokens securely. Check keyring, cryptography, etc.
# for secure storage.
access_token = None
refresh_token = None

license_data = None

def get_auth_server_config():
    """
    Load the authentication server configuration from a YAML file
    and set the global variable `base_url`.
    """
    global base_url
    BASE_DIR = Path(__file__).resolve().parent.parent
    config_file_path = BASE_DIR / "config.yaml"
    
    try:
        with open(config_file_path, "r") as config_file:
            config = yaml.safe_load(config_file)
            auth_server_config = config.get("auth_server", {})
            host = auth_server_config.get("host", "127.0.0.1")
            port = auth_server_config.get("port", 5000)
            if port is not None:
                base_url = f"https://{host}:{port}"
            else:
                base_url = f"https://{host}"
    
    except FileNotFoundError:
        print("Configuration file not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

# TODO : This is not the best practice to call this function at the module level.
#      : It should be called explicitly in the main application logic.
#      : You can do lazy loading - Load the configuration the first time it is
#       needed (on-demand), and cache it for future use. 
# Load the authentication server configuration at module import time.
get_auth_server_config()

# User management functions
# -------------------------

def login(username: str, password: str) -> dict:
    """
    Verify username and password by contacting the API server.
    """
    global base_url
    global access_token, refresh_token

    # Append '/user/login' to the base URL
    login_url = f"{base_url}/user/login"
    # print(f"Login URL: {login_url}")  # Debugging line

    try:
        # Prepare the payload
        payload = {
            "username": username,
            "password": password
        }

        # Send POST request to the API server
        response = requests.post(login_url, json=payload)

        # Check if the response status code indicates success
        if response.status_code == 200:
            # Parse the response JSON
            data = response.json()

            # update the access and refresh tokens
            access_token = data.get("access_token")
            refresh_token = data.get("refresh_token")

            # print(f"Response from server: {data}")  # Debugging line
            return {"status_code": True, "message": "Login successful.", "authenticated": data.get("authenticated", False)}
        
        else:
            print(f"Authentication failed with status code: {response.status_code}")
            return {"status_code": False, "message": f"Authentication failed with status code: {response.status_code}", "authenticated": False}

    except requests.RequestException as e:
        print(f"Error contacting the authentication server: {e}")
        return {"status_code": False, "message": str(e), "authenticated": False}

def logout() -> dict:
    """
    Log out the current user by invalidating the token on the server.
    """
    global access_token
    global base_url
    
    # Check if access token is available
    if not access_token:
        print("No access token found.")
        return {"status_code": False, "message": "No access token found."}

    logout_url = f"{base_url}/user/logout"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.post(logout_url, headers=headers)
        if response.status_code == 200:
            print("Logout successful.")
            access_token = None
            return {"status_code": True, "message": response.json().get("msg", "Logout successful.")}
        else:
            print(f"Logout failed: {response.status_code}")
            return {"status_code": False, "message": f"Logout failed: {response.status_code}"}
    except requests.RequestException as e:
        print(f"Error contacting the authentication server: {e}")
        return {"status_code": False, "message": str(e)}

def get_fullname() -> dict:
    """
    Get the full name of the current user.
    """
    global access_token
    global base_url
    
    # Check if access token is available
    if not access_token:
        print("No access token found.")
        return {"status_code": False, "message": "No access token found."}

    fullname_url = f"{base_url}/user/get_fullname"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(fullname_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            return {"status_code": True, "message": "Full name retrieved successfully.", "fullname": data.get("full_name")}
        else:
            print(f"Failed to get full name: {response.status_code}")
            return {"status_code": False, "message": f"Failed to get full name: {response.status_code}"}
    except requests.RequestException as e:
        print(f"Error contacting the authentication server: {e}")
        return {"status_code": False, "message": str(e)}

def refresh_access_token() -> dict:
    """
    Refresh the JWT access token using the refresh token.
    """
    global access_token, refresh_token
    global base_url

    if not refresh_token:
        print("No refresh token found.")
        return {"status_code": False, "message": "No refresh token found."}

    refresh_url = f"{base_url}/user/refresh_token"
    headers = {"Authorization": f"Bearer {refresh_token}"}
    try:
        response = requests.post(refresh_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            access_token = data.get("access_token")
            print("Access token refreshed.")
            return {"status_code": True, "message": "Access token refreshed."}
        else:
            print(f"Failed to refresh token: {response.status_code}")
            return {"status_code": False, "message": f"Failed to refresh token: {response.status_code}"}
    except requests.RequestException as e:
        print(f"Error contacting the authentication server: {e}")
        return {"status_code": False, "message": str(e)}

def change_password(old_password: str, new_password: str) -> dict:
    """
    Change the password for the current user.
    """
    if not access_token:
        print("No access token found.")
        return {"status_code": False, "message": "No access token found."}
    if not old_password or not new_password:
        print("Old password and new password must be provided.")
        return {"status_code": False, "message": "Old password and new password must be provided."}
    
    if old_password == new_password:
        print("Old password and new password cannot be the same.")
        return {"status_code": False, "message": "Old password and new password cannot be the same."}
    
    global base_url
    change_url = f"{base_url}/user/change_password"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "old_password": old_password,
        "new_password": new_password
    }
    try:
        response = requests.post(change_url, headers=headers, json=payload)
        if response.status_code == 200:
            print("Password changed successfully.")
            return {"status_code": True, "message": response.json().get("msg", "Password changed successfully. Please log in again.")}
        else:
            print(f"Failed to change password: {response.status_code}")
            return False
    except requests.RequestException as e:
        print(f"Error contacting the authentication server: {e}")
        return {"status_code": False, "message": str(e)}

def is_authenticated() -> dict:
    """
    Check if the user is authenticated based on the presence and validity of the access token.
    """
    global access_token
    if not access_token:
        return {"status_code": False, "message": "No access token found."}
    try:
        # Decode without verifying signature, just to read 'exp'
        payload = jwt.decode(access_token, options={"verify_signature": False})
        exp = payload.get("exp")

        # if exp:
        #     exp_datetime = datetime.fromtimestamp(exp)
        #     print(f"Access token expires at: {exp_datetime}")  # Debugging line
        # print(f"Access token expiration time: {exp}")  # Debugging line
        # print(payload)

        if exp and exp > int(time.time()):
            return {"status_code": True, "message": "User is authenticated."}
        else:
            print("Access token expired.")
            return {"status_code": False, "message": "Access token expired."}
    except Exception as e:
        print(f"Error decoding access token: {e}")
        return {"status_code": False, "message": str(e)}


# License management functions
# ----------------------------

def get_license() -> dict:
    """
    Get the current user's license details from the authentication server.
    """
    global license_data

    if license_data:
        return {"status_code": True, "license_data": license_data}
    
    global access_token, base_url
    if not access_token:
        return {"status_code": False, "message": "No access token found."}

    license_url = f"{base_url}/license/get_license"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        response = requests.get(license_url, headers=headers)
        if response.status_code == 200:
            license_data = dict(response.json())
            return {"status_code": True, "license_data": license_data}
        elif response.status_code == 404:
            return {"status_code": False, "message": "License not found."}
        else:
            return {"status_code": False, "message": f"Failed to get license: {response.status_code}"}
    except requests.RequestException as e:
        return {"status_code": False, "message": str(e)}

def is_license_valid() -> bool:
    """
    Check if the current user's license is valid.
    A license is considered valid if it has not expired and has remaining usage for at least one feature.
    """
    l = get_license()
    
    if not l.get("status_code", False):
        print("License retrieval failed.")
        return False
    
    license_data = l.get("license_data", {})
    
    # Check if the license has expired
    expiry_date = license_data.get("expiry_date", None)

    if expiry_date:
        try:
            expiry_timestamp = int(time.mktime(time.strptime(expiry_date, "%a, %d %b %Y %H:%M:%S %Z")))
            if expiry_timestamp < int(time.time()):
                print("License has expired.")
                return False  # License has expired
        except ValueError:
            print("Invalid date format in license data.")
            return False  # Invalid date format
    else:
        print("No expiry date found in license data.")
        return False

    # Check if there are any features with remaining usage
    features = license_data.get("features", [])
    for feature in features:
        if feature.get("remaining_usage", 0) > 0:
            print(f"Feature '{feature.get('feature_name')}' is available with {feature.get('remaining_usage')} usages remaining.")
            return True  # At least one feature is available for use
    
    print("No valid features available in the license.")
    return False  # No valid features available

def can_use_feature(feature_name: str) -> bool:
    """
    Check if the current user can use a specific feature based on their license.
    """
    if not feature_name:
        return False  # Feature name must be provided

    l = get_license()
    
    if not l.get("status_code", False):
        return False  # License retrieval failed
    
    license_data = l.get("license_data", {})
    
    # Check if the feature exists in the license
    features = license_data.get("features", [])
    for feature in features:
        if feature.get("feature_name") == feature_name:
            remaining_usage = feature.get("remaining_usage", 0)
            return remaining_usage > 0  # Feature is available if remaining usage is greater than 0
    
    return False  # Feature not found or no remaining usage

def record_license_usage(feature_name: str) -> dict:
    """
    Record feature usage for the current user.
    """
    global access_token, base_url

    if not feature_name:
        return {"status_code": False, "message": "Feature name must be provided."}
    
    if not _rerecord_license_usage_local(feature_name):
        return {"status_code": False, "message": "Local usage recording failed."}
    
    if not access_token:
        return {"status_code": False, "message": "No access token found."}

    usage_url = f"{base_url}/license/record_usage"
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"feature_name": feature_name}
    
    try:
        response = requests.post(usage_url, headers=headers, json=payload)
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

def _rerecord_license_usage_local(feature_name: str) -> bool:
    """
    Rerecord the license usage locally.
    This function is a placeholder for local license usage recording logic.
    """
    l = get_license()
    print(f"License data from _rerecord_license_usage_local: {l}")  # Debugging line
    if not l.get("status_code", False):
        return False
    
    license_data = l.get("license_data", {})
    features = license_data.get("features", [])
    for feature in features:
        if feature.get("feature_name") == feature_name:
            remaining_usage = feature.get("remaining_usage", 0)
            if remaining_usage > 0:
                # Here you would implement the logic to record the usage locally
                print(f"Feature '{feature_name}' has {remaining_usage} usages remaining.")
                # For example, you could write this to a local database or file
                remaining_usage -= 1
                print(f"Usage recorded for feature '{feature_name}'. Remaining usage: {remaining_usage}")
                feature["remaining_usage"] = remaining_usage
                return True  # Indicate that the local usage recording was successful
    
    return False  # No valid features available for local usage recording