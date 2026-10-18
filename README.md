# udi-SpanIO - SPAN IO Power Panel Node Server for Polyglot PG3x

This node server integrates, monitors, and controls one or more **SPAN IO** smart electrical panels with Universal Devices systems (eisy / IoX) using Polyglot PG3x.

The node server connects locally to the SPAN panel using the local SPAN REST API.

---

## Features

- **Controller Node**:
  - `ST`: Node Status (`Connected` / `Not Connected`)
  - `GV1`: Number of SPAN Panels Monitored
  - Periodic heartbeat (`DON`/`DOF`)
  - Commands: `UPDATE` (Update System Data - refreshes all panels and breakers), `QUERY` (Query)
- **Panel Node (per SPAN Panel)**:
  - `ST`: Instant Panel Power (Watts)
  - `GV0`: Panel Door State (`Closed` / `Open` / `Unknown`)
  - `GV1`: Main Panel Breaker State (`Closed` / `Open` / `Unknown`)
  - `GV2`: Instant Feedthrough Power (Watts)
  - `GV3`: Grid State (`DSM_GRID_UP` / `DSM_GRID_DOWN` / `Unknown`)
  - `GV4`: Grid Status (`ON_GRID` / `OFF_GRID` / `Unknown`)
  - `GV5`: Panel Update Time (Epoch seconds, UOM 151)
  - `GV7`: Backup Battery Capacity (%, optional when battery backup enabled)
  - Commands: `UPDATE` (Update Panels Data - refreshes panel telemetry and cascades forced updates to all breaker subnodes), `QUERY` (Query)
- **Circuit / Breaker Sub-Nodes (per Circuit)**:
  - `ST`: Instantaneous Power (Watts)
  - `GV1`: Circuit Priority (`Must Have` / `Nice to Have` / `Not Essential` / `Unknown`)
  - `GV2`: Circuit Relay State (`Closed` / `Open` / `Unknown`)
  - `GV4`: Power Measurement Time (Epoch seconds, UOM 151)
  - `GV5`: Imported Energy (kWh)
  - `GV6`: Exported Energy (kWh)
  - `GV7`: Energy Last 1 Hour (Wh net energy)
  - `GV8`: Energy Last 24 Hours (Wh net energy)
  - `GV9`: Energy Measurement Time (Epoch seconds, UOM 151)
  - Commands: `UPDATE` (Update Breaker Data), `OPENCLOSE` (Set State - Open/Close circuit relay), `QUERY` (Query)
- **Dynamic Profile Provisioning**:
  - Automatically provisions profile definitions (editors, node definitions, translations) to IoX via PG3x dynamic profile support (`updateJsonProfile`), keeping definitions synchronized without requiring manual profile installations or IoX restarts.
  - Also includes a pre-packaged static profile (`profile.zip` with `version.txt`).
- **Resilience & Self-Healing**:
  - Automatic Subnode Recovery: Automatically discovers and creates breaker subnodes if the panel was temporarily unreachable at boot (e.g. after a router reboot), retrying seamlessly during polling cycles and manual update commands.
  - Safe Timestamps: Timestamps update only when valid telemetry is received, preventing false updates during network errors or missing data.
  - Driver Force Reporting: Ensures IoX advances timestamps and updates driver states even when raw wattage or relay values remain unchanged between polls.
  - Comprehensive UI Logging: Full debug logging for all UI calls (`UPDATE`, `OPENCLOSE`, `QUERY`), parameter parsing, and API responses when log level is set to `DEBUG`.

---

## Configuration

In the Polyglot Dashboard under **Configuration**, configure the following parameters:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `LOCAL_IP_ADDRESSES` | String | Space-separated list of local IP addresses for your SPAN panels (e.g. `192.168.1.50`). Use only **one** IP address per physical panel (Ethernet connection with a static DHCP reservation is strongly recommended). |
| `BACKUP_BATTERY` | String | Set to `TRUE` if you have an integrated home battery backup system (e.g. Tesla Powerwall, Enphase) connected to the SPAN panel to report State of Charge (SOC %), or `FALSE` otherwise. |

---

## Installation & Panel Pairing

1. Enter your panel's IP address in the configuration and start the node server.
2. When the node server starts for the first time with an unregistered panel, it will request authorization. A notice will appear in Polyglot.
3. Walk over to your SPAN panel, open the panel door, and **quickly press the door proximity/tamper switch in the upper corner 3 times**.
4. The panel light will blink to indicate it has entered registration mode.
5. The node server will complete registration, save the auth token to custom data, discover all panel circuits and subnodes, and begin regular polling.

---

## Polling Behavior

- **shortPoll** (default 60s): Polls panel telemetry, battery status, and all circuit/breaker sub-nodes, ensuring driver states and timestamps update automatically in IoX. Automatically recovers missing sub-nodes if initial startup communication was interrupted.
- **longPoll** (default 300s): Performs full panel telemetry sync, recalculates 1-hour and 24-hour energy averages, and saves historical accumulation data.

---

## Notes

- **Energy Measurement**: Breaker energy reports imported energy (energy consumed by the circuit) and exported energy (e.g., solar or storage backfeed).
- **1-Hour and 24-Hour Averages**: 1-hour and 24-hour net energy statistics will populate once the node server has collected data across those respective time windows. Historical data is persisted per panel across restarts (`accum_data_<IP>.json`).
- **Manual Updates**: Clicking **"Update Panels Data"** on a panel node pulls fresh telemetry from the SPAN API, updates the panel node timestamp (`GV5`), and immediately refreshes and updates all breaker subnodes under that panel.
