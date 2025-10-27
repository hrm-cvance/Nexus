"""
Test script for DataVerify automation
"""
import asyncio
from pathlib import Path
from models.user import EntraUser
from automation.vendors.dataverify import provision_user

async def test_dataverify():
    """Test DataVerify automation with a mock user"""

    # Create a test user (replace with real user data for testing)
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
        business_phones=["555-123-4567"],
        mobile_phone="555-987-6543"
    )

    # Path to DataVerify config
    config_path = Path(__file__).parent / "Vendors" / "DataVerify" / "config.json"

    print(f"Testing DataVerify automation...")
    print(f"User: {test_user.display_name} ({test_user.mail})")
    print(f"Expected username: TProcessor (First initial + Last name)")
    print(f"Config: {config_path}")
    print("-" * 60)

    # Run automation
    result = await provision_user(test_user, str(config_path), api_key=None)

    # Display results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Success: {result['success']}")

    if result.get('messages'):
        print("\nMessages:")
        for msg in result['messages']:
            print(f"  {msg}")

    if result.get('warnings'):
        print("\nWarnings:")
        for warning in result['warnings']:
            print(f"  {warning}")

    if result.get('errors'):
        print("\nErrors:")
        for error in result['errors']:
            print(f"  {error}")

    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_dataverify())
