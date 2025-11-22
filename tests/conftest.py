import pytest
import sys
import os

# Add src/backend to python path so we can import moodmend_backend
sys.path.append(os.path.join(os.path.dirname(__file__), '../src/backend'))

from moodmend_backend import app, init_db

@pytest.fixture
def client(tmp_path):
    app.config['TESTING'] = True
    
    # Use a temporary file for the database
    db_path = tmp_path / "test_moodmend.db"
    
    # Patch the DB_NAME in the backend module
    import moodmend_backend
    moodmend_backend.DB_NAME = str(db_path)
    
    with app.test_client() as client:
        with app.app_context():
            init_db()
        yield client
        
    # Cleanup is handled by tmp_path fixture
