"""
Flask-based REST API for RADIUS server configuration.

Provides endpoints for managing devices, clients, policies, and viewing logs.
"""

from flask import Flask, jsonify, request

from src.client_manager import (
    Client_Manager,
    ClientGroupNotFoundError,
    ClientNotFoundError,
    DuplicateClientError,
    DuplicateClientGroupError,
    InvalidMACAddressError,
    ReferentialIntegrityError as ClientReferentialIntegrityError,
)
from src.device_manager import (
    Device_Manager,
    DeviceGroupNotFoundError,
    DeviceNotFoundError,
    DuplicateDeviceError,
    DuplicateDeviceGroupError,
    ReferentialIntegrityError as DeviceReferentialIntegrityError,
)
from src.log_manager import Log_Manager
from src.models import AuthenticationOutcome, PolicyDecision
from src.policy_engine import (
    DuplicatePolicyError,
    InvalidVLANError,
    Policy_Engine,
    PolicyNotFoundError,
)
from src.freeradius_config_generator import FreeRADIUSConfigGenerator


def create_app(
    device_manager: Device_Manager,
    client_manager: Client_Manager,
    policy_engine: Policy_Engine,
    log_manager: Log_Manager,
    config_generator: FreeRADIUSConfigGenerator = None,
) -> Flask:
    """Create and configure the Flask application."""
    import os
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), 'static'))

    # ------------------------------------------------------------------
    # Root route
    # ------------------------------------------------------------------

    @app.route("/", methods=["GET"])
    def index():
        from flask import send_file
        return send_file(os.path.join(os.path.dirname(__file__), 'static', 'index.html'))

    @app.route("/api", methods=["GET"])
    def api_info():
        return jsonify({
            "status": "running",
            "service": "RADIUS Server",
            "version": "1.0.0",
            "endpoints": {
                "devices": "/api/devices",
                "clients": "/api/clients",
                "policies": "/api/policies",
                "logs": "/api/logs"
            }
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _err(msg: str, status: int = 400):
        return jsonify({"error": msg}), status

    def _update_freeradius_config():
        """Update FreeRADIUS config files after data changes."""
        if config_generator:
            try:
                config_generator.update_all_configs(reload=True, dry_run=False)
            except Exception as e:
                logger.warning(f"Failed to update FreeRADIUS config: {e}")

    def _device_to_dict(d):
        return {
            "name": d.name,
            "ip_address": d.ip_address,
            "shared_secret": d.shared_secret,
            "device_group_name": d.device_group_name,
            "created_at": d.created_at.isoformat(),
            "updated_at": d.updated_at.isoformat(),
        }

    def _device_group_to_dict(g):
        return {
            "name": g.name,
            "created_at": g.created_at.isoformat(),
            "updated_at": g.updated_at.isoformat(),
        }

    def _client_to_dict(c):
        return {
            "mac_address": c.mac_address,
            "client_group_name": c.client_group_name,
            "created_at": c.created_at.isoformat(),
            "updated_at": c.updated_at.isoformat(),
        }

    def _client_group_to_dict(g):
        return {
            "name": g.name,
            "created_at": g.created_at.isoformat(),
            "updated_at": g.updated_at.isoformat(),
        }

    def _policy_to_dict(p):
        return {
            "name": p.name,
            "client_group_name": p.client_group_name,
            "decision": p.decision.value,
            "vlan_id": p.vlan_id,
            "created_at": p.created_at.isoformat(),
            "updated_at": p.updated_at.isoformat(),
        }

    def _log_to_dict(l):
        return {
            "id": l.id,
            "timestamp": l.timestamp.isoformat(),
            "client_mac": l.client_mac,
            "device_id": l.device_id,
            "outcome": l.outcome.value,
            "vlan_id": l.vlan_id,
            "policy_decision": l.policy_decision,
            "policy_name": l.policy_name,
            "created_at": l.created_at.isoformat(),
        }

    # ------------------------------------------------------------------
    # Device management  (Requirement 8.1)
    # ------------------------------------------------------------------

    @app.route("/api/devices", methods=["GET"])
    def list_devices():
        return jsonify([_device_to_dict(d) for d in device_manager.list_devices()])

    @app.route("/api/devices", methods=["POST"])
    def create_device():
        body = request.get_json(silent=True) or {}
        required = ["name", "ip_address", "shared_secret", "device_group_name"]
        for field in required:
            if not body.get(field):
                return _err(f"Field '{field}' is required")
        try:
            device = device_manager.create_device(
                body["name"], body["ip_address"], body["shared_secret"], body["device_group_name"]
            )
            _update_freeradius_config()
            return jsonify(_device_to_dict(device)), 201
        except DuplicateDeviceError as e:
            return _err(str(e))
        except DeviceGroupNotFoundError as e:
            return _err(str(e))
        except ValueError as e:
            return _err(str(e))

    @app.route("/api/devices/<device_name>", methods=["PUT"])
    def update_device(device_name):
        body = request.get_json(silent=True) or {}
        try:
            device = device_manager.update_device(
                device_name,
                ip_address=body.get("ip_address"),
                shared_secret=body.get("shared_secret"),
                device_group_name=body.get("device_group_name"),
            )
            return jsonify(_device_to_dict(device))
        except DeviceNotFoundError as e:
            return _err(str(e), 404)
        except DeviceGroupNotFoundError as e:
            return _err(str(e))
        except ValueError as e:
            return _err(str(e))

    @app.route("/api/devices/<device_name>", methods=["DELETE"])
    def delete_device(device_name):
        try:
            device_manager.delete_device(device_name)
            _update_freeradius_config()
            return "", 204
        except DeviceNotFoundError as e:
            return _err(str(e), 404)

    @app.route("/api/device-groups", methods=["GET"])
    def list_device_groups():
        return jsonify([_device_group_to_dict(g) for g in device_manager.list_device_groups()])

    @app.route("/api/device-groups", methods=["POST"])
    def create_device_group():
        body = request.get_json(silent=True) or {}
        if not body.get("name"):
            return _err("Field 'name' is required")
        try:
            group = device_manager.create_device_group(body["name"])
            return jsonify(_device_group_to_dict(group)), 201
        except DuplicateDeviceGroupError as e:
            return _err(str(e))

    @app.route("/api/device-groups/<group_name>", methods=["DELETE"])
    def delete_device_group(group_name):
        try:
            device_manager.delete_device_group(group_name)
            return "", 204
        except DeviceGroupNotFoundError as e:
            return _err(str(e), 404)
        except DeviceReferentialIntegrityError as e:
            return _err(str(e))

    # ------------------------------------------------------------------
    # Client management  (Requirement 8.2)
    # ------------------------------------------------------------------

    @app.route("/api/clients", methods=["GET"])
    def list_clients():
        return jsonify([_client_to_dict(c) for c in client_manager.list_clients()])

    @app.route("/api/clients", methods=["POST"])
    def create_client():
        body = request.get_json(silent=True) or {}
        if not body.get("mac_address"):
            return _err("Field 'mac_address' is required")
        if not body.get("client_group_name"):
            return _err("Field 'client_group_name' is required")
        try:
            client = client_manager.create_client(body["mac_address"], body["client_group_name"])
            _update_freeradius_config()
            return jsonify(_client_to_dict(client)), 201
        except InvalidMACAddressError as e:
            return _err(str(e))
        except DuplicateClientError as e:
            return _err(str(e))
        except ClientGroupNotFoundError as e:
            return _err(str(e))

    @app.route("/api/clients/<path:mac>", methods=["PUT"])
    def update_client(mac):
        body = request.get_json(silent=True) or {}
        if not body.get("client_group_name"):
            return _err("Field 'client_group_name' is required")
        try:
            client = client_manager.update_client(mac, body["client_group_name"])
            return jsonify(_client_to_dict(client))
        except ClientNotFoundError as e:
            return _err(str(e), 404)
        except ClientGroupNotFoundError as e:
            return _err(str(e))

    @app.route("/api/clients/<path:mac>", methods=["DELETE"])
    def delete_client(mac):
        try:
            client_manager.delete_client(mac)
            _update_freeradius_config()
            return "", 204
        except ClientNotFoundError as e:
            return _err(str(e), 404)

    @app.route("/api/client-groups", methods=["GET"])
    def list_client_groups():
        return jsonify([_client_group_to_dict(g) for g in client_manager.list_client_groups()])

    @app.route("/api/client-groups", methods=["POST"])
    def create_client_group():
        body = request.get_json(silent=True) or {}
        if not body.get("name"):
            return _err("Field 'name' is required")
        try:
            group = client_manager.create_client_group(body["name"])
            return jsonify(_client_group_to_dict(group)), 201
        except DuplicateClientGroupError as e:
            return _err(str(e))

    @app.route("/api/client-groups/<group_name>", methods=["DELETE"])
    def delete_client_group(group_name):
        try:
            client_manager.delete_client_group(group_name)
            return "", 204
        except ClientGroupNotFoundError as e:
            return _err(str(e), 404)
        except ClientReferentialIntegrityError as e:
            return _err(str(e))

    # ------------------------------------------------------------------
    # Policy management  (Requirement 8.3)
    # ------------------------------------------------------------------

    @app.route("/api/policies", methods=["GET"])
    def list_policies():
        return jsonify([_policy_to_dict(p) for p in policy_engine.list_policies()])

    @app.route("/api/policies", methods=["POST"])
    def create_policy():
        body = request.get_json(silent=True) or {}
        required = ["name", "client_group_name", "decision"]
        for field in required:
            if not body.get(field):
                return _err(f"Field '{field}' is required")
        try:
            decision = PolicyDecision(body["decision"])
        except ValueError:
            return _err(f"Invalid decision value: {body['decision']}")
        try:
            policy = policy_engine.create_policy(
                body["name"], body["client_group_name"], decision, vlan_id=body.get("vlan_id")
            )
            _update_freeradius_config()
            return jsonify(_policy_to_dict(policy)), 201
        except DuplicatePolicyError as e:
            return _err(str(e))
        except InvalidVLANError as e:
            return _err(str(e))

    @app.route("/api/policies/<policy_name>", methods=["PUT"])
    def update_policy(policy_name):
        body = request.get_json(silent=True) or {}
        decision = None
        if "decision" in body:
            try:
                decision = PolicyDecision(body["decision"])
            except ValueError:
                return _err(f"Invalid decision value: {body['decision']}")
        try:
            policy = policy_engine.update_policy(
                policy_name, decision=decision, vlan_id=body.get("vlan_id")
            )
            return jsonify(_policy_to_dict(policy))
        except PolicyNotFoundError as e:
            return _err(str(e), 404)
        except InvalidVLANError as e:
            return _err(str(e))

    @app.route("/api/policies/<policy_name>", methods=["DELETE"])
    def delete_policy(policy_name):
        try:
            policy_engine.delete_policy(policy_name)
            _update_freeradius_config()
            return "", 204
        except PolicyNotFoundError as e:
            return _err(str(e), 404)

    # ------------------------------------------------------------------
    # Log viewing  (Requirement 8.4)
    # ------------------------------------------------------------------

    @app.route("/api/logs", methods=["GET"])
    def list_logs():
        from datetime import datetime

        date_start = request.args.get("date_start")
        date_end = request.args.get("date_end")
        mac_address = request.args.get("mac_address")
        outcome_str = request.args.get("outcome")

        dt_start = None
        dt_end = None
        outcome = None

        if date_start:
            try:
                dt_start = datetime.fromisoformat(date_start)
            except ValueError:
                return _err("Invalid date_start format; use ISO 8601")
        if date_end:
            try:
                dt_end = datetime.fromisoformat(date_end)
            except ValueError:
                return _err("Invalid date_end format; use ISO 8601")
        if outcome_str:
            try:
                outcome = AuthenticationOutcome(outcome_str)
            except ValueError:
                return _err(f"Invalid outcome value: {outcome_str}")

        logs = log_manager.filter_logs(
            date_start=dt_start,
            date_end=dt_end,
            mac_address=mac_address,
            outcome=outcome,
        )
        return jsonify([_log_to_dict(l) for l in logs])

    return app
