"""
Client_Manager component for managing network clients and client groups.

This module implements the Client_Manager interface which handles:
- Creating, updating, and deleting clients (identified by MAC address)
- Creating and deleting client groups
- Validating MAC address format
- Enforcing one-to-one Client-to-Client_Group relationships
- Maintaining referential integrity
- Persisting changes to clients.json
"""

from typing import List, Optional, Dict
from src.models import Client, ClientGroup, validate_mac_address
from src.persistence import ClientPersistence


class ClientManagerError(Exception):
    """Base exception for Client_Manager errors."""
    pass


class ClientNotFoundError(ClientManagerError):
    """Raised when a client is not found."""
    pass


class ClientGroupNotFoundError(ClientManagerError):
    """Raised when a client group is not found."""
    pass


class DuplicateClientError(ClientManagerError):
    """Raised when attempting to create a client with a duplicate MAC address."""
    pass


class DuplicateClientGroupError(ClientManagerError):
    """Raised when attempting to create a client group with a duplicate ID."""
    pass


class ReferentialIntegrityError(ClientManagerError):
    """Raised when a referential integrity constraint is violated."""
    pass


class InvalidMACAddressError(ClientManagerError):
    """Raised when a MAC address format is invalid."""
    pass


class Client_Manager:
    """
    Manages Client and ClientGroup entities with referential integrity.
    
    Enforces:
    - One-to-one Client-to-ClientGroup relationship
    - Valid MAC address format (XX:XX:XX:XX:XX:XX)
    - Referential integrity when deleting clients or groups
    - Persistence of all changes to clients.json
    """
    
    def __init__(self):
        """Initialize Client_Manager and load persisted data."""
        self._clients: Dict[str, Client] = {}
        self._client_groups: Dict[str, ClientGroup] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """Load clients and client groups from persistent storage."""
        try:
            clients, client_groups = ClientPersistence.load()
            self._clients = {client.mac_address: client for client in clients}
            self._client_groups = {group.id: group for group in client_groups}
        except Exception:
            # If loading fails, start with empty state
            self._clients = {}
            self._client_groups = {}
    
    def _save_data(self) -> None:
        """Save clients and client groups to persistent storage."""
        clients = list(self._clients.values())
        client_groups = list(self._client_groups.values())
        ClientPersistence.save(clients, client_groups)
    
    def validate_mac_address(self, mac_address: str) -> bool:
        """
        Validate that a string is a valid MAC address in XX:XX:XX:XX:XX:XX format.
        
        Args:
            mac_address: String to validate as MAC address
            
        Returns:
            True if valid MAC address format
            
        Raises:
            InvalidMACAddressError: If mac_address is not a valid MAC address
        """
        try:
            validate_mac_address(mac_address)
            return True
        except ValueError as e:
            raise InvalidMACAddressError(str(e))
    
    def create_client(
        self,
        mac_address: str,
        client_group_id: str
    ) -> Client:
        """
        Create a new client with the specified MAC address and group assignment.
        
        Args:
            mac_address: MAC address of the client (format: XX:XX:XX:XX:XX:XX)
            client_group_id: ID of the client group to assign to
            
        Returns:
            The created Client object
            
        Raises:
            InvalidMACAddressError: If mac_address format is invalid
            DuplicateClientError: If mac_address already exists
            ClientGroupNotFoundError: If client_group_id does not exist
        """
        # Validate MAC address format
        try:
            validate_mac_address(mac_address)
        except ValueError as e:
            raise InvalidMACAddressError(str(e))
        
        if mac_address in self._clients:
            raise DuplicateClientError(
                f"Client with MAC address '{mac_address}' already exists"
            )
        
        if client_group_id not in self._client_groups:
            raise ClientGroupNotFoundError(
                f"Client group with ID '{client_group_id}' does not exist"
            )
        
        client = Client(
            mac_address=mac_address,
            client_group_id=client_group_id
        )
        
        self._clients[mac_address] = client
        self._save_data()
        return client
    
    def update_client(
        self,
        mac_address: str,
        client_group_id: Optional[str] = None
    ) -> Client:
        """
        Update an existing client's group assignment.
        
        Args:
            mac_address: MAC address of the client to update
            client_group_id: New client group ID (optional)
            
        Returns:
            The updated Client object
            
        Raises:
            ClientNotFoundError: If mac_address does not exist
            ClientGroupNotFoundError: If new client_group_id does not exist
        """
        if mac_address not in self._clients:
            raise ClientNotFoundError(
                f"Client with MAC address '{mac_address}' not found"
            )
        
        client = self._clients[mac_address]
        
        if client_group_id is not None:
            if client_group_id not in self._client_groups:
                raise ClientGroupNotFoundError(
                    f"Client group with ID '{client_group_id}' does not exist"
                )
            client.client_group_id = client_group_id
        
        from datetime import datetime
        client.updated_at = datetime.utcnow()
        
        self._save_data()
        return client
    
    def delete_client(self, mac_address: str) -> None:
        """
        Delete a client from the system.
        
        Args:
            mac_address: MAC address of the client to delete
            
        Raises:
            ClientNotFoundError: If mac_address does not exist
        """
        if mac_address not in self._clients:
            raise ClientNotFoundError(
                f"Client with MAC address '{mac_address}' not found"
            )
        
        del self._clients[mac_address]
        self._save_data()
    
    def get_client(self, mac_address: str) -> Optional[Client]:
        """
        Retrieve a client by its MAC address.
        
        Args:
            mac_address: MAC address of the client to retrieve
            
        Returns:
            The Client object if found, None otherwise
        """
        return self._clients.get(mac_address)
    
    def list_clients(self) -> List[Client]:
        """
        List all clients in the system.
        
        Returns:
            List of all Client objects
        """
        return list(self._clients.values())
    
    def create_client_group(self, group_id: str, name: str) -> ClientGroup:
        """
        Create a new client group.
        
        Args:
            group_id: Unique identifier for the group
            name: Human-readable name for the group
            
        Returns:
            The created ClientGroup object
            
        Raises:
            DuplicateClientGroupError: If group_id already exists
        """
        if group_id in self._client_groups:
            raise DuplicateClientGroupError(
                f"Client group with ID '{group_id}' already exists"
            )
        
        group = ClientGroup(id=group_id, name=name)
        self._client_groups[group_id] = group
        self._save_data()
        return group
    
    def delete_client_group(self, group_id: str) -> None:
        """
        Delete a client group from the system.
        
        Raises an error if any clients are assigned to this group.
        
        Args:
            group_id: ID of the group to delete
            
        Raises:
            ClientGroupNotFoundError: If group_id does not exist
            ReferentialIntegrityError: If clients are assigned to this group
        """
        if group_id not in self._client_groups:
            raise ClientGroupNotFoundError(
                f"Client group with ID '{group_id}' not found"
            )
        
        # Check for clients assigned to this group
        for client in self._clients.values():
            if client.client_group_id == group_id:
                raise ReferentialIntegrityError(
                    f"Cannot delete client group '{group_id}' because it has "
                    f"assigned clients. Remove all clients from this group first."
                )
        
        del self._client_groups[group_id]
        self._save_data()
    
    def get_client_group(self, group_id: str) -> Optional[ClientGroup]:
        """
        Retrieve a client group by its ID.
        
        Args:
            group_id: ID of the group to retrieve
            
        Returns:
            The ClientGroup object if found, None otherwise
        """
        return self._client_groups.get(group_id)
    
    def list_client_groups(self) -> List[ClientGroup]:
        """
        List all client groups in the system.
        
        Returns:
            List of all ClientGroup objects
        """
        return list(self._client_groups.values())
