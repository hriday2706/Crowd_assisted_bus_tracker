from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from typing import Dict, Any
from functools import wraps
from datetime import timedelta, datetime, time
import db as dbm
import threading
import time as time_module

import os
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

# Use environment variable for secret key in production
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'your-secret-key-here')

# Determine if we're running in production
is_production = os.environ.get('FLASK_ENV') == 'production'

# Configure session to be more persistent and support multiple users
app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SECURE=is_production,  # Use secure cookies in production
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME='bus_tracker_session'
)

# Track active sessions
active_sessions = {}

BUS_ID = "S1/A"  # default bus id
QUORUM = 1      # change quorum here if needed

# Track last driver location update time
last_driver_update = {}

# Dummy user database - In a real app, this would be in a database
USERS = {
    "driver1": {
        "password": "driverpass123",
        "role": "driver",
        "bus_id": "S1/A"  # Assigned bus ID
    },
    "student1": {
        "password": "studentpass123",
        "role": "student"
    },
    "student2": {
        "password": "studentpass123",
        "role": "student"
    },
    "student3": {
        "password": "studentpass123",
        "role": "student"
    }
}

from uuid import uuid4

def generate_session_id():
    return str(uuid4())

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_id = session.get('session_id')
        if not session_id or session_id not in active_sessions:
            session.clear()
            return redirect(url_for('login'))
        # Update session data from active_sessions
        session.update(active_sessions[session_id])
        return f(*args, **kwargs)
    return decorated_function

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_id = session.get('session_id')
            if not session_id or session_id not in active_sessions:
                session.clear()
                return redirect(url_for('login'))
            user_data = active_sessions[session_id]
            if user_data.get('role') != role:
                return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def update_session_data():
    """Update active_sessions with current session data"""
    session_id = session.get('session_id')
    if session_id and session_id in active_sessions:
        # Update stored session data
        active_sessions[session_id].update({
            'username': session.get('username'),
            'role': session.get('role'),
            'bus_id': session.get('bus_id'),
            'last_active': datetime.now()
        })

init_done = False
bus_status: Dict[str, str] = {}  # e.g., { BUS_ID: "departing" }

def reset_bus_to_start():
    """Reset bus to starting stop - used for daily reset and manual reset"""
    dbm.reset_bus_to_starting_stop(BUS_ID)
    bus_status.pop(BUS_ID, None)
    last_driver_update.pop(BUS_ID, None)
    app.logger.info(f"Bus {BUS_ID} reset to starting stop")

def daily_reset_scheduler():
    """Background thread that resets the bus at midnight every day"""
    while True:
        now = datetime.now()
        # Calculate time until next midnight
        tomorrow = now + timedelta(days=1)
        midnight = datetime.combine(tomorrow.date(), time(0, 0, 0))
        seconds_until_midnight = (midnight - now).total_seconds()
        
        # Sleep until midnight
        time_module.sleep(seconds_until_midnight)
        
        # Reset the bus
        reset_bus_to_start()
        app.logger.info("Daily automatic reset completed at midnight")

@app.before_request
def ensure_init() -> None:
    global init_done
    if not init_done:
        dbm.init_db()
        # Start daily reset scheduler in background thread
        reset_thread = threading.Thread(target=daily_reset_scheduler, daemon=True)
        reset_thread.start()
        init_done = True


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = USERS.get(username)
        if user and user['password'] == password:
            # Generate new session
            session.permanent = True
            session_id = generate_session_id()
            session['session_id'] = session_id
            session['username'] = username
            session['role'] = user['role']
            
            # Store session data
            session_data = {
                'username': username,
                'role': user['role'],
                'last_active': datetime.now()
            }
            
            if user['role'] == 'driver':
                bus_id = user.get('bus_id', BUS_ID)
                session['bus_id'] = bus_id
                session_data['bus_id'] = bus_id
            
            # Store in active sessions
            active_sessions[session_id] = session_data
            
            if user['role'] == 'driver':
                return redirect(url_for('driver_page'))
            else:
                return redirect(url_for('student_page'))
        
        return render_template('login.html', error='Invalid username or password')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session_id = session.get('session_id')
    if session_id:
        active_sessions.pop(session_id, None)
    session.clear()
    return redirect(url_for('login'))

# Add session cleanup for inactive sessions
def cleanup_inactive_sessions():
    """Remove sessions that have been inactive for more than the session lifetime"""
    now = datetime.now()
    max_age = timedelta(days=7)
    inactive_sessions = [
        sid for sid, data in active_sessions.items()
        if now - data['last_active'] > max_age
    ]
    for sid in inactive_sessions:
        active_sessions.pop(sid, None)

# Add before_request handler to update session activity
@app.before_request
def before_request():
    global init_done
    if not init_done:
        dbm.init_db()
        init_done = True
    
    # Update last active time for current session
    if request.endpoint != 'static':
        update_session_data()
        cleanup_inactive_sessions()

@app.get("/")
def home():
    if 'username' not in session:
        return redirect(url_for('login'))
    if session['role'] == 'driver':
        return redirect(url_for('driver_page'))
    return redirect(url_for('student_page'))

@app.get("/driver")
@login_required
@role_required('driver')
def driver_page():
    return render_template("driver.html", bus_id=session.get('bus_id', BUS_ID))

@app.get("/student")
@login_required
@role_required('student')
def student_page():
    return render_template("student.html", bus_id=BUS_ID)


# Rate limiting for location updates (per user)
last_update_time = {}
MIN_UPDATE_INTERVAL = 1.0  # seconds

# Track last student location update time
last_student_update = {}

# Student location sharing toggle (per bus)
student_location_enabled = {}  # {bus_id: True/False}

# --- API ---
@app.post("/location/share")
@login_required
def share_location():
    """Allow both drivers and students to share location"""
    try:
        user_type = session.get('role')
        
        # Rate limiting check
        user_id = session.get('username')
        now = datetime.now()
        if user_id in last_update_time:
            time_since_last = (now - last_update_time[user_id]).total_seconds()
            if time_since_last < MIN_UPDATE_INTERVAL:
                return jsonify({
                    "error": "Too many updates",
                    "retry_after": MIN_UPDATE_INTERVAL - time_since_last
                }), 429
        
        # Parse and validate input
        data = request.get_json(force=True)
        try:
            bus_id = data.get("bus_id", BUS_ID)
            lat = float(data.get("lat"))
            lon = float(data.get("lon"))
            accuracy = float(data.get("accuracy", 20.0))
            
            # Basic validation
            if not (-90 <= lat <= 90) or not (-180 <= lon <= 180) or accuracy <= 0:
                return jsonify({"error": "Invalid coordinates or accuracy"}), 400
                
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid location data"}), 400
        
        # Check if student location sharing is enabled for this bus
        if user_type == 'student':
            if not student_location_enabled.get(bus_id, False):
                return jsonify({"error": "Student location sharing is disabled"}), 403
        
        # Store location in database for all users
        dbm.update_user_location(bus_id, user_id, user_type, lat, lon, accuracy)
        last_update_time[user_id] = now
        
        # Update last update time based on user type
        if user_type == 'driver':
            last_driver_update[bus_id] = now
        else:  # student
            last_student_update[bus_id] = now
        
        # Priority logic: Determine if this user should update bus position
        # Priority: Driver GPS > Student GPS > Manual controls
        should_update_bus = False
        location_source = None
        
        if user_type == 'driver':
            # Driver always updates bus position
            should_update_bus = True
            location_source = 'driver'
        elif user_type == 'student':
            # Student only updates if driver GPS is not active (>30 seconds old)
            if bus_id not in last_driver_update:
                should_update_bus = True
                location_source = 'student'
            else:
                seconds_since_driver = (now - last_driver_update[bus_id]).total_seconds()
                if seconds_since_driver > 30:
                    should_update_bus = True
                    location_source = 'student'
        
        # Update bus position if this is the authoritative source
        if should_update_bus:
            
            # Check proximity to stops FIRST (within 50 meters)
            proximity_result = dbm.check_stop_proximity(bus_id, lat, lon, radius_meters=50)
            
            current_state = dbm.get_bus_state(bus_id)
            
            if proximity_result:
                # Driver is near a stop (within 50m)
                stop_id = proximity_result['id']
                stop_index = proximity_result['seq']
                
                # Snap to stop coordinates for clean positioning
                state = dbm.set_bus_to_stop(bus_id, stop_index)
                bus_status[bus_id] = "arrived"
                
                app.logger.info(f"Bus {bus_id} arrived at stop {proximity_result['name']} (within 50m)")
            else:
                # Not near any stop - update to exact GPS coordinates
                state = dbm.update_bus_location(bus_id, lat, lon)
                
                # Determine if departing from current stop
                if current_state and current_state['stop_index'] is not None:
                    current_stop = dbm.current_stop_for_index(current_state['stop_index'])
                    if current_stop:
                        # Check distance from current stop
                        distance_from_current = dbm.calculate_distance(
                            lat, lon, current_stop['lat'], current_stop['lon']
                        )
                        
                        if distance_from_current > 50:
                            # Moving away from current stop
                            bus_status[bus_id] = "departing"
                            # Get next stop for status message
                            next_stop = dbm.current_stop_for_index(current_state['stop_index'] + 1)
                            if next_stop:
                                app.logger.info(f"Bus {bus_id} departing to {next_stop['name']}")
                        else:
                            # Still near current stop but not snapped
                            bus_status[bus_id] = "arrived"
                    else:
                        bus_status[bus_id] = "departing"
                else:
                    bus_status[bus_id] = "departing"
        
        # Get updated state and stop info
        state = dbm.get_bus_state(bus_id)
        if state:
            state = dict(state)
            stop = dbm.current_stop_for_index(state.get("stop_index", 0))
            state.update({
                "stop_name": stop["name"] if stop else None,
                "stop_id": stop["id"] if stop else None,
                "status": bus_status.get(bus_id),
                "accuracy": accuracy,
                "user_type": user_type,  # Include user type in response
                "location_source": location_source if should_update_bus else None,
                "updated_bus": should_update_bus  # Did this update move the bus?
            })
        
        return jsonify(state)
        
    except Exception as e:
        app.logger.error(f"Error in location sharing: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.get("/location/active")
@login_required
def get_active_locations():
    """Get all active location sharers for the bus"""
    bus_id = request.args.get("bus_id", BUS_ID)
    
    try:
        # Get recent locations
        locations = dbm.get_recent_locations(bus_id, max_age_seconds=60)
        if not locations:
            return jsonify({
                "active_users": 0,
                "clusters": [],
                "last_update": None
            })
        
        # Get current clusters
        clusters = dbm.find_location_clusters(bus_id, max_radius=80.0, min_points=2)
        
        # Process driver information
        driver_locations = [loc for loc in locations if loc['user_type'] == 'driver']
        driver_info = None
        if driver_locations:
            latest_driver = max(driver_locations, key=lambda x: x['timestamp'])
            driver_info = {
                "last_update": latest_driver['timestamp'],
                "accuracy": latest_driver['accuracy']
            }
        
        # Process student information
        student_locations = [loc for loc in locations if loc['user_type'] == 'student']
        student_info = {
            "count": len(student_locations),
            "last_update": max(loc['timestamp'] for loc in student_locations) if student_locations else None,
            "average_accuracy": sum(loc['accuracy'] for loc in student_locations) / len(student_locations) if student_locations else None
        }
        
        # Process cluster information
        cluster_info = [{
            "center_lat": c['center_lat'],
            "center_lon": c['center_lon'],
            "radius": c['radius'],
            "point_count": len(c['points']),
            "is_majority": len(c['points']) > len(locations) / 2,
            "source": c['source']
        } for c in clusters]
        
        return jsonify({
            "driver": driver_info,
            "students": student_info,
            "clusters": cluster_info,
            "active_users": len(locations),
            "last_update": max(loc['timestamp'] for loc in locations)
        })
        
    except Exception as e:
        app.logger.error(f"Error getting active locations: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.get("/bus/<path:bus_id>")
@login_required
def get_bus(bus_id: str):
    state = dbm.get_bus_state(bus_id)
    if not state:
        return jsonify({}), 404
    stop = dbm.current_stop_for_index(state["stop_index"])
    state = dict(state)
    state["stop_name"] = stop["name"] if stop else None
    state["stop_id"] = stop["id"] if stop else None
    state["status"] = bus_status.get(bus_id)
    return jsonify(state)

@app.get("/stops")
@login_required
def get_stops():
    rows = dbm.get_stops()
    return jsonify([dict(r) for r in rows])

@app.post("/driver/departed")
@login_required
@role_required('driver')
def driver_departed():
    """Only use if driver location is outdated (>30 seconds)"""
    data = request.get_json(force=True)
    bus_id = data.get("bus_id", BUS_ID)
    
    # verify the driver is assigned to this bus
    if bus_id != session.get('bus_id'):
        return jsonify({"error": "unauthorized"}), 403
    
    # Check if we have recent driver or student location
    now = datetime.now()
    gps_active = False
    gps_source = None
    
    # Priority 1: Check driver GPS
    if bus_id in last_driver_update:
        seconds_since_update = (now - last_driver_update[bus_id]).total_seconds()
        if seconds_since_update < 30:
            gps_active = True
            gps_source = 'driver'
    
    # Priority 2: Check student GPS if driver not active
    if not gps_active and bus_id in last_student_update:
        seconds_since_update = (now - last_student_update[bus_id]).total_seconds()
        if seconds_since_update < 30:
            gps_active = True
            gps_source = 'student'
    
    if gps_active:
        return jsonify({
            "error": "Using live GPS - manual control disabled",
            "message": f"Bus position is being tracked via {gps_source} GPS",
            "gps_active": True,
            "gps_source": gps_source
        }), 400
    
    # Fallback: set status to departing without moving
    bus_status[bus_id] = "departing"
    state = dbm.get_bus_state(bus_id)
    if not state:
        return jsonify({}), 404
    stop = dbm.current_stop_for_index(state["stop_index"])
    resp = dict(state)
    resp["stop_name"] = stop["name"] if stop else None
    resp["stop_id"] = stop["id"] if stop else None
    resp["status"] = bus_status.get(bus_id)
    resp["gps_active"] = False
    return jsonify(resp)

@app.post("/driver/arrived")
@login_required
@role_required('driver')
def driver_arrived():
    """Only use if driver location is outdated (>30 seconds)"""
    data = request.get_json(force=True)
    bus_id = data.get("bus_id", BUS_ID)
    
    # verify the driver is assigned to this bus
    if bus_id != session.get('bus_id'):
        return jsonify({"error": "unauthorized"}), 403
    
    # Check if we have recent driver or student location
    now = datetime.now()
    gps_active = False
    gps_source = None
    
    # Priority 1: Check driver GPS
    if bus_id in last_driver_update:
        seconds_since_update = (now - last_driver_update[bus_id]).total_seconds()
        if seconds_since_update < 30:
            gps_active = True
            gps_source = 'driver'
    
    # Priority 2: Check student GPS if driver not active
    if not gps_active and bus_id in last_student_update:
        seconds_since_update = (now - last_student_update[bus_id]).total_seconds()
        if seconds_since_update < 30:
            gps_active = True
            gps_source = 'student'
    
    if gps_active:
        return jsonify({
            "error": "Using live GPS - manual control disabled",
            "message": f"Bus position is being tracked via {gps_source} GPS",
            "gps_active": True,
            "gps_source": gps_source
        }), 400
    
    action = data.get("action")
    if action != "arrived":
        return jsonify({"error": "invalid action"}), 400
    
    # Fallback: clear status when arriving
    bus_status.pop(bus_id, None)
    state = dbm.move_bus_to_next_stop(bus_id)
    stop = dbm.current_stop_for_index(state.get("stop_index", 0))
    state["stop_name"] = stop["name"] if stop else None
    state["stop_id"] = stop["id"] if stop else None
    state["status"] = bus_status.get(bus_id)
    state["gps_active"] = False
    return jsonify(state)

@app.post("/driver/reset")
@login_required
@role_required('driver')
def driver_reset():
    """Manual reset button for driver - resets bus to starting stop"""
    data = request.get_json(force=True)
    bus_id = data.get("bus_id", BUS_ID)
    
    # verify the driver is assigned to this bus
    if bus_id != session.get('bus_id'):
        return jsonify({"error": "unauthorized"}), 403
    
    # Reset bus to start
    reset_bus_to_start()
    
    # Get updated state
    state = dbm.get_bus_state(bus_id)
    if state:
        state = dict(state)
        stop = dbm.current_stop_for_index(state.get("stop_index", 0))
        state.update({
            "stop_name": stop["name"] if stop else None,
            "stop_id": stop["id"] if stop else None,
            "status": bus_status.get(bus_id),
            "gps_active": False
        })
        return jsonify(state)
    
    return jsonify({"error": "Failed to reset bus"}), 500

@app.post("/location/stop")
@login_required
@role_required('driver')
def stop_location_sharing():
    """Immediately stop GPS tracking and enable manual controls"""
    bus_id = session.get('bus_id', BUS_ID)
    
    # Clear the GPS timestamp to immediately enable manual controls
    last_driver_update.pop(bus_id, None)
    
    app.logger.info(f"GPS tracking stopped for bus {bus_id} - manual controls enabled")
    
    return jsonify({
        "message": "GPS tracking stopped",
        "gps_active": False
    })

@app.post("/driver/toggle-student-location")
@login_required
@role_required('driver')
def toggle_student_location():
    """Toggle student location sharing on/off"""
    data = request.get_json(force=True)
    bus_id = data.get("bus_id", BUS_ID)
    enabled = data.get("enabled", False)
    
    # Verify the driver is assigned to this bus
    if bus_id != session.get('bus_id'):
        return jsonify({"error": "unauthorized"}), 403
    
    # Update the toggle state
    student_location_enabled[bus_id] = enabled
    
    # If disabling, clear all student location updates
    if not enabled:
        last_student_update.pop(bus_id, None)
        app.logger.info(f"Student location sharing disabled for bus {bus_id}")
    else:
        app.logger.info(f"Student location sharing enabled for bus {bus_id}")
    
    return jsonify({
        "bus_id": bus_id,
        "student_location_enabled": enabled,
        "message": f"Student location sharing {'enabled' if enabled else 'disabled'}"
    })

@app.get("/driver/student-location-status")
@login_required
@role_required('driver')
def get_student_location_status():
    """Get current student location sharing status"""
    bus_id = request.args.get("bus_id", BUS_ID)
    
    # Verify the driver is assigned to this bus
    if bus_id != session.get('bus_id'):
        return jsonify({"error": "unauthorized"}), 403
    
    return jsonify({
        "bus_id": bus_id,
        "student_location_enabled": student_location_enabled.get(bus_id, False)
    })

@app.get("/student/location-status")
@login_required
@role_required('student')
def get_student_sharing_status():
    """Check if student location sharing is enabled"""
    bus_id = request.args.get("bus_id", BUS_ID)
    
    return jsonify({
        "bus_id": bus_id,
        "enabled": student_location_enabled.get(bus_id, False)
    })

@app.post("/student/arrived")
@login_required
@role_required('student')
def student_arrived():
    """Students can confirm arrival - but only moves bus if GPS is inactive (>30s)"""
    data = request.get_json(force=True)
    bus_id = data.get("bus_id", BUS_ID)
    student_id = session.get('username', 'S1')  # Use logged in username as student ID

    # Check if driver's or student's GPS is active
    now = datetime.now()
    gps_active = False
    gps_source = None
    
    # Priority 1: Check driver GPS
    if bus_id in last_driver_update:
        seconds_since_update = (now - last_driver_update[bus_id]).total_seconds()
        if seconds_since_update < 30:
            gps_active = True
            gps_source = 'driver'
    
    # Priority 2: Check student GPS if driver not active
    if not gps_active and bus_id in last_student_update:
        seconds_since_update = (now - last_student_update[bus_id]).total_seconds()
        if seconds_since_update < 30:
            gps_active = True
            gps_source = 'student'

    state = dbm.get_bus_state(bus_id)
    if not state:
        return jsonify({"error": "bus not found"}), 404

    stop_index = state["stop_index"]
    stop = dbm.current_stop_for_index(stop_index)
    if not stop:
        return jsonify({"error": "stop not found"}), 404

    # Always record the confirmation
    dbm.insert_confirmation(bus_id, stop["id"], "student", student_id)
    cnt = dbm.count_confirmations(bus_id, stop["id"])

    moved = False
    new_state: Dict[str, Any] = dict(state)
    
    # Only move bus if GPS is NOT active and quorum is reached
    if cnt >= QUORUM and not gps_active:
        new_state = dbm.move_bus_to_next_stop(bus_id)
        moved = True
        bus_status.pop(bus_id, None)
    elif cnt >= QUORUM and gps_active:
        # Quorum reached but GPS is active - don't move
        app.logger.info(f"Student confirmation quorum reached for bus {bus_id}, but GPS is active - ignoring manual control")

    # augment response
    curr_stop = dbm.current_stop_for_index(new_state.get("stop_index", 0))
    new_state["stop_name"] = curr_stop["name"] if curr_stop else None
    new_state["stop_id"] = curr_stop["id"] if curr_stop else None
    new_state["status"] = bus_status.get(bus_id)
    new_state["gps_active"] = gps_active  # Add GPS status to response

    return jsonify({"confirmations": cnt, "moved": moved, "state": new_state, "gps_active": gps_active})

@app.get("/confirmations")
@login_required
def get_confirmations():
    bus_id = request.args.get("bus_id", BUS_ID)
    stop_id = int(request.args.get("stop_id", "0"))
    cnt = dbm.count_confirmations(bus_id, stop_id)
    return jsonify({"bus_id": bus_id, "stop_id": stop_id, "confirmations": cnt})

@app.get("/gps/status")
@login_required
def get_gps_status():
    """Check if driver's GPS is currently active"""
    bus_id = request.args.get("bus_id", BUS_ID)
    
    now = datetime.now()
    gps_active = False
    last_update_time = None
    
    if bus_id in last_driver_update:
        last_update_time = last_driver_update[bus_id]
        seconds_since_update = (now - last_update_time).total_seconds()
        if seconds_since_update < 30:
            gps_active = True
    
    return jsonify({
        "bus_id": bus_id,
        "gps_active": gps_active,
        "last_update": last_update_time.isoformat() if last_update_time else None
    })


if __name__ == "__main__":
    dbm.init_db()
    app.run(debug=True) 