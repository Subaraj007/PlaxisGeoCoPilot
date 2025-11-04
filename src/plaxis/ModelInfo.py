import pandas as pd
'''
The purpose of this module
This module will read the relevant sheet from ModelInfo.xlsx at the same directory and return the data in the form pandas data frame
'''

path =''

class ModelInput:
    project_info = pd.DataFrame()
    geometry_info = pd.DataFrame()
    plate_info = pd.DataFrame()
    borehole_info = pd.DataFrame()
    soil_info = pd.DataFrame()
    anchor_info = pd.DataFrame()
    strut_info = pd.DataFrame()
    erssWall_info = pd.DataFrame()
    lineload_details = pd.DataFrame()
    excavation_details = pd.DataFrame()
    construction_sequence = pd.DataFrame()

    
    @classmethod
    def GetProjectInfo(cls):
        cls.project_info = pd.read_excel(path, sheet_name='Project Info', engine= 'openpyxl')
        #cls.project_info.dropna(inplace= True)
        #cls.project_info.index = cls.project_info['Parameters']
        return cls.project_info
    
    @classmethod
    def GetGeometryInfo(cls):
        cls.geometry_info = pd.read_excel(path, sheet_name='Geometry Info', engine= 'openpyxl')
        #cls.geometry_info.dropna(inplace=True)
        cls.geometry_info.index = cls.geometry_info['Parameters']
        return cls.geometry_info

    @classmethod
    def GetPlateProperties(cls):
        cls.plate_info = pd.read_excel(path, sheet_name='Plate Properties', engine= 'openpyxl')
        #cls.plate_info.dropna(inplace= True)
        #cls.plate_info.index = cls.plate_info['PlateName']
        return cls.plate_info

    @classmethod
    def GetBoreholeInfo(cls):
       cls.borehole_info = pd.read_excel(path, sheet_name='Borehole', engine='openpyxl')
       return cls.borehole_info

    @classmethod
    def GetSoilInfo(cls):
        cls.soil_info = pd.read_excel(path, sheet_name='Soil Properties', engine= 'openpyxl')
        #cls.soil_info.dropna(inplace=True)
        #cls.soil_info.index = cls.soil_info['SoilType']
        return cls.soil_info

    @classmethod
    def GetAnchorProperties(cls):
        cls.anchor_info = pd.read_excel(path, sheet_name='Anchor Properties', engine= 'openpyxl')
        #cls.anchor_info.dropna(inplace=True)
        #cls.anchor_info.index = cls.anchor_info['AnchorName']
        return cls.anchor_info

    @classmethod
    def GetERSSWallDetails(cls):
        cls.erssWall_info = pd.read_excel(path, sheet_name='ERSS Wall Detail', engine= 'openpyxl')

        return cls.erssWall_info
    
    @classmethod
    def GetStrutDetails(cls):
        cls.strut_info = pd.read_excel(path, sheet_name='Strut Details', engine= 'openpyxl')

        return cls.strut_info

    @classmethod
    def GetLineLoadDetails(cls):
        cls.lineload_details = pd.read_excel(path, sheet_name='Line Load', engine= 'openpyxl')

        return cls.lineload_details

    @classmethod
    def GetExcavationDetails(cls):
        cls.excavation_details = pd.read_excel(path, sheet_name='Excavation Details', engine= 'openpyxl')

        return cls.excavation_details
    
    @classmethod
    def GetConstructionSequence(cls):
        cls.construction_sequence = pd.read_excel(path, sheet_name='Construction Sequence', engine= 'openpyxl')

        return cls.construction_sequence
    
