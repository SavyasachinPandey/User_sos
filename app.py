from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_socketio import SocketIO, emit
import socketio  # Correct import
import requests
from datetime import datetime
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'user-app-secret-key-2025'
socketio_app = SocketIO(app, cors_allowed_origins="*")

# Simple user storage
users = {
    'demo': 'password123',
    'user1': 'pass123',
    'emergency_user': 'sos123',
    'john': 'john123',
    'alice': 'alice123'
}

# Admin panel connection settings
ADMIN_PANEL_URL = 'http://127.0.0.1:5001'

@app.route('/')
def index():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username in users and users[username] == password:
            session['username'] = username
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials!', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username not in users:
            users[username] = password
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Username already exists!', 'error')
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Logged out successfully!', 'info')
    return redirect(url_for('login'))

# Fixed SOS Emergency Handler
@socketio_app.on('send_sos')
def handle_sos(data):
    if 'username' in session:
        sos_data = {
            'user': session['username'],
            'location': data.get('location', 'Location not provided'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'emergency_type': data.get('type', 'General Emergency'),
            'lane_id': 1,
            'user_id': session['username'],
            'coordinates': data.get('coordinates', 'Unknown'),
            'phone': data.get('phone', 'Not provided')
        }
        
        print(f"🚨 SOS Signal from {sos_data['user']}: {sos_data}")
        
        success = False
        error_messages = []
        
        # Method 1: Try SocketIO connection first (FIXED)
        try:
            # Use python-socketio client correctly
            sio_client = socketio.Client()
            
            @sio_client.event
            def connect():
                print("✅ Connected to admin panel via SocketIO")
            
            @sio_client.event
            def sos_confirmation(data):
                nonlocal success
                if data.get('status') == 'success':
                    success = True
                    print("✅ SOS confirmed by admin panel")
            
            # Connect and send SOS
            sio_client.connect(ADMIN_PANEL_URL, wait_timeout=10)
            sio_client.emit('user_sos_signal', sos_data)
            sio_client.sleep(3)  # Wait for response
            sio_client.disconnect()
            
            if success:
                emit('sos_sent', {
                    'status': 'success', 
                    'message': 'SOS sent via real-time connection!',
                    'method': 'SocketIO'
                })
                return
                
        except Exception as e:
            error_messages.append(f"SocketIO: {str(e)}")
            print(f"SocketIO connection failed: {e}")
        
        # Method 2: Fallback to HTTP API (FIXED ENDPOINTS)
        try:
            response = requests.post(
                f"{ADMIN_PANEL_URL}/api/emergency/sos", 
                json={'lane_id': 1, 'user_data': sos_data},
                timeout=10,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    success = True
                    print("✅ SOS sent via HTTP API")
                    emit('sos_sent', {
                        'status': 'success',
                        'message': 'SOS sent to emergency services!',
                        'method': 'HTTP API'
                    })
                    return
                else:
                    error_messages.append(f"API error: {result.get('message', 'Unknown error')}")
            else:
                error_messages.append(f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            error_messages.append(f"HTTP API: {str(e)}")
            print(f"HTTP API failed: {e}")
        
        # Method 3: Simple POST fallback (FIXED ENDPOINT)
        try:
            simple_data = {
                'emergency': True,
                'user': sos_data['user'],
                'type': sos_data['emergency_type'],
                'location': sos_data['location'],
                'time': sos_data['timestamp']
            }
            
            response = requests.post(
                f"{ADMIN_PANEL_URL}/api/emergency/simple", 
                data=simple_data,
                timeout=5
            )
            
            if response.status_code in [200, 201, 202]:
                success = True
                emit('sos_sent', {
                    'status': 'success', 
                    'message': 'SOS sent (backup method)!',
                    'method': 'Simple POST'
                })
                return
                
        except Exception as e:
            error_messages.append(f"Simple POST: {str(e)}")
            print(f"Simple POST failed: {e}")
        
        # If all methods failed
        if not success:
            error_msg = "Failed to reach emergency services. " + " | ".join(error_messages[:2])
            emit('sos_sent', {
                'status': 'error', 
                'message': error_msg,
                'details': error_messages
            })
            print(f"❌ All SOS methods failed: {error_messages}")

@app.route('/api/test-connection')
def test_connection():
    """Test connection to admin panel"""
    try:
        response = requests.get(f"{ADMIN_PANEL_URL}/health", timeout=5)
        if response.status_code == 200:
            return {
                'status': 'success', 
                'message': 'Connection to admin panel successful',
                'admin_status': response.json()
            }
        else:
            return {
                'status': 'error', 
                'message': f'Admin panel returned {response.status_code}'
            }
    except Exception as e:
        return {
            'status': 'error', 
            'message': f'Cannot reach admin panel: {str(e)}'
        }

if __name__ == '__main__':
    print("🚀 Starting User App...")
    print(f"📱 User Interface: http://127.0.0.1:5000")
    print(f"🔗 Admin Panel URL: {ADMIN_PANEL_URL}")
    print(f"👥 Demo Users: {list(users.keys())}")
    print("🚨 SOS System: Ready")
    
    socketio_app.run(app, debug=True, host='0.0.0.0', port=5000)
