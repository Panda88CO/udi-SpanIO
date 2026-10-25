#!/usr/bin/env python3
"""
udiSpanSummaryNode: Dedicated Power Summary Node for SPAN IO.

Reports:
- Instantaneous Total Consumption (W)
- Total Energy Last 1 Hour (Wh)
- Total Energy Last 1 Day (Wh)
- Top 3 Consumers across:
  * Instantaneous Power (W)
  * 1-Hour Energy (Wh)
  * 1-Day Energy (Wh)
Uses dynamic UOM 25 CIRCUIT_LIST editor to display actual circuit names in IoX.
"""

import time
from typing import Dict, List, Tuple, Optional, Any

try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)


class udiSpanSummaryNode(udi_interface.Node):
    from udiLib import node_queue, wait_for_node_done, my_setDriver

    def __init__(self, polyglot, primary, address, name, span_panel, circuit_index_map: Optional[Dict[str, int]] = None):
        super().__init__(polyglot, primary, address, name)
        logging.info(f'_init_ Span Summary Node {name} ({address})')
        self.poly = polyglot
        self.primary = primary
        self.address = address
        self.name = name
        self.span_panel = span_panel
        self.circuit_index_map = circuit_index_map or {}
        self.node = self
        self.node_ok = False
        self._starting = False
        self.n_queue = []

        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.addNode(self)
        self.wait_for_node_done(address)
        self.node = self.poly.getNode(address) or self
        time.sleep(0.1)

    def set_circuit_index_map(self, mapping: Dict[str, int]):
        self.circuit_index_map = mapping

    def start(self):
        logging.info(f'Start Span Summary Node {self.name}')
        if self.node_ok:
            return
        self._starting = True
        self.node = self.poly.getNode(self.address) or self
        self.updateISYdrivers(force=True)
        self.node_ok = True
        self._starting = False

    def stop(self):
        logging.debug(f'stop Span Summary Node {self.name}')

    def node_ready(self):
        return self.node_ok

    def compute_summary(self) -> Dict[str, Any]:
        """Calculates totals and top 3 rankings for instant, 1h, and 24h consumption."""
        if not self.span_panel or not isinstance(self.span_panel.span_data.get('circuit_info'), dict):
            return {}

        circuits = self.span_panel.span_data['circuit_info']

        instant_consumers: List[Tuple[str, float]] = []
        hour_consumers: List[Tuple[str, float]] = []
        day_consumers: List[Tuple[str, float]] = []

        total_instant_w = 0.0
        total_hour_wh = 0.0
        total_day_wh = 0.0
        has_hour_data = False
        has_day_data = False

        for cid, data in circuits.items():
            if not isinstance(data, dict):
                continue

            raw_pwr = data.get('instantPowerW')
            if raw_pwr is not None:
                try:
                    val = float(raw_pwr)
                    # In SPAN IoX convention: consuming power is negative in instantPowerW, so -val is positive consumption
                    cons_w = -val if val < 0 else 0.0
                except (ValueError, TypeError):
                    cons_w = 0.0
            else:
                cons_w = 0.0

            if cons_w > 0.0:
                total_instant_w += cons_w
                instant_consumers.append((cid, cons_w))

            # 1-Hour Energy consumption:
            cons_1h = data.get('cons_1hour')
            if cons_1h is not None:
                try:
                    val_1h = max(0.0, float(cons_1h))
                    total_hour_wh += val_1h
                    has_hour_data = True
                    if val_1h > 0.0:
                        hour_consumers.append((cid, val_1h))
                except (ValueError, TypeError):
                    pass

            # 24-Hour Energy consumption:
            cons_24h = data.get('cons_24hour')
            if cons_24h is not None:
                try:
                    val_24h = max(0.0, float(cons_24h))
                    total_day_wh += val_24h
                    has_day_data = True
                    if val_24h > 0.0:
                        day_consumers.append((cid, val_24h))
                except (ValueError, TypeError):
                    pass

        # Sort descending by consumption
        instant_consumers.sort(key=lambda x: x[1], reverse=True)
        hour_consumers.sort(key=lambda x: x[1], reverse=True)
        day_consumers.sort(key=lambda x: x[1], reverse=True)

        return {
            'total_instant_w': total_instant_w,
            'total_hour_wh': total_hour_wh if has_hour_data else None,
            'total_day_wh': total_day_wh if has_day_data else None,
            'top_instant': instant_consumers[:3],
            'top_hour': hour_consumers[:3],
            'top_day': day_consumers[:3],
            'update_time': int(time.time()),
        }

    def updateISYdrivers(self, force=False):
        logging.debug(f'SpanSummary updateISYdrivers force={force}')
        summary = self.compute_summary()
        if not summary:
            return

        # ST: Instantaneous Total Consumption (W)
        self.my_setDriver('ST', round(summary['total_instant_w'], 1), 73, force=force)

        # GV0: Total Energy Last 1 Hour (Wh)
        if summary['total_hour_wh'] is not None:
            self.my_setDriver('GV0', round(summary['total_hour_wh'], 1), 119, force=force)
        else:
            self.my_setDriver('GV0', None, 25, force=force)

        # GV1: Total Energy Last 1 Day (Wh)
        if summary['total_day_wh'] is not None:
            self.my_setDriver('GV1', round(summary['total_day_wh'], 1), 119, force=force)
        else:
            self.my_setDriver('GV1', None, 25, force=force)

        # Helper to unpack top 3
        def get_top_rank(rank_list: List[Tuple[str, float]], rank_idx: int) -> Tuple[int, float]:
            if rank_idx < len(rank_list):
                cid, val = rank_list[rank_idx]
                c_idx = self.circuit_index_map.get(cid, 0)
                return c_idx, round(val, 1)
            return 0, 0.0

        # Top 3 Instant Consumers
        idx1, pwr1 = get_top_rank(summary['top_instant'], 0)
        idx2, pwr2 = get_top_rank(summary['top_instant'], 1)
        idx3, pwr3 = get_top_rank(summary['top_instant'], 2)

        self.my_setDriver('GV2', idx1, 25, force=force)
        self.my_setDriver('GV3', pwr1, 73, force=force)
        self.my_setDriver('GV4', idx2, 25, force=force)
        self.my_setDriver('GV5', pwr2, 73, force=force)
        self.my_setDriver('GV6', idx3, 25, force=force)
        self.my_setDriver('GV7', pwr3, 73, force=force)

        # Top 3 1-Hour Energy Consumers
        idx_h1, e_h1 = get_top_rank(summary['top_hour'], 0)
        idx_h2, e_h2 = get_top_rank(summary['top_hour'], 1)
        idx_h3, e_h3 = get_top_rank(summary['top_hour'], 2)

        self.my_setDriver('GV8', idx_h1, 25, force=force)
        self.my_setDriver('GV9', e_h1, 119, force=force)
        self.my_setDriver('GV10', idx_h2, 25, force=force)
        self.my_setDriver('GV11', e_h2, 119, force=force)
        self.my_setDriver('GV12', idx_h3, 25, force=force)
        self.my_setDriver('GV13', e_h3, 119, force=force)

        # Top 3 1-Day Energy Consumers
        idx_d1, e_d1 = get_top_rank(summary['top_day'], 0)
        idx_d2, e_d2 = get_top_rank(summary['top_day'], 1)
        idx_d3, e_d3 = get_top_rank(summary['top_day'], 2)

        self.my_setDriver('GV14', idx_d1, 25, force=force)
        self.my_setDriver('GV15', e_d1, 119, force=force)
        self.my_setDriver('GV16', idx_d2, 25, force=force)
        self.my_setDriver('GV17', e_d2, 119, force=force)
        self.my_setDriver('GV18', idx_d3, 25, force=force)
        self.my_setDriver('GV19', e_d3, 119, force=force)

        # GV20: Summary Update Time
        self.my_setDriver('GV20', summary['update_time'], 151, force=force)

    def ISYupdate(self, command=None):
        logging.info(f'ISYupdate called for summary {self.name}')
        self.updateISYdrivers(force=True)

    def query(self, command=None):
        logging.debug(f'UI Call QUERY received on summary {self.name}')
        self.updateISYdrivers(force=True)

    id = 'spansummary'
    commands = {
        'UPDATE': ISYupdate,
        'QUERY': query,
    }

    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 73, 'name': 'Instantaneous Total Consumption'},
        {'driver': 'GV0', 'value': 0, 'uom': 119, 'name': 'Total Energy Last 1 Hour'},
        {'driver': 'GV1', 'value': 0, 'uom': 119, 'name': 'Total Energy Last 1 Day'},
        {'driver': 'GV2', 'value': 0, 'uom': 25, 'name': 'Top 1 Instant Consumer'},
        {'driver': 'GV3', 'value': 0, 'uom': 73, 'name': 'Top 1 Instant Power'},
        {'driver': 'GV4', 'value': 0, 'uom': 25, 'name': 'Top 2 Instant Consumer'},
        {'driver': 'GV5', 'value': 0, 'uom': 73, 'name': 'Top 2 Instant Power'},
        {'driver': 'GV6', 'value': 0, 'uom': 25, 'name': 'Top 3 Instant Consumer'},
        {'driver': 'GV7', 'value': 0, 'uom': 73, 'name': 'Top 3 Instant Power'},
        {'driver': 'GV8', 'value': 0, 'uom': 25, 'name': 'Top 1 1-Hour Consumer'},
        {'driver': 'GV9', 'value': 0, 'uom': 119, 'name': 'Top 1 1-Hour Energy'},
        {'driver': 'GV10', 'value': 0, 'uom': 25, 'name': 'Top 2 1-Hour Consumer'},
        {'driver': 'GV11', 'value': 0, 'uom': 119, 'name': 'Top 2 1-Hour Energy'},
        {'driver': 'GV12', 'value': 0, 'uom': 25, 'name': 'Top 3 1-Hour Consumer'},
        {'driver': 'GV13', 'value': 0, 'uom': 119, 'name': 'Top 3 1-Hour Energy'},
        {'driver': 'GV14', 'value': 0, 'uom': 25, 'name': 'Top 1 1-Day Consumer'},
        {'driver': 'GV15', 'value': 0, 'uom': 119, 'name': 'Top 1 1-Day Energy'},
        {'driver': 'GV16', 'value': 0, 'uom': 25, 'name': 'Top 2 1-Day Consumer'},
        {'driver': 'GV17', 'value': 0, 'uom': 119, 'name': 'Top 2 1-Day Energy'},
        {'driver': 'GV18', 'value': 0, 'uom': 25, 'name': 'Top 3 1-Day Consumer'},
        {'driver': 'GV19', 'value': 0, 'uom': 119, 'name': 'Top 3 1-Day Energy'},
        {'driver': 'GV20', 'value': 0, 'uom': 151, 'name': 'Summary Measurement Time'},
    ]

