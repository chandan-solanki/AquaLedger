# Reuses the existing settings:manage permission (seeded in
# 67c33121fc54_auth_and_tenancy_tables.py) rather than introducing
# company_profile:view/company_profile:edit. Unlike companies (a
# multi-record resource where operators/accountants legitimately need
# read-only access day to day), this is a single admin-only settings
# screen - every role that can even see the Settings nav group already
# requires settings:manage (frontend navigation.ts gates Company
# Profile/Numbering Sequences/Categories identically), so splitting
# read from write here would add a permission no role configuration
# actually needs.
SETTINGS_MANAGE = "settings:manage"
