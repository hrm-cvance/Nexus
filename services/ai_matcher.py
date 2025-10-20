"""
AI Matching Service

Uses AI to intelligently match user attributes to vendor field values.
Provides suggestions with confidence levels for fields like Role, Branch, etc.
"""

import json
from typing import Optional, Dict, Any, List
from pathlib import Path
from utils.logger import get_logger

# Try to import anthropic, but don't fail if not available
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = get_logger(__name__)


class AIMatcherService:
    """Service for AI-powered field matching"""

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize AI Matcher Service

        Args:
            api_key: Anthropic API key (optional, can use env var ANTHROPIC_API_KEY)
        """
        self.client = None
        self.api_key = api_key

        # Try to initialize the client
        if not ANTHROPIC_AVAILABLE:
            logger.warning("Anthropic SDK not available - AI matching will use keyword fallback")
            return

        try:
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
            else:
                # Will use ANTHROPIC_API_KEY env var
                self.client = anthropic.Anthropic()
            logger.info("AI Matcher Service initialized successfully")
        except Exception as e:
            logger.warning(f"AI Matcher Service could not initialize: {e}")
            logger.warning("AI matching will use keyword fallback")

    def suggest_role(
        self,
        job_title: str,
        available_roles: List[Dict[str, Any]],
        department: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Suggest the best role based on job title

        Args:
            job_title: User's job title from Entra ID
            available_roles: List of available role configurations
            department: User's department (optional, for additional context)

        Returns:
            Dict with suggested role, confidence, and reasoning
        """
        if not self.client:
            logger.warning("AI client not available, using keyword matching fallback")
            return self._fallback_role_match(job_title, available_roles)

        try:
            # Build the prompt
            roles_text = "\n".join([
                f"- {role['value']}: {role['description']}"
                for role in available_roles
            ])

            prompt = f"""Given a user's job title, suggest the most appropriate role from the available options.

Job Title: {job_title}
{f"Department: {department}" if department else ""}

Available Roles:
{roles_text}

Analyze the job title and select the SINGLE most appropriate role. Consider:
1. Keywords in the job title that match role descriptions
2. Level of responsibility implied by the title
3. Common role assignments for similar titles

Respond with ONLY valid JSON in this exact format:
{{
    "suggested_role": "RoleName",
    "confidence": 0.95,
    "reasoning": "Brief explanation of why this role was selected"
}}

The confidence should be a number between 0 and 1.
"""

            # Call Claude API
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Parse response
            response_text = message.content[0].text.strip()
            logger.debug(f"AI response: {response_text}")

            # Extract JSON from response (might be wrapped in markdown)
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()

            result = json.loads(response_text)

            # Validate the suggested role exists
            role_values = [r['value'] for r in available_roles]
            if result['suggested_role'] not in role_values:
                logger.warning(f"AI suggested invalid role: {result['suggested_role']}")
                return self._fallback_role_match(job_title, available_roles)

            logger.info(f"AI suggested role '{result['suggested_role']}' with {result['confidence']:.2f} confidence")
            return result

        except Exception as e:
            logger.error(f"Error in AI role suggestion: {e}")
            return self._fallback_role_match(job_title, available_roles)

    def _fallback_role_match(
        self,
        job_title: str,
        available_roles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Fallback keyword-based role matching when AI is unavailable

        Args:
            job_title: User's job title
            available_roles: List of available role configurations

        Returns:
            Dict with suggested role, confidence, and reasoning
        """
        job_title_lower = job_title.lower()

        # Score each role based on keyword matches
        best_role = None
        best_score = 0

        for role in available_roles:
            score = 0
            matched_keywords = []

            for keyword in role.get('keywords', []):
                if keyword.lower() in job_title_lower:
                    score += 1
                    matched_keywords.append(keyword)

            if score > best_score:
                best_score = score
                best_role = role
                best_keywords = matched_keywords

        # If no keyword matches, default to "User"
        if best_score == 0:
            best_role = next((r for r in available_roles if r['value'] == 'User'), available_roles[0])
            confidence = 0.3
            reasoning = f"No specific keywords matched. Defaulting to '{best_role['value']}' (standard role)"
        else:
            confidence = min(0.5 + (best_score * 0.15), 0.95)
            reasoning = f"Matched keywords: {', '.join(best_keywords)}"

        return {
            'suggested_role': best_role['value'],
            'confidence': confidence,
            'reasoning': reasoning
        }

    @staticmethod
    def extract_cost_center(office_location: str) -> Optional[str]:
        """
        Extract 4-digit cost center from office location string

        Args:
            office_location: Office location from Entra ID

        Returns:
            4-digit cost center code, or None if not found
        """
        if not office_location:
            return None

        # Remove whitespace
        location = office_location.strip()

        # Look for patterns like "001200" or "1200"
        # Try to find a sequence of digits
        import re

        # First, try to find leading zeros pattern (e.g., "001200")
        match = re.search(r'\b0*(\d{4})\b', location)
        if match:
            return match.group(1)

        # If not found, try to find any 4-digit number
        match = re.search(r'\b(\d{4})\b', location)
        if match:
            return match.group(1)

        # If still not found, try to find the first sequence of digits
        match = re.search(r'(\d+)', location)
        if match:
            digits = match.group(1)
            # If more than 4 digits, take the last 4
            if len(digits) > 4:
                return digits[-4:]
            # If less than 4, pad with zeros
            elif len(digits) < 4:
                return digits.zfill(4)
            else:
                return digits

        return None

    @staticmethod
    def match_branch_from_dropdown(
        cost_center: str,
        dropdown_options: List[str]
    ) -> Dict[str, Any]:
        """
        Match a cost center to a branch from dropdown options

        Args:
            cost_center: 4-digit cost center code
            dropdown_options: List of branch options from the dropdown

        Returns:
            Dict with matched branch, match type, and confidence
        """
        if not cost_center or not dropdown_options:
            return {
                'matched_branch': 'Main',
                'match_type': 'fallback',
                'confidence': 0.0,
                'reasoning': 'No cost center or dropdown options available'
            }

        # Try to find exact match (cost center appears in option text)
        for option in dropdown_options:
            if cost_center in option:
                return {
                    'matched_branch': option,
                    'match_type': 'exact',
                    'confidence': 1.0,
                    'reasoning': f'Cost center {cost_center} found in branch name'
                }

        # No match found - use "Main" as fallback
        # Try to find "Main" in the dropdown options
        main_option = next((opt for opt in dropdown_options if 'Main' in opt), None)

        if main_option:
            return {
                'matched_branch': main_option,
                'match_type': 'fallback',
                'confidence': 0.0,
                'reasoning': f'No match found for cost center {cost_center}, using Main branch as fallback'
            }
        else:
            # If "Main" not found, use the first option
            return {
                'matched_branch': dropdown_options[0] if dropdown_options else 'Main',
                'match_type': 'fallback',
                'confidence': 0.0,
                'reasoning': f'No match found for cost center {cost_center}, Main branch not available, using first option'
            }
