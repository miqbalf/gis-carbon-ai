"""
GeoServer Unified Role Setup Script
Creates users and roles that match the unified authentication system
"""

import requests
import json
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Allow overriding via environment when running inside containers
GEOSERVER_URL = os.getenv("GEOSERVER_URL", "http://geoserver:8080/geoserver")
GEOSERVER_ADMIN_USER = "admin"
GEOSERVER_ADMIN_PASSWORD = "admin"

AUTH = (GEOSERVER_ADMIN_USER, GEOSERVER_ADMIN_PASSWORD)

# Unified role configuration
UNIFIED_ROLES = {
    "ROLE_ANONYMOUS": {
        "description": "Unauthenticated users - limited access",
        "permissions": ["public_layers_read"]
    },
    "ROLE_AUTHENTICATED": {
        "description": "Basic authenticated users",
        "permissions": ["authenticated_layers_read", "public_layers_read"]
    },
    "ROLE_ANALYST": {
        "description": "Data analysts - can run analysis",
        "permissions": ["authenticated_layers_read", "public_layers_read", "analysis_layers_read"]
    },
    "ADMIN": {
        "description": "System administrators - full access",
        "permissions": ["*"]
    }
}

# Test users
TEST_USERS = [
    {
        "username": "demo_user",
        "password": "demo123",
        "roles": ["ROLE_AUTHENTICATED"],
        "email": "demo@example.com"
    },
    {
        "username": "analyst",
        "password": "analyst123",
        "roles": ["ROLE_AUTHENTICATED", "ROLE_ANALYST"],
        "email": "analyst@example.com"
    },
    {
        "username": "admin",
        "password": "admin123",
        "roles": ["ADMIN"],
        "email": "admin@example.com"
    }
]

def create_user_group(group_name, description=""):
    """Create a user group in GeoServer (XML payload)."""
    url = f"{GEOSERVER_URL}/rest/security/usergroup/groups"
    headers = {'Content-type': 'application/xml'}
    xml = (
        f"<group>"
        f"<groupname>{group_name}</groupname>"
        f"<enabled>true</enabled>"
        f"<description>{description}</description>"
        f"</group>"
    )
    response = requests.post(url, headers=headers, data=xml.encode('utf-8'), auth=AUTH)
    if response.status_code == 201:
        logger.info(f"✅ Created group: {group_name}")
    elif response.status_code == 409:
        logger.info(f"ℹ️  Group already exists: {group_name}")
    elif response.status_code in (404, 405):
        logger.info(f"ℹ️  Skipping group create for {group_name}: endpoint not available ({response.status_code})")
    else:
        logger.error(f"❌ Error creating group {group_name}: {response.status_code} - {response.text}")
    return response.status_code

def create_user(username, password, email, groups=None):
    """Create a user in GeoServer (XML payload with group assignments)."""
    if groups is None:
        groups = []
    
    url = f"{GEOSERVER_URL}/rest/security/usergroup/users"
    headers = {'Content-type': 'application/xml'}
    # Build groups XML entries
    groups_xml = ''.join([f"<groupname>{g}</groupname>" for g in groups])
    xml = (
        f"<user>"
        f"<userName>{username}</userName>"
        f"<password>{password}</password>"
        f"<enabled>true</enabled>"
        f"<email>{email}</email>"
        f"<groups>{groups_xml}</groups>"
        f"</user>"
    )
    response = requests.post(url, headers=headers, data=xml.encode('utf-8'), auth=AUTH)
    if response.status_code == 201:
        logger.info(f"✅ Created user: {username}")
    elif response.status_code == 409:
        logger.info(f"ℹ️  User already exists: {username}")
    elif response.status_code in (404, 405):
        logger.info(f"ℹ️  Skipping user create for {username}: endpoint not available ({response.status_code})")
    else:
        logger.error(f"❌ Error creating user {username}: {response.status_code} - {response.text}")
    return response.status_code

def create_role(role_name: str) -> int:
    """Create a security role via roles REST API (works when usergroup API is restricted)."""
    url = f"{GEOSERVER_URL}/rest/security/roles/role/{role_name}"
    headers = {'Content-type': 'text/plain'}
    response = requests.post(url, headers=headers, data=b"", auth=AUTH)
    if response.status_code in (200, 201):
        logger.info(f"✅ Ensured role exists: {role_name}")
    elif response.status_code == 409:
        logger.info(f"ℹ️  Role already exists: {role_name}")
    elif response.status_code in (404, 405):
        logger.info(f"ℹ️  Skipping role create for {role_name}: endpoint not available ({response.status_code})")
    else:
        logger.error(f"❌ Error creating role {role_name}: {response.status_code} - {response.text}")
    return response.status_code

def assign_role_to_user(username: str, role_name: str) -> int:
    """Assign role to user via roles REST API."""
    url = f"{GEOSERVER_URL}/rest/security/roles/user/{username}/role/{role_name}"
    headers = {'Content-type': 'text/plain'}
    response = requests.post(url, headers=headers, data=b"", auth=AUTH)
    if response.status_code in (200, 201):
        logger.info(f"✅ Assigned role {role_name} to user {username}")
    elif response.status_code == 409:
        logger.info(f"ℹ️  Role {role_name} already assigned to user {username}")
    elif response.status_code in (404, 405):
        logger.info(f"ℹ️  Skipping role assignment {role_name}->{username}: endpoint not available ({response.status_code})")
    else:
        logger.error(f"❌ Error assigning role {role_name} to user {username}: {response.status_code} - {response.text}")
    return response.status_code

def configure_layer_security(workspace, layer_name, read_roles, write_roles=None):
    """Configure layer security with role-based access"""
    if write_roles is None:
        write_roles = ["ADMIN"]
    
    url = f"{GEOSERVER_URL}/rest/security/acl/layers/{workspace}.{layer_name}.properties"
    
    # Construct the ACL content
    content = f"{workspace}.{layer_name}.r = {','.join(read_roles)}\n"
    content += f"{workspace}.{layer_name}.w = {','.join(write_roles)}\n"

    headers = {'Content-type': 'text/plain'}
    response = requests.put(url, headers=headers, data=content, auth=AUTH)
    if response.status_code == 200:
        logger.info(f"✅ Configured security for layer: {workspace}.{layer_name}")
    elif response.status_code in (404, 405):
        logger.info(f"ℹ️  Skipping layer ACL for {workspace}.{layer_name}: endpoint not available ({response.status_code})")
    else:
        logger.error(f"❌ Error configuring security for {workspace}.{layer_name}: {response.status_code} - {response.text}")
    return response.status_code

def setup_workspace_security(workspace):
    """Set up security for all layers in a workspace"""
    # Get all layers in the workspace
    url = f"{GEOSERVER_URL}/rest/workspaces/{workspace}/layers"
    response = requests.get(url, auth=AUTH)
    
    if response.status_code != 200:
        logger.error(f"❌ Error fetching layers for workspace {workspace}")
        return
    
    layers_data = response.json()
    layers = layers_data.get('layers', {}).get('layer', [])
    
    if not isinstance(layers, list):
        layers = [layers]
    
    for layer in layers:
        layer_name = layer['name']
        
        # Configure different security based on layer type
        if 'public' in layer_name.lower():
            # Public layers - accessible to all
            configure_layer_security(
                workspace, layer_name,
                read_roles=["ROLE_ANONYMOUS", "ROLE_AUTHENTICATED", "ROLE_ANALYST", "ADMIN"],
                write_roles=["ADMIN"]
            )
        elif 'analysis' in layer_name.lower():
            # Analysis layers - authenticated users only
            configure_layer_security(
                workspace, layer_name,
                read_roles=["ROLE_AUTHENTICATED", "ROLE_ANALYST", "ADMIN"],
                write_roles=["ROLE_ANALYST", "ADMIN"]
            )
        else:
            # Default - authenticated users only
            configure_layer_security(
                workspace, layer_name,
                read_roles=["ROLE_AUTHENTICATED", "ROLE_ANALYST", "ADMIN"],
                write_roles=["ADMIN"]
            )

def main():
    """Main setup function"""
    logger.info("🚀 Starting GeoServer unified role setup...")
    
    # Wait for GeoServer to be ready
    time.sleep(5)
    
    # 1. Ensure roles exist via roles API
    logger.info("📋 Ensuring roles exist...")
    for role_name in UNIFIED_ROLES.keys():
        create_role(role_name)
    # 1b. Best-effort: also try creating user groups (no-op if unsupported)
    logger.info("📋 Creating user groups (best effort)...")
    for role_name, role_config in UNIFIED_ROLES.items():
        create_user_group(role_name, role_config.get("description", ""))
    
    # 2. Create test users (best effort if usergroup API is restricted)
    logger.info("👥 Creating test users...")
    for user_config in TEST_USERS:
        create_user(
            user_config["username"],
            user_config["password"],
            user_config["email"],
            user_config["roles"]
        )
        for role in user_config["roles"]:
            assign_role_to_user(user_config["username"], role)
    
    # 3. Configure workspace security
    logger.info("🔒 Configuring workspace security...")
    workspaces = ["demo_workspace", "gis_carbon", "auth_demo"]
    
    for workspace in workspaces:
        try:
            setup_workspace_security(workspace)
        except Exception as e:
            logger.warning(f"⚠️  Could not configure security for workspace {workspace}: {e}")
    
    logger.info("✅ GeoServer unified role setup complete!")
    logger.info("📋 Test users created:")
    for user in TEST_USERS:
        logger.info(f"  - {user['username']} (password: {user['password']}) - Roles: {user['roles']}")

if __name__ == "__main__":
    main()
