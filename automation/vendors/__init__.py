"""
Vendor automation modules for Nexus GUI

Each vendor module provides a provision_user function that automates
account creation/configuration for that vendor.
"""

from .accountchek import provision_user as provision_accountchek
from .bankvod import provision_user as provision_bankvod
from .certifiedcredit import provision_user as provision_certifiedcredit
from .clearcapital import provision_user as provision_clearcapital
from .dataverify import provision_user as provision_dataverify
from .experience import provision_user as provision_experience
from .mmi import provision_user as provision_mmi
from .partnerscredit import provision_user as provision_partnerscredit
from .theworknumber import provision_user as provision_theworknumber

__all__ = [
    'provision_accountchek',
    'provision_bankvod',
    'provision_certifiedcredit',
    'provision_clearcapital',
    'provision_dataverify',
    'provision_experience',
    'provision_mmi',
    'provision_partnerscredit',
    'provision_theworknumber',
]
