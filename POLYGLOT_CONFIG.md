# SPAN IO Node Server Configuration

## Configuration Parameters

Navigate to the **Configuration** tab in the Polyglot dashboard for this node server and configure the following parameters:

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`LOCAL_IP_ADDRESSES`** | String | Yes | Space-separated list of local IP addresses for each SPAN panel in your home (e.g. `192.168.1.100`). Use only **one** IP address per physical panel. A reserved or static DHCP IP address via an Ethernet connection is strongly recommended. |
| **`PANEL_PASSPHRASES`** | String | Recommended | Space-separated list of passphrases corresponding to each panel in `LOCAL_IP_ADDRESSES`. Enables high-performance, real-time push streaming via the modern SPAN local MQTT/Homie v2 API. |
| **`BACKUP_BATTERY`** | String | No | Set to `TRUE` if your SPAN panel is connected to an integrated battery storage system (such as Tesla Powerwall or Enphase) to monitor backup battery State of Charge (`GV7`), or `FALSE` otherwise. |

Click **Save** and restart the node server after making changes.

---

## SPAN MQTT v2 & Pairing

### Recommended: Local MQTT v2 (Push Streaming)
1. Configure `LOCAL_IP_ADDRESSES` and `PANEL_PASSPHRASES` in the Polyglot configuration.
2. The node server connects directly to the panel's local MQTT broker (`span-panel-api`).
3. Telemetry is streamed in real-time with automatic **eisy-friendly throttling**:
   - Updates are debounced to a minimum 30-second interval.
   - Power telemetry is updated whenever power changes by **$\ge$ 15W**.
   - If power changes remain under 15W, a **15-minute fallback heartbeat** ensures status freshness without flooding the eisy event bus.
   - Discrete state changes (breaker relay open/closed, priority changes) are dispatched **immediately**.

### Legacy REST v1 Pairing (Fallback)
If no passphrase is provided:
1. Walk to your physical SPAN panel, open the outer door, and **press the door proximity switch 3 times**.
2. The panel LED will blink to enter registration mode, and the node server will obtain a REST token.
3. Node server operates via standard REST polling.

---

## Nodes & Drivers Reference

### 1. Controller Node (`controller`)
- **`ST`** (Node Status): `Connected` / `Not Connected`
- **`GV1`** (Monitored Panels): Total number of SPAN panels monitored
- **Heartbeat**: Periodic `DON` / `DOF` toggle
- **Commands**:
  - `UPDATE` (**Update System Data**): Refreshes telemetry across all panels and breaker subnodes.
  - `QUERY` (**Query**): Refreshes controller status drivers.

### 2. SPAN Panel Node (`spanpanel`)
Created for each configured SPAN panel:
- **`ST`** (Instant Power): Total panel instant power in Watts
- **`GV0`** (Door State): `Closed` / `Open` / `Unknown`
- **`GV1`** (Main Breaker State): `Closed` / `Open` / `Unknown`
- **`GV2`** (Feedthrough Power): Instant feedthrough power in Watts
- **`GV3`** (Grid State): `DSM_GRID_UP` / `DSM_GRID_DOWN` / `Unknown`
- **`GV4`** (Grid Status): `ON_GRID` / `OFF_GRID` / `Unknown`
- **`GV5`** (Panel Update Time): Epoch timestamp of last successful panel data update (UOM 151)
- **`GV7`** (Battery Capacity): Battery State of Charge percentage (when `BACKUP_BATTERY=TRUE`)
- **Commands**:
  - `UPDATE` (**Update Panels Data**): Updates panel timestamp and cascades updates to all breaker subnodes.
  - `QUERY` (**Query**): Refreshes panel drivers.

### 3. Dedicated Power Summary Node (`spansummary`)
A dedicated summary node created automatically for each panel (`${panel}_sum`):
- **`ST`** (Instant Total Consumption): Total power consumed by all active circuits (Watts, UOM 73)
- **`GV0`** (Total Energy Last 1 Hour): Net energy consumed across all circuits over the last 1 hour (Wh, UOM 119)
- **`GV1`** (Total Energy Last 1 Day): Net energy consumed across all circuits over the last 24 hours (Wh, UOM 119)
- **Top 3 Instantaneous Power Consumers**:
  - **`GV2`** (Top 1 Instant Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV3`** (Top 1 Instant Power): Instant power in Watts (UOM 73)
  - **`GV4`** (Top 2 Instant Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV5`** (Top 2 Instant Power): Instant power in Watts (UOM 73)
  - **`GV6`** (Top 3 Instant Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV7`** (Top 3 Instant Power): Instant power in Watts (UOM 73)
- **Top 3 1-Hour Energy Consumers**:
  - **`GV8`** (Top 1 1-Hour Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV9`** (Top 1 1-Hour Energy): Energy in Wh (UOM 119)
  - **`GV10`** (Top 2 1-Hour Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV11`** (Top 2 1-Hour Energy): Energy in Wh (UOM 119)
  - **`GV12`** (Top 3 1-Hour Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV13`** (Top 3 1-Hour Energy): Energy in Wh (UOM 119)
- **Top 3 1-Day Energy Consumers**:
  - **`GV14`** (Top 1 1-Day Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV15`** (Top 1 1-Day Energy): Energy in Wh (UOM 119)
  - **`GV16`** (Top 2 1-Day Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV17`** (Top 2 1-Day Energy): Energy in Wh (UOM 119)
  - **`GV18`** (Top 3 1-Day Consumer): Circuit name via dynamic UOM 25 `CIRCUIT_LIST`
  - **`GV19`** (Top 3 1-Day Energy): Energy in Wh (UOM 119)
- **`GV20`** (Summary Measurement Time): Epoch timestamp of summary calculation (UOM 151)
- **Commands**:
  - `UPDATE` (**Update Summary Data**): Recalculates consumption totals and consumer rankings.
  - `QUERY` (**Query**): Refreshes summary drivers.

### 4. Circuit / Breaker Nodes (`spancircuit`)
Created dynamically for every circuit breaker discovered on the panel:
- **`ST`** (Instant Power): Instantaneous circuit power in Watts (positive for power consumed)
- **`GV1`** (Circuit Priority): `Must Have` / `Nice to Have` / `Not Essential` / `Unknown`
- **`GV2`** (Relay State): `Closed` / `Open` / `Unknown`
- **`GV4`** (Power Measurement Time): Epoch timestamp of power telemetry (UOM 151)
- **`GV5`** (Imported Energy): Cumulative energy imported/consumed by circuit (kWh)
- **`GV6`** (Exported Energy): Cumulative energy exported/backfed (kWh, e.g. solar)
- **`GV7`** (Energy Last 1 Hour): Net energy over the last 1 hour (Wh)
- **`GV8`** (Energy Last 24 Hours): Net energy over the last 24 hours (Wh)
- **`GV9`** (Energy Measurement Time): Epoch timestamp of energy telemetry (UOM 151)
- **Commands**:
  - `UPDATE` (**Update Breaker Data**): Refreshes circuit breaker telemetry and updates timestamps.
  - `OPENCLOSE` (**Set State**): Controls the circuit relay (`Open` or `Close`).
  - `PRIORITY` (**Set Priority**): Sets load-shedding priority (`Must Have`, `Nice to Have`, or `Not Essential`).
  - `QUERY` (**Query**): Refreshes breaker drivers.

---

## Polling & Self-Healing

- **shortPoll (30s default)**: If MQTT streaming is active, redundant REST polling is suppressed; otherwise, updates panel, summary, and circuit breaker telemetry.
- **longPoll (900s default)**: Persists historical accumulation windows (`accum_data_<IP>.json`) across restarts and runs health checks.
- **Dynamic Profile Provisioning**: Breaker names discovered at boot or on refresh are automatically published to IoX via PG3x `updateJsonProfile`, generating the enumerated UOM 25 editor `CIRCUIT_LIST` so the Admin Console displays human-readable names.
