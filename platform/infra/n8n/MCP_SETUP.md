# n8n MCP setup

This project is ready to use n8n's built-in MCP server once the n8n instance is prepared.

## What the official docs confirm

- n8n's instance-level MCP server can now create, update, validate, and execute workflows.
- MCP must be enabled at the instance level first.
- Workflows are not exposed automatically. Each workflow must be enabled for MCP individually.
- Codex can connect over HTTP using the n8n MCP token and the `/mcp-server/http` endpoint.
- n8n recommends version `2.18.4` or newer for the best workflow-building experience.

Sources:
- `https://docs.n8n.io/advanced-ai/mcp/accessing-n8n-mcp-server/`
- `https://blog.n8n.io/n8n-mcp-server/`

## Instance steps

1. Open n8n as an admin or instance owner.
2. Go to `Settings -> Instance-level MCP`.
3. Enable MCP access.
4. Open `Connection details`.
5. Generate or copy the Access Token.
6. After importing workflows, enable each workflow for MCP access.

## Codex config snippet

Add this to `C:\Users\tobid\.codex\config.toml` after the token is available:

```toml
[mcp_servers.n8n_mcp]
url = "http://178.104.229.163.nip.io/mcp-server/http"
http_headers = { authorization = "Bearer <YOUR_N8N_MCP_TOKEN>" }
```

Replace `<YOUR_N8N_MCP_TOKEN>` with the token shown by n8n.

## Current blocker

The repo now contains the workflows to import, but the live MCP connection cannot be completed until:

- the n8n instance-level MCP toggle is enabled
- the personal n8n MCP access token is generated and provided

## Import order

Import these workflows first:

1. `systemeio_lead_capture_eu.json`
2. `systemeio_lead_capture_usca.json`
3. `streamyard_session_update.json`
4. `streamyard_registrants_sync.json`
5. `streamyard_attendance_sync.json`
6. `engagement_signal_ingest.json`

Then mark them `Available in MCP` inside n8n if you want Codex to edit or run them through MCP.
