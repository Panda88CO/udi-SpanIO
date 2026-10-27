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
  - `GV8`: Solar Power Flow (Watts)
  - `GV9`: Battery Power Flow (Watts, positive = discharging, negative = charging)
  - `GV10`: Grid Power Flow (Watts, positive = importing, negative = exporting)
  - `GV11`: Home Site Load (Watts)
  - `GV12`: Backup Time Remaining (Projected minutes, UOM 44)
  - `GV13`: Time to Next Shed (Projected minutes, UOM 44)
  - `GV14`: Shed SOC Threshold (Battery % to shed, UOM 51)
  - `GV15`: Release SOC Threshold (Battery % to restore, UOM 51)
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
- **Intelligent Node Name Management & Persistence**:
  - **Custom Renaming in IoX**: Any custom names assigned to nodes (Controller, Panels, Breakers, Summary Node) via IoX Admin Console or PG3x are remembered across restarts and never overwritten.
  - **Automatic SPAN App Sync**: If a circuit is renamed upstream in the SPAN mobile app, the new API name is automatically detected, updates the node name in PG3x/IoX, and refreshes the dynamic UOM 25 profile dropdowns.
  - **Live Runtime Detection**: Name changes from either IoX or SPAN are synced live during background polling cycles and manual update commands without requiring a node server restart.
- **Thread-Safe Historical Energy Accumulation**:
  - Thread-locked concurrency engine for 1-hour and 24-hour energy averages (`accum_data_<IP>.json`), preventing race conditions between the real-time MQTT streaming thread and background Polyglot polling threads.
  - Optimized disk I/O ensures accumulation data is saved cleanly without unnecessary flash storage wear on eisy.

---

## Configuration

In the Polyglot Dashboard under **Configuration**, configure the following parameters:

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `LOCAL_IP_ADDRESSES` | String | Yes | Space-separated list of local IP addresses for your SPAN panels (e.g. `192.168.1.50`). Use only **one** IP address per physical panel (Ethernet connection with a static DHCP reservation is strongly recommended). |
| `PANEL_PASSPHRASES` | String | Recommended | Space-separated list of passphrases corresponding to each panel in `LOCAL_IP_ADDRESSES`. Enables real-time local MQTT streaming. |
| `BACKUP_BATTERY` | String | No | Set to `TRUE` if you have an integrated home battery backup system (e.g. Tesla Powerwall, Enphase) connected to the SPAN panel to report State of Charge (SOC %), or `FALSE` otherwise. |
| `POWER_THRESHOLD_WATTS` | Float | No | Minimum wattage delta required to trigger an update to IoX (default: `15.0` Watts). Absolute floor for low power circuits. |
| `POWER_THRESHOLD_PCT` | Float | No | Percentage variation threshold relative to the last reported power (default: `5.0`%). Prevents high-load fluctuations ($\pm 20$–$50\text{W}$) on large consumers (EV chargers, heat pumps) from flooding IoX. Trigger threshold: $\max(\text{POWER\_THRESHOLD\_WATTS}, |P_{\text{last}}| \times \frac{\text{POWER\_THRESHOLD\_PCT}}{100})$. |
| `MIN_UPDATE_INTERVAL` | Float | No | Minimum seconds between driver update dispatches per panel to protect the eisy event bus (default: `30.0` seconds). Changes within the window are debounced and dispatched immediately when the timer expires. |
| `HEARTBEAT_INTERVAL_SECONDS` | Float | No | Fallback telemetry refresh interval in seconds (default: `900.0` seconds / 15 minutes). Forces fresh telemetry updates if power fluctuations remain below trigger thresholds. |

---

## Setup & Pairing

### How to Find Your SPAN Passphrase

Your panel's local passphrase can be obtained through any of the following methods:

1. **SPAN Home Mobile App (Recommended)**:
   - Connect your phone/tablet to the **same local Wi-Fi** as your SPAN panel.
   - Open the **SPAN Home App**.
   - Navigate to **Settings** (gear icon) $\rightarrow$ **All Settings** $\rightarrow$ **On-premise settings** (or *Access SPAN Home On-premise*).
   - Your local **Passphrase** is displayed on the screen.
2. **Physical Panel Door Label**:
   - On newer panels, the passphrase is printed on the factory sticker on the inside of the door or near the corner of the deadfront rim, labeled **Passphrase** or **WPA2 Password / Key** near the QR code.
3. **SPAN Support**:
   - If your panel is an older generation without the sticker and your app does not show the menu, SPAN Support (`support@span.io` or 1-855-980-SPAN) can provide the passphrase using your serial number.

---

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

- **Controller Heartbeat**: Single pulsed signal on short poll (sends `DON`, waits 5 seconds, sends `DOF`) without blocking the event loop.
- **shortPoll** (default 30s): When MQTT is active, redundant REST polling is suppressed; otherwise, polls panel telemetry, summary, and all circuit breakers.
- **longPoll** (default 900s): Persists historical accumulation windows (`accum_data_<IP>.json`) across restarts using thread-safe snapshot serialization, checks for node name changes, and validates health.
- **Timestamp Accuracy**: Timestamps (`GV5`, `GV4`, `GV9`, `GV20`) only advance when fresh, valid telemetry is received.
- **Node Name Persistence**: Stored mappings (`customData['node_name_map']` and `node_names.json`) ensure custom IoX names are preserved across reboots, while new names from the SPAN API automatically trigger live updates.
