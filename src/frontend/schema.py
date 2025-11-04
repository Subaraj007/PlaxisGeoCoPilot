import os
import sqlite3
import logging

def create_database_schema(db_path):
    """
    Create database schema for SQLite (License tables REMOVED)
    """
    try:
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        
        # Project Info Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            common_id TEXT,
            project_title TEXT,
            section TEXT,
            unit_force TEXT,
            unit_length TEXT,
            unit_time TEXT,
            model_type TEXT,
            element_type TEXT,
            borehole_type TEXT,
            borehole TEXT,
            design_approach TEXT
        )
        ''')
        
        # Borehole Data Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS borehole_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            common_id TEXT,
            SoilType TEXT,
            DrainType TEXT,
            SPT INTEGER,
            TopDepth REAL,
            BottomDepth REAL,
            gammaUnsat REAL,
            gammaSat REAL,
            Eref REAL,
            nu REAL,
            cref REAL,
            phi REAL,
            kx REAL,
            ky REAL,
            Rinter REAL,
            K0Primary REAL
        )
        ''')
        
        # Geometry Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS geometry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            common_id TEXT,
            excavation_type TEXT,
            wall_top_level REAL,
            excavation_depth REAL,
            excavation_width REAL,
            toe_level REAL,
            no_of_strut INTEGER,
            strut_type TEXT,
            excavation_below_strut REAL,
            over_excavation REAL,
            wall_type TEXT,
            material TEXT,
            member_size TEXT,
            spacing REAL,
            borehole_x_coordinate REAL,
            GroundWatertable REAL,
            x_min_coordinate REAL,
            y_min_coordinate REAL,
            x_max_coordinate REAL,
            y_max_coordinate REAL
        )
        ''')
        
        # Soil Properties Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS soil_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            MaterialName TEXT,
            SoilModel TEXT,
            DrainageType TEXT,
            gammaUnsat REAL,
            gammaSat REAL,
            Eref INTEGER,
            nu REAL,
            cref REAL,
            phi REAL,
            kx REAL,
            ky REAL,
            Strength TEXT,
            Rinter REAL,
            K0Determination TEXT,
            K0Primary REAL,
            Colour INTEGER
        )
        ''')
        
        # User Details Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS userdetails (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            plaxis_path TEXT,
            port_i TEXT,
            port_o TEXT,
            plaxis_password TEXT,
            plaxis_version TEXT
        )
        ''')
        
        # ERSS Wall Details Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS erss_wall_details (
            MaterialName TEXT,
            WallName TEXT,
            x_Top INTEGER,
            y_Top INTEGER,
            x_Bottom INTEGER,
            y_Bottom INTEGER,
            common_id TEXT
        )
        ''')
        
        # Line Load Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS lineload (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            LoadName TEXT NOT NULL,
            x_start REAL NOT NULL,
            y_start REAL NOT NULL,
            x_end REAL NOT NULL,
            y_end REAL NOT NULL,
            qx_start REAL,
            qy_start REAL,
            Distribution TEXT,
            common_id TEXT
        )
        ''')
        
        # Anchor Properties Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS anchor_properties (
            MaterialName TEXT NOT NULL,
            Elasticity TEXT NOT NULL,
            EA INTEGER NOT NULL,
            Lspacing TEXT,
            Colour INTEGER NOT NULL,
            common_id TEXT
        )
        ''')
        
        # Strut Details Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS strutdetails (
            MaterialName TEXT NOT NULL,
            StrutName TEXT NOT NULL,
            x_Left INTEGER NOT NULL,
            y_Left INTEGER NOT NULL,
            x_Right INTEGER NOT NULL,
            y_Right INTEGER NOT NULL,
            Type TEXT NOT NULL,
            Direction_x TEXT,
            Direction_y TEXT,
            common_id TEXT
        )
        ''')
        
        # Excavation Stages Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS excavationstages (
            StageNo INTEGER NOT NULL,
            StageName TEXT,
            `From` DECIMAL(5,2),
            `To` DECIMAL(5,2),
            BatchID INTEGER NULL,
            common_id TEXT
        )
        ''')
        
        # Sequence Construct Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS sequenceconstruct (
            common_id INTEGER NOT NULL,
            phase_no INTEGER NOT NULL,
            phase_name TEXT NULL,
            element_type TEXT  NULL,
            element_name TEXT  NULL,
            action TEXT  NULL,
            model_element_type TEXT  NULL
        )
        ''')
        
        # User Plaxis Config Table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_plaxis_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            plaxis_path TEXT,
            port_i TEXT,
            port_o TEXT,
            plaxis_password TEXT,
            plaxis_version TEXT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # ✅ REMOVED: user_feature_usage table
        # ✅ REMOVED: project_creation_log table
        
        # Insert default users
        cursor.execute('''
        INSERT INTO userdetails (id, username, password, plaxis_path, port_i, port_o, plaxis_password) 
        VALUES (2, 'user', '12345', '', '', '', '')
        ON CONFLICT(id) DO NOTHING
        ''')
        cursor.execute('''
        INSERT INTO userdetails (id, username, password, plaxis_path, port_i, port_o, plaxis_password) 
        VALUES (3, 'UserNew', '12345', '', '', '', '')
        ON CONFLICT(id) DO NOTHING
        ''')
        
        connection.commit()
        connection.close()
        logging.info(f"Database schema created successfully at {db_path}")
    
    except sqlite3.Error as e:
        logging.error(f"Error creating database schema: {e}")
        raise

def ensure_database_ready(db_path):
    """
    Check if database exists and create/update schema as needed
    """
    try:
        abs_db_path = os.path.abspath(db_path)
        print(f"=" * 70)
        print(f"DATABASE LOCATION CHECK")
        print(f"=" * 70)
        print(f"Requested DB path: {db_path}")
        print(f"Absolute DB path: {abs_db_path}")
        print(f"Database exists: {os.path.exists(abs_db_path)}")
        
        db_dir = os.path.dirname(abs_db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            print(f"Created database directory: {db_dir}")
        else:
            print(f"Database directory exists: {db_dir}")
        
        print(f"=" * 70)
        
        create_database_schema(abs_db_path)
        
        # Verify critical tables exist
        connection = sqlite3.connect(abs_db_path)
        cursor = connection.cursor()
        
        required_tables = [
            'project_info', 
            'user_plaxis_config'
        ]
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Existing tables in database: {existing_tables}")
        
        missing_tables = [t for t in required_tables if t not in existing_tables]
        
        if missing_tables:
            logging.error(f"Missing required tables: {missing_tables}")
            connection.close()
            create_database_schema(abs_db_path)
            
            connection = sqlite3.connect(abs_db_path)
            cursor = connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            existing_tables = [row[0] for row in cursor.fetchall()]
            missing_tables = [t for t in required_tables if t not in existing_tables]
            
            if missing_tables:
                logging.error(f"Still missing tables after recreation: {missing_tables}")
                connection.close()
                return False
        
        connection.close()
        logging.info(f"Database schema verified successfully at: {abs_db_path}")
        print(f"Database ready at: {abs_db_path}")
        return True
    
    except Exception as e:
        logging.error(f"Database preparation error: {e}")
        import traceback
        traceback.print_exc()
        return False