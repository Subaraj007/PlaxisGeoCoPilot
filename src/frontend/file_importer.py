import csv
import yaml
from typing import List, Dict, Optional
from frontend.database_connection import DatabaseConnection
from frontend.database_config import DatabaseConfig

class FileImporter:
    def __init__(self, db_config: DatabaseConfig):
        self.db_config = db_config

    def import_from_csv(self, file_path: str, table_name: str) -> List[Dict]:
        """Import data from a CSV file into the specified table."""
        try:
            with open(file_path, mode='r') as file:
                reader = csv.DictReader(file)
                data = [row for row in reader]
                
                if not data:
                    raise ValueError("CSV file is empty or improperly formatted.")
                
                with DatabaseConnection(self.db_config) as db:
                    for row in data:
                        columns = ', '.join(row.keys())
                        values = ', '.join([f"'{value}'" for value in row.values()])
                        query = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
                        db.cursor.execute(query)
                    db.connection.commit()
                
                return data
        except Exception as e:
            print(f"Error importing from CSV: {e}")
            return []

    def import_from_yaml(self, file_path: str, table_name: str) -> List[Dict]:
        """Import data from a YAML file into the specified table."""
        try:
            with open(file_path, mode='r') as file:
                data = yaml.safe_load(file)
                
                if not data:
                    raise ValueError("YAML file is empty or improperly formatted.")
                
                with DatabaseConnection(self.db_config) as db:
                    for row in data:
                        columns = ', '.join(row.keys())
                        values = ', '.join([f"'{value}'" for value in row.values()])
                        query = f"INSERT INTO {table_name} ({columns}) VALUES ({values})"
                        db.cursor.execute(query)
                    db.connection.commit()
                
                return data
        except Exception as e:
            print(f"Error importing from YAML: {e}")
            return []