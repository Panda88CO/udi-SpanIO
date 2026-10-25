#!/usr/bin/env python3

import time
from typing import Dict, Optional
from Spanlib import SpanAccess
from udiSpanCircuitNode import udiSpanCircuitNode
from udiSpanSummaryNode import udiSpanSummaryNode
from dynamic_profile import dynamic_profile_payload
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)



class udiSpanPanelNode(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, openClose2ISY, priority2ISY, mask2key, bool2ISY, round2ISY, my_setDriver, gridState2ISY, gridStatus2ISY

    def __init__(self, polyglot, primary, address, name, span_ipadr, token, battery, passphrase=None, mqtt_manager=None):
        super().__init__(polyglot, primary, address, name)
        logging.info(f'_init_ Span Panel Status Node {span_ipadr}')
        self.poly = polyglot
        self.span_ipadr = span_ipadr
        self.panel_node_adr = address
        self.token = token
        self.passphrase = passphrase
        self.mqtt_manager = mqtt_manager
        self.battery_backup = battery
        self.ISYforced = False
        self.node_ok = False
        self._starting = False
        self.address = address
        self.primary = primary
        self.name = name
        self.node = self
        self.circuit_access = {}
        self.summary_node = None
        self.circuit_index_map: Dict[str, int] = {}
        self.index_name_map: Dict[int, str] = {}
        self.span_panel = None
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.POLL, self.systemPoll)
        self.poly.addNode(self)
        self.wait_for_node_done(address)
        self.node = self.poly.getNode(address) or self
        time.sleep(0.1)
        
    def start(self):   
        logging.info(f'StartSpanIO Panel Node {self.name}')
        if self.node_ok:
            logging.debug('Span Panel Node already initialized')
            return
        self._starting = True
        if not hasattr(self, 'span_panel') or self.span_panel is None:
            self.span_panel = SpanAccess(self.span_ipadr, self.token, battery_backup=self.battery_backup, mqtt_manager=self.mqtt_manager)

        # Register panel with MQTT manager if available
        if self.mqtt_manager and self.mqtt_manager.is_available:
            logging.info(f'Registering panel {self.span_ipadr} with MQTT manager')
            self.mqtt_manager.add_panel(
                self.span_ipadr,
                passphrase=self.passphrase,
                on_snapshot_callback=self.on_mqtt_snapshot,
            )

        self.update_data()        
        created = self.create_subnodes()
        self.updateISYdrivers(force=True)
        if self.summary_node:
            self.summary_node.updateISYdrivers(force=True)
        if created and self.circuit_access:
            self.node_ok = True
            logging.info(f'Span Panel Node {self.name} successfully initialized with {len(self.circuit_access)} circuits')
        else:
            self.node_ok = False
            logging.warning(f'Span Panel Node {self.name} sub-node creation not completed; will retry on MQTT snapshot or next poll')
        self._starting = False

    def on_mqtt_snapshot(self, snapshot):
        logging.debug(f'on_mqtt_snapshot received for panel {self.name}')
        if not hasattr(self, 'span_panel') or self.span_panel is None:
            self.span_panel = SpanAccess(self.span_ipadr, self.token, battery_backup=self.battery_backup, mqtt_manager=self.mqtt_manager)
        self.span_panel.load_snapshot(snapshot)
        if not self.circuit_access:
            if self.create_subnodes() and self.circuit_access:
                self.node_ok = True
                logging.info(f'Subnodes created from MQTT snapshot for {self.name} ({len(self.circuit_access)} circuits)')
        self.updateISYdrivers(force=False)
        if self.summary_node:
            self.summary_node.updateISYdrivers(force=False)
        for circuit_node in self.circuit_access.values():
            circuit_node.updateISYdrivers(force=False)

    def is_mqtt_active(self) -> bool:
        if self.mqtt_manager and self.mqtt_manager.is_available:
            panel_state = self.mqtt_manager.panels.get(self.span_ipadr)
            if panel_state and panel_state.streaming and panel_state.connected:
                return True
        return False

    def publish_circuit_profile(self):
        try:
            updater = getattr(self.poly, 'updateJsonProfile', None)
            if callable(updater) and self.index_name_map:
                payload = dynamic_profile_payload('1.0.0', self.index_name_map)
                updater(payload)
                logging.info(f'Published dynamic CIRCUIT_LIST profile for {len(self.index_name_map)} circuits')
        except Exception as e:
            logging.warning(f'Error publishing dynamic circuit profile: {e}')

    def create_subnodes(self):
        if self.circuit_access:
            logging.debug(f'create_subnodes - {self.name}: already created ({len(self.circuit_access)} circuits)')
            return True
        logging.info(f'create_subnodes - {self.name}')
        if not hasattr(self, 'span_panel') or self.span_panel is None:
            self.span_panel = SpanAccess(self.span_ipadr, self.token, battery_backup=self.battery_backup, mqtt_manager=self.mqtt_manager)
        cached_circuits = self.span_panel.span_data.get('circuit_info')
        if isinstance(cached_circuits, dict) and cached_circuits:
            code, self.circuits = 200, cached_circuits
        else:
            code, self.circuits = self.span_panel.getSpanCircuitsInfo()
        #logging.debug(f'Panel {self.span_ipadr} Circuits info: {code} , {self.circuits }')            
        if code == 200 and isinstance(self.circuits, dict) and self.circuits:
            # Build 1-based index mapping for UOM 25 CIRCUIT_LIST
            self.circuit_index_map = {}
            self.index_name_map = {}
            for idx, (cid, cdata) in enumerate(self.circuits.items(), start=1):
                cname = cdata.get('name', str(cid)) if isinstance(cdata, dict) else str(cid)
                self.circuit_index_map[str(cid)] = idx
                self.index_name_map[idx] = cname

            # Push dynamic profile with discovered circuit names for UOM 25 CIRCUIT_LIST
            self.publish_circuit_profile()

            # Create the dedicated Power Summary Node
            sum_adr = self.poly.getValidAddress(self.panel_node_adr[:10] + '_sum')
            sum_name = f'{self.name} Summary'
            if self.summary_node is None:
                self.summary_node = udiSpanSummaryNode(
                    self.poly,
                    self.panel_node_adr,
                    sum_adr,
                    sum_name,
                    self.span_panel,
                    self.circuit_index_map,
                )
            else:
                self.summary_node.set_circuit_index_map(self.circuit_index_map)

            for circuit, circuit_data in self.circuits.items():
                if not isinstance(circuit_data, dict):
                    continue
                circuit_name = circuit_data.get('name', str(circuit))
                logging.info(f'adding circuit {circuit} = {circuit_name}')
                circuitADR = circuit[-14:]
                nodeaddress  = self.poly.getValidAddress(circuitADR)
                nodename = self.poly.getValidName(circuit_name)
                circuit_node = udiSpanCircuitNode(self.poly, self.panel_node_adr, nodeaddress, nodename, self.span_panel, str(circuit))
                self.circuit_access[circuit] = circuit_node
                self.poly.addNode(circuit_node)
                self.wait_for_node_done(nodeaddress)
                if not circuit_node.node_ok:
                    circuit_node.start()
                time.sleep(0.1)

            if self.summary_node and not self.summary_node.node_ok:
                self.summary_node.start()

            logging.info(f'Successfully created {len(self.circuit_access)} circuit sub-nodes and Summary Node for {self.name}')
            return bool(self.circuit_access)
        else:
            logging.warning(f'Failed to get circuit info for {self.name} (code={code}); will retry later')
            return False
                                                                
    def systemPoll(self, pollList):
        logging.info(f'systemPoll {self.span_ipadr}')
        if not self.circuit_access or not self.node_ok:
            logging.info(f'Subnodes missing for panel {self.name}; attempting creation in systemPoll')
            if not hasattr(self, 'span_panel') or self.span_panel is None:
                self.span_panel = SpanAccess(self.span_ipadr, self.token, battery_backup=self.battery_backup, mqtt_manager=self.mqtt_manager)
            if not self.is_mqtt_active():
                self.update_data()
            if self.create_subnodes() and self.circuit_access:
                self.node_ok = True
                self.updateISYdrivers(force=True)
                if self.summary_node:
                    self.summary_node.updateISYdrivers(force=True)
                for circuit_node in self.circuit_access.values():
                    circuit_node.updateISYdrivers(force=True)
                return

        if self.node_ok:
            if 'longPoll' in pollList:
                self.longPoll()
            elif 'shortPoll' in pollList and 'longPoll' not in pollList:
                self.shortPoll()
        else:
            logging.info('Waiting for system/nodes to initialize')

    def update_critical_data(self):
        logging.debug(f'update_critical_data {self.span_ipadr}')
        if hasattr(self, 'span_panel') and self.span_panel:
            self.span_panel.update_critical_span_data()

    def shortPoll(self):
        logging.debug(f'shortPoll {self.span_ipadr}')
        if not self.circuit_access:
            self.create_subnodes()
        if self.is_mqtt_active():
            logging.debug(f'shortPoll: MQTT active on {self.span_ipadr}, skipping REST poll')
            return
        self.update_critical_data()
        self.updateISYdrivers(force=True)
        if self.summary_node:
            self.summary_node.updateISYdrivers(force=True)
        for circuit_node in self.circuit_access.values():
            circuit_node.updateISYdrivers(force=True)

    def longPoll(self):
        logging.debug(f'longPoll {self.span_ipadr}')
        if not self.circuit_access:
            self.create_subnodes()
        if self.is_mqtt_active():
            logging.debug(f'longPoll: MQTT active on {self.span_ipadr}, saving accum data')
            if hasattr(self, 'span_panel') and self.span_panel:
                self.span_panel.save_accum_data()
            return
        self.update_data()   
        self.updateISYdrivers(force=True)
        if self.summary_node:
            self.summary_node.updateISYdrivers(force=True)
        for circuit_node in self.circuit_access.values():
            circuit_node.updateISYdrivers(force=True)

    def update_data(self):
        logging.debug(f'update_data {self.span_ipadr}')
        if hasattr(self, 'span_panel') and self.span_panel:
            self.span_panel.update_span_data()

    def stop(self):
        logging.debug('stop - Cleaning up')
        if self.summary_node and hasattr(self.summary_node, 'stop'):
            try:
                self.summary_node.stop()
            except Exception:
                pass
        if hasattr(self, 'span_panel') and self.span_panel:
            self.span_panel.save_accum_data()
            self.span_panel.close()
    
    def node_ready(self):
        return(self.node_ok)

    def updateISYdrivers(self, force=False):
        logging.debug(f'Span Panel updateISYdrivers force={force}')
        if not hasattr(self, 'span_panel') or self.span_panel is None:
            logging.warning(f'updateISYdrivers called on {self.name} before span_panel initialized')
            return
        grid_pwr = self.span_panel.get_instant_grid_power()
        self.my_setDriver('ST', round(grid_pwr, 1) if isinstance(grid_pwr, (int, float)) else None, 73, force=force)
        self.my_setDriver('GV0', self.openClose2ISY(self.span_panel.get_panel_door_state()), 25, force=force)
        self.my_setDriver('GV1', self.openClose2ISY(self.span_panel.get_main_panel_breaker_state()), 25, force=force)
        ft_pwr = self.span_panel.get_feedthrough_power()
        self.my_setDriver('GV2', round(ft_pwr, 1) if isinstance(ft_pwr, (int, float)) else None, 73, force=force)
        self.my_setDriver('GV3', self.gridState2ISY(self.span_panel.get_grid_state()), 25, force=force)
        self.my_setDriver('GV4', self.gridStatus2ISY(self.span_panel.get_dms_state()), 25, force=force)
        panel_time = self.span_panel.get_panel_update_time()
        if panel_time is not None:
            self.my_setDriver('GV5', panel_time, 151, force=force)
        if self.battery_backup:
            bat = self.span_panel.get_battery_percentage()
            self.my_setDriver('GV7', int(bat) if isinstance(bat, (int, float)) else None, 51, force=force)   
        else:
            self.my_setDriver('GV7', None, 25, force=force)

    def runCmd(self, command):
        logging.debug(f'UI Call runCmd received on panel {self.name} ({self.address}): command={command}')
        super().runCmd(command)

    def ISYupdate(self, command=None):
        logging.info(f'ISYupdate called for panel {self.name} ({self.span_ipadr})')
        logging.debug(f'UI Call UPDATE (Update Panels Data) on panel {self.name} ({self.address}): command={command}')
        if not self.circuit_access:
            logging.info(f'Subnodes missing in ISYupdate for {self.name}; attempting creation')
            logging.debug(f'UI Call UPDATE: attempting create_subnodes() because circuit_access is empty')
            if not hasattr(self, 'span_panel') or self.span_panel is None:
                self.span_panel = SpanAccess(self.span_ipadr, self.token, battery_backup=self.battery_backup, mqtt_manager=self.mqtt_manager)
            self.create_subnodes()
            if self.circuit_access:
                self.node_ok = True
                logging.debug(f'UI Call UPDATE: subnodes created successfully ({len(self.circuit_access)} circuits)')
            else:
                logging.debug('UI Call UPDATE: subnodes creation failed or panel unreachable')
        logging.debug(f'UI Call UPDATE: refreshing telemetry data for panel {self.name} ({self.span_ipadr})')
        if not self.is_mqtt_active():
            self.update_data()
        logging.debug(f'UI Call UPDATE: updating ISY drivers for panel {self.name}')
        self.updateISYdrivers(force=True)
        if self.summary_node:
            self.summary_node.updateISYdrivers(force=True)
        logging.debug(f'UI Call UPDATE: updating ISY drivers across {len(self.circuit_access)} circuit subnodes')
        for circuit_node in self.circuit_access.values():
            circuit_node.updateISYdrivers(force=True)
        logging.info(f'ISYupdate completed for panel {self.name}: updated panel and {len(self.circuit_access)} circuits')
        logging.debug(f'UI Call UPDATE finished for panel {self.name} ({self.address})')

    def query(self, command=None):
        logging.debug(f'UI Call QUERY received on panel {self.name} ({self.address}): command={command}')
        if not self.is_mqtt_active():
            self.update_data()
        self.updateISYdrivers(force=True)
        if self.summary_node:
            self.summary_node.updateISYdrivers(force=True)
        logging.debug(f'UI Call QUERY completed on panel {self.name}')

    id = 'spanpanel'
    commands = { 
        'UPDATE': ISYupdate,
        'QUERY': query,
    }
 
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 73, 'name': 'Instant Panel Power'},         
        {'driver': 'GV0', 'value': 0, 'uom': 25, 'name': 'Panel Door State'},       
        {'driver': 'GV1', 'value': 99, 'uom': 25, 'name': 'Main Panel Breaker State'},
        {'driver': 'GV2', 'value': 0, 'uom': 73, 'name': 'Instant Feedthrough Power'},  
        {'driver': 'GV3', 'value': 0, 'uom': 25, 'name': 'Grid State'}, 
        {'driver': 'GV4', 'value': 0, 'uom': 25, 'name': 'Grid Status'},  
        {'driver': 'GV5', 'value': 0, 'uom': 151, 'name': 'Panel Update Time'},  
        {'driver': 'GV7', 'value': 0, 'uom': 51, 'name': 'Backup Battery Capacity'},  
    ]
