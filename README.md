# udi-SpanIO - SPAN IO Power Panel Node Server for Polyglot PG3x

This node server integrates, monitors, and controls one or more **SPAN IO** smart electrical panels with Universal Devices systems (eisy / IoX) using Polyglot PG3x.

Starting with **v1.0.0**, the node server supports real-time push streaming via the modern local SPAN MQTT / Homie v2 API (`span-panel-api`), with an eisy-friendly throttling engine, a dedicated **Power Summary Node**, and graceful fallback to local REST polling.

---

## Features

- **Local MQTT v2 Push Streaming**:
  - Connects locally to SPAN panels via MQTT/Homie v2 push streaming.
  - Zero polling lag: circuit power, main grid power, and door/breaker states are pushed instantly by the panel.
- **eisy-Friendly Throttling & Heartbeat**:
  - Minimum 30-second delay between driver updates to avoid flooding the IoX event bus.
  - Power updates triggered whenever a $\ge$ 15W delta occurs.
  - 15-minute fallback heartbeat to guarantee data freshness even if power remains static.
  - Discrete state changes (breaker relay state, circuit priority) are reported immediately without debounce delay.
- **Dedicated Power Summary Node (`spansummary`)**:
  - Consolidates consumption totals and top consumer analytics into one clean child node per panel.
  - `ST`: Instantaneous Total Consumption in Watts.
  - `GV0`: Total Energy Consumed in Last 1 Hour (Wh).
  - `GV1`: Total Energy Consumed in Last 1 Day / 24 Hours (Wh).
  - **Top 3 Instantaneous Power Consumers** (Circuit name via dynamic UOM 25 + Power in Watts).
  - **Top 3 1-Hour Energy Consumers** (Circuit name via dynamic UOM 25 + Energy in Wh).
  - **Top 3 1-Day Energy Consumers** (Circuit name via dynamic UOM 25 + Energy in Wh).
- **Dynamic UOM 25 Circuit Mapping**:
  - Scans all breaker names during startup and dynamically generates an enumerated UOM 25 `CIRCUIT_LIST` profile editor via PG3x `updateJsonProfile`.
  - IoX displays human-readable breaker names (e.g. `HVAC`, `Kitchen Refrigerator`, `EV Charger`) directly in the Admin Console rather than cryptic circuit numbers.
- **Controller Node (`controller`)**:
  - `ST`: Node Status (`Connected` / `Not Connected`)
  - `GV1`: Number of SPAN Panels Monitored
  - Periodic heartbeat (`DON`/`DOF`)
  - Commands: `UPDATE` (Update System Data), `QUERY` (Query)
- **Panel Node (per SPAN Panel, `spanpanel`)**:
  - `ST`: Instant Panel Power (Watts)
  - `GV0`: Panel Door State (`Closed` / `Open` / `Unknown`)
  - `GV1`: Main Panel Breaker State (`Closed` / `Open` / `Unknown`)
  - `GV2`: Instant Feedthrough Power (Watts)
  - `GV3`: Grid State (`DSM_GRID_UP` / `DSM_GRID_DOWN` / `Unknown`)
  - `GV4`: Grid Status (`ON_GRID` / `OFF_GRID` / `Unknown`)
  - `GV5`: Panel Update Time (Epoch seconds, UOM 151)
  - `GV7`: Backup Battery Capacity (%, optional when battery backup enabled)
  - Commands: `UPDATE` (Update Panels Data), `QUERY` (Query)
- **Circuit / Breaker Sub-Nodes (per Circuit, `spancircuit`)**:
  - `ST`: Instantaneous Power (Watts, positive for consumption)
  - `GV1`: Circuit Priority (`Must Have` / `Nice to Have` / `Not Essential` / `Unknown`)
  - `GV2`: Circuit Relay State (`Closed` / `Open` / `Unknown`)
  - `GV4`: Power Measurement Time (Epoch seconds, UOM 151)
  - `GV5`: Imported Energy (kWh)
  - `GV6`: Exported Energy (kWh)
  - `GV7`: Energy Last 1 Hour (Wh net energy)
  - `GV8`: Energy Last 24 Hours (Wh net energy)
  - `GV9`: Energy Measurement Time (Epoch seconds, UOM 151)
  - Commands: `UPDATE` (Update Breaker Data), `OPENCLOSE` (Set State - Open/Close circuit relay), `PRIORITY` (Set Priority - Must Have/Nice to Have/Not Essential), `QUERY` (Query)
- **Dynamic Profile Provisioning**:
  - Automatically provisions profile definitions (editors, node definitions, translations) to IoX via PG3x dynamic profile support (`updateJsonProfile`), keeping definitions synchronized without requiring manual profile installations or IoX restarts.
  - Includes a pre-packaged static profile (`profile.zip` with `version.txt`).

---

## Configuration

In the Polyglot Dashboard under **Configuration**, configure the following parameters:

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `LOCAL_IP_ADDRESSES` | String | Yes | Space-separated list of local IP addresses for your SPAN panels (e.g. `192.168.1.50`). Use only **one** IP address per physical panel (Ethernet connection with a static DHCP reservation is strongly recommended). |
| `PANEL_PASSPHRASES` | String | Recommended | Space-separated list of passphrases corresponding to each panel in `LOCAL_IP_ADDRESSES`. Enables real-time local MQTT streaming. |
| `BACKUP_BATTERY` | String | No | Set to `TRUE` if you have an integrated home battery backup system (e.g. Tesla Powerwall, Enphase) connected to the SPAN panel to report State of Charge (SOC %), or `FALSE` otherwise. |

---

## Setup & Pairing

### Recommended: Local MQTT v2 Setup
1. Enter your panel's IP address in `LOCAL_IP_ADDRESSES` and your panel's passphrase in `PANEL_PASSPHRASES`.
2. Save configuration and start the node server.
3. The node server connects directly to the panel's local MQTT broker and starts streaming immediately.

### Legacy REST Fallback
If no passphrase is provided:
1. When the node server starts for the first time, walk over to your SPAN panel, open the panel door, and **press the door proximity switch 3 times**.
2. The panel light will blink to indicate registration mode.
3. The node server obtains a local REST token and uses REST polling.

---

## Polling & Heartbeat Behavior

- **shortPoll** (default 30s): When MQTT is active, redundant REST polling is suppressed; otherwise, polls panel telemetry, summary, and all circuit breakers.
- **longPoll** (default 900s): Persists historical accumulation windows (`accum_data_<IP>.json`) across restarts and checks health.
- **Timestamp Accuracy**: Timestamps (`GV5`, `GV4`, `GV9`, `GV20`) only advance when fresh, valid telemetry is received.
