#!/usr/bin/env python3
"""Example: Authentication options and token management."""

from pathlib import Path

from easygoogleapi import GoogleService

CREDENTIALS_PATH = Path(__file__).parent.parent / "tests" / "credentials.json"
TOKEN_PATH = Path(__file__).parent.parent / "tests" / "example_token.pickle"


def example_auto_auth():
    """Default: automatic authentication on init."""
    print("=== Auto Authentication ===")

    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["calendar"],
        token_path=TOKEN_PATH,
        oauth_port=8080,
    )

    print(f"  Authenticated: {google.is_authenticated}")
    print(f"  Credential type: {google.credential_type.value}")
    print(f"  Token expiry: {google.token_expiry}")
    print(f"  Redirect URI: {google.oauth_redirect_uri}")
    print(f"  Scopes: {len(google.scopes)} scope(s)")

    return google


def example_delayed_auth():
    """Delayed authentication - useful for checking token status first."""
    print("\n=== Delayed Authentication ===")

    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["calendar"],
        token_path=TOKEN_PATH,
        auto_auth=False,  # Don't authenticate yet
    )

    print(f"  Authenticated before: {google.is_authenticated}")

    # Manually trigger authentication
    google.authenticate()

    print(f"  Authenticated after: {google.is_authenticated}")

    return google


def example_manual_flow():
    """Manual OAuth flow - for web apps or custom UIs."""
    print("\n=== Manual OAuth Flow ===")

    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["calendar"],
        token_path=Path("/tmp/manual_token.pickle"),
        auto_auth=False,
    )

    # Get the authorization URL
    auth_url = google.get_auth_url()
    print(f"  Authorization URL (first 80 chars):")
    print(f"    {auth_url[:80]}...")

    print("\n  In a real app, you would:")
    print("    1. Redirect user to auth_url")
    print("    2. User authorizes your app")
    print("    3. Google redirects back with a code")
    print("    4. Call google.exchange_code(code)")


def example_token_refresh():
    """Force refresh an existing token."""
    print("\n=== Token Refresh ===")

    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["calendar"],
        token_path=TOKEN_PATH,
    )

    print(f"  Token expiry before: {google.token_expiry}")

    try:
        google.refresh_token()
        print(f"  Token expiry after: {google.token_expiry}")
        print("  Token refreshed successfully!")
    except Exception as e:
        print(f"  Could not refresh: {e}")


def example_logout():
    """Local logout - delete stored token."""
    print("\n=== Logout ===")

    # Create a separate token for this example
    temp_token = Path("/tmp/logout_example_token.pickle")

    google = GoogleService(
        credentials_path=CREDENTIALS_PATH,
        services=["calendar"],
        token_path=temp_token,
    )

    print(f"  Token file exists: {temp_token.exists()}")
    print(f"  Authenticated: {google.is_authenticated}")

    # Logout (local only - doesn't revoke with Google)
    google.logout()

    print(f"  After logout:")
    print(f"    Token file exists: {temp_token.exists()}")
    print(f"    Authenticated: {google.is_authenticated}")


def main():
    print("EasyGoogleAPI Authentication Examples")
    print("=" * 50)

    google = example_auto_auth()
    example_delayed_auth()
    example_manual_flow()
    example_token_refresh()
    example_logout()

    print("\n" + "=" * 50)
    print("All examples completed!")


if __name__ == "__main__":
    main()
