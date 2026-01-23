import sys
import time 
import traceback
import requests
import json

from udiSpanPanelNode import udiSpanPanelNode
try:
    import udi_interface
    logging = udi_interface.LOGGER
    Custom = udi_interface.Custom
    Interface = udi_interface.Interface

except ImportError:
    import logging
    logging.basicConfig(level=30)


VERSION = '0.1.15'
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
        self.battery_backup = False
        self.hb = 0

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

        #logging.debug('self.address : ' + str(self.address))
        #logging.debug('self.name :' + str(self.name))
        self.hb = 0

        self.poly.Notices.clear()
        self.nodeDefineDone = False
        self.longPollCountMissed = 0
        self.poly.ready()
        logging.debug('Controller init DONE')        
        
        self.poly.addNode(self)
        self.wait_for_node_done()
        
        self.node = self.poly.getNode(self.address)
        logging.debug('Node info: {}'.format(self.node))
        self.my_setDriver('ST', 1)
        logging.debug('Calling start')       
        self.poly.subscribe(self.poly.START, self.start, 'controller')
        self.poly.updateProfile()
        logging.debug('finish Init ')
        
    
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
            if self.customParameters['LOCAL_IP_ADDRESSES'] != 'x.x.x.x':
                ipstring = self.customParameters['LOCAL_IP_ADDRESSES']
                self.span_ip_list= ipstring.split()
                self.NBR_PANELS = len(self.span_ip_list)
                #oauthSettingsUpdate['client_secret'] = self.customParameters['clientSecret']
                #secret_ok = True
        else:
            logging.warning('No LOCAL_IP_ADDRESS found')
            self.customParameters['LOCAL_IP_ADDRESS'] = 'enter list of LOCAL_IP_ADDRESSES (one per panel)'
            self.span_ip_list = []
        logging.debug('customParamsHandler finish ')
        self.customParam_done = True

        if 'BACKUP_BATTERY' in self.customParameters:
            if self.customParameters['BACKUP_BATTERY'] != 'TRUE/FALSE':
                self.battery_backup =  self.customParameters['BACKUP_BATTERY'][0].upper() == 'T'
                #oauthSettingsUpdate['client_secret'] = self.customParameters['clientSecret']
                #secret_ok = True
        else:
            logging.warning('No BACKUP_BATTERY found')
            self.customParameters['BACKUP_BATTERY'] = 'TRUE/FALSE'
            self.battery_backup = False
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
                       'accept': 'application/json'}
            data ={
                    'name':'udiSPAN-'+str(uid),
                    'description':'UDI integration of SpanIO panels'
                }
    
            completeUrl = f'http://{ipAddress}/api/v1/auth/register'

            response = requests.post(completeUrl, headers=headers, json=data)
            #logging.debug(f'response {response} test {response.text}')

            if response.status_code == 200:
                res =  response.json()
                #logging.debug(f'res {res}')
                accessToken = res['accessToken']
            else:
                return(None)
            #logging.debug(f'AccessToken {accessToken}')
            return(accessToken)   
        except Exception as e:
            logging.debug(f'exception {e}')
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
            if IPaddress in self.customData.keys():
                token = self.customData[IPaddress]
            else:
                while token == None:
                    #logging.debug(f'Add panel {IPaddress}  {uid}')
                    token = self.registerSpanPanel(IPaddress, uid)
                    if token != None:
                        self.customData[IPaddress]= token
                    else:
                        self.poly.Notices['panel'] = 'Click Span Panel door switch 3 times to register Panels'
                        time.sleep(10)
            self.poly.Notices.clear()

            logging.debug(f'Panel info : {address} , {nodename}')
            self.span_panel[IPaddress] = udiSpanPanelNode(self.poly, address, address, nodename, IPaddress, token, self.battery_backup)    
            # need to retrieve unique ID and Token and store in customData          
            
  
            assigned_addresses.append(address)
     
    
        while not self.config_done:
            time.sleep(5)
        
        logging.debug('Checking for existing nodes not used anymore: {}'.format(self.nodes_in_db))
        for nde in range(0, len(self.nodes_in_db)):
            node = self.nodes_in_db[nde]
            #logging.debug('Scanning db for extra nodes : {}'.format(node))
            if node['primaryNode'] not in assigned_addresses:
                logging.debug('Removing node : {} {}'.format(node['name'], node))
                self.poly.delNode(node['address'])

        self.updateISYdrivers()
        self.initialized = True
        #time.sleep(1)
    #def handleNotices(self):
    #    logging.debug('handleNotices')

   

    def stop(self):
        #self.removeNoticesAll()

        self.poly.Notices.clear()

        self.node.setDriver('ST', 0 )
        self.poly.stop()
        logging.debug('stop - Cleaning up')
    

        
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


    def ISYupdate (self, command):
        logging.debug('ISY-update called')
        self.shortPoll()


    id = 'controller'
    commands = { 'UPDATE': ISYupdate }
    drivers = [
            {'driver': 'ST', 'value':0, 'uom':25},
            {'driver': 'GV1', 'value':0, 'uom':56},
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