import sys
import time 
import traceback
import requests
import json

from udiSpanPanelNode import udiSpanPanelNode
from SpanMqttManager import SpanMqttManager
from dynamic_profile import dynamic_profile_payload
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
    Interface = udi_interface.Interface

except ImportError:
    import logging
    logging.basicConfig(level=30)


VERSION = '1.1.1'
class SPANController(udi_interface.Node):
    from  udiLib import node_queue, wait_for_node_done, random_string, mask2key, heartbeat, bool2ISY, my_setDriver

    def __init__(self, polyglot, primary, address, name):
        super(SPANController, self).__init__(polyglot, primary, address, name )

        self.poly = polyglot
        logging.info(f'_init_ SPAN Controller ver {VERSION} ')
        self.ISYforced = False
        self.name = name
        self.primary = primary
        self.address = address
        self.name = name
        self.config_done = False
        self.initialized = False
        self.customParam_done = False
        self.n_queue = []
        self.span_panel = {}
        self.span_ip_list = []
        self.span_passphrases = []
        self.battery_backup = False
        self.hb = 0
        self.mqtt_manager = SpanMqttManager(
            min_update_interval=30.0,
            power_threshold_w=15.0,
            heartbeat_interval=900.0,
        )
        self.mqtt_manager.start()

        self.customParameters = Custom(self.poly, 'customparams')
        self.customData = Custom(self.poly, 'customdata')
        self.Notices = Custom(self.poly, 'notices')
       
        logging.debug('before subscribe')
        self.poly.subscribe(self.poly.STOP, self.stop)
        self.poly.subscribe(self.poly.CUSTOMPARAMS, self.customParamsHandler)
        self.poly.subscribe(self.poly.CUSTOMDATA, self.customDataHandler) 
        self.poly.subscribe(self.poly.CONFIGDONE, self.configDoneHandler)
        self.poly.subscribe(self.poly.ADDNODEDONE, self.node_queue)        
        self.poly.subscribe(self.poly.LOGLEVEL, self.handleLevelChange)
        self.poly.subscribe(self.poly.NOTICES, self.handleNotices)
        self.poly.subscribe(self.poly.POLL, self.systemPoll)
        self.poly.subscribe(self.poly.START, self.start, 'controller')

        #logging.debug('self.address : ' + str(self.address))
        #logging.debug('self.name :' + str(self.name))
        self.hb = 0

        self.poly.Notices.clear()
        self.nodeDefineDone = False
        self.longPollCountMissed = 0
        self.poly.ready()
        logging.debug('Controller init DONE')        
        
        self.poly.addNode(self)
        self.wait_for_node_done(self.address)
        time.sleep(0.1)
        
        self.node = self.poly.getNode(self.address) or self
        logging.debug('Node info: {}'.format(self.node))
        self.my_setDriver('ST', 1)
        logging.debug('finish Init ')
        
    def _profiles_match(self, current_profile, expected_profile) -> bool:
        if not isinstance(current_profile, dict) or not isinstance(expected_profile, dict):
            return False
        return all(
            current_profile.get(k, []) == expected_profile.get(k, [])
            for k in ("editors", "nodedefs", "linkdefs")
        )

    def _update_dynamic_profile(self, wait_response: bool = False) -> None:
        updater = getattr(self.poly, 'updateJsonProfile', None)
        if not callable(updater):
            logging.info('updateJsonProfile is not available on this interface; falling back to updateProfile')
            try:
                self.poly.updateProfile()
            except Exception as e:
                logging.warning(f'Static profile update failed or not supported: {e}')
            return

        payload = dynamic_profile_payload(VERSION)

        getter = getattr(self.poly, 'getJsonProfile', None)
        if callable(getter):
            try:
                current = getter({'waitResponse': False})
                if self._profiles_match(current, payload):
                    logging.info('Dynamic profile already up to date, skipping publish')
                    return
            except Exception:
                try:
                    current = getter()
                    if self._profiles_match(current, payload):
                        logging.info('Dynamic profile already up to date, skipping publish')
                        return
                except Exception as err:
                    logging.warning(f'Unable to read existing profile: {err}')

        try:
            updater(payload, {'waitResponse': wait_response})
            logging.info('Dynamic profile updated successfully via PG3x updateJsonProfile')
            if hasattr(self.poly, 'Notices') and hasattr(self.poly.Notices, 'delete'):
                try:
                    self.poly.Notices.delete('profile')
                except Exception:
                    pass
        except TypeError:
            try:
                updater(payload)
                logging.info('Dynamic profile updated successfully via PG3x updateJsonProfile (no options)')
                if hasattr(self.poly, 'Notices') and hasattr(self.poly.Notices, 'delete'):
                    try:
                        self.poly.Notices.delete('profile')
                    except Exception:
                        pass
            except Exception as e:
                logging.exception(f'Dynamic profile publish failed: {e}')
        except Exception as e:
            logging.exception(f'Dynamic profile update failed: {e}')
            if hasattr(self.poly, 'Notices') and hasattr(self.poly.Notices, '__setitem__'):
                try:
                    self.poly.Notices['profile'] = f'Dynamic profile update failed: {e}'
                except Exception:
                    pass
        
    
    def customDataHandler(self, Data):
        logging.debug('customDataHandler')
        self.customData.load(Data)
        #logging.debug('handleData load - {}'.format(self.customData))
    
 
    def check_config(self):
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.config_done= True


    def configDoneHandler(self):
        logging.debug('configDoneHandler - config_done')
        # We use this to discover devices, or ask to authenticate if user has not already done so
        self.poly.Notices.clear()
        self.nodes_in_db = self.poly.getNodesFromDb()
        self.config_done= True

    def handleLevelChange(self, level):
        logging.info('New log level: {}'.format(level))

    def handleNotices(self, level):
        logging.info('handleNotices:')

    def customParamsHandler(self, userParams):
        self.customParameters.load(userParams)
        #logging.debug('customParamsHandler called {}'.format(userParams))

        oauthSettingsUpdate = {}
        #oauthSettingsUpdate['parameters'] = {}
        oauthSettingsUpdate['token_parameters'] = {}
        # Example for a boolean field

        if 'LOCAL_IP_ADDRESSES' in self.customParameters:
            ipstring = self.customParameters['LOCAL_IP_ADDRESSES']
            if ipstring is not None and ipstring != 'x.x.x.x':
                self.span_ip_list = ipstring.split()
                self.NBR_PANELS = len(self.span_ip_list)
                #oauthSettingsUpdate['client_secret'] = self.customParameters['clientSecret']
                #secret_ok = True
        else:
            logging.warning('No LOCAL_IP_ADDRESSES found')
            self.customParameters['LOCAL_IP_ADDRESSES'] = 'enter list of LOCAL_IP_ADDRESSES (one per panel)'
            self.span_ip_list = []

        if 'BACKUP_BATTERY' in self.customParameters:
            battery_val = self.customParameters['BACKUP_BATTERY']
            if battery_val is not None and battery_val != 'TRUE/FALSE' and len(battery_val) > 0:
                self.battery_backup = battery_val[0].upper() == 'T'
                #oauthSettingsUpdate['client_secret'] = self.customParameters['clientSecret']
                #secret_ok = True
        else:
            logging.warning('No BACKUP_BATTERY found')
            self.customParameters['BACKUP_BATTERY'] = 'TRUE/FALSE'
            self.battery_backup = False

        self.span_passphrases = []
        if 'PANEL_PASSPHRASES' in self.customParameters:
            passphrase_str = self.customParameters['PANEL_PASSPHRASES']
            if passphrase_str and passphrase_str not in ('enter list of passphrases', 'x.x.x.x'):
                self.span_passphrases = passphrase_str.split()
        elif 'PANEL_PASSPHRASE' in self.customParameters:
            passphrase_str = self.customParameters['PANEL_PASSPHRASE']
            if passphrase_str and passphrase_str not in ('enter passphrase', 'x.x.x.x'):
                self.span_passphrases = [passphrase_str]
        else:
            logging.info('No PANEL_PASSPHRASES found')
            self.customParameters['PANEL_PASSPHRASES'] = 'enter list of passphrases'
        logging.debug('customParamsHandler finish ')
        self.customParam_done = True



    def addNodeDoneHandler(self, node):
        pass
        # We will automatically query the device after discovery
        #controller.addNodeDoneHandler(node)

    def registerSpanPanel(self, ipAddress, uid):
        #logging.debug(f'registerSpanPanel ({ipAddress}) , ({uid})')
        accessToken = None
        try:       

            headers = {'Content-Type': 'application/json',
                       'Accept': 'application/json'}
            data ={
                    'name':'udiSPAN-'+str(uid),
                    'description':'UDI integration of SpanIO panels'
                }
    
            completeUrl = f'http://{ipAddress}/api/v1/auth/register'

            response = requests.post(completeUrl, headers=headers, json=data, timeout=10)
            #logging.debug(f'response {response} test {response.text}')

            if response.status_code == 200:
                res = response.json()
                #logging.debug(f'res {res}')
                if isinstance(res, dict):
                    accessToken = res.get('accessToken')
            else:
                logging.warning(f'registerSpanPanel ({ipAddress}) returned status {response.status_code}')
                return(None)
            #logging.debug(f'AccessToken {accessToken}')
            return(accessToken)   
        except Exception as e:
            logging.warning(f'registerSpanPanel ({ipAddress}) exception: {e}')
            return(None)


    def start(self):
        site_string = ''
        assigned_addresses = ['controller']
        logging.debug('start SPAN')
        while not self.customParam_done or not self.config_done:
            logging.info('Waiting for node to initialize')
            #logging.debug(' 1 2: {} {}'.format(self.customParam_done , self.config_done))
            time.sleep(1)
        #logging.debug('access {} {}'.format(self.local_access_enabled, self.cloud_access_enabled))
        self._update_dynamic_profile()
        
        if 'uid' not in self.customData.keys():
            uid = self.random_string(16)
            self.customData['uid']= uid
        else:
            uid = self.customData['uid']
        self.my_setDriver('GV1', len(self.span_ip_list))
        for indx, IPaddress in enumerate(self.span_ip_list):
            #self.span_panel[indx]= SpanAccess(IPaddress)    
            token = None
            tempstr = IPaddress
            tempstr = tempstr.replace('.','')
            tempstr= tempstr[-14:]
            address = self.poly.getValidAddress(tempstr)

            nodename = 'SPAN '+str(IPaddress)
            passphrase = self.span_passphrases[indx] if indx < len(self.span_passphrases) else None

            if IPaddress in self.customData.keys():
                token = self.customData[IPaddress]
            else:
                token = self.registerSpanPanel(IPaddress, uid)
                if token is not None:
                    self.customData[IPaddress] = token
                elif passphrase:
                    logging.info(f'Panel {IPaddress}: REST registration token not available, but MQTT passphrase is set. Proceeding with MQTT.')
                else:
                    logging.warning(f'Panel {IPaddress}: No REST token and no passphrase provided.')
                    self.poly.Notices['panel'] = f'Click Span Panel ({IPaddress}) door switch 3 times or enter PANEL_PASSPHRASES'

            self.poly.Notices.clear()

            logging.debug(f'Panel info : {address} , {nodename}')
            self.span_panel[IPaddress] = udiSpanPanelNode(
                self.poly, address, address, nodename, IPaddress, token, self.battery_backup,
                passphrase=passphrase, mqtt_manager=self.mqtt_manager
            )    
            # need to retrieve unique ID and Token and store in customData          
            
  
            assigned_addresses.append(address)
            time.sleep(0.2)
     
    
        while not self.config_done:
            time.sleep(5)
        
        logging.debug('Checking for existing nodes not used anymore: {}'.format(self.nodes_in_db))
        for node in (self.nodes_in_db or []):
            #logging.debug('Scanning db for extra nodes : {}'.format(node))
            if isinstance(node, dict) and node.get('primaryNode') not in assigned_addresses:
                logging.debug('Removing node : {} {}'.format(node.get('name'), node))
                self.poly.delNode(node['address'])

        self.updateISYdrivers()
        self.initialized = True
        #time.sleep(1)
    #def handleNotices(self):
    #    logging.debug('handleNotices')

   

    def stop(self):
        #self.removeNoticesAll()
        logging.debug('stop - Cleaning up')
        if hasattr(self, 'mqtt_manager') and self.mqtt_manager:
            try:
                self.mqtt_manager.stop()
            except Exception as e:
                logging.error(f'Error stopping MQTT manager: {e}')

        for panel in self.span_panel.values():
            if panel and hasattr(panel, 'stop'):
                try:
                    panel.stop()
                except Exception as e:
                    logging.error(f'Error stopping panel node: {e}')

        self.poly.Notices.clear()

        self.my_setDriver('ST', 0 )
        self.poly.stop()
    

        
    def systemPoll(self, pollList):
        logging.info('systemPoll {}'.format(pollList))
        self.heartbeat()
        '''
        for indx, node_adr in enumerate(self.span_ip_list):
            node_adr.update_data()
        if self.initialized:    
            if 'longPoll' in pollList:
                pass
                #self.longPoll()
            elif 'shortPoll' in pollList: #and 'longPoll' not in pollList:
                self.shortPoll()
        else:
            logging.info('Waiting for system/nodes to initialize')
        '''

    def node_ready(self):
        logging.debug(' main node ready {} '.format(self.initialized ))
        return(self.initialized)
    

    def updateISYdrivers(self):
        #logging.debug('System updateISYdrivers')       
        pass


    def runCmd(self, command):
        logging.debug(f'UI Call runCmd received on controller {self.name} ({self.address}): {command}')
        super().runCmd(command)

    def ISYupdate (self, command=None):
        logging.info('ISYupdate called on controller')
        logging.debug(f'UI Call UPDATE (Update System Data) on controller {self.name} ({self.address}) with command={command}')
        for ip, panel in self.span_panel.items():
            if panel and hasattr(panel, 'ISYupdate'):
                logging.debug(f'UI Call UPDATE cascading to panel node {ip} ({panel.name})')
                panel.ISYupdate(command)
            else:
                logging.debug(f'Panel {ip} not available or has no ISYupdate method')
        logging.info(f'ISYupdate completed on controller across {len(self.span_panel)} panels')
        logging.debug(f'UI Call UPDATE completed on controller {self.name}')

    def query(self, command=None):
        logging.debug(f'UI Call QUERY received on controller {self.name} ({self.address}): command={command}')
        self.reportDrivers()
        logging.debug(f'UI Call QUERY completed on controller {self.name}')


    id = 'controller'
    commands = { 
        'UPDATE': ISYupdate,
        'QUERY': query,
    }
    drivers = [
        {'driver': 'ST', 'value': 0, 'uom': 25, 'name': 'Node Status'},
        {'driver': 'GV1', 'value': 0, 'uom': 56, 'name': 'Nbr Span Panels'},
    ]

if __name__ == "__main__":
    try:
        logging.info(f'Starting SpanIO Power Panel Controller version {VERSION}')
        polyglot = udi_interface.Interface([])
        polyglot.start(VERSION)
        #polyglot.updateProfile()
        #polyglot.setCustomParamsDoc()
        #polyglot.ready()
        SPANController(polyglot, 'controller', 'controller', 'SPANIO')

        polyglot.runForever()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(0)
    except Exception:
        logging.error(f"Error starting plugin: {traceback.format_exc()}")
        polyglot.stop()