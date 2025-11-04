'''
Purpose of the module
This is module connecte to the plaxis remote server by using following inputs.
1. Plaxis2D input program path in the locat machine
2. local host port no for plaxis 2D input program
3. local host port no for plaxis 2D output program
4. Password of the remote server
'''


from plxscripting.easy import *
import subprocess, time


class Plaxis2D:

    def __init__(self, Plaxis2DInput_Path=None,PORT_i=0,PORT_o=0,PASSWORD=None):
        self.Plaxis2DInput_Path = Plaxis2DInput_Path
        self.PORT_i = PORT_i
        self.PORT_o = PORT_o
        self.PASSWORD = PASSWORD

    def OpenPlaxis2D_input (self):
        # Start the PLAXIS remote scripting service.
        subprocess.Popen([self.Plaxis2DInput_Path, f'--AppServerPassword={self.PASSWORD}', f'--AppServerPort={self.PORT_i}'], shell=False) 
    
        # Wait for PLAXIS to boot before sending commands to the scripting service.
        time.sleep(5) 

        # Start the scripting server.
        '''
        s_i = object representing the PLAXIS input application
        g_i = global object of the current open Plaxis model in input (Plaxis2D input program)

        '''
        self.s_i, self.g_i = new_server('localhost', self.PORT_i, password=self.PASSWORD)

        return (self.s_i, self.g_i)
        

    
    def OpenPlaxis2D_output (self):
        '''
        s_o = object representing the PLAXIS output application
        g_o = global object of the current open Plaxis model in output (Plaxis2D output program)

        '''
        s_o, g_o = new_server(address='localhost', port=self.PORT_o,password=self.PASSWORD)

'''
Purpose of the class
This is the first step of the model creation after connecting to the Plaxis remote server.
The method serProjectProperties will take project parameters as input & set to the project.
The method SetWorkingArea will take coordinate as input & initialze the rectangular working space.
'''
class ModelCreation2D:

    def __init__(self,g_i):
        self.g_i= g_i

    #This instance method is to set the project properties.
    def SetProjectProperties (self,title = 'Project_01',
                               unitForce = 'kN', 
                               unitLength = 'm', 
                               unitTime = 's', 
                               modelType = 'Plane Strain',
                               elementType = '15noded'):
        self.title = title
        self.uniForce = unitForce
        self.unitLength = unitLength
        self.unitTime = unitTime
        self.modelType = modelType
        self.elementType = elementType

        # Set the project properties to the model
        self.g_i.setproperties ("Title", self.title,
                                "UnitForce", self.uniForce,
                                "UnitLength", self.unitLength,
                                "UnitTime", self.unitTime,
                                "ModelType", self.modelType,
                                "ElementType", self.elementType)
        

    # This instance method is to set the working area
    def SetWorkingArea(self, xmin_coordinate,ymin_coordinate,xmax_coordinate,ymax_coordinate):

        # Lower left-hand corner
        self.xmin_coordinate = xmin_coordinate
        self.ymin_coordinate = ymin_coordinate

        # Upper right-hand corner
        self.xmax_coordinate = xmax_coordinate
        self.ymax_coordinate = ymax_coordinate

        # Create the model with soil layers
        self.g_i.SoilContour.initializerectangular(self.xmin_coordinate, self.ymin_coordinate, self.xmax_coordinate, self.ymax_coordinate)


