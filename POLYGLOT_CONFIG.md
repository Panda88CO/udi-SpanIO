# SPAN IO Node Server Configuration

## Configuration Parameters

Navigate to the **Configuration** tab in the Polyglot dashboard for this node server and configure the following parameters:

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| **`LOCAL_IP_ADDRESSES`** | String | Yes | Space-separated list of local IP addresses for each SPAN panel in your home (e.g. `192.168.1.100`). Use only **one** IP address per physical panel. A reserved or static DHCP IP address via an Ethernet connection is strongly recommended. |
| **`PANEL_PASSPHRASES`** | String | Recommended | Space-separated list of local passphrases corresponding to each panel in `LOCAL_IP_ADDRESSES`. Enables high-performance, real-time push streaming via the modern SPAN local MQTT/Homie v2 API. |
| **`BACKUP_BATTERY`** | String | No | Set to `TRUE` if your SPAN panel is connected to an integrated battery storage system (such as Tesla Powerwall or Enphase) to monitor backup battery State of Charge (`GV7`), or `FALSE` otherwise. |
| **`POWER_THRESHOLD_WATTS`** | Float | No | Minimum wattage change required to trigger an update to IoX (default: `15.0` Watts). Serves as the absolute sensitivity floor for low loads. |
| **`POWER_THRESHOLD_PCT`** | Float | No | Percentage variation threshold relative to the last reported power (default: `5.0`%). Prevents high-power continuous loads (such as EV chargers or HVAC pulling 5kW–10kW) from triggering updates on harmless $\pm 20$–$50$W line voltage noise. Set to `0` to disable percentage filtering. Trigger threshold: $\max(\text{POWER\_THRESHOLD\_WATTS}, |P_{\text{last}}| \times \frac{\text{POWER\_THRESHOLD\_PCT}}{100})$. |
| **`MIN_UPDATE_INTERVAL`** | Float | No | Minimum seconds between driver update dispatches per panel to protect the eisy event bus (default: `30.0` seconds). Updates arriving within this window are debounced and dispatched immediately when the timer expires. |
| **`HEARTBEAT_INTERVAL_SECONDS`** | Float | No | Fallback telemetry refresh interval in seconds (default: `900.0` seconds / 15 minutes). Forces fresh telemetry updates if power fluctuations remain below the trigger thresholds. |

Click **Save** in Polyglot after making changes. Configuration parameters take effect dynamically at runtime without requiring a restart.

---

## SPAN MQTT v2 & Pairing

### How to Find Your SPAN Passphrase

Your SPAN panel's local passphrase can be obtained through any of the following methods:

#### Method A: From the SPAN Home App (Recommended)
This is the easiest method—especially for older panels where the physical label does not list a passphrase or the sticker is missing:
1. Make sure your smartphone or tablet is connected to the **same local Wi-Fi network** as your SPAN panel.
2. Open the **SPAN Home App**.
3. Tap the **Settings (gear icon)** $\rightarrow$ tap **All Settings**.
4. Tap **On-premise settings** (or **Access SPAN Home On-premise**).
5. Your panel's unique local **Passphrase** and local network address will be displayed on the screen. Copy this passphrase and enter it into `PANEL_PASSPHRASES`.

> [!TIP]
> If you do not see the "On-premise settings" option in the SPAN Home App, make sure your app is updated to the latest version in the iOS App Store or Google Play Store.

#### Method B: From the Physical Panel Label
For panels with updated door labels:
1. Open the outer metal door of your SPAN panel.
2. Inspect the factory sticker on the inside of the outer door or near the corner of the inner deadfront enclosure rim.
3. Look for the field labeled **Passphrase** or **WPA2 Password / Key** printed near the panel QR code and serial number.

#### Method C: SPAN Customer Support
If you have an older panel generation and cannot access the on-premise menu in the app, SPAN Customer Support (`support@span.io` or 1-855-980-SPAN) can provide your panel's on-premise local passphrase using your panel's serial number.

---

### Recommended: Local MQTT v2 (Push Streaming)
1. Configure `LOCAL_IP_ADDRESSES` and `PANEL_PASSPHRASES` in the Polyglot configuration.
2. The node server connects directly to the panel's local MQTT broker (`span-panel-api`).
3. Telemetry is streamed in real-time with automatic **eisy-friendly adaptive throttling**:
   - Updates are debounced to a minimum interval (default: `30` seconds via `MIN_UPDATE_INTERVAL`).
   - Power telemetry is updated whenever power changes by $\ge \max(\text{POWER\_THRESHOLD\_WATTS}, |P_{\text{last}}| \times \frac{\text{POWER\_THRESHOLD\_PCT}}{100})$.
   - At lower loads, the absolute floor (`15W`) triggers sensitive reporting.
   - At high loads (EV chargers, HVAC, solar arrays), percentage filtering (`5%`) suppresses harmless grid voltage noise ($\pm 20$–$50\text{W}$).
   - If power stays steady, a fallback heartbeat (default: `900`s / 15 min via `HEARTBEAT_INTERVAL_SECONDS`) forces fresh telemetry.
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
- **Heartbeat**: Single pulsed signal on short poll (sends `DON`, waits 5 seconds, sends `DOF`)
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
- **`GV8`** (Solar Power Flow): Real-time solar production in Watts (UOM 73)
- **`GV9`** (Battery Power Flow): Battery power in Watts (UOM 73, positive = discharging, negative = charging)
- **`GV10`** (Grid Power Flow): Utility power in Watts (UOM 73, positive = importing, negative = exporting)
- **`GV11`** (Home Site Load): Total household load consumption in Watts (UOM 73)
- **`GV12`** (Backup Time Remaining): Projected total battery runtime in minutes (UOM 44)
- **`GV13`** (Time to Next Shed): Projected minutes until next load shed threshold (UOM 44)
- **`GV14`** (Shed SOC Threshold): Battery SOC % threshold that triggers circuit shedding (UOM 51)
- **`GV15`** (Release SOC Threshold): Battery SOC % threshold that restores shed circuits (UOM 51)
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
- **longPoll (900s default)**: Recalculates 1-hour and 24-hour averages, persists historical accumulation windows (`accum_data_<IP>.json`) across restarts using thread-safe serialization, and checks for live node name updates.
- **Dynamic Profile Provisioning**: Breaker names discovered at boot or on refresh are automatically published to IoX via PG3x `updateJsonProfile`, generating the enumerated UOM 25 editor `CIRCUIT_LIST` so the Admin Console displays human-readable names.
- **Intelligent Node Name Synchronization**:
  - **Custom IoX Names Preserved**: If you rename any node (Controller, Panel, Breakers, Summary Node) in the IoX Admin Console or PG3x, the node server remembers your custom name across restarts and will not overwrite it.
  - **SPAN App Rename Sync**: If you rename a circuit in the SPAN mobile app, the new API name is detected automatically, updates the node name in IoX/PG3x, and republishes the dynamic profile.
  - **Dual Persistence**: Names are backed up in `customData['node_name_map']` and cached locally in `node_names.json`.
- **Thread-Safe Accumulation**: The 1-hour and 24-hour historical energy engine utilizes concurrency locks, eliminating race conditions between high-frequency MQTT streaming updates and background polling/disk serialization.
