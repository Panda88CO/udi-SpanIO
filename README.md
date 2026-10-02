# udi-SpanIO - SPAN IO Power Panel Node Server for Polyglot PG3x

This node server integrates, monitors, and controls one or more **SPAN IO** smart electrical panels with Universal Devices systems (eisy / IoX) using Polyglot PG3x.

The node server connects locally to the SPAN panel using the local SPAN REST API.

---

## Features

- **Controller Node**:
  - Monitors plugin connection status (`ST`: Connected / Not Connected)
  - Displays total number of SPAN panels monitored (`GV1`)
  - Periodic heartbeat (`DON`/`DOF`)
- **Panel Node (per SPAN Panel)**:
  - `ST`: Instant Panel Power (Watts)
  - `GV0`: Panel Door State (Closed / Open / Unknown)
  - `GV1`: Main Panel Breaker State (Closed / Open)
  - `GV2`: Instant Feedthrough Power (Watts)
  - `GV3`: Grid State (`DSM_GRID_UP` / `DSM_GRID_DOWN`)
  - `GV4`: Grid Status (`ON_GRID` / `OFF_GRID`)
  - `GV7`: Backup Battery Capacity (%, optional)
  - Manual data update command
- **Circuit / Breaker Sub-Nodes (per Circuit)**:
  - `ST`: Instantaneous Power (Watts)
  - `GV1`: Circuit Priority (`Must Have` / `Nice to Have` / `Not Essential`)
  - `GV2`: Circuit Relay State (Closed / Open)
  - `GV4`: Power Measurement Timestamp (Epoch seconds)
  - `GV5`: Imported Energy (kWh)
  - `GV6`: Exported Energy (kWh)
  - `GV7`: Net Energy Last 1 Hour (Wh)
  - `GV8`: Net Energy Last 24 Hours (Wh)
  - `GV9`: Energy Measurement Timestamp (Epoch seconds)
  - Command: `OPENCLOSE` (Open / Close circuit relay)
- **Dynamic Profile Provisioning**:
  - Automatically provisions profile definitions (editors, node definitions, translations) to IoX via PG3x dynamic profile support, keeping definitions synchronized without requiring manual profile installations or IoX restarts.
  - Also includes a pre-packaged static profile (`profile.zip` with `version.txt`).

---

## Configuration

In the Polyglot Dashboard under **Configuration**, configure the following parameters:

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `LOCAL_IP_ADDRESSES` | String | Space-separated list of local IP addresses for your SPAN panels (e.g. `192.168.1.50`). Use only **one** IP address per panel (Ethernet connection with a static DHCP reservation is strongly recommended). |
| `BACKUP_BATTERY` | String | Set to `TRUE` if you have an integrated home battery backup system (e.g. Tesla Powerwall, Enphase) connected to the SPAN panel to report State of Charge (SOC %), or `FALSE` otherwise. |

---

## Installation & Panel Pairing

1. Enter your panel's IP address in the configuration and start the node server.
2. When the node server starts for the first time with an unregistered panel, it will request authorization. A notice will appear in Polyglot.
3. Walk over to your SPAN panel, open the panel door, and **quickly press the door proximity/tamper switch in the upper corner 3 times**.
4. The panel light will blink to indicate it has entered registration mode.
5. The node server will complete registration, save the auth token to custom data, and discover all panel circuits and sub-nodes.

---

## Polling Behavior

- **shortPoll** (default 60s): Polls panel telemetry, battery status, and all circuit/breaker sub-nodes, ensuring driver states and timestamps update automatically in IoX.
- **longPoll** (default 300s): Performs full panel telemetry sync, recalculates 1-hour and 24-hour energy averages, and saves historical accumulation data.

---

## Notes

- **Energy Measurement**: Breaker energy reports imported energy (energy consumed by the circuit) and exported energy (e.g., solar or storage backfeed).
- **1-Hour and 24-Hour Averages**: 1-hour and 24-hour net energy statistics will populate once the node server has collected data across those respective time windows.
