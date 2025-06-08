#!/usr/bin/env python3

import os
import sys

import requests

# Set environment variables
os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:img2bffnlhslfigs@localhost:5433/code_myind"
)
os.environ["DATABASE_URL_WITHOUT_ASYNC"] = (
    "postgresql://postgres:img2bffnlhslfigs@localhost:5433/code_myind"
)
os.environ["JWT_SECRET_TOKEN"] = (
    "your-super-secret-jwt-key-change-this-in-production-2025"
)

BASE_URL = "http://localhost:8000"


def test_authentication_flow() -> bool:
    """Test complete authentication flow."""
    # Test 1: Login
    login_data = {"username_or_email": "testuser", "password": "MyStr0ng!P@ssw0rd2025"}

    response = requests.post(f"{BASE_URL}/api/v1/auth/login", json=login_data)

    if response.status_code == 200:
        login_result = response.json()
        access_token = login_result["access_token"]
        refresh_token = login_result["refresh_token"]
        login_result["user"]


        # Test 2: Access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = requests.get(f"{BASE_URL}/api/v1/auth/me", headers=headers)

        if me_response.status_code == 200:
            me_response.json()
        else:
            pass

        # Test 3: Session Management
        sessions_response = requests.get(
            f"{BASE_URL}/api/v1/auth/me/sessions", headers=headers,
        )

        if sessions_response.status_code == 200:
            sessions = sessions_response.json()
            for _i, _session in enumerate(sessions[:3]):  # Show first 3
                pass
        else:
            pass

        # Test 4: Token Refresh
        refresh_data = {"refresh_token": refresh_token}
        refresh_response = requests.post(
            f"{BASE_URL}/api/v1/auth/refresh", json=refresh_data,
        )

        if refresh_response.status_code == 200:
            refresh_result = refresh_response.json()
            new_access_token = refresh_result["access_token"]

            # Test new token
            new_headers = {"Authorization": f"Bearer {new_access_token}"}
            test_response = requests.get(
                f"{BASE_URL}/api/v1/auth/me", headers=new_headers,
            )
            if test_response.status_code == 200:
                pass
            else:
                pass
        else:
            pass

        # Test 5: Invalid token
        invalid_headers = {"Authorization": "Bearer invalid_token_here"}
        invalid_response = requests.get(
            f"{BASE_URL}/api/v1/auth/me", headers=invalid_headers,
        )

        if invalid_response.status_code == 401:
            pass
        else:
            pass

        # Test 6: No token
        no_token_response = requests.get(f"{BASE_URL}/api/v1/auth/me")

        if no_token_response.status_code == 401:
            pass
        else:
            pass


        return True

    return False


def test_security_features() -> None:
    """Test security features."""
    # Test password strength
    weak_passwords = ["123", "password", "abc123"]

    for pwd in weak_passwords:
        response = requests.post(
            f"{BASE_URL}/api/v1/auth/password/check", params={"password": pwd},
        )
        if response.status_code == 200:
            response.json()



if __name__ == "__main__":

    try:
        # Test if server is running
        response = requests.get(f"{BASE_URL}/docs")
        if response.status_code != 200:
            sys.exit(1)


        # Run tests
        auth_success = test_authentication_flow()
        test_security_features()

        if auth_success:
            pass
        else:
            pass

    except requests.exceptions.ConnectionError:
        pass
    except Exception:
        import traceback

        traceback.print_exc()
