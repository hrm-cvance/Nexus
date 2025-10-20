"""
Password Generator Utility

Generates secure random passwords for vendor accounts:
- Cryptographically secure using secrets module
- Configurable complexity requirements
- No ambiguous characters (0/O, 1/l/I)
- Vendor-specific rules from configuration
"""

import secrets
import string
from typing import Dict, Optional


class PasswordGenerator:
    """Secure password generator for vendor accounts"""

    # Character sets (excluding ambiguous characters)
    UPPERCASE = "ABCDEFGHJKLMNPQRSTUVWXYZ"  # Removed I, O
    LOWERCASE = "abcdefghjkmnpqrstuvwxyz"   # Removed l, o
    DIGITS = "23456789"                     # Removed 0, 1
    SPECIAL = "!@#$%^&*-_=+"                # Common allowed special chars

    @staticmethod
    def generate_password(
        length: int = 16,
        require_uppercase: int = 2,
        require_lowercase: int = 2,
        require_digits: int = 2,
        require_special: int = 2,
        allowed_special: Optional[str] = None
    ) -> str:
        """
        Generate a secure random password

        Args:
            length: Total password length
            require_uppercase: Minimum uppercase letters
            require_lowercase: Minimum lowercase letters
            require_digits: Minimum digits
            require_special: Minimum special characters
            allowed_special: Custom allowed special characters (optional)

        Returns:
            Secure random password string

        Raises:
            ValueError: If length is too short for requirements
        """
        # Validate requirements
        min_required = require_uppercase + require_lowercase + require_digits + require_special
        if length < min_required:
            raise ValueError(
                f"Password length {length} too short for requirements (min: {min_required})"
            )

        # Use custom special characters if provided
        special_chars = allowed_special if allowed_special else PasswordGenerator.SPECIAL

        # Build password with required characters
        password = []

        # Add required uppercase
        password.extend(
            secrets.choice(PasswordGenerator.UPPERCASE)
            for _ in range(require_uppercase)
        )

        # Add required lowercase
        password.extend(
            secrets.choice(PasswordGenerator.LOWERCASE)
            for _ in range(require_lowercase)
        )

        # Add required digits
        password.extend(
            secrets.choice(PasswordGenerator.DIGITS)
            for _ in range(require_digits)
        )

        # Add required special
        password.extend(
            secrets.choice(special_chars)
            for _ in range(require_special)
        )

        # Fill remaining length with random mix
        all_chars = (
            PasswordGenerator.UPPERCASE +
            PasswordGenerator.LOWERCASE +
            PasswordGenerator.DIGITS +
            special_chars
        )
        password.extend(
            secrets.choice(all_chars)
            for _ in range(length - min_required)
        )

        # Shuffle to avoid predictable patterns
        secrets.SystemRandom().shuffle(password)

        return ''.join(password)

    @staticmethod
    def generate_vendor_password(vendor_config: Dict) -> str:
        """
        Generate password based on vendor-specific requirements
        Reads requirements from vendor configuration

        Args:
            vendor_config: Vendor configuration dictionary

        Returns:
            Generated password meeting vendor requirements
        """
        password_rules = vendor_config.get("password_rules", {})

        # Extract rules with defaults
        length = password_rules.get("length", 16)
        min_uppercase = password_rules.get("min_uppercase", 2)
        min_lowercase = password_rules.get("min_lowercase", 2)
        min_digits = password_rules.get("min_digits", 2)
        min_special = password_rules.get("min_special", 2)
        allowed_special = password_rules.get("allowed_special", None)

        return PasswordGenerator.generate_password(
            length=length,
            require_uppercase=min_uppercase,
            require_lowercase=min_lowercase,
            require_digits=min_digits,
            require_special=min_special,
            allowed_special=allowed_special
        )

    @staticmethod
    def validate_password(password: str, vendor_config: Dict) -> tuple[bool, list]:
        """
        Validate a password against vendor requirements

        Args:
            password: Password to validate
            vendor_config: Vendor configuration dictionary

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        password_rules = vendor_config.get("password_rules", {})
        errors = []

        # Check length
        min_length = password_rules.get("length", 12)
        max_length = password_rules.get("max_length", 128)
        if len(password) < min_length:
            errors.append(f"Password must be at least {min_length} characters")
        if len(password) > max_length:
            errors.append(f"Password must be at most {max_length} characters")

        # Check uppercase
        min_uppercase = password_rules.get("min_uppercase", 1)
        uppercase_count = sum(1 for c in password if c.isupper())
        if uppercase_count < min_uppercase:
            errors.append(f"Password must contain at least {min_uppercase} uppercase letter(s)")

        # Check lowercase
        min_lowercase = password_rules.get("min_lowercase", 1)
        lowercase_count = sum(1 for c in password if c.islower())
        if lowercase_count < min_lowercase:
            errors.append(f"Password must contain at least {min_lowercase} lowercase letter(s)")

        # Check digits
        min_digits = password_rules.get("min_digits", 1)
        digit_count = sum(1 for c in password if c.isdigit())
        if digit_count < min_digits:
            errors.append(f"Password must contain at least {min_digits} digit(s)")

        # Check special characters
        min_special = password_rules.get("min_special", 1)
        allowed_special = password_rules.get("allowed_special", PasswordGenerator.SPECIAL)
        special_count = sum(1 for c in password if c in allowed_special)
        if special_count < min_special:
            errors.append(f"Password must contain at least {min_special} special character(s)")

        return (len(errors) == 0, errors)


# Convenience function for quick password generation
def generate_secure_password(length: int = 16) -> str:
    """Generate a secure password with default settings"""
    return PasswordGenerator.generate_password(length=length)
