import logging
import serial
import fcntl

DEFAULT_CMD_CALLERID = 'AT+VCID=1'
READ_RING_TIMOUT = 10
READ_IDLE_TIMEOUT = None

_LOGGER = logging.getLogger("BasicModem")
#_LOGGER.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
# add ch to logger
_LOGGER.addHandler(ch)

# 'application' code
class BasicModem(object):
    
    STATE_IDLE = 'idle'
    STATE_RING = 'ring'
    STATE_CALLERID = 'callerid'
    STATE_INIT = 'init'
    STATE_FAILED = 'fail'

    #Initialize internal variables.
    def __init__(self, device, incomingcallback, logfile, loglevel):
        import threading
        self.device = device
        self.incomingcallnotificationfunc = incomingcallback
        self._state = self.STATE_INIT
        self.cmd_callerid = DEFAULT_CMD_CALLERID
        self.cmd_response = ''
        self.cmd_responselines = []
        self.cid_time = 0
        self.cid_name = ''
        self.cid_number = ''
        self.ser = None

        fh = logging.FileHandler(logfile)
        _LOGGER.addHandler(fh)
        _LOGGER.setLevel(loglevel)
        _LOGGER.info('Opening device %s', self.device)
        try:
            self.ser = serial.Serial(port=self.device)
        except serial.SerialException:
            _LOGGER.error('Unable to open device %s', self.device)
            self.ser = None
            self.state = self.STATE_FAILED
            self.incomingcallnotificationfunc(self.state)
            return
        fcntl.lockf(self.ser, fcntl.LOCK_EX | fcntl.LOCK_NB)
        threading.Thread(target=self._modem_sm, daemon=True).start()
        try:
            self.sendcmd('AT')
            if self.get_response() == '':
                _LOGGER.info('No response from modem on port %s', self.port)
                self.ser.close()
                self.ser = None
                return
            self.sendcmd(self.cmd_callerid)
            if self.get_response() in ['', 'ERROR']:
                _LOGGER.info('Error enabling caller id on modem.')
                self.ser.close()
                self.ser = None
                return
        except serial.SerialException:
            _LOGGER.error('Unable to communicate with modem on port %s',
                          self.port)
            self.ser = None
        #self.set_state(self.STATE_IDLE)

    def read(self, timeout=1.0):
        """read from modem port, return null string on timeout."""
        self.ser.timeout = timeout
        if self.ser is None:
            return ''
        return self.ser.readline()

    def write(self, cmd='AT'):
        """write string to modem, returns number of bytes written."""
        self.cmd_response = ''
        self.cmd_responselines = []
        if self.ser is None:
            return 0
        cmd += '\r\n'
        return self.ser.write(cmd.encode())

    def sendcmd(self, cmd='AT', timeout=1.0):
        _LOGGER.debug('Command Sent: %s', cmd)
        """send command, wait for response. returns response from modem."""
        import time
        if self.write(cmd):
            while self.get_response() == '' and timeout > 0:
                time.sleep(0.1)
                timeout -= 0.1
        return self.get_lines()

    def set_state(self, state):
        """Set the state."""
        self._state = state
        return

    @property
    def state(self):
        """Return the state of the device."""
        return self._state

    @property
    def get_cidname(self):
        """Return last collected caller id name field."""
        return self.cid_name

    @property
    def get_cidnumber(self):
        """Return last collected caller id number."""
        return self.cid_number

    @property
    def get_cidtime(self):
        """Returns time of last call."""
        return self.cid_time

    def get_response(self):
        """Return completion code from modem (OK, ERROR, null string)."""
        return self.cmd_response

    def get_lines(self):
        """Returns response from last modem command, including blank lines."""
        return self.cmd_responselines

    def close(self):
        """close modem port, exit worker thread."""
        if self.ser:
            self.ser.close()
            self.ser = None
        return

    def _modem_sm(self):
        """Handle modem response state machine."""
        import datetime
        self.incomingcallnotificationfunc(self.state)

        #read_timeout = READ_IDLE_TIMEOUT
        read_timeout = 1
        while self.ser:
            try:
                resp = self.read(read_timeout)
            except (serial.SerialException, SystemExit, TypeError):
                _LOGGER.error('Unable to read from port %s', self.port)
                break

            if self.state != self.STATE_IDLE and len(resp) == 0:
                read_timeout = READ_IDLE_TIMEOUT
                self.set_state(self.STATE_IDLE)
                self.incomingcallnotificationfunc(self.state)
                continue

            resp = resp.decode()
            resp = resp.strip('\r\n')
            if self.cmd_response == '':
                self.cmd_responselines.append(resp)
            _LOGGER.debug('mdm: %s', resp)

            if resp in ['OK', 'ERROR']:
                self.cmd_response = resp
                continue

            if resp in ['RING']:
                if self.state == self.STATE_IDLE:
                    self.cid_name = ''
                    self.cid_number = ''
                    self.cid_time = datetime.datetime.now()

                self.set_state(self.STATE_RING)
                self.incomingcallnotificationfunc(self.state)
                read_timeout = READ_RING_TIMOUT
                continue

            if len(resp) <= 4 or self.state == self.STATE_INIT or resp.find('=') == -1:
                continue

            read_timeout = READ_RING_TIMOUT
            cid_field, cid_data = resp.split('=')
            cid_field = cid_field.strip()
            cid_data = cid_data.strip()
            if cid_field in ['DATE']:
                self.cid_time = datetime.datetime.now()
                continue

            if cid_field in ['NMBR']:
                self.cid_number = cid_data

            if cid_field in ['NAME']:
                self.cid_name = cid_data


            if self.cid_name != '' and  self.cid_number != '':
                self.set_state(self.STATE_CALLERID)
                self.incomingcallnotificationfunc(self.state)
                self.cid_name = ''
                self.cid_number = ''
            
                try:
                    self.write(self.cmd_callerid)
                except serial.SerialException:
                    _LOGGER.error('Unable to write to port %s', self.port)
                    break
            continue

        self.set_state(self.STATE_FAILED)
        self.incomingcallnotificationfunc(self.state)
        _LOGGER.info('Exiting modem state machine')
        return
