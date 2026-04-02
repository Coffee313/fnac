# Import/Export Feature Guide - FNAC v0.1.0-alpha

## Quick Start

### Exporting Configuration

1. Open the FNAC web interface (http://localhost:5000)
2. Click the **Settings** tab (💾 icon) in the sidebar
3. Click the **Download Settings** button
4. A JSON file will be downloaded with the name `fnac-config-YYYY-MM-DD.json`

The exported file contains:
- All device groups and devices
- All client groups and clients
- All authentication policies
- Timestamps and configuration details

### Importing Configuration

1. Open the FNAC web interface
2. Click the **Settings** tab (💾 icon)
3. In the "Import Configuration" section, click the file input
4. Select a previously exported JSON file
5. Click **Import Settings**
6. Review the import results showing success/failure counts
7. The GUI will automatically reload with the imported data

## What Gets Exported/Imported

### Device Configuration
- Device groups (names, creation dates)
- Devices (names, IP addresses, shared secrets, group assignments)

### Client Configuration
- Client groups (names, creation dates)
- Clients (MAC addresses, group assignments)

### Policy Configuration
- Policies (names, decisions, VLAN IDs, client group assignments)

## Use Cases

### Backup & Restore
Export your configuration regularly as a backup. If something goes wrong, import the backup to restore.

### Migration
Export from one FNAC instance and import into another to quickly set up a new server with the same configuration.

### Configuration Templates
Create standard configurations and export them as templates for quick deployment.

## Error Handling

If import fails:
- Check that the file is valid JSON format
- Ensure the file was exported from FNAC (has correct structure)
- Review error messages in the import results
- Check the server logs for detailed error information

## API Endpoints

### Export
```
GET /api/export
```
Returns JSON with all configuration.

### Import
```
POST /api/import
Content-Type: multipart/form-data

file: <JSON file>
```
Returns import results with success/failure counts.

## File Format

Exported JSON structure:
```json
{
  "version": "0.1.0-alpha",
  "exported_at": "2026-04-02T10:30:00.123456",
  "device_groups": [...],
  "devices": [...],
  "client_groups": [...],
  "clients": [...],
  "policies": [...]
}
```

## Notes

- Import validates all data before applying changes
- FreeRADIUS configuration is automatically updated after import
- MAC addresses are normalized during import (any format accepted)
- VLAN IDs are validated (1-4094)
- Timestamps are preserved in ISO 8601 format
- Duplicate entries are skipped with error reporting
