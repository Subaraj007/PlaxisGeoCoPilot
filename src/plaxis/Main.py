# Call ConnectToPlaxis for connecting to the plaxis scripting server.

import plaxis.ConnectToPlaxis as CP
import plaxis.ModelInfo as ModelInfo
import plaxis.Materials as mat
import plaxis.Structures as Structures
import pandas as pd
import os
from os import path
from pathlib import Path

# In Main.py, add this at the beginning or replace existing hardcoded values
import argparse
import yaml
import json
from pathlib import Path
import sys

def get_data_dir():
    if getattr(sys, 'frozen', False):
        # Running in bundled executable - use the temporary directory
        # But we need to go up one level from src to get to project root
        temp_dir = Path(sys._MEIPASS)
        # Check if we're in a src subdirectory structure
        if (temp_dir / "plaxis").exists() and (temp_dir / "frontend").exists():
            # We're in the src level, need to go up to project root equivalent
            BASE_DIR = temp_dir.parent if temp_dir.name == 'src' else temp_dir
        else:
            BASE_DIR = temp_dir
    else:
        # Running in development environment - go to project root (two levels up from frontend)
        BASE_DIR = Path(__file__).resolve().parent.parent.parent
    
    data_dir = os.path.join(BASE_DIR, "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    
    return data_dir

def get_model_info_path():
    data_dir = get_data_dir()
    model_info_path = os.path.join(data_dir, "ModelInfo.xlsx")
    return model_info_path

def load_config():
    try:
        # Locate config.yaml in the parent folder of the current folder
        config_path = Path(__file__).resolve().parent.parent / "config.yaml"
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        # Extract plaxis configuration from the unified config
        plaxis_config = config_data.get("plaxis", {})
        
        # Return the plaxis config in the format expected by your existing code
        return {
            "plaxis_path": plaxis_config.get("plaxis_path", ""),
            "port_i": plaxis_config.get("port_i", ""),
            "port_o": plaxis_config.get("port_o", ""),
            "password": plaxis_config.get("password", ""),
            "version": plaxis_config.get("version", "")
        }
        
    except Exception as e:
        print(f"Error loading config: {e}")
        raise

#This function return the element name specified in plaxis
def GetElementModelName(type, name):
    excavationPolygon = pd.read_excel(get_model_info_path(), sheet_name='Excavation_Polygon', engine='openpyxl')

    struts = pd.read_excel(get_model_info_path(), sheet_name='Struts', engine= 'openpyxl')

    plates = pd.read_excel(get_model_info_path(), sheet_name='Plates', engine= 'openpyxl')

    load_lineLoad = pd.read_excel(get_model_info_path(), sheet_name='Line Load', engine= 'openpyxl')


    model_name = []

    if (type == 'Line Load'):
            
            for i, load in load_lineLoad.iterrows():

                if(load['LineLoadName']== name):
                    model_name.append (load['LineName']) 

            return model_name                     
                                    
        
    elif(type == 'ERSS Wall'):

            for i, plate in plates.iterrows():

                if(plate['PlateName']== name):
                    model_name.append(plate['LineName'])

            return model_name
                        

    elif(type == 'Plate'):

            for i, plate in plates.iterrows():

                if(plate['PlateName']== name):
                    model_name.append(plate['LineName'])

            return model_name
                        


        
    elif(type == 'Excavation'):
                
            for i, excavation in excavationPolygon.iterrows():

                if(excavation['StageNo']== name):
                    model_name.append(excavation['PolygonName'])

            return model_name
                        
                   
        
    elif(type == 'Strut'):

            for i, strut in struts.iterrows():

                if(strut['StrutType']=='n2n'):

                    model_name.append(strut['LineName'])

                elif(strut['StrutType']=='fixedend'):
                    model_name.append(strut['Point_i_Name'])

            return model_name
                
                    
        
    else:
                pass
                #To be implemented

#This function return the plaxis object
def GetElementObject (g_i, type, name):
             
        model_object = ''
        g_i.gotostructures()

        if (type == 'Line'):
            
                for line in g_i.Lines:

                    if(line.Name== name):
                        model_object = line
                        return model_object
                        break

        elif (type == 'Point'):
            
                for point in g_i.Points:

                    if(point.Name== name):
                        model_object = point
                        return model_object
                        break
                    
        
        elif(type == 'Plate'):

                for plate in g_i.Plates:

                    if(plate.Name== name):
                        model_object = plate
                        return model_object
                        break
                    
        
        elif(type == 'Soil'):

                for soil in g_i.Soils:

                    if(soil.Name== name):
                        model_object = soil
                        return model_object
                        break
                   
        
        elif(type == 'Line Load'):

                for lineLoad in g_i.LineLoads:

                    if(lineLoad.Name == name):
                        model_object = lineLoad
                        return model_object
                        break

        elif(type == 'Strut'):

                for strut in g_i.Anchors:

                    if(strut.Name == name):
                        model_object = strut
                        return model_object
                        break
        
        

        elif(type == 'Polygon'):            
        
            for polygon in g_i.Polygons:
                
                if(polygon.Name == name):
                    model_object = polygon
                    return model_object
                    break
            

        elif(type == 'Phase'):

            g_i.gotostages()
            
            for phase in g_i.Phases:
                
                if(phase.Name == name):
                    model_object = phase
                    return model_object
                    break
        else:
                pass
                #To be implemented

def OpenNewProjectFile(g_i):
    #Call ModelInfo.py to obtain the geometry information of the model
    geometry_info = ModelInfo.ModelInput.GetGeometryInfo()

    # Extract the coordinate of the working area from excel sheet using ModelInfo.py
    xmin = geometry_info.at['x_min_coordinate','Value']
    ymin =geometry_info.at['y_min_coordinate','Value']

    xmax=geometry_info.at['x_max_coordinate','Value']
    ymax = geometry_info.at['y_max_coordinate','Value']

    # Call class ModelCreation2D from ConnectionToPlaxis.py & pass the global variable g_i
    project1 = CP.ModelCreation2D(g_i = g_i)

    #use defualt project properties
    project1.SetProjectProperties()

    #Set the working area using method SetWorkingArea
    project1.SetWorkingArea(xmin_coordinate=xmin,
                        ymin_coordinate= ymin,
                        xmax_coordinate= xmax,
                        ymax_coordinate= ymax)

def CreateMaterials(g_i, version):
    print(f"DEBUG: Creating materials with version: {version}")
    
    project_info = ModelInfo.ModelInput.GetProjectInfo()
    geometry_info = ModelInfo.ModelInput.GetGeometryInfo()
    boreholeData = ModelInfo.ModelInput.GetBoreholeInfo()
    
    # Rename SoilType to MaterialName for consistency
    boreholeData = boreholeData.rename(columns={'SoilType': 'MaterialName'})
    
    # CREATE UNIQUE MATERIAL NAMES FOR LAYERS WITH SAME SOIL TYPE BUT DIFFERENT PROPERTIES
    # Group by MaterialName and create unique names if there are duplicates
    material_counts = {}
    unique_material_names = []
    
    for idx, row in boreholeData.iterrows():
        base_name = row['MaterialName']
        spt_value = row['SPT']
        
        # Count occurrences of this material name
        if base_name not in material_counts:
            material_counts[base_name] = 1
            unique_name = base_name
        else:
            material_counts[base_name] += 1
            # Create unique name by appending SPT or layer number
            unique_name = f"{base_name}_SPT{spt_value}" if spt_value != '0' else f"{base_name}_{material_counts[base_name]}"
        
        unique_material_names.append(unique_name)
    
    # Add the unique names back to the dataframe
    boreholeData['UniqueMaterialName'] = unique_material_names
    
    # Now create soil properties with unique material names
    soilProperties = boreholeData.drop(['Top', 'Bottom'], axis=1).copy()
    # Replace MaterialName with UniqueMaterialName for creating materials
    soilProperties['MaterialName'] = soilProperties['UniqueMaterialName']
    soilProperties = soilProperties.drop('UniqueMaterialName', axis=1)
    # Remove duplicates based on the new unique material names
    soilProperties = soilProperties.drop_duplicates(subset=['MaterialName'], keep='first')
    
    plateProperties = ModelInfo.ModelInput.GetPlateProperties()
    anchorProperties = ModelInfo.ModelInput.GetAnchorProperties()

    print(f"DEBUG: Soil properties loaded: {len(soilProperties)} materials")
    print(f"DEBUG: Plate properties loaded: {len(plateProperties)} materials")
    print(f"DEBUG: Anchor properties loaded: {len(anchorProperties)} materials")

    # Create soil materials
    newSoilMaterial = mat.Soil(g_i=g_i)
    newSoilMaterial.CreateSoilMaterial(soilproperties=soilProperties, version=version)
    
    # Create plate materials
    newPlateMaterial = mat.Plate(g_i=g_i)
    newPlateMaterial.CreatePlateMaterial(plateProperties=plateProperties, version=version)
 
    # Create anchor materials
    newAnchorProperties = mat.Anchor(g_i=g_i)
    newAnchorProperties.CreateAnchorMaterial(anchorProperties=anchorProperties, version=version)

    # Debug: Print all created materials
    print(f"DEBUG: Total materials created: {len(g_i.Materials)}")
    for i, material in enumerate(g_i.Materials):
        material_name = getattr(material, 'MaterialName', None) or getattr(material, 'Identification', None)
        material_color = getattr(material, 'Colour', 'No Color')
        print(f"DEBUG: Material {i+1}: Name='{material_name}', Color='{material_color}'")

    # Create borehole and set soil properties to each soil layer
    # IMPORTANT: Pass the modified boreholeData with unique names
    print(f"DEBUG: Borehole info: {project_info}")

    borehole = mat.Borehole(g_i=g_i)
    borehole_name = 'BH_01'
    borehole_location = geometry_info.loc['Borehole_x_coordinate','Value']
    groundWaterLevel = geometry_info.loc['GroundWatertable', 'Value']

    # Call CreateBorehole function to create the borehole at given ordinate
    borehole.CreateBorehole(borehole_location=borehole_location, waterTable=groundWaterLevel, 
                           borehole_name=borehole_name, soil_zone=1)

    # Call CreateSoilLayers with the modified borehole data that has unique material names
    borehole.CreateSoilLayers(borehole_info=boreholeData)
print("Starting application...")
def find_material_by_name(g_i, material_name):
    """
    Enhanced material lookup function that handles V22+ material name changes
    """
    target_name = str(material_name).strip()
    
    # Debug: Print what we're looking for
    print(f"DEBUG: Searching for material: '{target_name}'")
    
    # Add specific material name mappings for common mismatches
    name_mappings = {
        'Sheet Pile': 'SoldierPile',
        'SoldierPile': 'Sheet Pile',
        # Add more mappings as needed
    }
    
    # Create list of names to search for
    search_names = [target_name]
    if target_name in name_mappings:
        search_names.append(name_mappings[target_name])
    
    # Debug: Print all available materials
    print("DEBUG: Available materials:")
    for i, material in enumerate(g_i.Materials):
        try:
            # Try different ways to get the material name
            names = []
            if hasattr(material, 'Name'):
                try:
                    names.append(f"Name: {material.Name}")
                except:
                    pass
            if hasattr(material, 'Identification'):
                try:
                    if hasattr(material.Identification, 'value'):
                        names.append(f"Identification.value: {material.Identification.value}")
                    else:
                        names.append(f"Identification: {material.Identification}")
                except:
                    pass
            if hasattr(material, 'MaterialName'):
                try:
                    if hasattr(material.MaterialName, 'value'):
                        names.append(f"MaterialName.value: {material.MaterialName.value}")
                    else:
                        names.append(f"MaterialName: {material.MaterialName}")
                except:
                    pass
            
            print(f"  Material {i}: {' | '.join(names) if names else 'No accessible name'}")
        except Exception as e:
            print(f"  Material {i}: Error getting name - {e}")
    
    # Now search for the material
    for material in g_i.Materials:
        found_names = []
        
        # V22+ materials use Name property after creation/renaming
        if hasattr(material, 'Name'):
            try:
                found_names.append(str(material.Name).strip())
            except:
                pass
        
        # Also try Identification property
        if hasattr(material, 'Identification'):
            try:
                if hasattr(material.Identification, 'value'):
                    found_names.append(str(material.Identification.value).strip())
                else:
                    found_names.append(str(material.Identification).strip())
            except:
                pass
                
        # Try MaterialName property as fallback
        if hasattr(material, 'MaterialName'):
            try:
                if hasattr(material.MaterialName, 'value'):
                    found_names.append(str(material.MaterialName.value).strip())
                else:
                    found_names.append(str(material.MaterialName).strip())
            except:
                pass
        
        # Check if any found name matches our search criteria
        for found_name in found_names:
            for search_name in search_names:
                # Create variations to check
                target_variations = [
                    search_name,
                    search_name.replace(' ', ''),  # Remove spaces
                    search_name.replace(' ', '_'), # Replace spaces with underscores
                    search_name.replace('(', '').replace(')', ''),  # Remove parentheses
                ]
                
                if found_name in target_variations:
                    print(f"DEBUG: Found material '{found_name}' for search '{target_name}'")
                    return material
    
    print(f"ERROR: Material '{target_name}' not found")
    return None

def CreateStructure(g_i):
    points = pd.DataFrame()

    #Define data frames for storing structure information
    columnsName = ['StrutName','MaterialName','LineName','Point_i_Name','Point_i_Coordinates','Point_j_Name','Point_j_Coordinates','StrutType','Direction_x','Direction_y'] 
    struts = pd.DataFrame(columns= columnsName)

    columnsName = ['PlateName', 'LineName', 'Point_i_Name', 'Point_i_Coordinates', 'Point_j_Name', 'Point_j_Coordinates', 'PositiveInterface', 'NegativeInterface']
    plates = pd.DataFrame(columns= columnsName)

    columnsName = ['LineLoadName','LineName','Point_i_Name','Point_i_Coordinates','Point_j_Name','Point_j_Coordinates','DistributionType','qx_start','qy_start'] 
    load_lineLoad = pd.DataFrame(columns=columnsName)

    erss_wall_info = ModelInfo.ModelInput.GetERSSWallDetails()

    #Create structure objects
    point = Structures.Point(g_i=g_i)
    line = Structures.Line(g_i=g_i)
    plate = Structures.Structure(g_i = g_i)

    # Print available materials for debugging
    print("DEBUG: Available materials at structure creation:")
    for i, material in enumerate(g_i.Materials):
        try:
            # Try to get material name using different methods
            name = None
            if hasattr(material, 'Identification') and hasattr(material.Identification, 'value'):
                name = material.Identification.value
            elif hasattr(material, 'MaterialName') and hasattr(material.MaterialName, 'value'):
                name = material.MaterialName.value
            elif hasattr(material, 'Identification'):
                name = str(material.Identification)
            elif hasattr(material, 'MaterialName'):
                name = str(material.MaterialName)
            else:
                name = f"<Material_{i}>"
                
            print(f"  {i}: {name}")
        except Exception as e:
            print(f"  {i}: <Error getting name: {e}>")

    #Create Plate Elements
    for index,data in erss_wall_info.iterrows():
        materialName = data['MaterialName']
        wallName = data['WallName']
        x_coordinate_top = data['x_Top']
        y_coordinate_top = data['y_Top']
        x_coordinate_bottom = data['x_Bottom']
        y_coordinate_bottom = data['y_Bottom']

        point_i_Name = 'point_' + wallName + '_Top'
        point_j_Name = 'point_' + wallName + '_Bottom'

        point_i = point.createPoint(pointName=point_i_Name,x_coordinate= x_coordinate_top,y_coordinate=y_coordinate_top)
        point_j = point.createPoint(pointName=point_j_Name,x_coordinate= x_coordinate_bottom,y_coordinate=y_coordinate_bottom)

        line_i_Name = 'Line_' + wallName
        line_i = line.createLine(lineName= line_i_Name, point1= point_i, point2= point_j)

        #Find plate material using enhanced lookup
        erss_wall_material = find_material_by_name(g_i, materialName)
            
        if erss_wall_material is None:
            print(f'ERROR: Material name "{materialName}" NOT found in materials list')
            continue  # Skip this wall if material not found
        else:
            print(f"DEBUG: Found plate material '{materialName}' for wall '{wallName}'")
    
        plate.createPlate(lineName=line_i, plateName= wallName, materialName= erss_wall_material)

        interfaceName_x = wallName + '_PositiveInterface'
        plate.createPositiveInterface(lineName=line_i, interFaceName= interfaceName_x)

        interfaceName_y = wallName + '_NegativeInterface'
        plate.createNegativeInterface(lineName=line_i, interFaceName= interfaceName_y)

        #Store plate info
        newRow = {  'PlateName':wallName,
                    'MaterialName': materialName,
                    'LineName': line_i_Name,
                    'Point_i_Name' : point_i_Name,
                    'Point_i_Coordinates':(x_coordinate_top,y_coordinate_top),
                    'Point_j_Name' : point_j_Name,
                    'Point_j_Coordinates': (x_coordinate_bottom,y_coordinate_bottom),
                    'PositiveInterface': interfaceName_x,
                    'NegativeInterface': interfaceName_y}
        
        plates.loc[len(plates)] = newRow

    # Save plates data
    isFileExist = path.isfile(get_model_info_path())
    if(isFileExist):
        writer = pd.ExcelWriter(get_model_info_path(), mode= 'a', engine= 'openpyxl', if_sheet_exists= 'replace')
        plates.to_excel(writer, sheet_name='Plates', index= False)
        writer.close()
    else:
        writer = pd.ExcelWriter(get_model_info_path(), engine= 'xlsxwriter')
        plates.to_excel(writer, sheet_name='Plates', index= False)
        writer.close()
    
    #Create Struts
    strut_detail = ModelInfo.ModelInput.GetStrutDetails()

    for index, data in strut_detail.iterrows():
        materialName = data['MaterialName']
        strutName = data['StrutName']
        x_coordinate_Left = data['x_Left']
        y_coordinate_Left = data['y_Left']
        x_coordinate_Right = data['x_Right']
        y_coordinate_Right = data['y_Right']
        strutType = data['Type']
        strut_dir_x = data['Direction_x']
        strut_dir_y = data['Direction_y']

        #Find strut material using enhanced lookup
        strutMaterial = find_material_by_name(g_i, materialName)
    
        if strutMaterial is None:
            print(f"ERROR: Anchor material '{materialName}' NOT found")
            continue  # Skip this strut if material not found
        else:
            print(f"DEBUG: Found anchor material '{materialName}' for strut '{strutName}'")

        #Create anchor based on type
        if(strutType == 'n2n'):
            point_i_Name = 'point_' + strutName+ 'Left'
            point_j_Name = 'point_' + strutName+ 'Right'
            point_i = point.createPoint(pointName=point_i_Name, x_coordinate= x_coordinate_Left, y_coordinate=y_coordinate_Left)
            point_j = point.createPoint(pointName=point_j_Name, x_coordinate= x_coordinate_Right, y_coordinate=y_coordinate_Right)

            line_i_Name = 'Line_' + strutName
            line_i = line.createLine(lineName=line_i_Name, point1= point_i, point2 =point_j )

            anchor = Structures.Structure(g_i = g_i)
            anchor.createn2nAchor(lineName=line_i, anchorName= strutName, materialName=strutMaterial)
        
        elif(strutType == 'fixedend'):
            point_i_Name = 'point_' + strutName
            point_i = point.createPoint(pointName=point_i_Name, x_coordinate= x_coordinate_Left, y_coordinate=y_coordinate_Left)

            
            anchor = Structures.Structure(g_i = g_i)
    
            anchor.createfixedendAnchor(pointName= point_i, anchorName= strutName, direction_x= strut_dir_x, direction_y= strut_dir_y, materialName= strutMaterial)
    
        #Store strut info
        if strutType == 'n2n':
            newRow = {  'StrutName': strutName,
                        'MaterialName': materialName,
                        'LineName': line_i_Name,
                        'Point_i_Name': point_i_Name,
                        'Point_i_Coordinates': (x_coordinate_Left, y_coordinate_Left),
                        'Point_j_Name': point_j_Name,
                        'Point_j_Coordinates': (x_coordinate_Right, y_coordinate_Right),
                        'StrutType': strutType,
                        'Direction_x': strut_dir_x,
                        'Direction_y': strut_dir_y}
            
        elif strutType == 'fixedend':
            newRow = {  'StrutName': strutName,
                        'MaterialName': materialName,
                        'LineName': '',  # Empty for fixedend
                        'Point_i_Name': point_i_Name,
                        'Point_i_Coordinates': (x_coordinate_Left, y_coordinate_Left),
                        'Point_j_Name': '',  # Empty for fixedend
                        'Point_j_Coordinates': '',  # Empty for fixedend
                        'StrutType': strutType,
                        'Direction_x': strut_dir_x,
                        'Direction_y': strut_dir_y}

        struts.loc[len(struts)] = newRow

    # Save struts data
    isFileExist = path.isfile(get_model_info_path())
    if(isFileExist):
        writer = pd.ExcelWriter(get_model_info_path(), mode= 'a', engine= 'openpyxl', if_sheet_exists= 'replace')
        struts.to_excel(writer, sheet_name='Struts', index= False)
        writer.close()
    else:
        writer = pd.ExcelWriter(get_model_info_path(), engine= 'xlsxwriter')
        struts.to_excel(writer, sheet_name='Struts', index= False)
        writer.close()

    #Create Line Loads
    lineLoad = Structures.Load(g_i = g_i)
    lineLoad_info = ModelInfo.ModelInput.GetLineLoadDetails()

    for index, data in lineLoad_info.iterrows():
        lineLoad_Name = data['LoadName']
        x_coordinate_start = data['x_start']
        y_coordinate_start = data['y_start']
        x_coordinate_end = data['x_end']
        y_coordinate_end = data['y_end']
        qx_start = data['qx_start']
        qy_start = data['qy_start']
        distributionType = data['Distribution']

        point_i_Name = 'point_' + lineLoad_Name + '_start'
        point_i = point.createPoint(pointName= point_i_Name, x_coordinate = x_coordinate_start, y_coordinate = y_coordinate_start)

        point_j_Name = 'point_' + lineLoad_Name + '_end'
        point_j = point.createPoint(pointName= point_j_Name, x_coordinate = x_coordinate_end, y_coordinate = y_coordinate_end)     

        line_i_Name = 'Line_'+lineLoad_Name
        line_i = line.createLine(lineName = line_i_Name, point1 = point_i, point2 = point_j )

        if (distributionType == 'Uniform'):
            lineLoad.addLineLoad(linename= line_i, lineLoadName= lineLoad_Name, qx_start= qx_start, qy_start= qy_start)
        
        #Store line load info
        newRow = {  'LineLoadName':lineLoad_Name,
                    'LineName': line_i_Name,
                    'Point_i_Name' : point_i_Name,
                    'Point_i_Coordinates':(x_coordinate_start,y_coordinate_start),
                    'Point_j_Name' : point_j_Name,
                    'Point_j_Coordinates': (x_coordinate_end,y_coordinate_end),
                    'DistributionType': distributionType,
                    'qx_start': qx_start,
                    'qy_start': qy_start}     
        
        load_lineLoad.loc[len(load_lineLoad)] = newRow

    # Save line loads data
    isFileExist = path.isfile(get_model_info_path())
    if(isFileExist):
        writer = pd.ExcelWriter(get_model_info_path(), mode= 'a', engine= 'openpyxl', if_sheet_exists= 'replace')
        load_lineLoad.to_excel(writer, sheet_name='Line Load', index= False)
        writer.close()
    else:
        writer = pd.ExcelWriter(get_model_info_path(), engine= 'xlsxwriter')
        load_lineLoad.to_excel(writer, sheet_name='Line Load', index= False)
        writer.close()
   
def DefineExcavation(g_i):
    excavation_details = ModelInfo.ModelInput.GetExcavationDetails()
    borehole_info = ModelInfo.ModelInput.GetBoreholeInfo()
    soilPolygon = Structures.SoilPolygon(g_i = g_i)

    #columnsName = ['StageNo', 'TopLevel', 'BottomLevel', 'PolygonName']
    df_excavationPolygon = pd.DataFrame()


    #Set the global object to structures before additing the polygons
    g_i.gotostructures()

    for index, data in excavation_details.iterrows():

        excavationStage = data['StageNo']
        exacavtionStageName = data['StageName']
        y_start_Left = data['y_start_Left']
        y_end_Left = data['y_end_Left']
        x_Left = data['x_Left']
        y_start_Right = data['y_start_Right']
        y_end_Right = data['y_end_Right']
        x_Right = data['x_Right']

        
        points = [x_Left, x_Right, y_start_Left, y_end_Left, y_start_Right, y_end_Right]
        print(points)

        #Create a polygon to represent the excavation 
        polygon_i_Name = 'polygon_Stage' + str(excavationStage) + '_Excavation'
        df_polygon = soilPolygon.createExcavationPolygon(polygon_i_Name, points, borehole_info, excavationStage)
        
        df_excavationPolygon =pd.concat([df_excavationPolygon,df_polygon])

    isFileExist = path.isfile(get_model_info_path())

    if(isFileExist):
        writer = pd.ExcelWriter(get_model_info_path(), mode= 'a', engine= 'openpyxl', if_sheet_exists= 'replace')
        df_excavationPolygon.to_excel(writer, sheet_name='Excavation_Polygon', index= False)
        writer.close()

    else:
        writer = pd.ExcelWriter(get_model_info_path(), engine= 'xlsxwriter')
        df_excavationPolygon.to_excel(writer, sheet_name='Excavation_Polygon', index= False)
        writer.close()

def DefineConstructionSequence(g_i):
    g_i.gotostages()

    constructionSequence_info = ModelInfo.ModelInput.GetConstructionSequence()

    excavationPolygon = pd.read_excel(get_model_info_path(), sheet_name='Excavation_Polygon', engine= 'openpyxl')

    struts = pd.read_excel(get_model_info_path(), sheet_name='Struts', engine= 'openpyxl')

    plates = pd.read_excel(get_model_info_path(), sheet_name='Plates', engine= 'openpyxl')

    load_lineLoad = pd.read_excel(get_model_info_path(), sheet_name='Line Load', engine= 'openpyxl')


    #Introduce new variable to store the data frame of constructionSequence_info
    data = constructionSequence_info
  

    for i in range(len(data)):

        phaseNo = data['PhaseNo'].iloc[i]
        phaseName = data['PhaseName'].iloc[i]
        elementType = data['ElementType'].iloc[i]
        elementName = data['ElementName'].iloc[i]
        action = data['Action'].iloc[i]
        modelElementType = data['ModelElementType'].iloc[i]

        element_model_Name = ''  

        if(i == 0):
            phase_i = g_i.InitialPhase
            phase_i.Identification.set(phaseName)
            phase_i.Name.set(phaseNo)


        elif(i == len(data)-1):

            phase_i = g_i.phase(phase_i)
            phase_i.Identification.set(phaseName)
            phase_i.Name.set(phaseNo)

            if(action == 'Activate'):

                element_model_Name = GetElementModelName(type= elementType, name= elementName)

                if(type(element_model_Name)==list):

                    for x in range(len(element_model_Name)):
                        objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name[x])

                        g_i.gotostages()

                        g_i.activate(objectName, phase_i)

                else:
                    objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name )

                    g_i.gotostages()

                    g_i.activate(objectName, phase_i)

            elif(action == 'Deactivate'):
                element_model_Name = GetElementModelName(type= elementType, name= elementName)

                if(type(element_model_Name)==list):

                    for x in range(len(element_model_Name)):
                        objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name[x] )

                        g_i.gotostages()

                        g_i.deactivate(objectName, phase_i)

                else:
                    objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name )

                    g_i.gotostages()

                    g_i.deactivate(objectName, phase_i)
       
        elif((data['PhaseNo'].iloc[i]) != (data['PhaseNo'].iloc[i+1]) and (data['PhaseNo'].iloc[i]!=(data['PhaseNo'].iloc[i-1]))):

            phase_i = g_i.phase(phase_i)
            phase_i.Identification.set(phaseName)
            phase_i.Name.set(phaseNo)

            if(action == 'Activate'):
                element_model_Name = GetElementModelName(type= elementType, name= elementName)

                if(type(element_model_Name)==list):

                    for x in range(len(element_model_Name)):
                        objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name[x] )

                        g_i.gotostages()

                        g_i.activate(objectName, phase_i)

                else:
                    objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name )

                    g_i.gotostages()

                    g_i.activate(objectName, phase_i)

            elif(action == 'Deactivate'):
                element_model_Name = GetElementModelName(type= elementType, name= elementName)

                if(type(element_model_Name)==list):

                    for x in range(len(element_model_Name)):
                        objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name[x] )

                        g_i.gotostages()

                        g_i.deactivate(objectName, phase_i)

                else:
                    objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name )

                    g_i.gotostages()

                    g_i.deactivate(objectName, phase_i)

        elif(data['PhaseNo'].iloc[i] == data['PhaseNo'].iloc[i+1] and ((data['PhaseNo'].iloc[i] != data['PhaseNo'].iloc[i-1]))):


            phase_i = g_i.phase(phase_i)
            phase_i.Identification.set(phaseName)
            phase_i.Name.set(phaseNo)
            
            if(action == 'Activate'):
                element_model_Name = GetElementModelName(type= elementType, name= elementName)

                if(type(element_model_Name)==list):

                    for x in range(len(element_model_Name)):
                        objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name[x] )

                        g_i.gotostages()

                        g_i.activate(objectName, phase_i)

                else:
                    objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name )

                    g_i.gotostages()

                    g_i.activate(objectName, phase_i)

            elif(action == 'Deactivate'):

                element_model_Name = GetElementModelName(type= elementType, name= elementName)

                if(type(element_model_Name)==list):

                    for x in range(len(element_model_Name)):
                        objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name[x] )

                        g_i.gotostages()

                        g_i.deactivate(objectName, phase_i)

                else:
                    objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name )

                    g_i.gotostages()

                    g_i.deactivate(objectName, phase_i)

            #Declare a variable to make a reference from i th row
            n = 1

            while((data['PhaseNo'].iloc[n]) == data['PhaseNo'].iloc[n+1]):

                elementType = (data['ElementType'].shift(-n)).iloc[i]
                elementName = (data['ElementName'].shift(-n)).iloc[i]

                if(action == 'Activate'):
                    element_model_Name = GetElementModelName(type= elementType, name= elementName)

                    if(type(element_model_Name)==list):

                        for x in range(len(element_model_Name)):
                            objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name[x] )

                            g_i.gotostages()

                            g_i.activate(objectName, phase_i)

                    else:
                        objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name )

                        g_i.gotostages()

                        g_i.activate(objectName, phase_i)


                elif(action == 'Deactivate'):
                    element_model_Name = GetElementModelName(type= elementType, name= elementName)

                    if(type(element_model_Name)==list):

                        for x in range(len(element_model_Name)):
                            objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name[x] )

                            g_i.gotostages()

                            g_i.deactivate(objectName, phase_i)

                    else:
                        objectName = GetElementObject(g_i, type= modelElementType, name= element_model_Name )

                        g_i.gotostages()

                        g_i.deactivate(objectName, phase_i)
        
                n += 1
      
def GenerateMesh(g_i):
    g_i.gotomesh()
    g_i.mesh()

def DefineClusterWaterTable(g_i):

    g_i.gotostages()

    constructionSequence_info = ModelInfo.ModelInput.GetConstructionSequence()

    excavationPolygon = pd.read_excel(get_model_info_path(), sheet_name='Excavation_Polygon', engine= 'openpyxl')

    waterPolygon = pd.read_excel(get_model_info_path(), sheet_name='Water_Polygon', engine= 'openpyxl')

    wetPolygons = []

    #Convert the excavation polygon to list
    list_excavationPolygons = excavationPolygon['PolygonName'].tolist()
    #Add the excavationPolygon into the wetPolygon list
    wetPolygons.extend(list_excavationPolygons)

    #Convert the waterPolygon dataframe to list
    list_waterPolygons = waterPolygon['PolygonName'].tolist()
    #Add the waterPolygon into the wetPolygon list
    wetPolygons.extend(list_waterPolygons)
    #Introduce new variable to store the data frame of constructionSequence_info

    print(wetPolygons)
    phase_object = GetElementObject(g_i, type= 'Phase', name= 'Phase_0')

    for y in range(len(wetPolygons)):
        g_i.gotostructures()

        polygon_object = GetElementObject(g_i, type= 'Polygon', name= wetPolygons[y])                
                
        g_i.gotostages()
        g_i.setwaterinterpolate(polygon_object,phase_object)

    data = constructionSequence_info

    for i in range(len(data)):

        phaseNo = data['PhaseNo'].iloc[i]
        elementType = data['ElementType'].iloc[i]
        elementName = data['ElementName'].iloc[i]

        
        stage_no = 0
        dryPolygons = []
        

        if (elementType == 'Excavation'):
            stage_no = elementName
            phase_object = GetElementObject(g_i, type= 'Phase', name= phaseNo)

            for j in range(len(excavationPolygon)):

                if(excavationPolygon['StageNo'].iloc[j]== stage_no and j == len(excavationPolygon) -1 ):
                    drySoil = excavationPolygon['PolygonName'].iloc[j]
                    dryPolygons.append(drySoil)

                    list_wetSoil =  excavationPolygon['PolygonName'].iloc[j+1:len(excavationPolygon)+1].tolist()
                    wetPolygons.extend(list_wetSoil)

                elif(excavationPolygon['StageNo'].iloc[j]== stage_no and excavationPolygon['StageNo'].iloc[j] != excavationPolygon['StageNo'].iloc[j+1] ):

                    drySoil = excavationPolygon['PolygonName'].iloc[j]
                    dryPolygons.append(drySoil)

                    list_wetSoil =  excavationPolygon['PolygonName'].iloc[j+1:len(excavationPolygon)+1].tolist()
                    wetPolygons.extend(list_wetSoil)
                
                elif(excavationPolygon['StageNo'].iloc[j]== stage_no and excavationPolygon['StageNo'].iloc[j] == excavationPolygon['StageNo'].iloc[j+1] ):

                    n =j

                    #Calculate how many same StageNo exist
                    while(excavationPolygon['StageNo'].iloc[n] == excavationPolygon['StageNo'].iloc[n+1]):

                        n+=1

                    list_drySoil = excavationPolygon['PolygonName'].iloc[j:n+1].tolist()
                    dryPolygons.extend(list_drySoil)

                    list_wetSoil =  excavationPolygon['PolygonName'].iloc[n+1:len(excavationPolygon)+1].tolist()
                    wetPolygons.extend(list_wetSoil)
                    break            


            for x in range(len(dryPolygons)):
                g_i.gotostructures()

                polygon_object = GetElementObject(g_i, type= 'Polygon', name= dryPolygons[x])                
                
                g_i.gotostages()
                g_i.setwaterdry(polygon_object,phase_object)

def DefineWaterCluster(g_i):

    excavation_details = ModelInfo.ModelInput.GetExcavationDetails()
    borehole_info = ModelInfo.ModelInput.GetBoreholeInfo()
    soilPolygon = Structures.SoilPolygon(g_i = g_i)
    borehole = ModelInfo.ModelInput.GetBoreholeInfo()

    columnsName = ['PolygonName', 'TopLevel', 'BottomLevel']
    df_waterPolygon = pd.DataFrame(columns=columnsName)

    #Select the last row from excavation_details
    data = excavation_details.iloc[-1]
    y_start_Left = data['y_end_Left']
    x_Left = data['x_Left']
    y_start_Right = data['y_end_Right']
    x_Right = data['x_Right']

    borehole_lastrow = borehole.iloc[-1]
    y_end = borehole_lastrow['Bottom']

    #Create a list for points to create polygons    
    points = [float(x_Left), float(x_Right), float(y_start_Left), float(y_end), float(y_start_Right), float(y_end)]
    print(points)
    #Create a polygons inside the ERSS cluster
    polygon_i_Name = 'polygon_WaterTable'

    #Set the global object to structures before additing the polygons
    g_i.gotostructures()
    df_polygon = soilPolygon.createWaterPolygon(polygon_i_Name, points, borehole_info)
    df_waterPolygon = pd.concat([df_waterPolygon,df_polygon])

    isFileExist = path.isfile(get_model_info_path())

    if(isFileExist):
        writer = pd.ExcelWriter(get_model_info_path(), mode= 'a', engine= 'openpyxl', if_sheet_exists= 'replace')
        df_waterPolygon.to_excel(writer, sheet_name='Water_Polygon', index= False)
        writer.close()

    else:
        writer = pd.ExcelWriter(get_model_info_path(), engine= 'xlsxwriter')
        df_waterPolygon.to_excel(writer, sheet_name='Water_Polygon', index= False)
        writer.close()

    waterPolygon = df_waterPolygon

    g_i.gotoflow()


def create_model():
    data_dir = get_data_dir()
    # Get configuration
    config = load_config()
    Plaxis2DInput_Path = config['plaxis_path']
    PORT_i = config['port_i']
    PORT_o = config['port_o']
    PASSWORD = config['password']
    #Define the variable for Plaxis version
    version = config['version']  # Default to 'Before V22' if not specified
    print("Plaxis Version:", version)
    inputFile_Path = os.path.join(data_dir, "Input_Data.xlsx")
    #set the path in to the ModelInfo file
    ModelInfo.path = inputFile_Path

    project1 = CP.Plaxis2D(Plaxis2DInput_Path=Plaxis2DInput_Path,
                            PORT_i=PORT_i,
                            PORT_o=PORT_o,
                            PASSWORD=PASSWORD)

    # Open the Plaxis 2D program
    s_i, g_i = project1.OpenPlaxis2D_input()

    # Create New project
    s_i.new()

    #After connect to the plaxis, call the function one by one to create the model
    OpenNewProjectFile(g_i)
    CreateMaterials(g_i, version)
    CreateStructure(g_i)
    DefineExcavation(g_i)
    DefineWaterCluster(g_i)
    GenerateMesh(g_i)
    DefineConstructionSequence(g_i)
    DefineClusterWaterTable(g_i)

if __name__ == "__main__":
    create_model()