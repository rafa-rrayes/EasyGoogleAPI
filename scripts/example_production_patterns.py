#!/usr/bin/env python3
"""Example: Multi-user web application pattern.

This example demonstrates how to use EasyGoogleAPI in a production
multi-user web application with database-backed token storage.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from easygoogleapi import GoogleService, InMemoryTokenStore

# In a real application, you would use a database-backed store
# For this example, we'll use InMemoryTokenStore for demonstration


def example_multi_user_calendar():
    """Demonstrate multi-user calendar access."""
    
    # Simulated user IDs (in real app, these come from your auth system)
    user_ids = ["user_alice", "user_bob", "user_charlie"]
    
    # Shared token store (in production, this would be backed by your database)
    token_store = InMemoryTokenStore()
    
    # Simulated credentials path (in production, this would be your OAuth client secrets)
    # For this demo, we're assuming tokens are already in the store
    credentials_path = Path(__file__).parent.parent / "tests" / "credentials.json"
    
    # Check if credentials exist
    if not credentials_path.exists():
        print(f"⚠️  Credentials not found at {credentials_path}")
        print("This example requires valid OAuth credentials for demonstration.")
        return
    
    print("=" * 70)
    print("Multi-User Calendar Example")
    print("=" * 70)
    
    # Process each user
    for user_id in user_ids:
        print(f"\n📅 Processing calendar for: {user_id}")
        print("-" * 70)
        
        try:
            # Create a GoogleService instance for this specific user
            # In a web app, you'd create this per-request or per-background-job
            google = GoogleService.for_user(
                user_id=user_id,
                token_store=token_store,
                credentials_path=credentials_path,
                services=["calendar"],
                auto_auth=False,  # Don't auto-authenticate (would open browser)
            )
            
            # In a real app, tokens would already be in the store from OAuth flow
            # For demo purposes, we check if authenticated
            if not google.is_authenticated:
                print(f"  ⚠️  User {user_id} not authenticated (no token in store)")
                print(f"  In production, redirect to OAuth flow for this user")
                continue
            
            # List upcoming events
            start = datetime.now(UTC)
            end = start + timedelta(days=7)
            
            events = google.calendar.list_events(
                time_min=start,
                time_max=end,
                max_results=5,
            )
            
            print(f"  ✓ Found {len(events)} upcoming events for {user_id}")
            
            for event in events[:3]:  # Show first 3
                summary = event.get("summary", "Untitled")
                start_time = event.get("start", {}).get("dateTime", "N/A")
                print(f"    • {summary} ({start_time})")
                
        except Exception as e:
            print(f"  ✗ Error for {user_id}: {e}")
    
    print("\n" + "=" * 70)
    print("Key Points:")
    print("=" * 70)
    print("✓ Each user has their own GoogleService instance")
    print("✓ Token store is shared (backed by database in production)")
    print("✓ Instances are stateless and safe for concurrent use")
    print("✓ Perfect for web requests or background workers")


def example_service_account_with_delegation():
    """Demonstrate service account with domain delegation."""
    
    print("\n" + "=" * 70)
    print("Service Account with Domain Delegation Example")
    print("=" * 70)
    
    # Service account credentials path
    sa_credentials_path = Path(__file__).parent.parent / "tests" / "service_account.json"
    
    if not sa_credentials_path.exists():
        print(f"\n⚠️  Service account credentials not found")
        print("This example requires a service account with domain delegation.")
        return
    
    # Example: Access user's calendar using service account
    user_email = "user@yourdomain.com"
    
    print(f"\n🔐 Accessing calendar for {user_email} via service account...")
    print("-" * 70)
    
    try:
        # Create GoogleService with service account
        google = GoogleService.for_service_account(
            credentials_path=sa_credentials_path,
            services=["calendar", "drive"],
            impersonate_user=user_email,  # Domain delegation
        )
        
        print(f"  ✓ Authenticated as service account")
        print(f"  ✓ Impersonating: {user_email}")
        
        # Now you can access the user's data without user consent
        events = google.calendar.list_events(max_results=5)
        print(f"  ✓ Retrieved {len(events)} events")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")


def example_background_worker_pattern():
    """Demonstrate safe pattern for background workers (Celery, RQ, etc.)."""
    
    print("\n" + "=" * 70)
    print("Background Worker Pattern Example")
    print("=" * 70)
    
    print("\n📦 Simulated Celery/RQ task execution...")
    print("-" * 70)
    
    # Check if credentials exist
    credentials_path = Path(__file__).parent.parent / "tests" / "credentials.json"
    if not credentials_path.exists():
        print("\n⚠️  No credentials found, showing conceptual example only\n")
        credentials_path = "oauth_client.json"  # Placeholder for demo
    
    # Simulate background task
    def sync_user_calendar(user_id: str, credentials_file: str):
        """Background task to sync a user's calendar.
        
        This would be a Celery task in production:
        
        @app.task
        def sync_user_calendar(user_id: str):
            ...
        """
        print(f"\n  [Task] Syncing calendar for user: {user_id}")
        
        # Create token store (in production, inject database connection)
        token_store = InMemoryTokenStore()
        
        try:
            # Create GoogleService instance for this task
            # Important: Create NEW instance per task, don't share!
            google = GoogleService.for_user(
                user_id=user_id,
                token_store=token_store,
                credentials_path=credentials_file,
                services=["calendar"],
                auto_auth=False,
            )
            
            if not google.is_authenticated:
                print(f"  [Task] ⚠️  User not authenticated, skipping")
                return
            
            # Perform sync operations
            events = google.calendar.list_events(max_results=10)
            print(f"  [Task] ✓ Synced {len(events)} events")
            # ... perform sync logic ...
            
        except Exception as e:
            print(f"  [Task] ℹ️  (Conceptual) Would handle: {e.__class__.__name__}")
            # In production: Celery will retry
        
        finally:
            # Instance is garbage collected after task completes
            # No cleanup needed - stateless design
            print(f"  [Task] ✓ Complete, instance will be GC'd")
    
    # Simulate processing multiple users in parallel tasks
    for user_id in ["user_1", "user_2", "user_3"]:
        sync_user_calendar(user_id, str(credentials_path))
    
    print("\n" + "-" * 70)
    print("Key Points:")
    print("  ✓ Create new GoogleService instance per task")
    print("  ✓ Don't share instances between tasks/threads")
    print("  ✓ Token store handles concurrency (database-backed)")
    print("  ✓ Automatic retry on transient errors (rate limits, etc.)")


def example_retry_and_error_handling():
    """Demonstrate automatic retry and error handling."""
    
    from easygoogleapi import RateLimitError, RetryConfig, MaxRetriesExceededError
    
    print("\n" + "=" * 70)
    print("Retry and Error Handling Example")
    print("=" * 70)
    
    # Create custom retry configuration
    retry_config = RetryConfig(
        max_retries=5,          # Retry up to 5 times
        base_delay=2.0,         # Start with 2 second delay
        max_delay=60.0,         # Cap at 60 seconds
        exponential_base=2.0,   # Double delay each time
        jitter=True,            # Add randomness to prevent thundering herd
    )
    
    print("\n⚙️  Custom Retry Configuration:")
    print(f"  • Max retries: {retry_config.max_retries}")
    print(f"  • Base delay: {retry_config.base_delay}s")
    print(f"  • Exponential backoff: {retry_config.exponential_base}x")
    print(f"  • Jitter: {retry_config.jitter}")
    
    print("\n🔄 The library automatically handles:")
    print("  • Rate limits (429) - Respects Retry-After header")
    print("  • Server errors (5xx) - Exponential backoff")
    print("  • Network failures - Automatic retry")
    print("  • Quota exceeded - Clear error message")
    
    print("\n💡 Error Types:")
    print("  • RateLimitError - Temporary, will retry")
    print("  • QuotaExceededError - Permanent, won't retry")
    print("  • PermissionDeniedError - Permanent, won't retry")
    print("  • NotFoundError - Permanent, won't retry")
    print("  • MaxRetriesExceededError - After all retries exhausted")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("EasyGoogleAPI - Production Multi-User Examples")
    print("=" * 70)
    
    # Run examples
    example_multi_user_calendar()
    example_service_account_with_delegation()
    example_background_worker_pattern()
    example_retry_and_error_handling()
    
    print("\n" + "=" * 70)
    print("✅ Examples Complete")
    print("=" * 70)
    print("\nFor production use:")
    print("  1. Use database-backed token store (not InMemoryTokenStore)")
    print("  2. Implement proper OAuth web flow for user consent")
    print("  3. Handle token refresh in background")
    print("  4. Monitor rate limits and quotas")
    print("  5. Implement proper error handling and logging")
    print("\nSee README.md for detailed production patterns.")
