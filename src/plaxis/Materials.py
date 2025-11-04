import pandas as pd
import math
import sys
'''
Purpose of  Materials mdoule
This module is equivalent to Soil Tab in Plaxis 2D Input programe.

'''

    
'''
Purpose of class Soil
The method CreateSoilMaterial will take the soil properties (Pandas Data Frame) as input and create new soil material
'''
class Soil:
    def __init__(self,g_i):
        self.g_i = g_i

    def map_drainage_type(self, drainage_value):
        """Map legacy drainage types to V22+ format"""
        mapping = {
            'Drain': 'drained',
            'Undrain': 'undraineda',
            'drained': 'drained',
            'undrained': 'undraineda',
            'undraineda': 'undraineda',
            'undrainedb': 'undrainedb', 
            'undrainedc': 'undrainedc',
            'nonporous': 'nonporous'
        }
        
        mapped_value = mapping.get(str(drainage_value), 'drained')
        if mapped_value != str(drainage_value):
            print(f"DEBUG: Mapped drainage type '{drainage_value}' to '{mapped_value}'")
        return mapped_value

    def CreateSoilMaterial (self,soilproperties, version):
        self.soilParameters = soilproperties
        self.version = version

        if version in ['Before V22', 'before_22']:

            for index,data in self.soilParameters.iterrows():
                try:
                    newMaterial = self.g_i.soilmat()
                    newMaterial.setproperties (
                                            "MaterialName",data['MaterialName'],
                                            "SoilModel",data['SoilModel'],
                                            "DrainageType", data['DrainageType'],
                                            "gammaUnsat", data['gammaUnsat'],
                                            "gammaSat", data['gammaSat'],
                                            "Eref",data['Eref'],
                                            "nu", data['nu'],
                                            "cref", data['cref'],
                                            "phi", data['phi'],
                                            "perm_primary_horizontal_axis", data['kx'],
                                            "perm_vertical_axis", data['ky'],
                                            "InterfaceStrength", data['Strength'],
                                            "Rinter",data['Rinter'],
                                            "K0Determination", data['K0Determination'],
                                            "K0Primary", data['K0Primary'],
                                            "Colour", data['Colour'],
                                            )
                    print(f"DEBUG: Created soil material: {data['MaterialName']}")
                except Exception as e:
                    print(f"ERROR: Failed to create soil material {data['MaterialName']}: {str(e)}")
                        
        elif version in ['V22 and after', 'after_22', 'After V22']:
            print("DEBUG: EXECUTING AFTER V22 BRANCH")
            for index,data in self.soilParameters.iterrows():
                try:
                    mapped_drainage = self.map_drainage_type(data['DrainageType'])
                    
                    # Validate and constrain Rinter value
                    rinter_value = float(data['Rinter'])
                    if rinter_value < 0.01:
                        rinter_value = 0.01
                        print(f"DEBUG: Constrained Rinter from {data['Rinter']} to 0.01 for {data['MaterialName']}")
                    elif rinter_value > 1.0:
                        rinter_value = 1.0
                        print(f"DEBUG: Constrained Rinter from {data['Rinter']} to 1.0 for {data['MaterialName']}")
                    
                    newMaterial = self.g_i.soilmat()
                    
                    # Set properties that work for all drainage types
                    basic_properties = [
                        ("Identification", data['MaterialName']),
                        ("SoilModel", data['SoilModel']),
                        ("DrainageType", mapped_drainage),
                        ("gammaUnsat", float(data['gammaUnsat'])),
                        ("gammaSat", float(data['gammaSat'])),
                        ("Eref", float(data['Eref'])),
                        ("cref", float(data['cref'])),
                        ("phi", float(data['phi'])),
                        ("PermHorizontalPrimary", float(data['kx'])),
                        ("PermVertical", float(data['ky'])),
                        ("InterfaceStrengthDetermination", data['Strength']),
                        ("Rinter", rinter_value),
                        ("K0Determination", data['K0Determination']),
                        ("K0Primary", float(data['K0Primary'])),
                        ("Colour", int(data['Colour']))
                    ]
                    
                    # Only set nuU for undrained materials (it's read-only for drained)
                    if mapped_drainage != 'drained':
                        basic_properties.insert(6, ("nuU", float(data['nu'])))
                    
                    for prop_name, prop_value in basic_properties:
                        try:
                            newMaterial.setproperties(prop_name, prop_value)
                        except Exception as prop_e:
                            print(f"WARNING: Failed to set {prop_name}={prop_value} for {data['MaterialName']}: {str(prop_e)}")
                            
                    print(f"DEBUG: Created soil material: {data['MaterialName']}")
                except Exception as e:
                    print(f"ERROR: Failed to create soil material {data['MaterialName']}: {str(e)}")
        else:
            print(f"WARNING: Unknown version '{version}' - no soil materials created")

class Plate:
    def __init__(self, g_i):
        self.g_i = g_i

    def CreatePlateMaterial (self,plateProperties,version):
        self.plateProperties = plateProperties
        self.version = version

        if version in ['Before V22', 'before_22']:
            print("DEBUG: Creating plate materials for Before V22")
            for index,data in self.plateProperties.iterrows():
                try:
                    if(data['IsIsotropic'] == True):
                        EA = data['EA']
                        EI = data['EI']
                        nu = data['StrutNu']
                        w = data['w']

                        d = math.sqrt(12 * EI / EA)
                        E = EA / d
                        G = E / (2 * (1 + nu))

                        wall_parameters = (('MaterialName', data['MaterialName']),
                                ('Colour', data['Colour']), ('IsIsotropic', data['IsIsotropic']),
                                ('EA', EA), ('EA2', EA), ('EI', EI), ('Gref', G),
                                ('d', d), ('nu', nu), ('w', w))

                        self.g_i.platemat(*wall_parameters)
                        print(f"DEBUG: Created plate material: {data['MaterialName']}")
                except Exception as e:
                    print(f"ERROR: Failed to create plate material {data['MaterialName']}: {str(e)}")
        
        elif version in ['V22 and after', 'after_22', 'After V22']:
            print("DEBUG: Creating plate materials for V22 and after")
            for index,data in self.plateProperties.iterrows():
                try:
                    if(data['IsIsotropic'] == True):
                        EA1 = float(data['EA'])
                        EI = float(data['EI'])
                        w = float(data['w'])

                        # Create material using the V22+ approach
                        newPlateMaterial = self.g_i.platemat()
                        
                        # Set properties that are valid for V22+
                        property_sets = [
                            ("Identification", data['MaterialName']),
                            ("Colour", int(data['Colour'])),
                            ("MaterialType", "Elastic"),
                            ("EA1", EA1),  # Axial stiffness 1
                            ("EI", EI),    # Flexural rigidity
                            ("w", w)       # Weight per unit length
                        ]
                        
                        for prop_name, prop_value in property_sets:
                            try:
                                newPlateMaterial.setproperties(prop_name, prop_value)
                                print(f"DEBUG: Set {prop_name}={prop_value} for {data['MaterialName']}")
                            except Exception as prop_e:
                                print(f"WARNING: Failed to set {prop_name}={prop_value} for {data['MaterialName']}: {str(prop_e)}")
                                
                        print(f"DEBUG: Created plate material: {data['MaterialName']}")
                        
                except Exception as e:
                    print(f"ERROR: Failed to create plate material {data['MaterialName']}: {str(e)}")
        else:
            print(f"WARNING: Unknown version '{version}' - no plate materials created")

class Anchor:
    def __init__(self,g_i):
        self.g_i = g_i
         
    def CreateAnchorMaterial (self,anchorProperties, version):
        self.anchorProperties = anchorProperties

        if version in ['Before V22', 'before_22']:
            print("DEBUG: Creating anchor materials for Before V22")
            for index,data in self.anchorProperties.iterrows():
                try:
                    newAnchorMaterial = self.g_i.anchormat()
                    newAnchorMaterial.setproperties (
                                                    "MaterialName", data['MaterialName'],
                                                    "Elasticity", data['Elasticity'],                                                
                                                    "EA", data['EA'],
                                                    "Lspacing", data['Lspacing'],                                                
                                                    "Colour", data['Colour'],
                                                )
                    print(f"DEBUG: Created anchor material: {data['MaterialName']}")
                except Exception as e:
                    print(f"ERROR: Failed to create anchor material {data['MaterialName']}: {str(e)}")
                                                
        elif version in ['V22 and after', 'after_22', 'After V22']:
            print("DEBUG: Creating anchor materials for V22 and after")
            for index,data in self.anchorProperties.iterrows():
                try:
                    newAnchorMaterial = self.g_i.anchormat()
                    
                    # Set properties step by step
                    property_sets = [
                        ("Identification", data['MaterialName']),
                        ("MaterialType", data['Elasticity']),
                        ("EA", float(data['EA'])),
                        ("LSpacing", float(data['Lspacing'])),
                        ("Colour", int(data['Colour']))
                    ]
                    
                    for prop_name, prop_value in property_sets:
                        try:
                            newAnchorMaterial.setproperties(prop_name, prop_value)
                        except Exception as prop_e:
                            print(f"WARNING: Failed to set {prop_name}={prop_value} for {data['MaterialName']}: {str(prop_e)}")
                            
                    print(f"DEBUG: Created anchor material: {data['MaterialName']}")
                except Exception as e:
                    print(f"ERROR: Failed to create anchor material {data['MaterialName']}: {str(e)}")
        else:
            print(f"WARNING: Unknown version '{version}' - no anchor materials created")

class Borehole:
    def __init__(self, g_i):
        self.g_i = g_i
        self.Soillayer_no = []
        
    def CreateBorehole(self,borehole_location, waterTable, borehole_name='borehole_0',  soil_zone=0, ):
        self.borehole_name = borehole_name
        self.x_coordinate = borehole_location          
        self.soil_zone = soil_zone
        self.waterTable = waterTable

        try:
            borehole_i = self.g_i.borehole(self.x_coordinate)
            borehole_i.Head.set(waterTable)
            borehole_i.rename(self.borehole_name)
            print(f"DEBUG: Created borehole '{self.borehole_name}' at x={self.x_coordinate}")
        except Exception as e:
            print(f"ERROR: Failed to create borehole: {str(e)}")
        
    def CreateSoilLayers(self, borehole_info):
      self.borehole_info = borehole_info

      i = 0
      for index, data in self.borehole_info.iterrows():
        try:
            if i == 0:
                self.g_i.soillayer(0)
                self.g_i.Soillayers[i].Zones[0].Top.set(data['Top'])
                self.g_i.Soillayers[i].Zones[0].Bottom.set(data['Bottom'])
            else:
                self.g_i.soillayer(0)
                self.g_i.Soillayers[i].Zones[0].Bottom.set(data['Bottom'])

            # Enhanced material matching for V22+
            material_found = False
            
            # CHANGED: Use 'UniqueMaterialName' if available, otherwise fall back to 'SoilType'
            if 'UniqueMaterialName' in data:
                target_soil_type = str(data['UniqueMaterialName']).strip()
            elif 'MaterialName' in data:
                target_soil_type = str(data['MaterialName']).strip()
            else:
                target_soil_type = str(data['SoilType']).strip()
            
            print(f"DEBUG: Looking for material '{target_soil_type}' for soil layer {i} (SPT={data.get('SPT', 'N/A')})")
            
            for existingMaterial in self.g_i.Materials:
                material_name = None
                
                # For V22+, materials are renamed during creation
                if hasattr(existingMaterial, 'Name'):
                    try:
                        material_name = str(existingMaterial.Name).strip()
                    except:
                        pass
                
                # Also try the original property name methods
                if not material_name:
                    if hasattr(existingMaterial, 'Identification'):
                        try:
                            if hasattr(existingMaterial.Identification, 'value'):
                                material_name = str(existingMaterial.Identification.value).strip()
                            else:
                                material_name = str(existingMaterial.Identification).strip()
                        except:
                            pass
                
                # Check for exact match or handle special cases like parentheses removal
                target_variations = [
                    target_soil_type,
                    target_soil_type.replace('(', '').replace(')', ''),
                    target_soil_type.replace('(D)', 'D').replace('(B)', 'B').replace('(A)', 'A'),
                    target_soil_type.replace(' ', ''),  # Remove spaces
                    target_soil_type.replace('_SPT', '_SPT')  # Handle SPT suffix
                ]
                
                if material_name:
                    # Also create variations of the found material name
                    material_variations = [
                        material_name,
                        material_name.replace('(', '').replace(')', ''),
                        material_name.replace(' ', '')
                    ]
                    
                    # Check if any variation matches
                    for target_var in target_variations:
                        for mat_var in material_variations:
                            if target_var == mat_var:
                                self.g_i.Soillayers[i].Soil.Material = existingMaterial
                                material_found = True
                                print(f"DEBUG: Assigned material '{material_name}' to soil layer {i}")
                                break
                        if material_found:
                            break
                
                if material_found:
                    break
            
            if not material_found:
                print(f"WARNING: Material '{target_soil_type}' not found for soil layer {i}")
                print(f"DEBUG: Available materials for layer {i}:")
                for j, mat in enumerate(self.g_i.Materials):
                    try:
                        if hasattr(mat, 'Name'):
                            name = mat.Name
                        elif hasattr(mat, 'Identification'):
                            name = mat.Identification.value if hasattr(mat.Identification, 'value') else mat.Identification
                        else:
                            name = 'Unknown'
                        print(f"  - {name}")
                    except:
                        print(f"  - <Could not get name for material {j}>")
                
        except Exception as e:
            print(f"ERROR: Failed to create soil layer {i}: {str(e)}")
            import traceback
            traceback.print_exc()
                      
        i += 1