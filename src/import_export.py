"""
Import/Export functionality for FNAC configuration.

Allows users to:
- Export all settings (devices, clients, policies) to JSON
- Import settings from JSON file
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, List

from src.device_manager import Device_Manager
from src.client_manager import Client_Manager
from src.policy_engine import Policy_Engine

logger = logging.getLogger(__name__)


class ConfigExporter:
    """Export FNAC configuration to JSON format."""

    def __init__(self, device_manager: Device_Manager, client_manager: Client_Manager, policy_engine: Policy_Engine):
        self.device_manager = device_manager
        self.client_manager = client_manager
        self.policy_engine = policy_engine

    def export_all(self) -> Dict[str, Any]:
        """Export all configuration."""
        return {
            "version": "0.1.0-alpha",
            "exported_at": datetime.utcnow().isoformat(),
            "device_groups": self._export_device_groups(),
            "devices": self._export_devices(),
            "client_groups": self._export_client_groups(),
            "clients": self._export_clients(),
            "policies": self._export_policies(),
        }

    def _export_device_groups(self) -> List[Dict[str, Any]]:
        """Export device groups."""
        groups = self.device_manager.list_device_groups()
        return [
            {
                "name": g.name,
                "created_at": g.created_at.isoformat(),
            }
            for g in groups
        ]

    def _export_devices(self) -> List[Dict[str, Any]]:
        """Export devices."""
        devices = self.device_manager.list_devices()
        return [
            {
                "name": d.name,
                "ip_address": d.ip_address,
                "shared_secret": d.shared_secret,
                "device_group_name": d.device_group_name,
                "created_at": d.created_at.isoformat(),
            }
            for d in devices
        ]

    def _export_client_groups(self) -> List[Dict[str, Any]]:
        """Export client groups."""
        groups = self.client_manager.list_client_groups()
        return [
            {
                "name": g.name,
                "created_at": g.created_at.isoformat(),
            }
            for g in groups
        ]

    def _export_clients(self) -> List[Dict[str, Any]]:
        """Export clients."""
        clients = self.client_manager.list_clients()
        return [
            {
                "mac_address": c.mac_address,
                "client_group_name": c.client_group_name,
                "created_at": c.created_at.isoformat(),
            }
            for c in clients
        ]

    def _export_policies(self) -> List[Dict[str, Any]]:
        """Export policies."""
        policies = self.policy_engine.list_policies()
        return [
            {
                "name": p.name,
                "client_group_name": p.client_group_name,
                "decision": p.decision.value,
                "vlan_id": p.vlan_id,
                "created_at": p.created_at.isoformat(),
            }
            for p in policies
        ]


class ConfigImporter:
    """Import FNAC configuration from JSON format."""

    def __init__(self, device_manager: Device_Manager, client_manager: Client_Manager, policy_engine: Policy_Engine):
        self.device_manager = device_manager
        self.client_manager = client_manager
        self.policy_engine = policy_engine

    def import_all(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Import all configuration."""
        results = {
            "device_groups": {"success": 0, "failed": 0, "errors": []},
            "devices": {"success": 0, "failed": 0, "errors": []},
            "client_groups": {"success": 0, "failed": 0, "errors": []},
            "clients": {"success": 0, "failed": 0, "errors": []},
            "policies": {"success": 0, "failed": 0, "errors": []},
        }

        # Import in order: groups first, then items
        results["device_groups"] = self._import_device_groups(config.get("device_groups", []))
        results["devices"] = self._import_devices(config.get("devices", []))
        results["client_groups"] = self._import_client_groups(config.get("client_groups", []))
        results["clients"] = self._import_clients(config.get("clients", []))
        results["policies"] = self._import_policies(config.get("policies", []))

        return results

    def _import_device_groups(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import device groups."""
        results = {"success": 0, "failed": 0, "errors": []}
        for group in groups:
            try:
                self.device_manager.create_device_group(group["name"])
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Device group '{group.get('name', 'unknown')}': {str(e)}")
                logger.warning(f"Failed to import device group: {e}")
        return results

    def _import_devices(self, devices: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import devices."""
        results = {"success": 0, "failed": 0, "errors": []}
        for device in devices:
            try:
                self.device_manager.create_device(
                    name=device["name"],
                    ip_address=device["ip_address"],
                    shared_secret=device["shared_secret"],
                    device_group_name=device["device_group_name"],
                )
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Device '{device.get('name', 'unknown')}': {str(e)}")
                logger.warning(f"Failed to import device: {e}")
        return results

    def _import_client_groups(self, groups: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import client groups."""
        results = {"success": 0, "failed": 0, "errors": []}
        for group in groups:
            try:
                self.client_manager.create_client_group(group["name"])
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Client group '{group.get('name', 'unknown')}': {str(e)}")
                logger.warning(f"Failed to import client group: {e}")
        return results

    def _import_clients(self, clients: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import clients."""
        results = {"success": 0, "failed": 0, "errors": []}
        for client in clients:
            try:
                self.client_manager.create_client(
                    mac_address=client["mac_address"],
                    client_group_name=client["client_group_name"],
                )
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Client '{client.get('mac_address', 'unknown')}': {str(e)}")
                logger.warning(f"Failed to import client: {e}")
        return results

    def _import_policies(self, policies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Import policies."""
        from src.models import PolicyDecision
        
        results = {"success": 0, "failed": 0, "errors": []}
        for policy in policies:
            try:
                self.policy_engine.create_policy(
                    name=policy["name"],
                    client_group_name=policy["client_group_name"],
                    decision=PolicyDecision(policy["decision"]),
                    vlan_id=policy.get("vlan_id"),
                )
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(f"Policy '{policy.get('name', 'unknown')}': {str(e)}")
                logger.warning(f"Failed to import policy: {e}")
        return results
