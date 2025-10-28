"""
Test script for Certified Credit automation

This script tests the Certified Credit user provisioning automation
with a mock user to verify the workflow before using with real users.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from models.user import EntraUser
from automation.vendors.certifiedcredit import provision_user


async def test_certifiedcredit():
    """Test Certified Credit automation with a mock user"""

    # Create a test user
    test_user = EntraUser(
        id="test-user-id",
        user_principal_name="test.processor@example.com",
        display_name="Test Processor",
        given_name="Test",
        surname="Processor",
        mail="test.processor@example.com",
        job_title="Loan Processor",
        department="Operations",
        office_location="Main Office",
        business_phones=["336-848-1234"],
        mobile_phone="336-848-5678"
    )

    print("Testing Certified Credit automation...")
    print(f"User: {test_user.display_name} ({test_user.mail})")
    print(f"Expected username: TProcessor (First initial + Last name)")

    # Get config path
    config_path = Path(__file__).parent / "Vendors" / "CertifiedCredit" / "config.json"
    print(f"Config: {config_path}")
    print("-" * 60)

    # Run automation (no API key needed for Certified Credit)
    result = await provision_user(test_user, str(config_path), api_key=None)

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"\nMessages:")
    for msg in result.get('messages', []):
        print(f"  {msg}")

    if result.get('warnings'):
        print(f"\nWarnings:")
        for warning in result['warnings']:
            print(f"  {warning}")

    if result.get('errors'):
        print(f"\nErrors:")
        for error in result['errors']:
            print(f"  {error}")

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_certifiedcredit())
