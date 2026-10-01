# SPAN IO Node Server Configuration

## Configuration Parameters

Navigate to the **Configuration** tab in the Polyglot dashboard for this node server and configure the following parameters:

- **`LOCAL_IP_ADDRESSES`**: Space-separated list of IP addresses for each SPAN panel in your home (e.g. `192.168.1.100`).
  - *Recommendation*: Use a reserved/static DHCP IP address for each panel. Prefer an Ethernet connection over Wi-Fi if available. Use only **one** IP address per physical panel.
- **`BACKUP_BATTERY`**: Set to `TRUE` if your SPAN panel is connected to an integrated battery storage system (to monitor backup battery SOC percentage), or `FALSE` otherwise.

Click **Save** and restart the node server.

## Initial Panel Pairing

To authorize the node server to communicate with your SPAN panel:

1. Start the node server after saving the configuration.
2. Go to the physical SPAN panel, open the outer door, and **quickly press the door contact switch (located in the upper corner) 3 times**.
3. The panel LED will blink indicating it has entered pairing/registration mode.
4. The node server will automatically obtain a local access token, create all panel and circuit nodes, and begin polling data.
