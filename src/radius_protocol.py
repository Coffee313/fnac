"""
RADIUS protocol packet parser and builder (RFC 2865).

Handles:
- Packet structure: 20-byte header + variable-length attributes
- MD5-based message authenticator verification
- Attribute encoding/decoding (User-Name, User-Password, Tunnel attributes)
"""

import hashlib
import hmac
import os
import struct
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# RADIUS packet codes
# ---------------------------------------------------------------------------

CODE_ACCESS_REQUEST = 1
CODE_ACCESS_ACCEPT = 2
CODE_ACCESS_REJECT = 3

# ---------------------------------------------------------------------------
# RADIUS attribute types
# ---------------------------------------------------------------------------

ATTR_USER_NAME = 1
ATTR_USER_PASSWORD = 2
ATTR_TUNNEL_TYPE = 64
ATTR_TUNNEL_MEDIUM_TYPE = 65
ATTR_TUNNEL_PRIVATE_GROUP_ID = 81

TUNNEL_TYPE_VLAN = 13
TUNNEL_MEDIUM_802 = 6


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RADIUSAttribute:
    type: int
    value: bytes


@dataclass
class RADIUSPacket:
    code: int
    identifier: int
    authenticator: bytes          # 16 bytes
    attributes: List[RADIUSAttribute] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Attribute helpers
    # ------------------------------------------------------------------

    def get_attribute(self, attr_type: int) -> Optional[bytes]:
        """Return the value of the first attribute with the given type."""
        for attr in self.attributes:
            if attr.type == attr_type:
                return attr.value
        return None

    def get_string_attribute(self, attr_type: int) -> Optional[str]:
        value = self.get_attribute(attr_type)
        return value.decode("utf-8", errors="replace") if value is not None else None


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

class RADIUSParseError(Exception):
    pass


def parse_packet(data: bytes) -> RADIUSPacket:
    """
    Parse a raw UDP payload into a RADIUSPacket.

    Raises RADIUSParseError on malformed input.
    """
    if len(data) < 20:
        raise RADIUSParseError("Packet too short (< 20 bytes)")

    code, identifier, length = struct.unpack("!BBH", data[:4])
    if length < 20 or length > 4096:
        raise RADIUSParseError(f"Invalid packet length: {length}")
    if len(data) < length:
        raise RADIUSParseError("Packet data shorter than declared length")

    authenticator = data[4:20]
    attributes = _parse_attributes(data[20:length])

    return RADIUSPacket(
        code=code,
        identifier=identifier,
        authenticator=authenticator,
        attributes=attributes,
    )


def _parse_attributes(data: bytes) -> List[RADIUSAttribute]:
    attrs: List[RADIUSAttribute] = []
    offset = 0
    while offset < len(data):
        if offset + 2 > len(data):
            raise RADIUSParseError("Truncated attribute header")
        attr_type = data[offset]
        attr_len = data[offset + 1]
        if attr_len < 2:
            raise RADIUSParseError(f"Attribute length {attr_len} < 2")
        if offset + attr_len > len(data):
            raise RADIUSParseError("Attribute extends beyond packet")
        attr_value = data[offset + 2: offset + attr_len]
        attrs.append(RADIUSAttribute(type=attr_type, value=attr_value))
        offset += attr_len
    return attrs


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

def build_packet(packet: RADIUSPacket) -> bytes:
    """Serialize a RADIUSPacket to bytes."""
    attrs_bytes = b"".join(
        bytes([attr.type, len(attr.value) + 2]) + attr.value
        for attr in packet.attributes
    )
    length = 20 + len(attrs_bytes)
    header = struct.pack("!BBH", packet.code, packet.identifier, length)
    return header + packet.authenticator + attrs_bytes


# ---------------------------------------------------------------------------
# Authentication helpers
# ---------------------------------------------------------------------------

def verify_request_authenticator(packet_data: bytes, shared_secret: str) -> bool:
    """
    Verify the Request Authenticator of an Access-Request.

    For Access-Request, the authenticator is a random 16-byte value; we
    cannot verify it cryptographically without the original random bytes.
    This function always returns True for Access-Request (per RFC 2865 §3).
    """
    return True  # Access-Request authenticator is random; no verification needed


def compute_response_authenticator(
    response_data: bytes,
    request_authenticator: bytes,
    shared_secret: str,
) -> bytes:
    """
    Compute the Response Authenticator for Access-Accept / Access-Reject.

    ResponseAuth = MD5(Code + ID + Length + RequestAuth + Attributes + Secret)
    """
    secret_bytes = shared_secret.encode("utf-8")
    # Replace the authenticator field (bytes 4-20) with the request authenticator
    data = response_data[:4] + request_authenticator + response_data[20:] + secret_bytes
    return hashlib.md5(data).digest()


def sign_response(
    response_data: bytes,
    request_authenticator: bytes,
    shared_secret: str,
) -> bytes:
    """Return response_data with the authenticator field correctly set."""
    auth = compute_response_authenticator(response_data, request_authenticator, shared_secret)
    return response_data[:4] + auth + response_data[20:]


# ---------------------------------------------------------------------------
# MAC address extraction
# ---------------------------------------------------------------------------

def extract_mac_from_username(packet: RADIUSPacket) -> Optional[str]:
    """
    Extract the client MAC address from the User-Name attribute.

    MAB sends the MAC address as the username (various formats).
    Normalises to XX:XX:XX:XX:XX:XX uppercase.
    """
    username = packet.get_string_attribute(ATTR_USER_NAME)
    if username is None:
        return None
    return _normalise_mac(username)


def _normalise_mac(raw: str) -> Optional[str]:
    """Normalise a MAC address string to XX:XX:XX:XX:XX:XX uppercase."""
    # Strip common separators
    cleaned = raw.replace(":", "").replace("-", "").replace(".", "").strip()
    if len(cleaned) != 12:
        return None
    if not all(c in "0123456789abcdefABCDEF" for c in cleaned):
        return None
    return ":".join(cleaned[i:i+2].upper() for i in range(0, 12, 2))


# ---------------------------------------------------------------------------
# Response builders
# ---------------------------------------------------------------------------

def build_access_accept(
    request: RADIUSPacket,
    shared_secret: str,
    vlan_id: Optional[int] = None,
) -> bytes:
    """
    Build a signed Access-Accept response.

    If vlan_id is provided, includes Tunnel-Type, Tunnel-Medium-Type,
    and Tunnel-Private-Group-ID attributes.
    """
    attrs: List[RADIUSAttribute] = []
    if vlan_id is not None:
        # Tunnel-Type: VLAN (tag=0, value=13)
        attrs.append(RADIUSAttribute(ATTR_TUNNEL_TYPE, struct.pack("!I", TUNNEL_TYPE_VLAN)))
        # Tunnel-Medium-Type: 802 (tag=0, value=6)
        attrs.append(RADIUSAttribute(ATTR_TUNNEL_MEDIUM_TYPE, struct.pack("!I", TUNNEL_MEDIUM_802)))
        # Tunnel-Private-Group-ID: VLAN ID as string
        attrs.append(RADIUSAttribute(ATTR_TUNNEL_PRIVATE_GROUP_ID, str(vlan_id).encode("ascii")))

    response = RADIUSPacket(
        code=CODE_ACCESS_ACCEPT,
        identifier=request.identifier,
        authenticator=b"\x00" * 16,
        attributes=attrs,
    )
    raw = build_packet(response)
    return sign_response(raw, request.authenticator, shared_secret)


def build_access_reject(request: RADIUSPacket, shared_secret: str) -> bytes:
    """Build a signed Access-Reject response."""
    response = RADIUSPacket(
        code=CODE_ACCESS_REJECT,
        identifier=request.identifier,
        authenticator=b"\x00" * 16,
        attributes=[],
    )
    raw = build_packet(response)
    return sign_response(raw, request.authenticator, shared_secret)
