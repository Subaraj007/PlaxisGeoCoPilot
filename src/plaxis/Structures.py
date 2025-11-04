import pandas as pd

'''
The purpose of this module
This module is equivalent to the 'Strctures' Tab in Plaxis 2D Input program
'''

'''
The class Point is equvalent to the 'Create point' in Plaxis 2D Input program under Structures tab
'''

class Point:

    def __init__(self,g_i):
        self.g_i = g_i

    def createPoint(self, pointName, x_coordinate, y_coordinate):
        self.x_coordinate = x_coordinate
        self.y_coordinate = y_coordinate
        self.pointName = pointName

        # Creates a point with specified coordinates.
        point_i = self.g_i.point(x_coordinate,y_coordinate)
        point_i.rename(self.pointName)

        return point_i

    def createMultiplePoints (self, pointDict):
        self.pointDict = pointDict

        #loop through pointDict and create new points
        #point_name - Name of the point (Dictionary Key)
        #coordinate - It consist of x,y coorninate (list)

        for point_name, coordinate in self.pointDict.items():

            # Creates a point with specified coordinates.
            point_i = self.g_i.point(coordinate[0],coordinate[1])
            point_i.rename(point_name)

'''
class Line is equivalent to Create line under Structures tab
'''

class Line:
        def __init__(self,g_i):
            self.g_i = g_i
        
        # Creates a line between two points.
        def createLine(self,lineName,point1, point2):
             self.point1_name = point1
             self.point2_name = point2
             self.lineName = lineName

             line_i = self.g_i.line(self.point1_name, self.point2_name)
             line_i.rename(self.lineName)

             return line_i
        

class SoilPolygon:
        def __init__(self,g_i):
            self.g_i = g_i
        
        #Create a polygon(s) and assign soil  for excavation purpose
        def createExcavationPolygon (self, polygonName, points, borehole_info, excavationStage):
            
            self.polygonName = polygonName
            self.points = points
            self.borehole_info = borehole_info
            stage = excavationStage
       
            '''
            Create dictionary to store the polygon names
            Key - Excavation Stage no
            values - Polygon name
            '''
            columnsName = ['StageNo', 'TopLevel', 'BottomLevel', 'PolygonName']
            df_excavationPolygon = pd.DataFrame(columns=columnsName)
            newRow = {}

            #Variables to storey the top & bottom level of the given soil polygon
            x_Left = self.points[0]
            x_Right = self.points[1]
            y_start_Left = self.points[2]
            y_end_Left = self.points[3]
            y_start_Right = self.points[4]
            y_end_Right = self.points[5]

            y_top = 0
            y_bottom = 0

            #Check whether ground is sloping or not
            if (y_start_Left == y_start_Right and y_end_Left == y_end_Right):
                y_top = y_start_Left
                y_bottom = y_end_Left
            
           
                '''
                Choose the Borehole soil layer one by one and determine the position of excavation area.
                '''
                for index, data in self.borehole_info.iterrows():
                    soil_top = data['Top']
                    soil_bottom = data['Bottom']
                    soilType = data['SoilType']
                
                
                    if (y_top <= soil_top and y_top> soil_bottom):
                        '''
                        check the top & bottom level of bore hole soil layer with Top level of excavation area
                        True - Top level of excavation area within the selected borehole soil layer
                        '''
                    
                    
                        if (y_bottom >= soil_bottom):
                        
                            #True - Excavation area (Polygon) within selected Borehole soil layer

                            #Assign corner points of the polygon to the variable 
                            polygonPoint = [(x_Left,y_top),(x_Left,y_bottom), (x_Right, y_bottom), (x_Right, y_top)]

                            #Call the function to choose the soil type from Plaxis Material object
                            soilType = self.DetermineSoilType(y_top, y_bottom)

                            #Call the function to assign the soil material to the newly created polygon
                            self.AddSoilPolygon(polygonPoint, self.polygonName, soilType)
                        

                            #Additing new row to the data frame
                            newRow = {'StageNo':stage, 'TopLevel': y_top, 'BottomLevel' : y_bottom, 'PolygonName' : self.polygonName}
                            df_excavationPolygon.loc[len(df_excavationPolygon)] = newRow

                            break

                        else:
                            '''
                            True - Bottom level of the excavation area is beyond the bottom level of selected borehole soil layer
                            Excavation polygon should be divided in to the parts.
                            '''

                            new_y_bottom = soil_bottom
                            new_y_top = y_top

                            # looping through Borehole_info & determine how many polygon needs to create the excavation area
                            i = 1
                            for row,info in self.borehole_info.iterrows():

                                soil_bottom_i = info['Bottom']

                                if (y_bottom <= soil_bottom_i and y_top > soil_bottom_i):

                                    new_y_bottom = soil_bottom_i

                                    #Assign corner points of the polygon to the variable 
                                    polygonPoint = [(x_Left,new_y_top),(x_Left,new_y_bottom), (x_Right, new_y_bottom), (x_Right, new_y_top)]

                                    #Create new variable for polygon name & assign the values
                                    newPolygonName = f'{self.polygonName}_{i}' 

                                    #Call the function to choose the soil type from Plaxis Material object
                                    soilType = self.DetermineSoilType(new_y_top, new_y_bottom)
                        
                                    #Call the function to assign the soil material to the newly created polygon
                                    self.AddSoilPolygon(polygonPoint, newPolygonName, soilType )

                                    #Additing new row to the data frame
                                    newRow = {'StageNo':stage, 'TopLevel': new_y_top, 'BottomLevel' : new_y_bottom, 'PolygonName' : newPolygonName}
                                    df_excavationPolygon.loc[len(df_excavationPolygon)] = newRow

                                    if(y_bottom == new_y_bottom):
                                        break

                                    else:

                                        #Assign new_y_bottom as top level for next polygon
                                        new_y_top = new_y_bottom

                                        i+=1
                            
                                elif(y_bottom > soil_bottom_i and y_top > soil_bottom_i):

                                    new_y_bottom = y_bottom

                                    #Assign corner points of the polygon to the variable 
                                    polygonPoint = [(x_Left,new_y_top),(x_Left,new_y_bottom), (x_Right, new_y_bottom), (x_Right, new_y_top)]

                                    #Create new variable for polygon name & assign the values
                                    newPolygonName = f'{self.polygonName}_{i}' 

                                    #Call the function to choose the soil type from Plaxis Material object
                                    soilType = self.DetermineSoilType(new_y_top, new_y_bottom)
                        
                                    #Call the function to assign the soil material to the newly created polygon
                                    self.AddSoilPolygon(polygonPoint, newPolygonName, soilType)

                                    #Additing new row to the data frame                         
                                    newRow = {'StageNo':stage, 'TopLevel': new_y_top, 'BottomLevel' : new_y_bottom, 'PolygonName' : newPolygonName}
                                    df_excavationPolygon.loc[len(df_excavationPolygon)] = newRow

                                    break

                return df_excavationPolygon
            
            else:
                pass
                #To be implemented for sloping ground


        #Create polygon(s) for assign water presure inside ERSS area
        def createWaterPolygon (self, polygonName, points, borehole_info):
            
            self.polygonName = polygonName
            self.points = points
            self.borehole_info = borehole_info

            columnsName = ['PolygonName','TopLevel', 'BottomLevel']
            df_waterPolygon = pd.DataFrame(columns=columnsName)

            #Variables to storey the top & bottom level of the given soil polygon
            x_Left = self.points[0]
            x_Right = self.points[1]
            y_start_Left = self.points[2]
            y_end_Left = self.points[3]
            y_start_Right = self.points[4]
            y_end_Right = self.points[5]

            y_top = 0
            y_bottom = 0

            #Check whether ground is sloping or not
            if (y_start_Left == y_start_Right and y_end_Left == y_end_Right):
                y_top = y_start_Left
                y_bottom = y_end_Left

            
            '''
            Choose the Borehole soil layer one by one and determine the position of polygon.
            '''
            for index, data in self.borehole_info.iterrows():
                soil_top = data['Top']
                soil_bottom = data['Bottom']
                soilType = data['SoilType']
                
                
                if (y_top <= soil_top and y_top> soil_bottom):
                    '''
                    check the top & bottom level of bore hole soil layer with Top level of polygon 
                    True - Top level of polygon within the selected borehole soil layer
                    '''
                    
                    
                    if (y_bottom >= soil_bottom):
                        
                        #True - Polygon within selected Borehole soil layer

                        self.g_i.gotostructures()

                        #Assign corner points of the polygon to the variable 
                        polygonPoint = [(x_Left,y_start_Left),(x_Left,y_end_Left), (x_Right, y_end_Right), (x_Right, y_start_Right)]

                        #Call the function to choose the soil type from Plaxis Material object
                        soilType = self.DetermineSoilType(y_start_Left, y_end_Left)

                        #Call the function to assign the soil material to the newly created polygon
                        self.AddSoilPolygon(polygonPoint, self.polygonName, soilType)
                        
                        #Additing new row to the data frame
                        newRow = {'PolygonName' : self.polygonName,'TopLevel': y_start_Left, 'BottomLevel' : y_end_Left}
                        df_waterPolygon.loc[len(df_waterPolygon)] = newRow

                        break

                    else:
                        '''
                        True - Bottom level of the polygon is beyond the bottom level of selected borehole soil layer
                        Polygon should be divided in to the parts.
                        '''

                        new_y_bottom = soil_bottom
                        new_y_top = y_top

                        # looping through Borehole_info & determine how many polygons needs to create within the area
                        i = 1
                        for row,info in self.borehole_info.iterrows():

                            soil_bottom_i = info['Bottom']

                            if (y_bottom <= soil_bottom_i and y_top > soil_bottom_i):

                                new_y_bottom = soil_bottom_i

                                #Assign corner points of the polygon to the variable 
                                polygonPoint = [(x_Left,new_y_top),(x_Left,new_y_bottom), (x_Right, new_y_bottom), (x_Right, new_y_top)]

                                #Create new variable for polygon name & assign the values
                                newPolygonName = f'{self.polygonName}_{i}' 

                                #Call the function to choose the soil type from Plaxis Material object
                                soilType = self.DetermineSoilType(new_y_top, new_y_bottom)
                        
                                #Call the function to assign the soil material to the newly created polygon
                                self.AddSoilPolygon(polygonPoint, newPolygonName, soilType)

                                #Additing new row to the data frame
                                newRow = {'PolygonName' : self.polygonName,'TopLevel': new_y_top, 'BottomLevel' : new_y_bottom}
                                df_waterPolygon.loc[len(df_waterPolygon)] = newRow

                                if(y_bottom == new_y_bottom):
                                    break
                                else:
                                    #Assign new_y_bottom as top level for next polygon
                                    new_y_top = new_y_bottom

                                i+=1
                            
                            elif(y_bottom > soil_bottom_i and y_top > soil_bottom_i):

                                new_y_bottom = y_bottom

                                #Assign corner points of the polygon to the variable 
                                polygonPoint = [(x_Left,new_y_top),(x_Left,new_y_bottom), (x_Right, new_y_bottom), (x_Right, new_y_top)]

                                #Create new variable for polygon name & assign the values
                                newPolygonName = f'{self.polygonName}_{i}' 

                                #Call the function to choose the soil type from Plaxis Material object
                                soilType = self.DetermineSoilType(new_y_top, new_y_bottom)
                        
                                #Call the function to assign the soil material to the newly created polygon
                                self.AddSoilPolygon(polygonPoint, newPolygonName, soilType)

                                #Additing new row to the data frame
                                newRow = {'PolygonName' : self.polygonName,'TopLevel': y_start_Left, 'BottomLevel' : y_end_Left}
                                df_waterPolygon.loc[len(df_waterPolygon)] = newRow

                                break

            return df_waterPolygon
                          
    # Add Soilmpolygon to the model
        def AddSoilPolygon (self, points, polygonName, soilType):
            self.points = points
            self.polygonName = polygonName
            #self.borehole_info = borehole_info
            self.soilType = soilType

            #Create polygon
            self.g_i.polygon(*self.points)

            #Select the last polygon from g_i.Polygons object            
            polygon_i = self.g_i.Polygons[-1]

            polygon_i.rename(self.polygonName)

          #Loop through Materials object & check whether soilType exist or not
            material_found = False
            target_soil_type = str(soilType).strip()
        
            for soilMaterial in self.g_i.Materials:
                material_name = None
            
                # Try different ways to get the material name for V22+
                if hasattr(soilMaterial, 'Name'):
                    try:
                        material_name = str(soilMaterial.Name).strip()
                    except:
                        pass
                
                if not material_name and hasattr(soilMaterial, 'Identification'):
                    try:
                        if hasattr(soilMaterial.Identification, 'value'):
                            material_name = str(soilMaterial.Identification.value).strip()
                        else:
                            material_name = str(soilMaterial.Identification).strip()
                    except:
                        pass
                
                # Also try the legacy MaterialName attribute as fallback
                if not material_name and hasattr(soilMaterial, 'MaterialName'):
                    try:
                        if hasattr(soilMaterial.MaterialName, 'value'):
                            material_name = str(soilMaterial.MaterialName.value).strip()
                        else:
                            material_name = str(soilMaterial.MaterialName).strip()
                    except:
                        pass
                
                # Check for match (handle parentheses variations)
                if material_name:
                    # Create variations to match against
                    target_variations = [
                        target_soil_type,
                        target_soil_type.replace('(', '').replace(')', ''),  # Remove parentheses
                        target_soil_type.replace('(D)', 'D').replace('(B)', 'B').replace('(A)', 'A')  # Replace (X) with X
                    ]
                    
                    if material_name in target_variations:
                        polygon_i.Soil.Material = soilMaterial
                        material_found = True
                        print(f"DEBUG: Assigned material '{material_name}' to polygon '{polygonName}'")
                        break
            
            if not material_found:
                print(f"WARNING: Could not find material '{target_soil_type}' for polygon '{polygonName}'")
        
        #Determine the type of soil assigned in the borehole
        def DetermineSoilType (self, Top, Bottom):
            # Note: self.borehole_info should be available from the calling method
            Top = Top
            Bottom = Bottom
            soilType = ''
            
            for index, data in self.borehole_info.iterrows():
                soil_top = data['Top']
                soil_bottom = data['Bottom']

                if(Top <= soil_top and Bottom >=soil_bottom):

                    soilType = data['SoilType']
                    break
            return soilType
            
'''
class Structure is equivalent to Structure under Structures tab
'''
class Structure:
    def __init__(self,g_i):
        self.g_i = g_i
        
    # Add  plate feature to the existing line object
    def createPlate(self, lineName, plateName, materialName = None):
        self.lineName = lineName
        self.plateName = plateName
        self.materialName = materialName
    

        if (self.materialName == None):
            plate_i = self.g_i.plate(self.lineName)
            plate_i.rename(self.plateName)
    
        else:
            plate_i = self.g_i.plate(self.lineName, "Material", self.materialName)
            plate_i.rename(self.plateName)
        
        return plate_i

        #Add Node to Node anchor feature to the exisitng line object
    def createn2nAchor(self, lineName, anchorName, direction_x=None, direction_y = None, materialName = None):
        self.lineName = lineName
        self.anchorName = anchorName
        self.materialName = materialName


        if (self.materialName == None):
            anchor_i = self.g_i.n2nanchor(self.lineName)
            anchor_i.rename(self.anchorName)
    
        else:
            anchor_i = self.g_i.n2nanchor(self.lineName, "Material", self.materialName)
            anchor_i.rename(self.anchorName)

    #Add Fixed end anchor to the existing point
    def createfixedendAnchor (self, pointName, anchorName, direction_x=None, direction_y = None,materialName = None):
        self.pointName = pointName
        self.anchorName = anchorName
        self.materialName = materialName
        self.direction_x = direction_x
        self.direction_y = direction_y

        if(self.direction_x == None and self.direction_y == None):


            if (self.materialName == None):
                anchor_i = self.g_i.fixedendanchor(self.pointName)
                anchor_i.rename(self.anchorName)
    
            else:
                anchor_i = self.g_i.fixedendanchor(self.pointName, "Material", self.materialName)
                anchor_i.rename(self.anchorName)
        
        else:

            if (self.materialName == None):
                anchor_i = self.g_i.fixedendanchor(self.pointName,"Direction_x", self.direction_x, "Direction_y", self.direction_y)
                anchor_i.rename(self.anchorName)
    
            else:
                anchor_i = self.g_i.fixedendanchor(self.pointName,"Direction_x", self.direction_x, "Direction_y", self.direction_y, "Material", self.materialName)
                anchor_i.rename(self.anchorName)

    # Add positive interface feature to the existing line object            
    def createPositiveInterface(self, lineName, interFaceName= None):
        self.lineName = lineName
        self.interFaceName = interFaceName

        positiveInterFace_i = self.g_i.posinterface(self.lineName)
        positiveInterFace_i.rename(self.interFaceName)
    

    # Add positive interface feature to the existing line object            
    def createNegativeInterface(self, lineName, interFaceName= None):
        self.lineName = lineName
        self.interFaceName = interFaceName

        positiveInterFace_i = self.g_i.neginterface(self.lineName)
        positiveInterFace_i.rename(self.interFaceName)

'''
class Load is equivalent to Load under Structures tab
'''
class Load:
    def __init__(self,g_i):
        self.g_i = g_i

    #Add Line load to the exisitng line
    def addLineLoad(self, linename, lineLoadName, qx_start, qy_start):
        self.lineName = linename
        self.lineLoadName = lineLoadName
        self.qx_start = qx_start
        self.qy_start = qy_start

        lineload_i = self.g_i.lineload(self.lineName,"qx_start", self.qx_start, "qy_start", self.qy_start)
        lineload_i.rename(self.lineLoadName)

    #Add Point load to the existing point

    def addPointLoad (self, pointName, pointLoadName, fx=0, fy=0):
        self.pointName = pointName
        self.pointLoadName = pointLoadName
        self.fx = fx
        self.fy = fy

        pointload_i = self.g_i.pointload(self.lineName, fx, self.fx, fy, self.fy)
        pointload_i.rename(self.pointLoadName)