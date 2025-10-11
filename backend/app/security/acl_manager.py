import json
import logging
from typing import Dict, List, Optional, Set, Any
from pathlib import Path
import fnmatch
from datetime import datetime

# Make watchdog optional
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
    
    class ACLFileWatcher(FileSystemEventHandler):
        """Watches ACL file for changes and triggers reload"""
        
        def __init__(self, acl_manager, filepath: Path):
            super().__init__()
            self.acl_manager = acl_manager
            self.filepath = filepath
        
        def on_modified(self, event):
            if event.src_path == str(self.filepath):
                logger.info(f"ACL file modified: {self.filepath}")
                self.acl_manager.reload()
                
except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    ACLFileWatcher = None  # type: ignore
    logging.warning("watchdog not installed, ACL hot reload disabled")

logger = logging.getLogger(__name__)

class ACLManager:
    """Manages user permissions and access control"""
    
    def __init__(self, acl_file_path: str = "acl_config.json"):
        self.acl_file_path = Path(acl_file_path)
        self.acl_data: Dict = {}
        self.roles: Dict = {}
        self.users: Dict = {}
        self.default_policy: str = "deny"
        self.last_loaded: Optional[datetime] = None
        
        # File watcher for hot reload (if available)
        self.observer = None
        
        # Load initial ACL
        self.reload()
    
    def reload(self):
        """Reload ACL configuration from file"""
        try:
            logger.info(f"Loading ACL configuration from {self.acl_file_path}")
            
            with open(self.acl_file_path, 'r') as f:
                self.acl_data = json.load(f)
            
            self.roles = self.acl_data.get("roles", {})
            self.users = self.acl_data.get("users", {})
            self.default_policy = self.acl_data.get("default_policy", "deny")
            self.last_loaded = datetime.utcnow()
            
            logger.info(f"ACL loaded: {len(self.users)} users, {len(self.roles)} roles")
            logger.info(f"Default policy: {self.default_policy}")
            
        except FileNotFoundError:
            logger.error(f"ACL file not found: {self.acl_file_path}")
            logger.warning("Creating default ACL file with open permissions")
            self._create_default_acl()
            self.reload()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in ACL file: {e}")
        except Exception as e:
            logger.error(f"Error loading ACL: {e}")
    
    def _create_default_acl(self):
        """Create a default ACL file with basic permissions"""
        default_acl = {
            "version": "1.0",
            "default_policy": "allow",
            "roles": {
                "default": {
                    "description": "Default role with full access",
                    "permissions": [
                        {"pattern": "#", "allow": ["subscribe", "publish"]}
                    ]
                }
            },
            "users": {}
        }
        
        with open(self.acl_file_path, 'w') as f:
            json.dump(default_acl, f, indent=2)
    
    def start_watching(self):
        """Start watching ACL file for changes"""
        if not WATCHDOG_AVAILABLE or Observer is None or ACLFileWatcher is None:
            logger.warning("Watchdog not available, ACL hot reload disabled")
            return
        
        if self.observer:
            return
        
        event_handler = ACLFileWatcher(self, self.acl_file_path)
        self.observer = Observer()
        self.observer.schedule(event_handler, str(self.acl_file_path.parent), recursive=False)
        self.observer.start()
        logger.info("ACL file watcher started")
    
    def stop_watching(self):
        """Stop watching ACL file"""
        if not WATCHDOG_AVAILABLE or not self.observer:
            return
        
        try:
            self.observer.stop()
            self.observer.join()
            logger.info("ACL file watcher stopped")
        except Exception as e:
            logger.error(f"Error stopping ACL file watcher: {e}")
    
    def _expand_topic_pattern(self, pattern: str, user_id: str) -> str:
        """Expand variables in topic patterns"""
        return pattern.replace("${user_id}", user_id)
    
    def _match_topic(self, topic: str, pattern: str) -> bool:
        """Check if topic matches pattern (supports MQTT wildcards)"""
        # Convert MQTT wildcards to fnmatch patterns
        mqtt_pattern = pattern.replace('+', '*').replace('#', '**')
        
        # Handle multi-level wildcard
        if '**' in mqtt_pattern:
            # Split and check each part
            pattern_parts = mqtt_pattern.split('/')
            topic_parts = topic.split('/')
            
            # Simple implementation: if pattern has **, it matches rest
            if pattern_parts[-1] == '**':
                base_pattern = '/'.join(pattern_parts[:-1])
                topic_base = '/'.join(topic_parts[:len(pattern_parts)-1])
                return fnmatch.fnmatch(topic_base, base_pattern)
        
        return fnmatch.fnmatch(topic, mqtt_pattern)
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get list of roles assigned to user"""
        user_config = self.users.get(user_id, {})
        return user_config.get("roles", [])
    
    def get_user_permissions(self, user_id: str) -> List[Dict]:
        """Get all permissions for a user (from roles + custom)"""
        permissions = []
        
        # Get permissions from roles
        for role_name in self.get_user_roles(user_id):
            role = self.roles.get(role_name, {})
            role_permissions = role.get("permissions", [])
            permissions.extend(role_permissions)
        
        # Add custom permissions
        user_config = self.users.get(user_id, {})
        custom_permissions = user_config.get("custom_permissions", [])
        permissions.extend(custom_permissions)
        
        return permissions
    
    def check_permission(self, user_id: str, topic: str, action: str) -> bool:
        """Check if user has permission for action on topic"""
        
        # If user doesn't exist in ACL
        if user_id not in self.users:
            logger.warning(f"User {user_id} not found in ACL")
            return self.default_policy == "allow"
        
        # Get all user permissions
        permissions = self.get_user_permissions(user_id)
        
        # Check each permission
        for permission in permissions:
            pattern = self._expand_topic_pattern(permission.get("pattern", ""), user_id)
            allowed_actions = permission.get("allow", [])
            denied_actions = permission.get("deny", [])
            
            # Check if topic matches this permission's pattern
            if self._match_topic(topic, pattern):
                # Check explicit deny first
                if action in denied_actions:
                    logger.info(f"Permission DENIED for {user_id}: {action} on {topic} (explicit deny)")
                    return False
                
                # Check allow
                if action in allowed_actions:
                    logger.info(f"Permission GRANTED for {user_id}: {action} on {topic}")
                    return True
        
        # No matching permission found
        logger.info(f"Permission DENIED for {user_id}: {action} on {topic} (no match)")
        return self.default_policy == "allow"
    
    def can_subscribe(self, user_id: str, topic: str) -> bool:
        """Check if user can subscribe to topic"""
        return self.check_permission(user_id, topic, "subscribe")
    
    def can_publish(self, user_id: str, topic: str) -> bool:
        """Check if user can publish to topic"""
        return self.check_permission(user_id, topic, "publish")
    
    def add_user(self, user_id: str, roles: List[str], custom_permissions: Optional[List[Dict]] = None):
        """Add a new user to ACL"""
        self.users[user_id] = {
            "roles": roles,
            "custom_permissions": custom_permissions if custom_permissions is not None else []
        }
        self._save_acl()
        logger.info(f"Added user {user_id} with roles: {roles}")
    
    def remove_user(self, user_id: str):
        """Remove user from ACL"""
        if user_id in self.users:
            del self.users[user_id]
            self._save_acl()
            logger.info(f"Removed user {user_id}")
    
    def update_user_roles(self, user_id: str, roles: List[str]):
        """Update user's roles"""
        if user_id in self.users:
            self.users[user_id]["roles"] = roles
            self._save_acl()
            logger.info(f"Updated roles for {user_id}: {roles}")
    
    def add_user_permission(self, user_id: str, permission: Dict):
        """Add custom permission to user"""
        if user_id in self.users:
            self.users[user_id].setdefault("custom_permissions", []).append(permission)
            self._save_acl()
            logger.info(f"Added permission for {user_id}: {permission}")
    
    def _save_acl(self):
        """Save ACL configuration to file"""
        try:
            self.acl_data["users"] = self.users
            self.acl_data["roles"] = self.roles
            self.acl_data["default_policy"] = self.default_policy
            
            with open(self.acl_file_path, 'w') as f:
                json.dump(self.acl_data, f, indent=2)
            
            logger.info("ACL configuration saved")
        except Exception as e:
            logger.error(f"Error saving ACL: {e}")
    
    def get_acl_info(self) -> Dict:
        """Get ACL configuration info"""
        return {
            "version": self.acl_data.get("version", "unknown"),
            "default_policy": self.default_policy,
            "total_users": len(self.users),
            "total_roles": len(self.roles),
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None
        }
    
    def get_user_info(self, user_id: str) -> Optional[Dict]:
        """Get user's ACL information"""
        if user_id not in self.users:
            return None
        
        return {
            "user_id": user_id,
            "roles": self.get_user_roles(user_id),
            "permissions": self.get_user_permissions(user_id)
        }


# Global ACL manager instance
acl_manager: Optional[ACLManager] = None

def get_acl_manager() -> Optional[ACLManager]:
    """Get global ACL manager instance"""
    return acl_manager

def init_acl_manager(acl_file_path: str = "acl_config.json") -> ACLManager:
    """Initialize global ACL manager"""
    global acl_manager
    acl_manager = ACLManager(acl_file_path)
    acl_manager.start_watching()  # Start watching for file changes
    return acl_manager