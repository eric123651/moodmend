import json

def test_register(client):
    """Test user registration"""
    response = client.post('/api/register', json={
        'email': 'newuser@test.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'user_name': 'New User'
    })
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['email'] == 'newuser@test.com'

def test_login(client):
    """Test user login"""
    # First register a user
    client.post('/api/register', json={
        'email': 'loginuser@test.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'user_name': 'Login User'
    })
    
    # Then login
    response = client.post('/api/login', json={
        'email': 'loginuser@test.com',
        'password': 'password123'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['email'] == 'loginuser@test.com'

def test_process_emotion(client):
    """Test emotion processing"""
    response = client.post('/api/process-emotion', json={
        'input': '我今天非常快樂！', # Use Chinese input
        'email': 'test@test.com'
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['emotion'] == 'happy'
    assert 'package' in data
    assert 'nft' in data

def test_add_log(client):
    """Test adding a log entry"""
    # Register user first to ensure user_id exists
    client.post('/api/register', json={
        'email': 'loguser@test.com',
        'password': 'password123',
        'confirm_password': 'password123',
        'user_name': 'Log User'
    })

    response = client.post('/api/add-log', json={
        'email': 'loguser@test.com',
        'emotion': 'happy',
        'task': 'Smile',
        'nft': 'Happy Badge',
        'completed': True
    })
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert data['log']['emotion'] == 'happy'

def test_get_logs(client):
    """Test retrieving logs"""
    # Register user
    email = 'getloguser@test.com'
    client.post('/api/register', json={
        'email': email,
        'password': 'password123',
        'confirm_password': 'password123',
        'user_name': 'Get Log User'
    })

    # Add a log
    client.post('/api/add-log', json={
        'email': email,
        'emotion': 'sad',
        'task': 'Cry',
        'nft': 'Sad Badge',
        'completed': False
    })

    # Get logs
    response = client.get(f'/api/get-logs?email={email}')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['success'] is True
    assert len(data['logs']) == 1
    assert data['logs'][0]['emotion'] == 'sad'
