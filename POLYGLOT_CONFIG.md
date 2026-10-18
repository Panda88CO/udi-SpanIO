# SPAN IO Node Server Configuration

## Configuration Parameters

Navigate to the **Configuration** tab in the Polyglot dashboard for this node server and configure the following parameters:

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`LOCAL_IP_ADDRESSES`** | String | Yes | Space-separated list of local IP addresses for each SPAN panel in your home (e.g. `192.168.1.100`). Use only **one** IP address per physical panel. A reserved or static DHCP IP address via an Ethernet connection is strongly recommended. |
| **`BACKUP_BATTERY`** | String | No | Set to `TRUE` if your SPAN panel is connected to an integrated battery storage system (such as Tesla Powerwall or Enphase) to monitor backup battery State of Charge (`GV7`), or `FALSE` otherwise. |

Click **Save** and restart the node server after making changes.

---

## Initial Panel Pairing

To authorize the node server to communicate securely with your SPAN panel:

1. Save your configuration with the panel's IP address and start the node server.
2. If the panel is unregistered, the node server requests authorization and posts a notice in Polyglot.
3. Walk to your physical SPAN panel, open the outer door, and **quickly press the door proximity/contact switch (located in the upper corner) 3 times**.
4. The panel LED will blink to indicate it has entered registration mode.
5. The node server will automatically obtain a local access token, store it securely in custom data, discover all circuits, create IoX nodes, and begin polling telemetry.

---

## Nodes & Drivers Reference

### 1. Controller Node (`controller`)
- **`ST`** (Node Status): `Connected` / `Not Connected`
- **`GV1`** (Monitored Panels): Total number of SPAN panels monitored
- **Heartbeat**: Periodic `DON` / `DOF` toggle
- **Commands**:
  - `UPDATE` (**Update System Data**): Immediately polls fresh telemetry for all panels and forces updates across all breaker subnodes.
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
  - `UPDATE` (**Update Panels Data**): Fetches fresh panel telemetry from the local SPAN REST API, updates the panel timestamp (`GV5`), and immediately cascades forced updates to all breaker subnodes under this panel.
  - `QUERY` (**Query**): Refreshes panel drivers.

### 3. Circuit / Breaker Nodes (`spancircuit`)
Created dynamically for every circuit breaker discovered on the panel:
- **`ST`** (Instant Power): Instantaneous circuit power in Watts
- **`GV1`** (Circuit Priority): `Must Have` / `Nice to Have` / `Not Essential` / `Unknown`
- **`GV2`** (Relay State): `Closed` / `Open` / `Unknown`
- **`GV4`** (Power Measurement Time): Epoch timestamp of power telemetry (UOM 151)
- **`GV5`** (Imported Energy): Cumulative energy imported/consumed by circuit (kWh)
- **`GV6`** (Exported Energy): Cumulative energy exported/backfed (kWh, e.g. solar)
- **`GV7`** (Energy Last 1 Hour): Net energy over the last 1 hour (Wh)
- **`GV8`** (Energy Last 24 Hours): Net energy over the last 24 hours (Wh)
- **`GV9`** (Energy Measurement Time): Epoch timestamp of energy telemetry (UOM 151)
- **Commands**:
  - `UPDATE` (**Update Breaker Data**): Polls fresh circuit breaker telemetry and updates all driver values and timestamps.
  - `OPENCLOSE` (**Set State**): Controls the circuit relay (`Open` or `Close`).
  - `QUERY` (**Query**): Refreshes breaker drivers.

---

## Polling & Self-Healing

- **shortPoll (60s default)**: Updates panel telemetry, battery status, and all circuit breaker drivers and timestamps.
  - *Auto-Recovery*: If a panel was temporarily unreachable at node server startup (e.g. network switch reboot), missing circuit subnodes are automatically discovered and created during subsequent polling or manual update without requiring a node server restart.
- **longPoll (300s default)**: Syncs full telemetry, recalculates 1-hour and 24-hour net energy statistics, and persists historical accumulation windows (`accum_data_<IP>.json`) across restarts.
- **Timestamp Accuracy**: Timestamps (`GV5`, `GV4`, `GV9`) only advance when fresh, valid telemetry is received from the SPAN API, preventing misleading updates during communication outages.
