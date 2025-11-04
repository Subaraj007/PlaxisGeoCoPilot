import sqlite3
import os
from frontend.database_config import DatabaseConfig
class DatabaseConnection:
    def __init__(self, config: DatabaseConfig):
        """
        Initialize database connection for SQLite
        
        Args:
            config (DatabaseConfig): Configuration for SQLite database
        """
        self.config = config
        self.connection = None
        self.cursor = None

    def __enter__(self):
        """
        Establish a connection to the SQLite database
        
        Returns:
            DatabaseConnection: Configured database connection
        """
        try:
            # Ensure the directory exists
            os.makedirs(os.path.dirname(self.config.database), exist_ok=True)
            
            # Connect to SQLite database
            self.connection = sqlite3.connect(self.config.database)
            
            # Enable dictionary-like access to rows
            self.connection.row_factory = sqlite3.Row
            
            # Create cursor
            self.cursor = self.connection.cursor()
            
            print("Successfully connected to the SQLite database")
            return self
        except sqlite3.Error as err:
            print(f"Error connecting to database: {err}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Close database connection and handle transactions
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Traceback
        """
        if self.connection:
            if exc_type is None:
                # Commit changes if no exception occurred
                self.connection.commit()
            else:
                # Rollback changes if an exception occurred
                self.connection.rollback()
            
            # Close cursor and connection
            if self.cursor:
                self.cursor.close()
            self.connection.close()
