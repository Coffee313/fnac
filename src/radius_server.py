"""
RADIUS_Server: UDP listener and authentication flow orchestrator.

Listens on UDP port 1812, processes Access-Request packets, and returns
Access-Accept or Access-Reject responses according to the MAB policy.
"""

import logging
import socket
import threading
from typing import Optional, Tuple

from src.client_manager import Client_Manager
from src.device_manager import Device_Manager
from src.log_manager import Log_Manager
from src.models import AuthenticationOutcome, PolicyDecision
from src.policy_engine import Policy_Engine
from src.radius_protocol import (
    RADIUSParseError,
    build_access_accept,
    build_access_reject,
    extract_mac_from_username,
    parse_packet,
)

logger = logging.getLogger(__name__)

DEFAULT_PORT = 1812
DEFAULT_HOST = "0.0.0.0"


class RADIUS_Server:
    """
    Orchestrates the MAB authentication flow.

    Can be used standalone (call handle_request directly) or as a UDP server
    (call start() / stop()).
    """

    def __init__(
        self,
        device_manager: Device_Manager,
        client_manager: Client_Manager,
        policy_engine: Policy_Engine,
        log_manager: Log_Manager,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._device_manager = device_manager
        self._client_manager = client_manager
        self._policy_engine = policy_engine
        self._log_manager = log_manager
        self._host = host
        self._port = port
        self._socket: Optional[socket.socket] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Core authentication logic (testable without network)
    # ------------------------------------------------------------------

    def handle_request(self, data: bytes, source_ip: str) -> bytes:
        """
        Process a raw RADIUS Access-Request and return the response bytes.

        Steps:
        1. Parse packet
        2. Verify device by IP + shared secret
        3. Extract client MAC
        4. Look up client and group
        5. Evaluate policy
        6. Build response and log outcome
        """
        # --- Parse ---
        try:
            packet = parse_packet(data)
        except RADIUSParseError as exc:
            logger.warning("Malformed RADIUS packet from %s: %s", source_ip, exc)
            return b""  # silently drop per RFC 2865

        # --- Device verification ---
        device = self._device_manager.get_device_by_ip(source_ip)
        if device is None:
            logger.warning("RADIUS request from unregistered device %s", source_ip)
            return b""  # no shared secret available; drop

        # --- MAC extraction ---
        client_mac = extract_mac_from_username(packet)
        if client_mac is None:
            logger.warning("Could not extract MAC from request (device %s)", device.id)
            response = build_access_reject(packet, device.shared_secret)
            self._log_manager.create_log_entry(
                client_mac="unknown",
                device_id=device.id,
                outcome=AuthenticationOutcome.FAILURE,
            )
            return response

        # --- Client lookup ---
        client = self._client_manager.get_client(client_mac)
        if client is None:
            logger.info("Unknown client MAC %s from device %s", client_mac, device.id)
            response = build_access_reject(packet, device.shared_secret)
            self._log_manager.create_log_entry(
                client_mac=client_mac,
                device_id=device.id,
                outcome=AuthenticationOutcome.FAILURE,
            )
            return response

        # --- Policy evaluation ---
        decision, vlan_id = self._policy_engine.evaluate_policy(client.client_group_id)

        if decision == PolicyDecision.ACCEPT_WITH_VLAN:
            response = build_access_accept(packet, device.shared_secret, vlan_id=vlan_id)
            self._log_manager.create_log_entry(
                client_mac=client_mac,
                device_id=device.id,
                outcome=AuthenticationOutcome.SUCCESS,
                vlan_id=vlan_id,
            )
        elif decision == PolicyDecision.ACCEPT_WITHOUT_VLAN:
            response = build_access_accept(packet, device.shared_secret, vlan_id=None)
            self._log_manager.create_log_entry(
                client_mac=client_mac,
                device_id=device.id,
                outcome=AuthenticationOutcome.SUCCESS,
            )
        else:  # REJECT (including missing policy default)
            response = build_access_reject(packet, device.shared_secret)
            self._log_manager.create_log_entry(
                client_mac=client_mac,
                device_id=device.id,
                outcome=AuthenticationOutcome.FAILURE,
            )

        return response

    # ------------------------------------------------------------------
    # UDP server lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the UDP listener in a background thread."""
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._socket.bind((self._host, self._port))
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        logger.info("RADIUS server listening on %s:%d", self._host, self._port)

    def stop(self) -> None:
        """Stop the UDP listener."""
        self._running = False
        if self._socket:
            self._socket.close()
        if self._thread:
            self._thread.join(timeout=2)
        logger.info("RADIUS server stopped")

    def _listen(self) -> None:
        while self._running:
            try:
                data, addr = self._socket.recvfrom(4096)
                source_ip = addr[0]
                response = self.handle_request(data, source_ip)
                if response:
                    self._socket.sendto(response, addr)
            except OSError:
                break
            except Exception as exc:
                logger.error("Error handling RADIUS request: %s", exc, exc_info=True)
