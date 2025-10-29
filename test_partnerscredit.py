"""
Test script for Partners Credit automation
"""

import asyncio
from pathlib import Path

from models.user import EntraUser
from automation.vendors.partnerscredit import provision_user


async def test_partnerscredit():
    """Test Partners Credit user provisioning"""

    # Create test user
    test_user = EntraUser(
        id="test-user-id",
        user_principal_name="test.processor@example.com",
        display_name="Test Processor",
        given_name="Test",
        surname="Processor",
        mail="test.processor@highlandsmortgage.com",
        job_title="Loan Processor",
        department="Operations",
        business_phones=[],
        mobile_phone="3368481234"  # No dashes
    )

    # Path to config
    config_path = Path(__file__).parent / "Vendors" / "PartnersCredit" / "config.json"

    print(f"Testing Partners Credit automation for: {test_user.display_name}")
    print(f"Config path: {config_path}")
    print("-" * 60)

    # Run provisioning
    result = await provision_user(test_user, str(config_path), api_key=None)

    # Display results
    print("\n" + "=" * 60)
    print("PARTNERS CREDIT AUTOMATION RESULT")
    print("=" * 60)
    print(f"Success: {result['success']}")
    print(f"User: {result['user']}")
    print()

    if result['messages']:
        print("Messages:")
        for msg in result['messages']:
            print(f"  {msg}")
        print()

    if result['warnings']:
        print("Warnings:")
        for warn in result['warnings']:
            print(f"  ⚠ {warn}")
        print()

    if result['errors']:
        print("Errors:")
        for err in result['errors']:
            print(f"  ✗ {err}")
        print()

    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_partnerscredit())
