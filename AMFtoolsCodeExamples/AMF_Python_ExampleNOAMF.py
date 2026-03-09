import serial
import time


class AMF:

    # %%Define constants and commands
    # %%% CONSTANTS   
    CONNECTION_PARAMS = {'baudrate': 9600,
                         'timeout': 1000}
    
    POLLING_PERIODE = 0.05

    START_COMMAND = '/'
    END_COMMAND = '\r'

    START_ANSWER = '/'
    MASTER_ADDRESS = '0'
    END_ANSWER = '\x03\r\n'

    NO_R_REQUIRED = ['?', '!', 'H', 'T', 'Q','X','$','%','#','&','*']

    ERROR_CODES = {'@': [0, 'No Error'],
                   "`": [0, 'No Error'],
                   'A': [1, 'Initialization'],
                   'B': [2, 'Invalid command'],
                   'C': [3, 'Invalid operand'],
                   'D': [4, 'Missing trailing [R]'],
                   'G': [7, 'Device not initialized'],
                   'H': [8, 'Internal failure (valve)'],
                   'I': [9, 'Plunger overload'],
                   'J': [10, 'Valve overload'],
                   'N': [14, 'A/D converter failure'],
                   'O': [15, 'Command overflow'], }

    STATUS_CODES = {'255': [255, 'Busy', 'Valve currently executing an instruction.'],
                    '000': [0, 'Done', 'Valve available for next instruction.'],
                    '128': [128, 'Unknown command', 'Check that the command is written properly'],
                    '144': [144, 'Not homed', 'You forgot the homing! Otherwise, check that you have the right port configuration and try again.'],
                    '145': [145, 'Move out of range', 'You’re probably trying to do a relative positioning and are too close to the limits.'],
                    '146': [146, 'Speed out of range', 'Check the speed that you’re trying to go at.'],
                    '224': [224, 'Blocked', 'Something prevented the valve to move.'],
                    '225': [225, 'Sensor error', 'Unable to read position sensor. This probably means that the cable is disconnected.'],
                    '226': [226, 'Missing main reference', ('Unable to find the valve’s main reference magnet '
                                                            'during homing. This can mean that a reference magnet '
                                                            'of the valve is bad/missing or that the motor is '
                                                            'blocked during homing. Please also check motor '
                                                            'cables and crimp.')],
                    '227': [227, 'Missing reference', ('Unable to find a valve’s reference magnet during '
                                                       'homing. Please check that you have the correct valve '
                                                       'number configuration with command "/1?801". If '
                                                       'not, change it according to the valve you are working '
                                                       'with. This can also mean that a reference magnet of '
                                                       'the valve is bad/missing or that the motor is blocked '
                                                       'during homing.')],
                    '228': [228, 'Bad reference polarity', ('One of the magnets of the reference valve has a bad '
                                                            'polarity. Please check that you have the correct valve '
                                                            'number configuration with command "/1?801". If '
                                                            'not, change it according to the valve you are working '
                                                            'with. This can also mean that a reference magnet has '
                                                            'been assembled in the wrong orientation in the valve.')],
                    }

    # %%% COMMANDS
    # %%%% Configuration Commands
    SET_ADDRESS = '@ADDR='              # 1-9 or A-E, 1 by default
    SET_ANSWER_MODE = '!50'             # Synchronous = 0, Asynchronous = 1, Asynchronous + counter = 2, 0 by default
    SET_VALVE_CONFIGURATION = '!80'     # 4, 6, 8, 10 or 12 valve positions, 6 by default
    RESET_VALVE_COUNTER = '!17'
    SLOW_MODE = '-'                     # RVMFS only
    FAST_MODE = '+'                     # RVMFS only
    ACTIVATE_RS232 = '@RS232'           # Activated by default
    ACTIVATE_RS485 = '@RS485F'
    
    # Plunger command
    SET_PLUNGER_FORCE = '!30'           # 0,1,2 or 3 (0 = high and 3 = low force), 3 by default
    SET_PEAK_SPEED = 'V'                # 0-1600 pulses/s, 150 by default
    SET_ACCELERATION_RATE = 'L'         # 100-59'590 pulses/s², 1557 by default
    SET_DECELERATION_RATE = 'l'         # 100-59'590 pulses/s², 59'590 by default
    SET_SCALLING = 'N'                      # 0 or 1 (0 = 0.01 mm resolution, 1 = 0.00125mm resolution), 0 by default
    
    # %%%% Control Commands
    EXECUTE = 'R'
    REEXECUTE = 'X'
    REPEAT = 'G'                        # 0-60'000, 0 by default = loop forever
    REPEAT_SEQUENCE_START = 'g'
    DELAY = 'M'                         # 0-86'400'000 milliseconds
    HALT = 'H'                          # Pause the sequence AFTER finishng the current move
    HARD_STOP = 'T'                     # Interrupt the current move and supress it from the sequence
    POWER_OFF = '@POWEROFF'             # Shut down the pump

    # %%%% Initialization Commands
    HOME = 'Z'
    HOME2 = 'Y'

    # %%%% Valve Commands
    SWITCH_SHORTEST_FORCE = 'B'
    SWITCH_SHORTEST = 'b'

    SWITCH_CLOCKWISE_FORCE = 'I'
    SWITCH_CLOCKWISE = 'i'

    SWITCH_COUNTERCLOCKWISE_FORCE = 'O'
    SWITCH_COUNTERCLOCKWISE = 'o'
    
    # %%%% Plunger Commands
    ABSOLUTE_POSITION = 'A'             # 0-3000 with N=0, 0-24'000 with N=1
    ABSOLUTE_POSITION2 = 'a'            
    
    RELATIVE_PICKUP = 'P'               # 0-3000 with N=0, 0-24'000 with N=1
    RELATIVE_PICKUP2 = 'p'
    
    RELATIVE_DISPENSE = 'D'             # 0-3000 with N=0, 0-24'000 with N=1
    RELATIVE_DISPENSE2 = 'd'

    # %%%% Report Commands
    GET_STATUS = 'Q'
    GET_PLUNGER_POSITION = '?'
    GET_MAX_SPEED = '?2'
    GET_PLUNGER_ACTUAL_POSITION = '?4'
    GET_VALVE_POSITION = '?6'
    GET_VALVE_NUMBER_MOVES = '?17'
    GET_VALVE_NUMBER_MOVES_SINCE_LAST = '?18'
    GET_SPEED_MODE = '?19' 
    GET_FIRMWARE_CHECKSUM = '?20'
    GET_FIRMWARE_VERSIOM = '?23'
    GET_ACCELERATION = '?25'
    GET_ADDRESS = '?26'
    GET_DECELERATION = '?27'
    GET_SCALLING = '?28'
    GET_CONFIGURATION = '?76'
    GET_PLUNGER_CURRENT = '?300'        # x10 mA
    GET_ANSWER_MODE = '?500'
    GET_NUMBER_VALVE_POSITION = '?801'
    RESET = '$'
    GET_SUPPLY_VOLTAGE = '*'            # x0.1 V
    GET_UID = '?9000'
    IS_PUMP_INITIALIZED = '?9010'       # 1 = True
    GET_PUMP_STATUS_DETAILS = '?9100'
    GET_STATUS_DETAILS = '?9200'

    # %% Functions

    def __init__(self, port: str, config: int = 6, address = 1, SPM: bool = 0, mode: int = 0): 
        '''Initialize stage for the spezified degree of freedom'''
        self.port = port
        self.config = config    #number of ports of the valve
        self.address = address
        self.mode = mode
        self.SPM = SPM
        
        if self.mode == 2:
            self.POLLING_PERIODE = 1.5
        else:
            self.POLLING_PERIODE = 0.05
        
        self.positions = range(1, self.config+1)

        self.connected = False
        self.connect()
        
        self._bare_send_and_receive(self.SET_ADDRESS, self.address)
        self._bare_send_and_receive(self.SET_ANSWER_MODE, self.mode)
        self._bare_send_and_receive(self.SET_VALVE_CONFIGURATION, self.config)
        
        self.home()
        
        
    def set_plunger_force_and_scalling(self, force: int = 0, scalling: bool = 0):
        self.force = force
        self.scalling = scalling
        self._bare_send_and_receive(self.SET_PLUNGER_FORCE, self.force)
        self._bare_send_and_receive(self.SET_SCALLING, self.scalling)
        

    def connect(self):
        if self.connected:
            raise ValveError(f'An AMF valve or pump is already connected at "{self.port}".')

        try:
            self.ser = serial.Serial(self.port, **self.CONNECTION_PARAMS)
            self.connected = True
        except serial.serialutil.SerialException:
            raise ValveError(f'No AMF valve or pump found at "{self.port}".')


    def disconnect(self):
        if not self.connected:
            raise ValveError('No AMF valve or pump connected.')
        self.ser.close()
        self.connected = False
        print(f'{self.port} disconnected')


    def __del__(self):
        if self.connected:
            self.disconnect()


    def home(self):
        self._send_and_receive(self.HOME)
        print('Valve homing complete')
        if self.SPM:
            self.checkStatus_SPM()
            print('Pump homing complete')
   
        
    def switch(self, position: str, direction='ANY', force=False):
        if direction not in ['ANY', 'CW', 'CCW']:
            raise ValueError('Direction parameter must be one of: "ANY","CW","CCW"]')

        if position not in self.positions:
            raise ValueError(f'position must be in: {range(1, self.config)}')

        command_switch = {'ANY': 'SWITCH_SHORTEST',
                          'CW': 'SWITCH_CLOCKWISE',
                          'CCW': 'SWITCH_COUNTERCLOCKWISE'}
        cmd = command_switch.get(direction)

        if force:
            cmd += '_FORCE'

        self._send_and_receive(eval(f'self.{cmd}'), position)
        
        print(f'Valve in position {position}')
        
        
    def move(self, position: str, movement='ABS'):
         if movement not in ['ABS', 'DIS', 'PIC']:
             raise ValueError('Direction parameter must be one of: "ABS","DIS","PIC"]')

         command_move = {'ABS': 'ABSOLUTE_POSITION',
                         'DIS': 'RELATIVE_DISPENSE',
                         'PIC': 'RELATIVE_PICKUP'}
         
         cmd = command_move.get(movement)

         self._send_and_receive_SPM(eval(f'self.{cmd}'), position)


    def getValvePosition(self):
        return int(self._bare_send_and_receive(self.GET_VALVE_POSITION))


    def _send_and_receive(self, command: str, parameter: str = None) -> str:
        data = self._bare_send_and_receive(command=command, parameter=parameter)
        self.checkStatus()
        return data
    
    
    def _send_and_receive_SPM(self, command: str, parameter: str = None) -> str:
        data = self._bare_send_and_receive(command=command, parameter=parameter)
        self.checkStatus_SPM()
        return data


    def _bare_send_and_receive(self, command: str, parameter: str = None) -> str:
        """Send a command, get a response back and return the response. (No Status check)"""
        if not self.connected:
            raise ValveError('No AMF valve is connected.')

        original_command = command
          
        command = self.START_COMMAND + str(self.address) + original_command

        # format the command if it has some parameter
        if parameter is not None:
            command = command + str(parameter)

        if original_command[0] not in self.NO_R_REQUIRED:
            command = command + self.EXECUTE

        command = command + self.END_COMMAND

        self.ser.write(data=command.encode())
        error, data = self._read()
        self._checkError(error)

        return data


    def _read(self):
        response = self.ser.read_until(self.END_ANSWER.encode()).decode('utf-8')
        #print(response)
        if self.mode == 2 and response[2] == '`' and len(response) > 2:
            if response[3] != 0:
                if response[-len(self.END_ANSWER):] == self.END_ANSWER:
                    response = response[:-len(self.END_ANSWER)]
                        
                error = self.ERROR_CODES[response[2].upper()]
                self.counter = response[3:]
                data = '0'
                return error, data
            else:
                response = response[2:]
        else: 
            response = response[2:]

        if response[-len(self.END_ANSWER):] == self.END_ANSWER:
            response = response[:-len(self.END_ANSWER)]

        error = self.ERROR_CODES[response[0].upper()]
        data = response[1:]

        return error, data


    def checkStatus(self):
        busy = True
        status = '255'
        while busy:
            if status == '0':
                busy = False
            else:
                time.sleep(self.POLLING_PERIODE)
            
            self.ser.reset_input_buffer()
            status = self._bare_send_and_receive(self.GET_STATUS_DETAILS)
            #print (f'status = {status}')
            if status not in ['0', '255', '', None]:
                raise ValveError(f'Bad Status: {self.STATUS_CODES.get(status)}')
                
    
    def checkStatus_SPM(self):
        busy = True
        status_pump = '255'
        while busy:
            if status_pump == '0':
                busy = False
            else:
                time.sleep(self.POLLING_PERIODE)
            
            self.ser.reset_input_buffer()
            status_pump = self._bare_send_and_receive(self.GET_PUMP_STATUS_DETAILS)
            #print (f'status_pump = {status_pump}')
            if status_pump not in ['0', '255', '', None]:
                raise ValveError(f'Bad Status: {self.STATUS_CODES.get(status_pump)}')


    def _checkError(self, error):
        code = error[0]

        if code == 0:
            return True
        raise ValveError(f'{error[0]}: {error[1]}')
        


class ValveError(Exception):
    '''Error class for AMF modules.

        Attributes:
          message -- explanation of the error
    '''

    def __init__(self, message):
        self.message = message

# %% Examples
# %%% RVM
RVM = AMF('COM4', 12) # Connect to an RVM on port COM4, with a 12 ports valve and home the valve
time.sleep(1)
RVM.switch(10)
time.sleep(1)
RVM.switch(6, 'CCW')
time.sleep(1)
RVM.switch(12, 'CW')
time.sleep(1)

print(RVM._send_and_receive(RVM.GET_STATUS_DETAILS))
RVM.disconnect()

# %%% SPM / LSPOne

LSP = AMF('COM9', 6, 1, 1) # Connect to an SPM on port COM9, with a 6 ports valve, gives address 1 to the SPM and home the SPM
LSP.move(250)
LSP.switch(3, 'CW')
LSP.move(1500, 'PIC')
LSP.switch(5, 'CCW')
LSP.move(1000, 'DIS')
LSP.disconnect()

