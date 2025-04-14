import time
import serial

class DG645:
    def __init__(self, com_port : str, baud_rate = 9600):
        '''
        Class to control the Stanford DG645 Digital Delay box
        '''
        self.com_port = com_port
        self.baud_rate = 9600
        self.timeout = 1 #Seconds for serial communication timeout
        self.ser = serial.Serial(self.com_port, self.baud_rate, timeout=self.timeout) #Serial connection for rest of code


    #Commands designated by 3 letters require a * before them. Four letter commands do not need the star
    def trigger(self):
        '''
        This will arm the box in single shot triggered mode or send a trigger in single shot mode
        '''
        self.ser.write(b'*TRG\n')
        time.sleep(0.1)
        
    def returnToLocalMode(self):
        self.ser.write(b'UNLK\n')
        self.ser.write(b'LCAL\n')

        #self.ser.close()

    def setChannelDelay(self,channel,delay,delayRelativeTo = 0):
        '''
        Delay command works as "DLAY Channel,Channel toOffsetFrom,Delay Time(seconds)(e.g. 10e-6 is 10 microseconds)"
        Channel 2 is A, Channel 3 is B, etc... as shown in this table:
        0 T0
        1 T1
        2 A
        3 B
        4 C
        5 D
        6 E
        7 F
        8 G
        9 H
        '''
        delayCommand = f"DLAY {channel},{delayRelativeTo},{delay}\n"
        self.ser.write(delayCommand.encode())
    
    def disableChannel(self,bncPort):
        '''
        Sets Output width tozero for the following bncPorts:
        0 T0
        1 AB
        2 CD
        3 EF
        4 GH
        '''
        self.setChannelDelay(bncPort*2+1,0,bncPort*2)

    def setOutputTimeandWidth(self,bncPort,delay,width=10e-6):
        '''
        set a channel(1=a, 2=c) to output a square with width starting at delay based on BNC port
        '''
        self.setChannelDelay(bncPort*2,delay)
        self.setChannelDelay(bncPort*2+1,width,bncPort*2)
    



if __name__ == '__main__':
    com = "COM3"
    trigBox = DG645(com)
    trigBox.disableChannel(1)
    
    trigBox.trigger()
    trigBox.returnToLocalMode()
    #trigBox.setChannelDelay(2,1.234)
