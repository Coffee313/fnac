"""
Device_Manager component for managing network devices and device groups.

This module implements the Device_Manager interface which handles:
- Creating, updating, and deleting devices
- Creating and deleting device groups
- Enforcing one-to-one Device-to-Device_Group relationships
- Maintaining referential integrity
- Persisting changes to devices.json
"""

from typing import List, Optional, Dict
from src.models import Device, DeviceGroup
from src.persistence import DevicePersistence


class DeviceManagerError(Exception):
    """Base exception for Device_Manager errors."""
    pass


class DeviceNotFoundError(DeviceManagerError):
    """Raised when a device is not found."""
    pass


class DeviceGroupNotFoundError(DeviceManagerError):
    """Raised when a device group is not found."""
    pass


class DuplicateDeviceError(DeviceManagerError):
    """Raised when attempting to create a device with a duplicate ID."""
    pass


class DuplicateDeviceGroupError(DeviceManagerError):
    """Raised when attempting to create a device group with a duplicate ID."""
    pass


class ReferentialIntegrityError(DeviceManagerError):
    """Raised when a referential integrity constraint is violated."""
    pass


class Device_Manager:
    """
    Manages Device and Device_Group entities with referential integrity.
    
    Enforces:
    - One-to-one Device-to-Device_Group relationship
    - Referential integrity when deleting devices or groups
    - Persistence of all changes to devices.json
    """
    
    def __init__(self):
        """Initialize Device_Manager and load persisted data."""
        self._devices: Dict[str, Device] = {}
        self._device_groups: Dict[str, DeviceGroup] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load devices and device groups from persistent storage."""
        try:
            devices, device_groups = DevicePersistence.load()
            self._devices = {device.name: device for device in devices}
            self._device_groups = {group.name: group for group in device_groups}
        except Exception:
            # If loading fails, start with empty state
            self._devices = {}
            self._device_groups = {}
    
    def _save_data(self) -> None:
        """Save devices and device groups to persistent storage."""
        devices = list(self._devices.values())
        device_groups = list(self._device_groups.values())
        DevicePersistence.save(devices, device_groups)
    
    def create_device(
        self,
        name: str,
        ip_address: str,
        shared_secret: str,
        device_group_name: str
    ) -> Device:
        """
        Create a new device with the specified attributes.
        
        Args:
            name: Unique name for the device
            ip_address: IPv4 address of the device
            shared_secret: RADIUS shared secret for the device
            device_group_name: Name of the device group to assign to
            
        Returns:
            The created Device object
            
        Raises:
            DuplicateDeviceError: If name already exists
            DeviceGroupNotFoundError: If device_group_name does not exist
            ValueError: If ip_address or shared_secret are invalid
        """
        if name in self._devices:
            raise DuplicateDeviceError(f"Device with name '{name}' already exists")
        
        if device_group_name not in self._device_groups:
            raise DeviceGroupNotFoundError(
                f"Device group with name '{device_group_name}' does not exist"
            )
        
        # Device.__post_init__ will validate ip_address
        device = Device(
            name=name,
            ip_address=ip_address,
            shared_secret=shared_secret,
            device_group_name=device_group_name
        )
        
        self._devices[name] = device
        self._save_data()
        return device
    
    def update_device(
        self,
        name: str,
        ip_address: Optional[str] = None,
        shared_secret: Optional[str] = None,
        device_group_name: Optional[str] = None
    ) -> Device:
        """
        Update an existing device's attributes.
        
        Args:
            name: Name of the device to update
            ip_address: New IPv4 address (optional)
            shared_secret: New shared secret (optional)
            device_group_name: New device group name (optional)
            
        Returns:
            The updated Device object
            
        Raises:
            DeviceNotFoundError: If name does not exist
            DeviceGroupNotFoundError: If new device_group_name does not exist
            ValueError: If ip_address is invalid
        """
        if name not in self._devices:
            raise DeviceNotFoundError(f"Device with name '{name}' not found")
        
        device = self._devices[name]
        
        if device_group_name is not None:
            if device_group_name not in self._device_groups:
                raise DeviceGroupNotFoundError(
                    f"Device group with name '{device_group_name}' does not exist"
                )
            device.device_group_name = device_group_name
        
        if ip_address is not None:
            # This will raise ValueError if invalid
            from src.models import validate_ipv4_address
            validate_ipv4_address(ip_address)
            device.ip_address = ip_address
        
        if shared_secret is not None:
            device.shared_secret = shared_secret
        
        from datetime import datetime
        device.updated_at = datetime.utcnow()
        
        self._save_data()
        return device
    
    def delete_device(self, name: str) -> None:
        """
        Delete a device from the system.
        
        Args:
            name: Name of the device to delete
            
        Raises:
            DeviceNotFoundError: If name does not exist
        """
        if name not in self._devices:
            raise DeviceNotFoundError(f"Device with name '{name}' not found")
        
        del self._devices[name]
        self._save_data()
    
    def get_device(self, name: str) -> Optional[Device]:
        """
        Retrieve a device by its name.
        
        Args:
            name: Name of the device to retrieve
            
        Returns:
            The Device object if found, None otherwise
        """
        return self._devices.get(name)
    
    def get_device_by_ip(self, ip_address: str) -> Optional[Device]:
        """
        Retrieve a device by its IP address.
        
        Args:
            ip_address: IPv4 address of the device
            
        Returns:
            The Device object if found, None otherwise
        """
        for device in self._devices.values():
            if device.ip_address == ip_address:
                return device
        return None
    
    def list_devices(self) -> List[Device]:
        """
        List all devices in the system.
        
        Returns:
            List of all Device objects
        """
        return list(self._devices.values())
    
    def create_device_group(self, name: str) -> DeviceGroup:
        """
        Create a new device group.
        
        Args:
            name: Unique name for the group
            
        Returns:
            The created DeviceGroup object
            
        Raises:
            DuplicateDeviceGroupError: If name already exists
        """
        if name in self._device_groups:
            raise DuplicateDeviceGroupError(
                f"Device group with name '{name}' already exists"
            )
        
        group = DeviceGroup(name=name)
        self._device_groups[name] = group
        self._save_data()
        return group
    
    def delete_device_group(self, name: str) -> None:
        """
        Delete a device group from the system.
        
        Raises an error if any devices are assigned to this group.
        
        Args:
            name: Name of the group to delete
            
        Raises:
            DeviceGroupNotFoundError: If name does not exist
            ReferentialIntegrityError: If devices are assigned to this group
        """
        if name not in self._device_groups:
            raise DeviceGroupNotFoundError(
                f"Device group with name '{name}' not found"
            )
        
        # Check for devices assigned to this group
        for device in self._devices.values():
            if device.device_group_name == name:
                raise ReferentialIntegrityError(
                    f"Cannot delete device group '{name}' because it has "
                    f"assigned devices. Remove all devices from this group first."
                )
        
        del self._device_groups[name]
        self._save_data()
    
    def get_device_group(self, name: str) -> Optional[DeviceGroup]:
        """
        Retrieve a device group by its name.
        
        Args:
            name: Name of the group to retrieve
            
        Returns:
            The DeviceGroup object if found, None otherwise
        """
        return self._device_groups.get(name)
    
    def list_device_groups(self) -> List[DeviceGroup]:
        """
        List all device groups in the system.
        
        Returns:
            List of all DeviceGroup objects
        """
        return list(self._device_groups.values())
