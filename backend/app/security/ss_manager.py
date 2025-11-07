import json
import logging
from token import EQUAL
from typing import Dict, List, Optional, Set, Any, Tuple
from pathlib import Path
import fnmatch
from datetime import datetime

# Make watchdog optional
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    WATCHDOG_AVAILABLE = True

    class SSFileWatcher(FileSystemEventHandler):
        """Watches SS file for changes and triggers reload"""

        def __init__(self, ss_manager, filepath: Path):
            super().__init__()
            self.ss_manager = ss_manager
            self.filepath = filepath

        def on_modified(self, event):
            if event.src_path == str(self.filepath):
                logger.info(f"SS file modified: {self.filepath}")
                self.ss_manager.reload()

except ImportError:
    WATCHDOG_AVAILABLE = False
    Observer = None
    SSFileWatcher = None  # type: ignore
    logging.warning("watchdog not installed, SS hot reload disabled")

logger = logging.getLogger(__name__)


class SSManager:
    """Manages sensor security"""

    def __init__(self, ss_file_path: str = "ss_config.json"):
        self.ss_file_path = Path(ss_file_path)
        self.ss_data: Dict = {}
        self.sensors: Dict = {}
        self.types: Dict = {}
        self.last_loaded: Optional[datetime] = None

        # File watcher for hot reload (if available)
        self.observer = None

        # Load initial SS
        self.reload()

    def reload(self):
        """Reload SS configuration from file"""
        try:
            logger.info(f"Loading SS configuration from {self.ss_file_path}")

            with open(self.ss_file_path, "r") as f:
                self.ss_data = json.load(f)

            self.sensors = self.ss_data.get("sensors", {})
            self.types = self.ss_data.get("types", {})
            self.last_loaded = datetime.utcnow()

            logger.info(f"SS loaded:  {len(self.sensors)} sensors")

        except FileNotFoundError:
            logger.error(f"SS file not found: {self.ss_file_path}")
            logger.warning("Creating default SS file with open permissions")
            self._create_default_ss()
            self.reload()
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in SS file: {e}")
        except Exception as e:
            logger.error(f"Error loading SS: {e}")

    def _create_default_ss(self):
        """Create a default SS file"""
        default_ss = {"version": "1.0", "types": {}, "sensors": {}}

        with open(self.ss_file_path, "w") as f:
            json.dump(default_ss, f, indent=2)

    def start_watching(self):
        """Start watching SS file for changes"""
        if not WATCHDOG_AVAILABLE or Observer is None or SSFileWatcher is None:
            logger.warning("Watchdog not available, SS hot reload disabled")
            return

        if self.observer:
            return

        event_handler = SSFileWatcher(self, self.ss_file_path)
        self.observer = Observer()
        self.observer.schedule(
            event_handler, str(self.ss_file_path.parent), recursive=False
        )
        self.observer.start()
        logger.info("SS file watcher started")

    def stop_watching(self):
        """Stop watching SS file"""
        if not WATCHDOG_AVAILABLE or not self.observer:
            return

        try:
            self.observer.stop()
            self.observer.join()
            logger.info("SS file watcher stopped")
        except Exception as e:
            logger.error(f"Error stopping SS file watcher: {e}")

    def get_sensor_type(self, sensor_id: str) -> Optional[str]:
        """Get sensor type"""
        sensor_config = self.sensors.get(sensor_id, {})
        if sensor_config is None:
            logger.warning(f"Sensor config for {sensor_id} not found in SS")
            return None
        return sensor_config.get("type", "")

    def get_sensor_activeness(self, sensor_id: str) -> Optional[bool]:
        """Get sensor activeness"""
        sensor_config = self.sensors.get(sensor_id, {})
        if sensor_config is None:
            logger.warning(f"Sensor config for {sensor_id} not found in SS")
            return None
        return sensor_config.get("active", "")

    def get_all_sensor_limits(self, sensor_id: str) -> Optional[Dict]:
        """Get limit info for a sensor"""
        sensor_config = self.sensors.get(sensor_id, {})
        limits = sensor_config.get("limits", {})
        if limits is None:
            logger.warning(f"Sensor limits for {sensor_id} not found in SS")
            return None
        return limits

    def get_sensor_limit_config(
        self, sensor_id: str
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """Get limit info for a sensor"""
        sensor_config = self.sensors.get(sensor_id, {})
        limits = sensor_config.get("limits", {})
        limit_name, limit_config = self._get_selected_config(limits)
        if limit_name or limit_config is None:
            logger.warning(f"Sensor limit config for {sensor_id} not found in SS")
            return None, None
        return limit_name, limit_config

    def _get_selected_config(
        self, limits: Dict
    ) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Returns the name and configuration of the selected limit.

        Args:
            limits (dict): Dictionary of limit configurations

        Returns:
            tuple: (limit_name, limit_config) or (None, None) if none selected
        """
        # Get all selected limits as a dictionary
        selected_limits = {
            name: config
            for name, config in limits.items()
            if config.get("selected") in ["true", True]
        }

        if selected_limits:
            # Get first (or only) selected limit
            limit_name = list(selected_limits.keys())[0]
            limit_config = selected_limits[limit_name]
            return limit_name, limit_config

        return None, None

    def check_limit_for_alert(
        self, sensor_id: str, value: str, unit: str
    ) -> Tuple[bool, Optional[str]]:
        # If sensor doesn't exist in SS
        if sensor_id not in self.sensors:
            logger.warning(f"Sensor {sensor_id} not found in SS")
            return False, None
        # Get sensor limits
        limit_name, limit_config = self.get_sensor_limit_config(sensor_id)
        # Check if limit info is null
        if limit_name or limit_config is None:
            logger.warning(f"Sensor limit config for {sensor_id} not found in SS")
            return False, None
        # Check if unit matches
        if not unit == limit_config["unit"]:
            logger.warning(
                f"Sensor limit unit for {sensor_id} does not match the unit in {limit_name} config in SS"
            )
            return False, None
        # Check if value is higher than the upper limit
        if value > limit_config["upper"]:
            logger.warning(
                f"Alert: Sensor value is greater than the upper limit for {sensor_id}"
            )
            return True, "upper"
        # Check if value is lower than the lower limit
        if value < limit_config["lower"]:
            logger.warning(
                f"Alert: Sensor value is lower than the lower limit for {sensor_id}"
            )
            return True, "lower"

        return False, None

    def add_sensor(
        self, sensor_id: str, pattern: str, sensor_type: str, active: bool, limits: Dict
    ):
        # Add a new sensor to SS
        self.sensors[sensor_id] = {
            "pattern": pattern,
            "sensor_type": sensor_type,
            "active": active,
            "limits": limits,
        }
        self._save_ss()
        logger.info(
            f"Added sensor {sensor_id} with pattern: {pattern}, sensor_type: {sensor_type}, active: {active}, limits: {limits}"
        )

    def remove_sensor(self, sensor_id: str):
        # Remove sensor from SS
        if sensor_id in self.sensors:
            del self.sensors[sensor_id]
            self._save_ss()
            logger.info(f"Removed sensor {sensor_id}")

    def update_sensor(
        self,
        sensor_id: str,
        pattern: Optional[str] = None,
        sensor_type: Optional[str] = None,
        active: Optional[bool] = None,
        limits: Optional[Dict] = None,
    ):
        # Update sensor info
        if sensor_id in self.sensors:
            if pattern is not None:
                self.sensors[sensor_id]["pattern"] = pattern
            if sensor_type is not None:
                self.sensors[sensor_id]["sensor_type"] = sensor_type
            if active is not None:
                self.sensors[sensor_id]["active"] = active
            if limits is not None:
                self.sensors[sensor_id]["limits"] = limits

            # Write to file
            self._save_ss()
            logger.info(
                f"Updated {sensor_id}: {pattern}, {sensor_type}, {active}, {limits}"
            )

    def add_sensor_limit_config(self, sensor_id: str, config: Dict):
        # Add limit config to sensor
        if sensor_id in self.sensors:
            self.sensors[sensor_id].setdefault("limits", []).append(config)
            self._save_ss()
            logger.info(f"Added limit config for {sensor_id}: {config}")

    def _save_ss(self):
        # Save SS configuration to file
        try:
            self.ss_data["sensors"] = self.sensors
            self.ss_data["types"] = self.types

            with open(self.ss_file_path, "w") as f:
                json.dump(self.ss_data, f, indent=2)

            logger.info("SS configuration saved")
        except Exception as e:
            logger.error(f"Error saving SS: {e}")

    def get_ss_info(self) -> Dict:
        # Get SS configuration info
        return {
            "version": self.ss_data.get("version", "unknown"),
            "total_sensors": len(self.sensors),
            "total_types": len(self.types),
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None,
        }

    def get_sensor_info(self, sensor_id: str) -> Optional[Dict]:
        # Get user's SS information
        if sensor_id not in self.sensors:
            logger.warning(f"Sensor {sensor_id} was not found in SS")
            return None

        return {
            "sensor_id": sensor_id,
            "pattern": self.sensors[sensor_id].get("pattern", ""),
            "sensor_type": self.sensors[sensor_id].get("sensor_type", ""),
            "active": self.sensors[sensor_id].get("active", ""),
            "limit_name": self.get_sensor_limit_config(sensor_id)[0],
            "limit_config": self.get_sensor_limit_config(sensor_id)[1],
        }


# Global SS manager instance
ss_manager: Optional[SSManager] = None


def get_ss_manager() -> Optional[SSManager]:
    """Get global SS manager instance"""
    return ss_manager


def init_ss_manager(ss_file_path: str = "ss_config.json") -> SSManager:
    """Initialize global SS manager"""
    global ss_manager
    ss_manager = SSManager(ss_file_path)
    ss_manager.start_watching()  # Start watching for file changes
    return ss_manager
