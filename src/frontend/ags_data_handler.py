import pandas as pd
import re
from pathlib import Path
import flet as ft
import asyncio
import sys


class AGSDataHandler:
    def __init__(self, form_app):
        self.form_app = form_app
        self.data_frames = {}
        self.proj_formation = ""
        self.excel_file_path = None
        
    # ADD THE MISSING METHOD HERE
    async def handle_borehole_type_change(self, e):
        """Handle when borehole type dropdown changes"""
        if e.control.value == "Ags file":
            print("DEBUG: Borehole Type changed to AGS file")
            try:
                # Get page from form_app instead of storing it
                page = self.form_app.page
                if page is None:
                    print("Page not initialized, cannot show file picker")
                    return
                if self.form_app.ags_file_picker is not None:
                    await self.form_app.ags_file_picker.pick_files(
                        allowed_extensions=["txt", "ags"],
                        dialog_title="Select AGS File"
                    )
                else:
                    print("File picker not initialized properly")
            except Exception as exc:
                print(f"DEBUG: Borehole_type_changed error: {exc}")
        else:
            self.update_borehole_field_to_text()

    # Rest of your existing AGSDataHandler methods continue here...
    # Helper function for natural sorting of borehole IDs
    def natural_sort_key(self, text):
        """Convert a string to a list of mixed strings and integers for natural sorting"""
        def convert(part):
            return int(part) if part.isdigit() else part.lower()
        return [convert(c) for c in re.split(r'([0-9]+)', str(text))]
    
    # Extract quoted cells from AGS line with enhanced parsing
    def extract_quoted_cells(self, line):
        cells = []
        if '"' in line:
            parts = line.split('"')
            for i in range(1, len(parts), 2):
                if i < len(parts):
                    cells.append(parts[i])
        else:
            # Handle comma or tab separated values
            cells = [cell.strip() for cell in re.split(r'[,\t]', line) if cell.strip()]
        return cells
    
    # IMPROVED: Enhanced AGS file reader with proper <CONT> handling
    def read_ags_file(self, file_path):
        self.data_frames = {}
        self.proj_formation = ""
        current_group = None
        headers = []
        data_rows = []
        is_header_continuing = False
        collected_header_cells = []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                lines = f.readlines()
                
        line_index = 0
        while line_index < len(lines):
            line = lines[line_index].strip()
            line_index += 1
            
            if not line:
                continue
                
            cells = self.extract_quoted_cells(line)
            if not cells:
                continue
                
            # New group
            if cells[0].startswith('**'):
                if current_group and headers and data_rows:
                    try:
                        df = pd.DataFrame(data_rows, columns=headers)
                        self.data_frames[current_group] = df
                        print(f"Saved group {current_group} with {len(df)} rows")
                        
                        # Extract FILE_FSET from PROJ section if available
                        if current_group == 'PROJ' and 'FILE_FSET' in headers:
                            try:
                                file_fset_idx = headers.index('FILE_FSET')
                                for row in data_rows:
                                    if len(row) > file_fset_idx and row[file_fset_idx] and not row[file_fset_idx].startswith('<'):
                                        self.proj_formation = row[file_fset_idx]
                                        print(f"Found project formation: {self.proj_formation}")
                                        break
                            except Exception as e:
                                print(f"Error extracting FILE_FSET from PROJ: {e}")
                                
                    except Exception as e:
                        print(f"Error creating DataFrame for {current_group}: {e}")
                        
                current_group = cells[0].strip('*')
                headers = []
                data_rows = []
                is_header_continuing = False
                collected_header_cells = []
                continue
                
            # Header line with continuation handling
            if cells[0].startswith('*'):
                if not is_header_continuing:
                    collected_header_cells = cells.copy()
                else:
                    collected_header_cells.extend(cells)
                    
                if line.strip().endswith(','):
                    is_header_continuing = True
                    continue
                else:
                    headers = [re.sub(r'[*?]', '', cell.strip()) for cell in collected_header_cells]
                    is_header_continuing = False
                    print(f"Headers for {current_group}: {headers}")
                    continue
                    
            if is_header_continuing:
                continue
                
            # Units and type rows
            if len(cells) > 0 and cells[0] in ['<UNITS>', '<TYPE>']:
                while len(cells) < len(headers):
                    cells.append('')
                cells = cells[:len(headers)]
                data_rows.append(cells)
                continue
                
            # IMPROVED: Enhanced continuation handling
            if len(cells) > 0 and cells[0] == '<CONT>':
                if data_rows and headers:
                    last_row = data_rows[-1]
                    print(f"Processing <CONT> for group {current_group}")
                    
                    # Merge continuation data with the last row
                    for i in range(1, len(cells)):  # Skip the '<CONT>' cell
                        if i < len(headers) and i < len(last_row):
                            continuation_value = cells[i].strip()
                            if continuation_value:  # Only process non-empty continuation values
                                if last_row[i]:
                                    # Concatenate if the field already has data (for descriptions)
                                    if any(desc_field in headers[i].upper() for desc_field in ['DESC', 'GEOL']):
                                        last_row[i] = last_row[i].rstrip() + " " + continuation_value
                                    else:
                                        # For non-description fields, replace if original was empty
                                        if not last_row[i].strip():
                                            last_row[i] = continuation_value
                                else:
                                    # Fill empty field with continuation value
                                    last_row[i] = continuation_value
                    
                    print(f"Last row after merge: {last_row}")
                continue
                
            # Regular data rows
            if len(cells) > 0 and not cells[0].startswith('<'):
                while len(cells) < len(headers):
                    cells.append('')
                cells = cells[:len(headers)]
                data_rows.append(cells)
                
        # Add final group
        if current_group and headers and data_rows:
            try:
                df = pd.DataFrame(data_rows, columns=headers)
                self.data_frames[current_group] = df
                print(f"Saved final group {current_group} with {len(df)} rows")
                
                # Extract FILE_FSET from final group if it's PROJ
                if current_group == 'PROJ' and 'FILE_FSET' in headers:
                    try:
                        file_fset_idx = headers.index('FILE_FSET')
                        for row in data_rows:
                            if len(row) > file_fset_idx and row[file_fset_idx] and not row[file_fset_idx].startswith('<'):
                                self.proj_formation = row[file_fset_idx]
                                print(f"Found project formation: {self.proj_formation}")
                                break
                    except Exception as e:
                        print(f"Error extracting FILE_FSET from PROJ: {e}")
                        
            except Exception as e:
                print(f"Error creating final DataFrame for {current_group}: {e}")
        
        print(f"Total groups loaded: {list(self.data_frames.keys())}")
    
    # Process ISPT data to fill missing values
    def process_ispt_data(self, df):
        """Process ISPT dataframe to fill missing ISPT_NVAL values from ISPT_REP column"""
        processed_df = df.copy()
        
        # Check if required columns exist
        if 'ISPT_NVAL' not in processed_df.columns or 'ISPT_REP' not in processed_df.columns:
            print("ISPT_NVAL or ISPT_REP columns not found in ISPT data")
            return processed_df
        
        # Function to extract N value from ISPT_REP
        def extract_n_value(ispt_rep):
            """Extract the N value from ISPT_REP string like '1,2/2,2,2,3 N=9'"""
            if pd.isna(ispt_rep) or not str(ispt_rep).strip():
                return None
                
            ispt_rep_str = str(ispt_rep).strip()
            
            # Look for N= pattern
            n_match = re.search(r'N\s*=\s*(\d+)', ispt_rep_str, re.IGNORECASE)
            if n_match:
                try:
                    return int(n_match.group(1))
                except ValueError:
                    return None
            
            return None
        
        # Process each row
        for index, row in processed_df.iterrows():
            ispt_nval = row['ISPT_NVAL']
            ispt_rep = row['ISPT_REP']
            
            # Check if ISPT_NVAL is null/empty/zero
            is_nval_empty = (
                pd.isna(ispt_nval) or 
                str(ispt_nval).strip() == '' or 
                str(ispt_nval).strip() == '0' or
                str(ispt_nval).strip().lower() in ['nan', 'none', 'null']
            )
            
            if is_nval_empty:
                # Extract N value from ISPT_REP
                n_value = extract_n_value(ispt_rep)
                if n_value is not None:
                    processed_df.at[index, 'ISPT_NVAL'] = n_value
                    print(f"Filled ISPT_NVAL at row {index}: {ispt_rep} -> {n_value}")
        
        return processed_df

    # Write dataframes to Excel
    def write_to_excel(self, output_path):
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            for group_name, df in self.data_frames.items():
                # Filter out system rows
                filtered_df = df[~df.iloc[:, 0].str.startswith('<', na=False)]
                
                # Special processing for ISPT data
                if group_name == 'ISPT':
                    filtered_df = self.process_ispt_data(filtered_df)
                    print(f"Processed ISPT data with {len(filtered_df)} rows")
                
                sheet_name = group_name[:31]  # Excel sheet name limit
                filtered_df.to_excel(writer, sheet_name=sheet_name, index=False)
        print(f"Excel file created at: {output_path}")
    
    # Extract borehole IDs from processed data
    def extract_borehole_ids(self):
        borehole_ids = []
        
        # Try Excel file first if available
        if self.excel_file_path and self.excel_file_path.exists():
            try:
                hole_df = pd.read_excel(self.excel_file_path, sheet_name="HOLE")
                if "HOLE_ID" in hole_df.columns:
                    unique_ids = hole_df["HOLE_ID"].dropna().unique()
                    borehole_ids = [str(id).strip() for id in unique_ids if str(id).strip()]
                    # Use natural sorting for proper alphanumeric order
                    borehole_ids.sort(key=self.natural_sort_key)
                    if borehole_ids:
                        print(f"Found borehole IDs in Excel HOLE sheet: {borehole_ids}")
                        return borehole_ids
            except Exception as e:
                print(f"Error reading Excel HOLE sheet: {e}")
        
        # Fallback to in-memory dataframes
        if "HOLE" in self.data_frames:
            hole_df = self.data_frames["HOLE"]
            print(f"HOLE group columns: {hole_df.columns.tolist()}")
            if "HOLE_ID" in hole_df.columns:
                unique_ids = hole_df["HOLE_ID"].dropna().unique()
                borehole_ids = [str(id).strip() for id in unique_ids if str(id).strip()]
                # Use natural sorting for proper alphanumeric order
                borehole_ids.sort(key=self.natural_sort_key)
                if borehole_ids:
                    print(f"Found borehole IDs in HOLE group: {borehole_ids}")
                    return borehole_ids
        
        return []
    
    # Function to check if soil type is effectively zero/empty
    def is_soil_type_zero_or_empty(self, soil_type):
        """Check if soil type is zero, empty, or effectively empty"""
        if not soil_type:
            return True
        
        soil_type_str = str(soil_type).strip()
        
        # Check for various representations of zero/empty
        if soil_type_str in ['0', '0.0', '', 'nan', 'None', 'null', 'NULL']:
            return True
            
        # Check if it's numeric zero
        try:
            if float(soil_type_str) == 0:
                return True
        except (ValueError, TypeError):
            pass
            
        return False
    
    # Function to get all GEOL ranges for a borehole
    def get_geol_ranges(self, borehole_id):
        """Get all GEOL ranges for a borehole as a list of dictionaries"""
        geol_ranges = []
        
        try:
            if self.excel_file_path and self.excel_file_path.exists():
                excel_data = pd.read_excel(self.excel_file_path, sheet_name=None)
                
                if 'GEOL' in excel_data:
                    geol_df = excel_data['GEOL']
                    geol_df = geol_df[~geol_df.iloc[:, 0].str.startswith('<', na=False)]
                    geol_df = geol_df[geol_df["HOLE_ID"] == borehole_id]
                    geol_df = geol_df.sort_values('GEOL_TOP', ascending=True)
                    
                    for _, row in geol_df.iterrows():
                        formation = str(row.get("GEOL_GEO3", "")).strip()
                        if not formation or formation == 'nan':
                            formation = self.proj_formation
                        
                        original_soil_type = str(row.get("GEOL_GEOL", "Unknown")).replace('"', '').strip()
                        
                        if self.is_soil_type_zero_or_empty(original_soil_type):
                            soil_type = formation if formation else "Unknown"
                        else:
                            soil_type = original_soil_type
                        
                        top_depth = float(row.get("GEOL_TOP", 0)) if pd.notna(row.get("GEOL_TOP")) else 0
                        bottom_depth = float(row.get("GEOL_BASE", 0)) if pd.notna(row.get("GEOL_BASE")) else 0
                        
                        geol_ranges.append({
                            "top": top_depth,
                            "bottom": bottom_depth,
                            "soil_type": soil_type,
                            "formation": formation
                        })
                        
            else:
                # Fallback to in-memory dataframes
                if "GEOL" in self.data_frames:
                    geol_df = self.data_frames["GEOL"]
                    hole_id_col = None
                    for col in geol_df.columns:
                        if "HOLE_ID" in col.upper() or "BORE" in col.upper():
                            hole_id_col = col
                            break
                    
                    if hole_id_col:
                        matching_rows = geol_df[geol_df[hole_id_col].astype(str).str.strip() == str(borehole_id).strip()]
                        
                        for _, row in matching_rows.iterrows():
                            formation = str(row.get("GEOL_GEO3", "")).strip()
                            if not formation or formation == 'nan':
                                formation = self.proj_formation
                            
                            original_soil_type = str(row.get("GEOL_GEOL", "Unknown")).replace('"', '').strip()
                            
                            if self.is_soil_type_zero_or_empty(original_soil_type):
                                soil_type = formation if formation else "Unknown"
                            else:
                                soil_type = original_soil_type
                            
                            try:
                                top_depth = float(row.get("GEOL_TOP", 0)) if pd.notna(row.get("GEOL_TOP")) else 0
                                bottom_depth = float(row.get("GEOL_BASE", 0)) if pd.notna(row.get("GEOL_BASE")) else 0
                            except (ValueError, TypeError):
                                top_depth = 0
                                bottom_depth = 0
                            
                            geol_ranges.append({
                                "top": top_depth,
                                "bottom": bottom_depth,
                                "soil_type": soil_type,
                                "formation": formation
                            })
                            
        except Exception as e:
            print(f"Error getting GEOL ranges: {e}")
        
        return geol_ranges
    
    # Function to get all SPT data with their corresponding GEOL ranges
    def get_spt_with_geol_ranges(self, borehole_id):
        """Get all SPT data with their corresponding GEOL ranges"""
        spt_with_ranges = []
        geol_ranges = self.get_geol_ranges(borehole_id)
        
        try:
            if self.excel_file_path and self.excel_file_path.exists():
                excel_data = pd.read_excel(self.excel_file_path, sheet_name=None)
                
                if 'ISPT' in excel_data:
                    ispt_df = excel_data['ISPT']
                    ispt_df = ispt_df[~ispt_df.iloc[:, 0].str.startswith('<', na=False)]
                    ispt_df = ispt_df[ispt_df["HOLE_ID"] == borehole_id]
                    ispt_df = ispt_df.sort_values('ISPT_TOP', ascending=True)
                    
                    for _, row in ispt_df.iterrows():
                        try:
                            ispt_top = float(row.get("ISPT_TOP", 0))
                            ispt_nval = row.get("ISPT_NVAL", "")
                            
                            # Convert SPT value to float if possible
                            try:
                                spt_value = float(ispt_nval)
                            except (ValueError, TypeError):
                                continue  # Skip non-numeric SPT values
                            
                            # Find which GEOL range this SPT falls into
                            matching_geol = None
                            for geol_range in geol_ranges:
                                if geol_range["top"] <= ispt_top <= geol_range["bottom"]:
                                    matching_geol = geol_range
                                    break
                            
                            if matching_geol:
                                spt_with_ranges.append({
                                    "spt_top": ispt_top,
                                    "spt_value": spt_value,
                                    "geol_top": matching_geol["top"],
                                    "geol_bottom": matching_geol["bottom"],
                                    "soil_type": matching_geol["soil_type"],
                                    "formation": matching_geol["formation"]
                                })
                                
                        except (ValueError, TypeError) as e:
                            print(f"Error processing ISPT row: {e}")
                            continue
                            
            else:
                # Fallback to in-memory dataframes
                if "ISPT" in self.data_frames:
                    ispt_df = self.data_frames["ISPT"]
                    
                    hole_id_col = None
                    for col in ispt_df.columns:
                        if "HOLE_ID" in col.upper():
                            hole_id_col = col
                            break
                    
                    if hole_id_col:
                        matching_rows = ispt_df[ispt_df[hole_id_col].astype(str).str.strip() == str(borehole_id).strip()]
                        
                        for _, row in matching_rows.iterrows():
                            try:
                                ispt_top = float(row.get("ISPT_TOP", 0))
                                ispt_nval = row.get("ISPT_NVAL", "")
                                
                                # Convert SPT value to float if possible
                                try:
                                    spt_value = float(ispt_nval)
                                except (ValueError, TypeError):
                                    continue  # Skip non-numeric SPT values
                                
                                # Find which GEOL range this SPT falls into
                                matching_geol = None
                                for geol_range in geol_ranges:
                                    if geol_range["top"] <= ispt_top <= geol_range["bottom"]:
                                        matching_geol = geol_range
                                        break
                                
                                if matching_geol:
                                    spt_with_ranges.append({
                                        "spt_top": ispt_top,
                                        "spt_value": spt_value,
                                        "geol_top": matching_geol["top"],
                                        "geol_bottom": matching_geol["bottom"],
                                        "soil_type": matching_geol["soil_type"],
                                        "formation": matching_geol["formation"]
                                    })
                                    
                            except (ValueError, TypeError) as e:
                                print(f"Error processing ISPT row: {e}")
                                continue
                                
        except Exception as e:
            print(f"Error getting SPT with GEOL ranges: {e}")
        
        return spt_with_ranges
    
    def apply_soil_layering_algorithm(self, borehole_id, nlimit=10):
      """Apply the improved soil layering algorithm with SPT grouping and correct depth ordering"""
      print(f"Applying soil layering algorithm for borehole: {borehole_id}")

    # Get all geological layers
      geol_ranges = self.get_geol_ranges(borehole_id)

    # Get SPT data with their corresponding GEOL ranges
      spt_with_ranges = self.get_spt_with_geol_ranges(borehole_id)

    # Create a list to store all layers (both with and without SPT)
      all_layers = []

    # Create a set to track soil types that have SPT data
      soil_types_with_spt = set()

    # First, process layers with SPT data using the grouping algorithm
      if spt_with_ranges:
        print(f"Found {len(spt_with_ranges)} SPT values with GEOL ranges")
        
        # Group SPT values by soil type to create continuous soil layers
        soil_type_groups = {}
        for spt_data in spt_with_ranges:
            soil_type = spt_data["soil_type"]
            soil_types_with_spt.add(soil_type)
            if soil_type not in soil_type_groups:
                soil_type_groups[soil_type] = []
            soil_type_groups[soil_type].append(spt_data)
        
        # Sort each group by SPT top depth
        for soil_type in soil_type_groups:
            soil_type_groups[soil_type].sort(key=lambda x: x["spt_top"])
        
        # Create continuous layers for each soil type
        continuous_layers = []
        
        # Process each soil type group
        for soil_type, spt_list in soil_type_groups.items():
            if not spt_list:
                continue
                
            # Find consecutive SPT values (they should be in order)
            current_group = [spt_list[0]]
            
            for i in range(1, len(spt_list)):
                # Check if this SPT value is consecutive (next in sequence)
                prev_spt = current_group[-1]
                current_spt = spt_list[i]
                
                # If they are consecutive or very close, add to current group
                if abs(current_spt["spt_top"] - prev_spt["spt_top"]) <= 3.0:  # Within reasonable depth range
                    current_group.append(current_spt)
                else:
                    # Process current group and start new group
                    if current_group:
                        continuous_layers.append({
                            "soil_type": soil_type,
                            "formation": current_group[0]["formation"],
                            "spt_data": current_group
                        })
                    current_group = [current_spt]
            
            # Add the final group
            if current_group:
                continuous_layers.append({
                    "soil_type": soil_type,
                    "formation": current_group[0]["formation"],
                    "spt_data": current_group
                })
        
        # Sort continuous layers by the first SPT top depth in each layer
        continuous_layers.sort(key=lambda x: x["spt_data"][0]["spt_top"] if x["spt_data"] else 0)
        
        # Now apply the subdivision algorithm within each continuous layer
        subdivided_layers = []
        
        for layer in continuous_layers:
            spt_data = layer["spt_data"]
            soil_type = layer["soil_type"]
            formation = layer["formation"]
            
            if not spt_data:
                continue
            
            # Sort SPT data by top depth
            spt_data.sort(key=lambda x: x["spt_top"])
            
            # Apply N-value based subdivision
            current_sublayer = {
                "spt_values": [spt_data[0]["spt_value"]],
                "min_spt": spt_data[0]["spt_value"],
                "spt_tops": [spt_data[0]["spt_top"]],
                "geol_bottoms": [spt_data[0]["geol_bottom"]]
            }
            
            sublayers = []
            
            for i in range(1, len(spt_data)):
                current_spt_value = spt_data[i]["spt_value"]
                current_spt_top = spt_data[i]["spt_top"]
                current_geol_bottom = spt_data[i]["geol_bottom"]
                
                # Calculate difference with minimum SPT in current sublayer
                diff = abs(current_sublayer["min_spt"] - current_spt_value)
                
                if diff <= nlimit:
                    # Add to current sublayer
                    current_sublayer["spt_values"].append(current_spt_value)
                    current_sublayer["min_spt"] = min(current_sublayer["min_spt"], current_spt_value)
                    current_sublayer["spt_tops"].append(current_spt_top)
                    current_sublayer["geol_bottoms"].append(current_geol_bottom)
                else:
                    # Finalize current sublayer and start new one
                    sublayers.append(current_sublayer.copy())
                    current_sublayer = {
                        "spt_values": [current_spt_value],
                        "min_spt": current_spt_value,
                        "spt_tops": [current_spt_top],
                        "geol_bottoms": [current_geol_bottom]
                    }
            
            # Add the final sublayer
            if current_sublayer["spt_values"]:
                sublayers.append(current_sublayer)
            
            # Convert sublayers to final format with CORRECTED depth boundaries
            for j, sublayer in enumerate(sublayers):
                # Calculate average SPT
                avg_spt = sum(sublayer["spt_values"]) / len(sublayer["spt_values"])
                
                # CORRECTED: Determine proper depth boundaries
                min_spt_top = min(sublayer["spt_tops"])
                max_spt_top = max(sublayer["spt_tops"])
                max_geol_bottom = max(sublayer["geol_bottoms"])
                
                # Determine top depth - start from the minimum SPT top in this group
                if j == 0 and not subdivided_layers:
                    # First sublayer overall - check if there's a geological layer that starts earlier
                    earliest_geol_top = float('inf')
                    for geol in geol_ranges:
                        if geol["soil_type"] == soil_type and geol["top"] < min_spt_top:
                            earliest_geol_top = min(earliest_geol_top, geol["top"])
                    
                    if earliest_geol_top != float('inf'):
                        sublayer_top = earliest_geol_top
                    else:
                        sublayer_top = min_spt_top
                elif j == 0:
                    # First sublayer in this soil type - start at the bottom of the previous layer
                    sublayer_top = subdivided_layers[-1]["bottom_depth"]
                else:
                    # Subsequent sublayers start where previous sublayer ended
                    sublayer_top = subdivided_layers[-1]["bottom_depth"]
                
                # Determine bottom depth
                if j == len(sublayers) - 1:
                    # Last sublayer - use the geol_bottom of the range containing the deepest SPT
                    sublayer_bottom = max_geol_bottom
                else:
                    # Not the last sublayer - end at the deepest SPT top in this group
                    sublayer_bottom = max_spt_top
                
                subdivided_layers.append({
                    "soil_type": soil_type,
                    "top_depth": sublayer_top,
                    "bottom_depth": sublayer_bottom,
                    "formation": formation,
                    "spt_values": sublayer["spt_values"],
                    "avg_spt": round(avg_spt)
                })
        
        print(f"Created {len(subdivided_layers)} subdivided layers")
        for i, layer in enumerate(subdivided_layers):
            print(f"Layer {i+1}: {layer['soil_type']}, {layer['top_depth']}-{layer['bottom_depth']}m, SPT: {layer['spt_values']}, Avg: {layer['avg_spt']}")
        
        # Add the subdivided layers to the final list
        all_layers.extend(subdivided_layers)

    # Now add geological layers that don't have any SPT data for their soil type
      for geol_range in geol_ranges:
        if geol_range["soil_type"] not in soil_types_with_spt:
            # This geological layer's soil type has no SPT data, add it
            all_layers.append({
                "soil_type": geol_range["soil_type"],
                "top_depth": geol_range["top"],
                "bottom_depth": geol_range["bottom"],
                "formation": geol_range["formation"],
                "spt_values": [],
                "avg_spt": 0
            })

    # CORRECTED: Sort all layers by top depth (shallow to deep - PROPER ORDER)
      all_layers.sort(key=lambda x: x["top_depth"])

    # NEW: Adjust all depths based on HOLE_GL value
      hole_gl = self.get_hole_gl_value(borehole_id)
      
      if hole_gl is not None and all_layers:
        print(f"Adjusting depths based on HOLE_GL value: {hole_gl}")
        
        # Start from HOLE_GL and work downward
        current_depth = hole_gl
        
        for layer in all_layers:
            # Calculate original layer thickness
            original_thickness = abs(layer["bottom_depth"] - layer["top_depth"])
            
            # Set new top depth
            layer["top_depth"] = current_depth
            
            # Calculate new bottom depth (going downward, so subtract)
            layer["bottom_depth"] = current_depth - original_thickness
            
            # Update current depth for next layer
            current_depth = layer["bottom_depth"]
            
            print(f"Adjusted layer: {layer['soil_type']}, top={layer['top_depth']}, bottom={layer['bottom_depth']}, thickness={original_thickness}")
            
      else:
        # Ensure the first layer starts at 0 if HOLE_GL is not available
        if all_layers and all_layers[0]["top_depth"] != 0:
            # Find the geological layer that should start at 0
            for geol_range in geol_ranges:
                if geol_range["top"] == 0:
                    # Insert this layer at the beginning
                    all_layers.insert(0, {
                        "soil_type": geol_range["soil_type"],
                        "top_depth": 0,
                        "bottom_depth": geol_range["bottom"],
                        "formation": geol_range["formation"],
                        "spt_values": [],
                        "avg_spt": 0
                    })
                    break

    # No need for continuity check since we're calculating sequentially above
    
      print(f"\nFinal layers (CORRECTED ORDER - shallow to deep):")
      for i, layer in enumerate(all_layers):
        spt_info = f"SPT: {layer['spt_values']}, Avg: {layer['avg_spt']}" if layer['spt_values'] else "No SPT data"
        print(f"Layer {i+1}: {layer['soil_type']}, {layer['top_depth']}-{layer['bottom_depth']}m, {spt_info}")

      return all_layers
  
    async def handle_ags_file_selection(self, e: ft.FilePickerResultEvent):
        """Handle AGS file selection and processing using the new algorithm"""
        if e.files:
            ags_path = e.files[0].path
            print(f"DEBUG: User selected AGS file at: {ags_path}")
                   
            try:
                print(f"Reading AGS file: {ags_path}")
                
                # Read AGS file using the new method
                self.read_ags_file(ags_path)
                
                if not self.data_frames:
                    raise Exception("No data groups found in the file!")
                
                # Create output directory
                self.form_app.export_dir.mkdir(exist_ok=True, parents=True)
                output_file = self.form_app.export_dir / "output_data.xlsx"
                
                # Write to Excel
                self.write_to_excel(output_file)
                self.excel_file_path = output_file
                
                print(f"AGS file processed successfully! Output saved to: {output_file}")
                print(f"Processed {len(self.data_frames)} data groups:")
                for group, df in self.data_frames.items():
                    print(f"  - {group}: {df.shape[0]} rows, {df.shape[1]} columns")
                
                # Extract borehole IDs
                borehole_ids = self.extract_borehole_ids()
                self.update_borehole_field_to_dropdown(borehole_ids)
                
                print(f"Found project formation: {self.proj_formation}")
                
            except Exception as e:
                print(f"Error processing AGS file: {e}")
                import traceback
                traceback.print_exc()

    async def handle_borehole_selection(self, e):
      """Handle borehole selection with the new soil layering algorithm"""
      selected_borehole = e.control.value
      print(f"User selected borehole: {selected_borehole}")

      self.form_app.selected_borehole_id = selected_borehole

      # Initialize attributes if they don't exist
      if not hasattr(self.form_app, 'selected_borehole_geology'):
        self.form_app.selected_borehole_geology = []
      else:
        self.form_app.selected_borehole_geology = []

      if not hasattr(self.form_app, 'pending_geology_data'):
        self.form_app.pending_geology_data = []
      else:
        self.form_app.pending_geology_data = []

      print(f"DEBUG: Selected borehole ID: {selected_borehole}")

      try:
        # Apply the soil layering algorithm (returns shallow to deep order)
        subdivided_layers = self.apply_soil_layering_algorithm(selected_borehole)
        
        # REVERSE the order and swap top/bottom depths for borehole tab display
        # This converts from shallow-to-deep to deep-to-shallow with swapped depths
        mapped_layers = []
        for layer in subdivided_layers:  # Keep original order
            mapped_layer = {
                "soil_type": layer.get("soil_type", "Unknown"),
                "top": layer.get("top_depth", 0),        # Keep as is
                "base": layer.get("bottom_depth", 0),    # Keep as is
                "spt_value": layer.get("avg_spt", ""),
                "spt_values": layer.get("spt_values", []),
                "formation": layer.get("formation", ""),
                "borehole_id": selected_borehole,
                "description": f"{layer.get('soil_type', '')} - {layer.get('formation', '')}"
            }
            mapped_layers.append(mapped_layer)

        # Use the mapped layers for the borehole tab
        self.form_app.selected_borehole_geology = mapped_layers
        
        print(f"DEBUG: Created {len(self.form_app.selected_borehole_geology)} layers using new algorithm")
        
        # Handle current section population
        for layer_data in self.form_app.selected_borehole_geology:
            if isinstance(self.form_app.current_section, self.form_app.sections[2].__class__):
                await self.form_app.current_section.populate_from_ags_data(layer_data, selected_borehole)
            else:
                self.form_app.pending_geology_data.append(layer_data)
        
        print(f"\nFinal geology data summary for borehole tab (REVERSED ORDER - deepest to shallowest):")
        print(f"Total layers created: {len(self.form_app.selected_borehole_geology)}")
        for i, layer in enumerate(self.form_app.selected_borehole_geology):
            spt_info = f"SPT={layer.get('spt_value', 'N/A')}" if layer.get('spt_value') else "No SPT data"
            if layer.get('spt_values'):
                spt_info = f"SPT values: {layer.get('spt_values')}, Avg: {layer.get('spt_value', 'N/A')}"
            print(f"  {i+1}. {layer.get('soil_type', 'Unknown')} ({layer.get('top', 0)}m-{layer.get('base', 0)}m) {spt_info}")
        
      except Exception as e:
        print(f"Error loading geological data: {e}")
        import traceback
        traceback.print_exc()
    def get_hole_gl_value(self, borehole_id):
      """Get the HOLE_GL value for a specific borehole ID"""
      try:
        if self.excel_file_path and self.excel_file_path.exists():
            excel_data = pd.read_excel(self.excel_file_path, sheet_name=None)
            
            if 'HOLE' in excel_data:
                hole_df = excel_data['HOLE']
                hole_df = hole_df[~hole_df.iloc[:, 0].str.startswith('<', na=False)]
                matching_row = hole_df[hole_df["HOLE_ID"] == borehole_id]
                
                if not matching_row.empty and "HOLE_GL" in hole_df.columns:
                    hole_gl = matching_row.iloc[0]["HOLE_GL"]
                    if pd.notna(hole_gl):
                        return float(hole_gl)
        else:
            # Fallback to in-memory dataframes
            if "HOLE" in self.data_frames:
                hole_df = self.data_frames["HOLE"]
                matching_row = hole_df[hole_df["HOLE_ID"] == borehole_id]
                
                if not matching_row.empty and "HOLE_GL" in hole_df.columns:
                    hole_gl = matching_row.iloc[0]["HOLE_GL"]
                    if pd.notna(hole_gl):
                        return float(hole_gl)
                        
      except Exception as e:
        print(f"Error getting HOLE_GL value: {e}")
    
      return None
    # Keep the existing methods for UI updates
    def update_borehole_field_to_dropdown(self, borehole_options):
        """Update borehole field to dropdown with AGS borehole options"""
        project_section = self.form_app.sections[0]
        fields = project_section.get_fields()
        
        for i, field in enumerate(fields):
            if field.label == "Borehole":
                field.field_type = "dropdown"
                field.options = borehole_options
                self.update_borehole_control_in_ui(borehole_options)
                break

    def update_borehole_field_to_text(self):
        """Update borehole field back to text input"""
        project_section = self.form_app.sections[0]
        fields = project_section.get_fields()
        
        for i, field in enumerate(fields):
            if field.label == "Borehole":
                field.field_type = "text"
                field.options = None
                self.update_borehole_control_to_text()
                break

    def update_borehole_control_in_ui(self, borehole_options):
        """Update the UI control to dropdown with borehole options"""
        page = self.form_app.page
        if page is None:
            return
            
        for container in self.form_app.form_content.controls:
            if isinstance(container, ft.Row):
                for control in container.controls:
                    if getattr(control, "label", "") == "Borehole" or getattr(control, "data", "") == "Borehole":
                        index = container.controls.index(control)
                        new_control = ft.Dropdown(
                            label="Borehole",
                            options=[ft.dropdown.Option(option) for option in borehole_options],
                            width=300,
                            data="Borehole",
                            on_change=self.handle_borehole_selection
                        )
                        container.controls[index] = new_control
                        page.update()
                        return

    def update_borehole_control_to_text(self):
        """Update the UI control back to text field"""
        page = self.form_app.page
        if page is None:
            return
            
        for container in self.form_app.form_content.controls:
            if isinstance(container, ft.Row):
                for control in container.controls:
                    if getattr(control, "label", "") == "Borehole" or getattr(control, "data", "") == "Borehole":
                        index = container.controls.index(control)
                        new_control = ft.TextField(
                            label="Borehole",
                            hint_text="e.g: BH_01",
                            width=300,
                            data="Borehole"
                        )
                        container.controls[index] = new_control
                        page.update()
                        return