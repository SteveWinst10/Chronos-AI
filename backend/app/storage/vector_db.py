import os
import lancedb
from app.core.config import settings

# 1. Define where the vector database files will be saved on your computer
# This creates a folder inside your backend directory to hold the mathematical embeddings
DB_PATH = os.path.join(os.path.dirname(__file__), "../../.lancedb")

# This global variable will hold our active database connection
_db_connection = None

def get_vector_db():
    """
    Establishes and returns a shared connection pool to your local vector database.
    If a connection is already open, it reuses it instead of opening a new one.
    """
    global _db_connection
    
    if _db_connection is None:
        try:
            # Connect to LanceDB at our designated local file path
            _db_connection = lancedb.connect(DB_PATH)
        except Exception as e:
            print(f"❌ Critical Error connecting to Vector DB: {str(e)}")
            raise e
            
    return _db_connection


def init_vector_db():
    """
    The Health-Check Function. This runs when the server boots up 
    to verify that the vector storage layer is working perfectly.
    """
    try:
        # Try to open a connection
        db = get_vector_db()
        
        # Print a clear confirmation message in your VS Code terminal
        print("🟢 [HEALTH CHECK] Vector Database (LanceDB) initialized and connected successfully!")
        return True
    except Exception:
        print("🔴 [HEALTH CHECK] Vector Database initialization failed!")
        return False