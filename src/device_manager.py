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
            self._devices = {device.id: device for device in devices}
            self._device_groups = {group.id: group for group in device_groups}
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
        device_id: str,
        ip_address: str,
        shared_secret: str,
        device_group_id: str
    ) -> Device:
        """
        Create a new device with the specified attributes.
        
        Args:
            device_id: Unique identifier for the device
            ip_address: IPv4 address of the device
            shared_secret: RADIUS shared secret for the device
            device_group_id: ID of the device group to assign to
            
        Returns:
            The created Device object
            
        Raises:
            DuplicateDeviceError: If device_id already exists
            DeviceGroupNotFoundError: If device_group_id does not exist
            ValueError: If ip_address or shared_secret are invalid
        """
        if device_id in self._devices:
            raise DuplicateDeviceError(f"Device with ID '{device_id}' already exists")
        
        if device_group_id not in self._device_groups:
            raise DeviceGroupNotFoundError(
                f"Device group with ID '{device_group_id}' does not exist"
            )
        
        # Device.__post_init__ will validate ip_address
        device = Device(
            id=device_id,
            ip_address=ip_address,
            shared_secret=shared_secret,
            device_group_id=device_group_id
        )
        
        self._devices[device_id] = device
        self._save_data()
        return device
    
    def update_device(
        self,
        device_id: str,
        ip_address: Optional[str] = None,
        shared_secret: Optional[str] = None,
        device_group_id: Optional[str] = None
    ) -> Device:
        """
        Update an existing device's attributes.
        
        Args:
            device_id: ID of the device to update
            ip_address: New IPv4 address (optional)
            shared_secret: New shared secret (optional)
            device_group_id: New device group ID (optional)
            
        Returns:
            The updated Device object
            
        Raises:
            DeviceNotFoundError: If device_id does not exist
            DeviceGroupNotFoundError: If new device_group_id does not exist
            ValueError: If ip_address is invalid
        """
        if device_id not in self._devices:
            raise DeviceNotFoundError(f"Device with ID '{device_id}' not found")
        
        device = self._devices[device_id]
        
        if device_group_id is not None:
            if device_group_id not in self._device_groups:
                raise DeviceGroupNotFoundError(
                    f"Device group with ID '{device_group_id}' does not exist"
                )
            device.device_group_id = device_group_id
        
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
    
    def delete_device(self, device_id: str) -> None:
        """
        Delete a device from the system.
        
        Args:
            device_id: ID of the device to delete
            
        Raises:
            DeviceNotFoundError: If device_id does not exist
        """
        if device_id not in self._devices:
            raise DeviceNotFoundError(f"Device with ID '{device_id}' not found")
        
        del self._devices[device_id]
        self._save_data()
    
    def get_device(self, device_id: str) -> Optional[Device]:
        """
        Retrieve a device by its ID.
        
        Args:
            device_id: ID of the device to retrieve
            
        Returns:
            The Device object if found, None otherwise
        """
        return self._devices.get(device_id)
    
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
    
    def create_device_group(self, group_id: str, name: str) -> DeviceGroup:
        """
        Create a new device group.
        
        Args:
            group_id: Unique identifier for the group
            name: Human-readable name for the group
            
        Returns:
            The created DeviceGroup object
            
        Raises:
            DuplicateDeviceGroupError: If group_id already exists
        """
        if group_id in self._device_groups:
            raise DuplicateDeviceGroupError(
                f"Device group with ID '{group_id}' already exists"
            )
        
        group = DeviceGroup(id=group_id, name=name)
        self._device_groups[group_id] = group
        self._save_data()
        return group
    
    def delete_device_group(self, group_id: str) -> None:
        """
        Delete a device group from the system.
        
        Raises an error if any devices are assigned to this group.
        
        Args:
            group_id: ID of the group to delete
            
        Raises:
            DeviceGroupNotFoundError: If group_id does not exist
            ReferentialIntegrityError: If devices are assigned to this group
        """
        if group_id not in self._device_groups:
            raise DeviceGroupNotFoundError(
                f"Device group with ID '{group_id}' not found"
            )
        
        # Check for devices assigned to this group
        for device in self._devices.values():
            if device.device_group_id == group_id:
                raise ReferentialIntegrityError(
                    f"Cannot delete device group '{group_id}' because it has "
                    f"assigned devices. Remove all devices from this group first."
                )
        
        del self._device_groups[group_id]
        self._save_data()
    
    def get_device_group(self, group_id: str) -> Optional[DeviceGroup]:
        """
        Retrieve a device group by its ID.
        
        Args:
            group_id: ID of the group to retrieve
            
        Returns:
            The DeviceGroup object if found, None otherwise
        """
        return self._device_groups.get(group_id)
    
    def list_device_groups(self) -> List[DeviceGroup]:
        """
        List all device groups in the system.
        
        Returns:
            List of all DeviceGroup objects
        """
        return list(self._device_groups.values())
