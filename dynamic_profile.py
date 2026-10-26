"""Dynamic profile definitions and payload generator for SPAN IO PG3x plugin.

Matches the node definitions, editors, and NLS translations previously kept in
static XML/NLS files, enabling real-time profile provisioning without manual
profile.zip packaging or IoX restart.
"""

from typing import Any, Dict, List, Optional


def circuit_list_editor(circuit_names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    """Generates dynamic UOM 25 CIRCUIT_LIST editor mapping integer indices to circuit breaker names."""
    mapping = {"0": "None"}
    if circuit_names:
        for idx, name in sorted(circuit_names.items(), key=lambda x: int(x[0])):
            clean_name = str(name).strip() if name else f"Circuit {idx}"
            mapping[str(idx)] = clean_name
    subset = list(mapping.keys())
    return {
        "id": "CIRCUIT_LIST",
        "ranges": [
            {
                "uom": "25",
                "subset": ",".join(subset),
                "names": mapping,
            }
        ],
    }


def profile_editors(circuit_names: Optional[Dict[int, str]] = None) -> List[Dict[str, Any]]:
    return [
        circuit_list_editor(circuit_names),
        {
            "id": "UPDN",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1",
                    "names": {"0": "Down", "1": "Up"},
                }
            ],
        },
        {
            "id": "CONNECTED",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1",
                    "names": {"0": "Not Connected", "1": "Connected"},
                }
            ],
        },
        {
            "id": "NBRSPAN",
            "ranges": [
                {
                    "uom": "56",
                    "min": 1,
                    "max": 9,
                    "prec": 0,
                    "step": 1,
                }
            ],
        },
        {
            "id": "OPENCLOSE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,99",
                    "names": {"0": "Closed", "1": "Open", "99": "Unknown"},
                }
            ],
        },
        {
            "id": "SET_OPENCLOSE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1",
                    "names": {"0": "Closed", "1": "Open"},
                }
            ],
        },
        {
            "id": "KW",
            "ranges": [
                {"uom": "30", "min": -100, "max": 100, "prec": 1},
                {
                    "uom": "25",
                    "subset": "98,99",
                    "names": {"98": "Error", "99": "No Data"},
                },
            ],
        },
        {
            "id": "KWH",
            "ranges": [
                {"uom": "33", "min": -1000000, "max": 1000000, "prec": 3},
                {
                    "uom": "25",
                    "subset": "98,99",
                    "names": {"98": "Error", "99": "No Data"},
                },
            ],
        },
        {
            "id": "W",
            "ranges": [
                {"uom": "73", "min": -150000, "max": 150000, "prec": 1},
                {
                    "uom": "25",
                    "subset": "98,99",
                    "names": {"98": "Error", "99": "No Data"},
                },
            ],
        },
        {
            "id": "WH",
            "ranges": [
                {"uom": "119", "min": -1000000, "max": 1000000, "prec": 1},
                {
                    "uom": "25",
                    "subset": "98,99",
                    "names": {"98": "Error", "99": "No Data"},
                },
            ],
        },
        {
            "id": "GRIDSTATE",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,99",
                    "names": {
                        "0": "DSM_GRID_UP",
                        "1": "DSM_GRID_DOWN",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "GRIDSTATUS",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,99",
                    "names": {
                        "0": "ON_GRID",
                        "1": "OFF_GRID",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "PRIORITY",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2,99",
                    "names": {
                        "0": "Must Have",
                        "1": "Nice to Have",
                        "2": "Not Essential",
                        "99": "Unknown",
                    },
                }
            ],
        },
        {
            "id": "SET_PRIORITY",
            "ranges": [
                {
                    "uom": "25",
                    "subset": "0,1,2",
                    "names": {
                        "0": "Must Have",
                        "1": "Nice to Have",
                        "2": "Not Essential",
                    },
                }
            ],
        },
        {
            "id": "BACKUP_MINS",
            "ranges": [
                {
                    "uom": "44",
                    "min": 0,
                    "max": 10080,
                    "prec": 0,
                },
                {
                    "uom": "25",
                    "subset": "98,99",
                    "names": {"98": "None", "99": "No Data"},
                },
            ],
        },
        {
            "id": "HOURS",
            "ranges": [
                {"uom": "20", "min": 0, "max": 100, "prec": 2},
                {
                    "uom": "25",
                    "subset": "97,98,99",
                    "names": {
                        "97": "No Data",
                        "98": "Unknown",
                        "99": "Not Present",
                    },
                },
            ],
        },
        {
            "id": "MINS",
            "ranges": [
                {"uom": "44", "min": 0, "max": 720, "prec": 2},
                {
                    "uom": "25",
                    "subset": "97,98,99",
                    "names": {
                        "97": "No Data",
                        "98": "Unknown",
                        "99": "Not Present",
                    },
                },
            ],
        },
        {
            "id": "UTIME",
            "ranges": [
                {"uom": "151", "min": 0, "max": 5000000000, "prec": 0},
                {
                    "uom": "25",
                    "subset": "97,98,99",
                    "names": {
                        "97": "No Data",
                        "98": "Unknown",
                        "99": "Not Present",
                    },
                },
            ],
        },
        {
            "id": "SECS",
            "ranges": [
                {"uom": "57", "min": 0, "max": 7200, "prec": 0},
                {
                    "uom": "25",
                    "subset": "97,98,99",
                    "names": {
                        "97": "No Data",
                        "98": "Unknown",
                        "99": "Not Present",
                    },
                },
            ],
        },
        {
            "id": "PERCENT",
            "ranges": [
                {"uom": "51", "min": 0, "max": 100, "prec": 0},
                {
                    "uom": "25",
                    "subset": "97,98,99",
                    "names": {
                        "97": "No Data",
                        "98": "Unknown",
                        "99": "Not Present",
                    },
                },
            ],
        },
    ]


def profile_nodedefs() -> List[Dict[str, Any]]:
    return [
        {
            "id": "controller",
            "name": "SPAN panels Info",
            "icon": "EnergyMonitor",
            "properties": [
                {"id": "ST", "editor": "CONNECTED", "name": "Node Status"},
                {"id": "GV1", "editor": "NBRSPAN", "name": "Nbr Span Panels"},
            ],
            "cmds": {
                "sends": [
                    {"id": "DON"},
                    {"id": "DOF"},
                ],
                "accepts": [
                    {"id": "UPDATE", "name": "Update System Data"},
                    {"id": "QUERY", "name": "Query"},
                ],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "spanpanel",
            "name": "SPAN Panel Status",
            "icon": "EnergyMonitor",
            "properties": [
                {"id": "ST", "editor": "W", "name": "Instant Panel Power"},
                {"id": "GV0", "editor": "OPENCLOSE", "name": "Panel Door State"},
                {"id": "GV1", "editor": "OPENCLOSE", "name": "Main Panel Breaker State"},
                {"id": "GV2", "editor": "W", "name": "Instant Feedthrough Power"},
                {"id": "GV3", "editor": "GRIDSTATE", "name": "Grid State"},
                {"id": "GV4", "editor": "GRIDSTATUS", "name": "Grid Status"},
                {"id": "GV5", "editor": "UTIME", "name": "Panel Update Time"},
                {"id": "GV7", "editor": "PERCENT", "name": "Backup Battery Capacity"},
                {"id": "GV8", "editor": "W", "name": "Solar Power Flow"},
                {"id": "GV9", "editor": "W", "name": "Battery Power Flow"},
                {"id": "GV10", "editor": "W", "name": "Grid Power Flow"},
                {"id": "GV11", "editor": "W", "name": "Home Site Load"},
                {"id": "GV12", "editor": "BACKUP_MINS", "name": "Backup Time Remaining"},
                {"id": "GV13", "editor": "BACKUP_MINS", "name": "Time to Next Shed"},
                {"id": "GV14", "editor": "PERCENT", "name": "Shed SOC Threshold"},
                {"id": "GV15", "editor": "PERCENT", "name": "Release SOC Threshold"},
            ],
            "cmds": {
                "sends": [],
                "accepts": [
                    {"id": "UPDATE", "name": "Update Panels Data"},
                    {"id": "QUERY", "name": "Query"},
                ],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "spansummary",
            "name": "SPAN Power Summary",
            "icon": "EnergyMonitor",
            "properties": [
                {"id": "ST", "editor": "W", "name": "Instantaneous Total Consumption"},
                {"id": "GV0", "editor": "WH", "name": "Total Energy Last 1 Hour"},
                {"id": "GV1", "editor": "WH", "name": "Total Energy Last 1 Day"},
                {"id": "GV2", "editor": "CIRCUIT_LIST", "name": "Top 1 Instant Consumer"},
                {"id": "GV3", "editor": "W", "name": "Top 1 Instant Power"},
                {"id": "GV4", "editor": "CIRCUIT_LIST", "name": "Top 2 Instant Consumer"},
                {"id": "GV5", "editor": "W", "name": "Top 2 Instant Power"},
                {"id": "GV6", "editor": "CIRCUIT_LIST", "name": "Top 3 Instant Consumer"},
                {"id": "GV7", "editor": "W", "name": "Top 3 Instant Power"},
                {"id": "GV8", "editor": "CIRCUIT_LIST", "name": "Top 1 1-Hour Consumer"},
                {"id": "GV9", "editor": "WH", "name": "Top 1 1-Hour Energy"},
                {"id": "GV10", "editor": "CIRCUIT_LIST", "name": "Top 2 1-Hour Consumer"},
                {"id": "GV11", "editor": "WH", "name": "Top 2 1-Hour Energy"},
                {"id": "GV12", "editor": "CIRCUIT_LIST", "name": "Top 3 1-Hour Consumer"},
                {"id": "GV13", "editor": "WH", "name": "Top 3 1-Hour Energy"},
                {"id": "GV14", "editor": "CIRCUIT_LIST", "name": "Top 1 1-Day Consumer"},
                {"id": "GV15", "editor": "WH", "name": "Top 1 1-Day Energy"},
                {"id": "GV16", "editor": "CIRCUIT_LIST", "name": "Top 2 1-Day Consumer"},
                {"id": "GV17", "editor": "WH", "name": "Top 2 1-Day Energy"},
                {"id": "GV18", "editor": "CIRCUIT_LIST", "name": "Top 3 1-Day Consumer"},
                {"id": "GV19", "editor": "WH", "name": "Top 3 1-Day Energy"},
                {"id": "GV20", "editor": "UTIME", "name": "Summary Measurement Time"},
            ],
            "cmds": {
                "sends": [],
                "accepts": [
                    {"id": "UPDATE", "name": "Update Summary Data"},
                    {"id": "QUERY", "name": "Query"},
                ],
            },
            "links": {"ctl": [], "rsp": []},
        },
        {
            "id": "spancircuit",
            "name": "SPAN Breaker Status",
            "icon": "EnergyMonitor",
            "properties": [
                {"id": "ST", "editor": "W", "name": "Instantaneous Power"},
                {"id": "GV1", "editor": "PRIORITY", "name": "Circuit (relay) Priority"},
                {"id": "GV2", "editor": "OPENCLOSE", "name": "Circuit (relay) State"},
                {"id": "GV4", "editor": "UTIME", "name": "Power Measurement Time"},
                {"id": "GV5", "editor": "KWH", "name": "Imported Energy"},
                {"id": "GV6", "editor": "KWH", "name": "Exported Energy"},
                {"id": "GV7", "editor": "WH", "name": "Energy last hour"},
                {"id": "GV8", "editor": "WH", "name": "Energy last 24 hours"},
                {"id": "GV9", "editor": "UTIME", "name": "Energy Measurement Time"},
            ],
            "cmds": {
                "sends": [],
                "accepts": [
                    {"id": "UPDATE", "name": "Update Breaker Data"},
                    {
                        "id": "OPENCLOSE",
                        "name": "Set State",
                        "parameters": [
                            {
                                "id": "openclose",
                                "name": "Breaker State",
                                "editor": "SET_OPENCLOSE",
                                "init": "GV2",
                            }
                        ],
                    },
                    {
                        "id": "PRIORITY",
                        "name": "Set Priority",
                        "parameters": [
                            {
                                "id": "priority",
                                "name": "Breaker Priority",
                                "editor": "SET_PRIORITY",
                                "init": "GV1",
                            }
                        ],
                    },
                ],
            },
            "links": {"ctl": [], "rsp": []},
        },
    ]


def dynamic_profile_payload(version: str = "1.1.0", circuit_names: Optional[Dict[int, str]] = None) -> Dict[str, Any]:
    return {
        "version": version,
        "delete": {
            "editors": ["*"],
            "nodedefs": ["*"],
            "linkdefs": ["*"],
        },
        "editors": profile_editors(circuit_names),
        "nodedefs": profile_nodedefs(),
        "linkdefs": [],
    }
