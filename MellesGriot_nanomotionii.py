# -*- coding: utf-8 -*-
"""
UPDATED: 02-06-2020
DESCRIPTION:
    Read and write commands to Melles Griot Nanomotion II motor controller
    
"""
import serial as s
import time


class motor:   # create a motor class
         
    def comset(self,num): # set comport to different value
        self.COMport=str(num)
        self.ser=s.Serial('COM'+self.COMport,baudrate=19200) 
        self.ser.timeout=0.5
        self.ser.close()
        print('COM port changed to '+str(num))
        return
    
    def oport(self): #check if COM port is open and if not, open it
        if self.ser.isOpen()==True:
            print('COM Port is already open.')
        else:
           self.ser.open()
           #print('Opening COM'+str(self.COMport))
        return;   
    
    def sercomformat(self,command,*args): # provides template for all serial commands
      self.oport()  
      motorvals=''
      for values in args:
          motorvals += ','+str(values)
      cmd=command+motorvals+'\r\n'
      self.ser.write(cmd.encode())
      time.sleep(0.5)
      cmdsent= self.ser.read_until(b'\r\n').decode()[:-2]
      response= self.ser.read_until(b'\r\n').decode()[:-2]
      #the [:-2:] removes the last 2 indices of the string which includes the \r\n This is optimal value.
      self.ser.close()
      return cmdsent, response
    
    def controlID(self): # call controller info
        cmdsent,response=self.sercomformat('*IDN?')
        return cmdsent, response
    
    def readstat(self,motornum): # check status of nanomover
        cmdsent,response=self.sercomformat('RS',motornum)
        if response==str(motornum)+',LL':
           response='Hard retraction limit'
        elif response==str(motornum)+',RL':
           response='Hard extension limit'
        elif response==str(motornum)+',IP':
           response='Index pulse switch active, look up.'   
        elif response==str(motornum)+',AL':
           response='User-defined retraction limit'
        elif response==str(motornum)+',AR':
           response='User-defined extension limit'
        elif response==str(motornum)+',MV':
           response='Motor is moving'
        elif response==str(motornum)+',OK':
           response='Motor OK'
        elif response==str(motornum)+',PK':
           response='Motor is parked. Will not move unless unparked.'
        elif response==str(motornum)+',EN':
           response='Motor stall detected with encoder'
        elif response==str(motornum)+',ME':
           response='Last movement did not finish'
        elif response==str(motornum)+',RS':
           response='Controller has been reset'
        else:
           response='Unknown response from controller' 
           
        
        return cmdsent, response
    
    def runits(self,motornum): # read units used by nanomover
        cmdsent,response=self.sercomformat('RU',motornum)
        return cmdsent, response
    
    def rsysres(self, motornum): # read resolution of motor in current units
        cmdsent,response=self.sercomformat('RRES',motornum)
        return cmdsent, response
    
    def rposition(self, motornum): # read motor position
        cmdsent,response=self.sercomformat('RP',motornum)
        return cmdsent, response
    
    def rmotorstep(self, motornum): # read motor steps/revolution
        cmdsent,response=self.sercomformat('RSTP',motornum)
        return cmdsent, response
    
    def rleftabs(self, motornum): # read software left stop (min retraction)
        cmdsent,response=self.sercomformat('RAL',motornum)
        return cmdsent, response
    
    def rrightabs(self, motornum): # read software right stop (max extension)
        cmdsent,response=self.sercomformat('RAR',motornum)
        return cmdsent, response
    
    def rspeed(self, motornum): # read motor linear speed in units/s
        cmdsent,response=self.sercomformat('RV1',motornum)
        return cmdsent, response
    
    def reset(self, motornum): #reset motor parameters
        cmdsent,response=self.sercomformat('RES',motornum)
        return cmdsent, response
    
    def stop(self, motornum): # stops motor
        cmdsent,response=self.sercomformat('S',motornum)
        return cmdsent, response
    
    def park(self, motornum): # parks motor for shutdown
        cmdsent,response=self.sercomformat('P',motornum)
        return cmdsent, response
    
    def unpark(self, motornum): # unparks motor on startup
        cmdsent,response=self.sercomformat('U',motornum)
        return cmdsent, response
    
    def setposition(self, motornum, pos): # THIS DOESN'T MOVE MOTOR. It specifies position associated with current motor position
        cmdsent,response=self.sercomformat('WP',motornum, pos)
        return cmdsent, response
    
    def setunits(self, motornum, units): # allowed are: NM, MI(microns), MM, CM, UI(microinches), ML(mils), I(inches)
        cmdsent,response=self.sercomformat('WU',motornum, units)
        return cmdsent, response
    
    def setspeed(self, motornum, speed): # max allowed is 2.5mm/s
        cmdsent,response=self.sercomformat('WV1',motornum, speed)
        return cmdsent, response
    
    def setleftabs(self, motornum, leftstop): # write software left stop (min retraction)
        cmdsent,response=self.sercomformat('WAL',motornum, leftstop)
        return cmdsent, response
    
    def setrightabs(self, motornum, rightstop): # write software right stop (max extension)
        cmdsent,response=self.sercomformat('WAR',motornum, rightstop)
        return cmdsent, response
    
    def move(self, motornum, dist): # move motor relative distance. '+' extends, '-' retracts
        cmdsent,response=self.sercomformat('MR',motornum, dist)
        return cmdsent, response
    
    def moveto(self, motornum, pos): # move motor to specified position
        cmdsent,response=self.sercomformat('MA',motornum, pos)
        return cmdsent, response
    
    def breakser(self): # reset serial connection
        cmdsent,response=self.sercomformat('BREAK')
        return cmdsent, response
    
    def checkstat(self): # check if all received commands are complete
        cmdsent,response=self.sercomformat('*OPC?')
        if response=='1':
            response='All commands completed'
        else:
            response='Working or error'
        return cmdsent, response
    
    def checklostmot(self, motornum): # check value for lost motion compensation. '0' means LMC is disabled
        cmdsent,response=self.sercomformat('RLM',motornum)
        return cmdsent, response
    
    def setlostmot(self, motornum, val): # set amount of lost motion compensation in microns
        cmdsent,response=self.sercomformat('WLM',motornum, val)
        return cmdsent, response
    
if __name__ == "__main__":
    mot1 = motor()
    mot1.comset(5)
    print(mot1.setleftabs(2,-2))
    print("status",mot1.readstat(2))
    print("units",mot1.runits(2))
    print("left,right",mot1.rleftabs(2),mot1.rrightabs(2))
    print("Motor steps", mot1.rmotorstep(2))
    print("Motor position",mot1.rposition(2))
    mot1.unpark(2)
    mot1.setspeed(2, 1000)
    while True:
        print(mot1.move(2,float(input("move:"))))
        print("status",mot1.readstat(2))
        print("Motor position",mot1.rposition(2))