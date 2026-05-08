# CONSAT Secure AI Gateway & Policy Engine

A Proof of Concept (PoC) for a Secure Agentic Workflow and Data Policy Engine designed to securely share Stockholm bus IoT and driver data.

## Features

- **3-Tier Data Policy Engine**: Automatically classifies data as `PUBLIC` (pass-through), `PII` (hashed/encrypted), or `COMPANY_SECRET` (redacted).
- **Secure Agentic Workflow**: Intercepts AI requests, classifies sensitivity, routes to local or cloud LLMs, and enforces data masking rules.
- **Web Dashboard & Data Explorer**: Real-time visualization of the system's routing, health, and a live Data Explorer that demonstrates the per-column data policy rules applied to Stockholm bus routes, vehicles, drivers, and IoT sensors.

## Quickstart: Web Dashboard

To run the live dashboard and Data Explorer:

```bash
pip install fastapi uvicorn jinja2 python-multipart
python web_dashboard.py
```
Then visit `http://localhost:8000` in your browser.
- **Monitor View**: Real-time metrics on LLM routing and requests.
- **Data Explorer View**: Interactive visualization showing how internal PII and company secrets are hashed/redacted before being exposed externally.

---

## Integrating with Cline (MCP Server)

The project includes a ready-to-use **Model Context Protocol (MCP)** server (`mcp_server.py`). This allows Cline to directly query the Stockholm bus mock database while automatically applying the security policies.

### How to set it up:

1. In Cline, click the **MCP Servers** icon (the plug 🔌 icon in the top-right corner of the Cline sidebar).
2. Click **Configure MCP Servers** (or open your `cline_mcp_settings.json` file).
3. Add the following configuration to your `mcpServers` object:

```json
{
  "mcpServers": {
    "consat-secure-gateway": {
      "command": "python",
      "args": [
        "/Users/phuwit.v/Hack_Project/Cline_Consat/mcp_server.py"
      ],
      "env": {}
    }
  }
}
```

4. Save the file. Cline will automatically restart its MCP connection. You should see a green dot next to **consat-secure-gateway** in your MCP list.

### Available MCP Tools:
Once connected, Cline can automatically use the following tools:
- `consat_bus_query`: Query bus routes, vehicles, drivers, or sensor data.
- `consat_driver_lookup`: Look up specific drivers (PII is auto-hashed).
- `consat_data_policy`: Inspect the data sharing policy rules.
- `consat_route` / `consat_mask` / `consat_policy_check`: Direct access to the security pipeline.
