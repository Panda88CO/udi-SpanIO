#!/usr/bin/env python3

import time
from Spanlib import SpanAccess
from udiSpanCircuitNode import udiSpanCircuitNode
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
except ImportError:
    import logging
    logging.basicConfig(level=30)



class udiSpanPanelNode(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, openClose2ISY, priority2ISY, mask2key, bool2ISY, round2ISY, my_setDriver, gridState2ISY, gridStatus2ISY

    def __init__(self, polyglot, primary, address, name, span_ipadr, token, battery):
        #super(teslaPWStatusNode, self).__init__(polyglot, primary, address, name)
        logging.info(f'_init_ Span Panel Status Node {span_ipadr}, {token}')
        self.poly = polyglot
        self.span_ipadr = span_ipadr
        self.panel_node_adr = address
        self.token = token
        self.battery_backup = battery
        self.ISYforced = False
        self.node_ok = False
        self.address = address
        self.primary = primary
        self.name = name
        self.node = self
        self.circuit_access = {}
        self.n_queue = []
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)
        self.poly.subscribe(self.poly.START, self.start, address)
        self.poly.subscribe(self.poly.POLL, self.systemPoll)
        self.poly.addNode(self)
        self.wait_for_node_done(address)
        self.node = self.poly.getNode(address) or self
        time.sleep(0.1)
        
    def start(self):   
        logging.debug('StartSpanIO Panel Node')
        if self.node_ok:
            logging.debug('Span Panel Node already initialized')
            return
        logging.info('Adding SPAN panel sub-nodes')
        self.span_panel = SpanAccess(self.span_ipadr, self.token)
        self.update_data()        
        self.create_subnodes()
        self.updateISYdrivers()
        self.node_ok = True


    def create_subnodes(self):
        logging.debug(f'create_subnodes - {self.name}')
        code, self.circuits = self.span_panel.getSpanCircuitsInfo()
        #logging.debug(f'Panel {self.span_ipadr} Circuits info: {code} , {self.circuits }')            
        if code == 200:
            for circuit in self.circuits:
                logging.info(f'adding circuit {circuit} = {self.circuits[circuit]["name"]}')
                circuitADR = circuit[-14:]
                nodeaddress  = self.poly.getValidAddress(circuitADR)
                nodename = self.poly.getValidName(self.circuits[circuit]['name'])
                circuit_node = udiSpanCircuitNode(self.poly, self.panel_node_adr, nodeaddress, nodename, self.span_panel, str(circuit))
                self.circuit_access[circuit] = circuit_node
                self.poly.addNode(circuit_node)
                self.wait_for_node_done(nodeaddress)
                if not circuit_node.node_ok:
                    circuit_node.start()
                time.sleep(0.1)
                                                                
    def systemPoll(self, pollList):
        logging.info(f'systemPoll {self.span_ipadr }')
        if self.node_ok:
            if 'longPoll' in pollList:
                #pass
                self.longPoll()
            elif 'shortPoll' in pollList and 'longPoll' not in pollList:
                self.shortPoll()
        else:
            logging.info('Waiting for system/nodes to initialize')

            #self.update_data()   
            #self.updateISYdrivers()
            #for circuit in self.circuit_access:
                #self.circuit_access[circuit].updateISYdrivers()



    def update_critical_data(self):
        logging.debug(f'update_critical_data {self.span_ipadr }')
        self.span_panel.update_critical_span_data()

    def shortPoll(self):
        logging.debug(f'shortPoll {self.span_ipadr }')
        self.update_critical_data()
        self.updateISYdrivers()

    def longPoll(self):
        logging.debug(f'longPoll {self.span_ipadr }')
        self.update_data()   
        self.updateISYdrivers()
        for circuit in self.circuit_access:
            self.circuit_access[circuit].updateISYdrivers()

    def update_data(self):
        self.span_panel.update_span_data()
                 

    def stop(self):
        logging.debug('stop - Cleaning up')
        if hasattr(self, 'span_panel') and self.span_panel:
            self.span_panel.save_accum_data()
    
    def node_ready(self):
        return(self.node_ok)




    def updateISYdrivers(self):
        logging.debug('Span Panel updateISYdrivers')
        #logging.debug(f'data: {self.span_panel.span_data}')
        self.my_setDriver('ST', self.openClose2ISY(self.span_panel.get_main_panel_breaker_state()), 25)
        self.my_setDriver('GV0', self.openClose2ISY(self.span_panel.get_panel_door_state()), 25)
        self.my_setDriver('GV1', round(self.span_panel.get_instant_grid_power(),1), 73)
        self.my_setDriver('GV2', round(self.span_panel.get_feedthrough_power(),1), 73)
        self.my_setDriver('GV3', self.gridState2ISY(self.span_panel.get_grid_state()), 25)
        self.my_setDriver('GV4', self.gridStatus2ISY(self.span_panel.get_dms_state()), 25)
        if self.battery_backup:
            self.my_setDriver('GV7', int(self.span_panel.get_battery_percentage()), 51 )   
        else:
            self.my_setDriver('GV7', None, 25 )


    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        #self.update_PW_data(self.site_id, 'all')
        self.update_data()
        self.updateISYdrivers()

 

    id = 'spanpanel'
    commands = { 'UPDATE': ISYupdate, 
                }
 
    drivers = [
            {'driver': 'ST', 'value': 99, 'uom': 25},  #online         
            {'driver': 'GV0', 'value': 0, 'uom': 25},       
            {'driver': 'GV1', 'value': 0, 'uom': 73},
            {'driver': 'GV2', 'value': 0, 'uom': 73},  
            {'driver': 'GV3', 'value': 0, 'uom': 25}, 
            {'driver': 'GV4', 'value': 0, 'uom': 25},  
            #{'driver': 'GV5', 'value': 0, 'uom': 33},  
            #{'driver': 'GV6', 'value': 0, 'uom': 33}, 
            {'driver': 'GV7', 'value': 0, 'uom': 51},  
                                          
            ]

    
