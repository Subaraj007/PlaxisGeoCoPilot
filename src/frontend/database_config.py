class DatabaseConfig:
    def __init__(self, database: str):
        """
        Initialize DatabaseConfig for SQLite
        
        Args:
            database (str): Path to the SQLite database file
        """
        self.database = database
