import sqlite3
from datetime import datetime, timezone, timedelta
from typing import List, Tuple, Optional, Dict, Any

DB_PATH = "bus.db"
DEFAULT_BUS_ID = "S1/A"

SEED_STOPS: List[Tuple[str, float, float, int]] = [
    ('Starting Point', 17.495643, 78.335691, 0),
    ('Stop A', 17.495255, 78.340605, 1), 
    ('Stop B', 17.496050, 78.358307, 2),
    ('Stop C', 17.496639, 78.366014, 3),
    ('Stop D', 17.497767, 78.377978, 4),
    ('Stop E', 17.498739, 78.389480, 4),
    ('Stop F', 17.511779, 78.384217, 5),
    ('Stop G', 17.528937, 78.385203, 6),
    ('VNR', 17.541772, 78.386868, 7),
]

def iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()
    
    # Create stops table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS stops(
            id INTEGER PRIMARY KEY,
            name TEXT,
            lat REAL,
            lon REAL,
            seq INTEGER
        )
        """
    )
    
    # Create enhanced bus_state table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bus_state(
            bus_id TEXT PRIMARY KEY,
            stop_index INTEGER,
            lat REAL,
            lon REAL,
            timestamp TEXT,
            status TEXT,  -- 'arrived', 'departing', etc
            location_source TEXT,  -- 'driver', 'students', 'last_known'
            location_accuracy REAL,
            sample_size INTEGER,
            last_arrival_time TEXT,
            last_departure_time TEXT
        )
        """
    )
    
    # Create confirmations table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS confirmations(
            id INTEGER PRIMARY KEY,
            bus_id TEXT,
            stop_id INTEGER,
            user_type TEXT,
            user_id TEXT,
            timestamp TEXT
        )
        """
    )
    
    # Create enhanced user_locations table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_locations(
            id INTEGER PRIMARY KEY,
            bus_id TEXT,
            user_id TEXT,
            user_type TEXT,
            lat REAL,
            lon REAL,
            accuracy REAL,
            speed REAL,
            heading REAL,
            timestamp TEXT,
            cluster_id INTEGER,  -- For tracking which cluster this point belongs to
            weight REAL,         -- For weighted aggregation
            UNIQUE(bus_id, user_id) ON CONFLICT REPLACE
        )
        """
    )
    
    # Create location_clusters table
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS location_clusters(
            id INTEGER PRIMARY KEY,
            bus_id TEXT,
            lat REAL,
            lon REAL,
            radius REAL,
            point_count INTEGER,
            total_points INTEGER,
            timestamp TEXT,
            is_majority BOOLEAN
        )
        """
    )
    conn.commit()

    # Reseed stops every run to enforce the configured list
    cur.execute("DELETE FROM stops")
    for name, lat, lon, seq in SEED_STOPS:
        cur.execute(
            "INSERT INTO stops(name, lat, lon, seq) VALUES (?, ?, ?, ?)",
            (name, lat, lon, seq),
        )
    conn.commit()

    # Reset bus to first stop every run
    cur.execute("SELECT id, lat, lon FROM stops ORDER BY seq LIMIT 1")
    first = cur.fetchone()
    if first:
        stop_index = 0
        lat = first[1]
        lon = first[2]
        ts = iso_now()
        cur.execute(
            "REPLACE INTO bus_state(bus_id, stop_index, lat, lon, timestamp) VALUES (?, ?, ?, ?, ?)",
            (DEFAULT_BUS_ID, stop_index, lat, lon, ts),
        )
        # Clear confirmations on startup for simplicity
        cur.execute("DELETE FROM confirmations")
        conn.commit()
    conn.close()


def get_stops() -> List[sqlite3.Row]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM stops ORDER BY seq").fetchall()
    conn.close()
    return rows


def get_bus_state(bus_id: str) -> Optional[sqlite3.Row]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM bus_state WHERE bus_id = ?", (bus_id,)
    ).fetchone()
    conn.close()
    return row


def update_bus_location(bus_id: str, lat: float, lon: float) -> Dict[str, Any]:
    ts = iso_now()
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE bus_state SET lat = ?, lon = ?, timestamp = ? WHERE bus_id = ?",
        (lat, lon, ts, bus_id),
    )
    conn.commit()
    row = cur.execute(
        "SELECT * FROM bus_state WHERE bus_id = ?", (bus_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def move_bus_to_next_stop(bus_id: str) -> Dict[str, Any]:
    conn = get_conn()
    cur = conn.cursor()
    bus = cur.execute(
        "SELECT * FROM bus_state WHERE bus_id = ?", (bus_id,)
    ).fetchone()
    stops = cur.execute("SELECT * FROM stops ORDER BY seq").fetchall()
    if not bus or not stops:
        conn.close()
        return {}

    current_index = bus["stop_index"]
    next_index = current_index + 1
    if next_index >= len(stops):
        # Stay at last stop by default
        next_index = current_index
    target_stop = stops[next_index]

    ts = iso_now()
    cur.execute(
        "UPDATE bus_state SET stop_index = ?, lat = ?, lon = ?, timestamp = ? WHERE bus_id = ?",
        (next_index, target_stop["lat"], target_stop["lon"], ts, bus_id),
    )
    conn.commit()
    new_state = cur.execute(
        "SELECT * FROM bus_state WHERE bus_id = ?", (bus_id,)
    ).fetchone()
    conn.close()
    return dict(new_state) if new_state else {}


def insert_confirmation(bus_id: str, stop_id: int, user_type: str, user_id: str) -> None:
    conn = get_conn()
    conn.execute(
        "INSERT INTO confirmations(bus_id, stop_id, user_type, user_id, timestamp) VALUES (?, ?, ?, ?, ?)",
        (bus_id, stop_id, user_type, user_id, iso_now()),
    )
    conn.commit()
    conn.close()


def count_confirmations(bus_id: str, stop_id: int) -> int:
    conn = get_conn()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM confirmations WHERE bus_id = ? AND stop_id = ?",
        (bus_id, stop_id),
    ).fetchone()
    conn.close()
    return int(row[0]) if row else 0


def current_stop_for_index(stop_index: int) -> Optional[sqlite3.Row]:
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM stops WHERE seq = ?", (stop_index,)
    ).fetchone()
    conn.close()
    return row

def reset_bus_to_starting_stop(bus_id: str) -> Dict[str, Any]:
    """Reset bus to the first stop (stop_index = 0)"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get first stop
    first_stop = cur.execute(
        "SELECT * FROM stops ORDER BY seq LIMIT 1"
    ).fetchone()
    
    if not first_stop:
        conn.close()
        return {}
    
    ts = iso_now()
    cur.execute(
        """UPDATE bus_state 
           SET stop_index = 0, lat = ?, lon = ?, timestamp = ?, 
               status = NULL, location_source = NULL
           WHERE bus_id = ?""",
        (first_stop["lat"], first_stop["lon"], ts, bus_id)
    )
    conn.commit()
    
    # Clear confirmations
    cur.execute("DELETE FROM confirmations WHERE bus_id = ?", (bus_id,))
    conn.commit()
    
    # Get updated state
    new_state = cur.execute(
        "SELECT * FROM bus_state WHERE bus_id = ?", (bus_id,)
    ).fetchone()
    conn.close()
    
    return dict(new_state) if new_state else {}

def set_bus_to_stop(bus_id: str, stop_index: int) -> Dict[str, Any]:
    """Set bus to a specific stop index"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get target stop
    stop = cur.execute(
        "SELECT * FROM stops WHERE seq = ?", (stop_index,)
    ).fetchone()
    
    if not stop:
        conn.close()
        return {}
    
    ts = iso_now()
    cur.execute(
        """UPDATE bus_state 
           SET stop_index = ?, lat = ?, lon = ?, timestamp = ?
           WHERE bus_id = ?""",
        (stop_index, stop["lat"], stop["lon"], ts, bus_id)
    )
    conn.commit()
    
    # Get updated state
    new_state = cur.execute(
        "SELECT * FROM bus_state WHERE bus_id = ?", (bus_id,)
    ).fetchone()
    conn.close()
    
    return dict(new_state) if new_state else {} 

def check_stop_proximity(bus_id: str, lat: float, lon: float) -> Dict[str, Any]:
    """
    Check proximity to stops using dual-radius system
    Returns dict with:
    - arrived: bool - whether bus has arrived at a stop
    - departed: bool - whether bus has departed from current stop
    - next_stop: bool - whether near next stop
    - stop_id: int - ID of relevant stop if any
    """
    ARRIVAL_RADIUS = 40  # meters
    DEPARTURE_RADIUS = 80  # meters
    
    conn = get_conn()
    cur = conn.cursor()
    
    # Get current bus state
    state = cur.execute("""
        SELECT stop_index, status, last_arrival_time, last_departure_time
        FROM bus_state WHERE bus_id = ?
    """, (bus_id,)).fetchone()
    
    if not state:
        conn.close()
        return {'arrived': False, 'departed': False, 'next_stop': False}
    
    current_stop = cur.execute("""
        SELECT * FROM stops WHERE seq = ?
    """, (state['stop_index'],)).fetchone()
    
    next_stop = cur.execute("""
        SELECT * FROM stops WHERE seq = ?
    """, (state['stop_index'] + 1,)).fetchone()
    
    result = {
        'arrived': False,
        'departed': False,
        'next_stop': False,
        'stop_id': None
    }
    
    # Check current stop
    if current_stop:
        dist = calculate_distance(lat, lon, current_stop['lat'], current_stop['lon'])
        if dist <= ARRIVAL_RADIUS and state['status'] != 'arrived':
            result['arrived'] = True
            result['stop_id'] = current_stop['id']
        elif dist > DEPARTURE_RADIUS and state['status'] == 'arrived':
            # Only mark as departed if we've been at the stop for at least 10 seconds
            if state['last_arrival_time']:
                arrival_time = datetime.fromisoformat(state['last_arrival_time'])
                if datetime.now(timezone.utc) - arrival_time > timedelta(seconds=10):
                    result['departed'] = True
                    result['stop_id'] = current_stop['id']
    
    # Check next stop
    if next_stop and not result['arrived'] and not result['departed']:
        dist = calculate_distance(lat, lon, next_stop['lat'], next_stop['lon'])
        if dist <= ARRIVAL_RADIUS:
            result['next_stop'] = True
            result['stop_id'] = next_stop['id']
    
    conn.close()
    return result

def update_bus_state_with_location(bus_id: str, location: Dict[str, Any]) -> Dict[str, Any]:
    """Update bus state with new location data and handle stop proximity"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Update location and basic state
    now = iso_now()
    cur.execute("""
        UPDATE bus_state 
        SET lat = ?, lon = ?, location_accuracy = ?, 
            location_source = ?, sample_size = ?,
            timestamp = ?
        WHERE bus_id = ?
    """, (
        location['center_lat'], location['center_lon'],
        location.get('accuracy', None),
        location['source'],
        len(location['points']) if 'points' in location else None,
        now, bus_id
    ))
    
    # Check stop proximity
    proximity = check_stop_proximity(
        bus_id, location['center_lat'], location['center_lon']
    )
    
    if proximity['arrived']:
        # Mark as arrived at current stop
        cur.execute("""
            UPDATE bus_state 
            SET status = 'arrived', last_arrival_time = ?
            WHERE bus_id = ?
        """, (now, bus_id))
    elif proximity['departed']:
        # Mark as departed from current stop
        cur.execute("""
            UPDATE bus_state 
            SET status = 'departing', last_departure_time = ?
            WHERE bus_id = ?
        """, (now, bus_id))
    elif proximity['next_stop']:
        # Move to next stop
        cur.execute("""
            UPDATE bus_state 
            SET stop_index = stop_index + 1,
                status = 'arrived',
                last_arrival_time = ?
            WHERE bus_id = ?
        """, (now, bus_id))
    
    conn.commit()
    
    # Get updated state
    state = cur.execute("""
        SELECT * FROM bus_state WHERE bus_id = ?
    """, (bus_id,)).fetchone()
    
    conn.close()
    return dict(state) if state else {}

def update_user_location(bus_id: str, user_id: str, user_type: str, lat: float, lon: float, accuracy: float) -> None:
    """Update a user's location in the database"""
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO user_locations(bus_id, user_id, user_type, lat, lon, accuracy, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (bus_id, user_id, user_type, lat, lon, accuracy, iso_now())
    )
    conn.commit()
    conn.close()

def get_recent_locations(bus_id: str, max_age_seconds: int = 60) -> List[sqlite3.Row]:
    """Get all locations reported within the last max_age_seconds"""
    conn = get_conn()
    cutoff_time = (datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)).isoformat()
    rows = conn.execute(
        """
        SELECT * FROM user_locations 
        WHERE bus_id = ? AND timestamp > ?
        ORDER BY timestamp DESC
        """,
        (bus_id, cutoff_time)
    ).fetchall()
    conn.close()
    return rows

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters using Haversine formula"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371000  # Earth radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c

def find_location_clusters(bus_id: str, max_radius: float = 80.0, min_points: int = 2) -> List[Dict[str, Any]]:
    """Find clusters of location points using a simple distance-based approach"""
    conn = get_conn()
    cur = conn.cursor()
    
    # Get recent locations (last 30 seconds)
    cutoff_time = (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat()
    locations = cur.execute("""
        SELECT id, lat, lon, accuracy, user_type
        FROM user_locations
        WHERE bus_id = ? AND timestamp > ?
        ORDER BY timestamp DESC
    """, (bus_id, cutoff_time)).fetchall()
    
    if not locations:
        return []
    
    # Initialize clusters
    clusters = []
    used_points = set()
    
    # Process driver locations first
    driver_locations = [loc for loc in locations if loc['user_type'] == 'driver']
    if driver_locations:
        driver_loc = driver_locations[0]  # Most recent driver location
        # Create a cluster centered on driver
        near_points = []
        for loc in locations:
            if calculate_distance(driver_loc['lat'], driver_loc['lon'], 
                               loc['lat'], loc['lon']) <= max_radius:
                near_points.append(loc)
        
        if len(near_points) >= min_points:
            clusters.append({
                'center_lat': driver_loc['lat'],
                'center_lon': driver_loc['lon'],
                'radius': max_radius,
                'points': near_points,
                'source': 'driver'
            })
            used_points.update(p['id'] for p in near_points)
    
    # Process remaining points
    for loc in locations:
        if loc['id'] in used_points:
            continue
            
        # Find all points within radius
        near_points = []
        for other in locations:
            if other['id'] not in used_points:
                dist = calculate_distance(loc['lat'], loc['lon'], 
                                       other['lat'], other['lon'])
                if dist <= max_radius:
                    near_points.append(other)
        
        if len(near_points) >= min_points:
            # Calculate weighted centroid
            total_weight = 0
            weighted_lat = 0
            weighted_lon = 0
            
            for p in near_points:
                # Weight by inverse square of accuracy (capped at 5m)
                weight = 1 / max(p['accuracy'], 5.0)**2
                total_weight += weight
                weighted_lat += p['lat'] * weight
                weighted_lon += p['lon'] * weight
            
            center_lat = weighted_lat / total_weight
            center_lon = weighted_lon / total_weight
            
            # Verify all points are within radius of centroid
            max_dist = 0
            valid_points = []
            for p in near_points:
                dist = calculate_distance(center_lat, center_lon, p['lat'], p['lon'])
                if dist <= max_radius:
                    valid_points.append(p)
                    max_dist = max(max_dist, dist)
            
            if len(valid_points) >= min_points:
                clusters.append({
                    'center_lat': center_lat,
                    'center_lon': center_lon,
                    'radius': max_dist,
                    'points': valid_points,
                    'source': 'students'
                })
                used_points.update(p['id'] for p in valid_points)
    
    # Sort clusters by number of points
    clusters.sort(key=lambda c: len(c['points']), reverse=True)
    
    # Store clusters in database
    cur.execute("DELETE FROM location_clusters WHERE bus_id = ?", (bus_id,))
    for i, cluster in enumerate(clusters):
        is_majority = (len(cluster['points']) > len(locations) / 2)
        cur.execute("""
            INSERT INTO location_clusters (
                bus_id, lat, lon, radius, point_count, 
                total_points, timestamp, is_majority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            bus_id, cluster['center_lat'], cluster['center_lon'],
            cluster['radius'], len(cluster['points']),
            len(locations), iso_now(), is_majority
        ))
        
        # Update cluster_id for points
        point_ids = ','.join(str(p['id']) for p in cluster['points'])
        cur.execute(f"""
            UPDATE user_locations 
            SET cluster_id = ?
            WHERE id IN ({point_ids})
        """, (i + 1,))
    
    conn.commit()
    conn.close()
    
    return clusters

def check_stop_proximity(bus_id: str, lat: float, lon: float, radius_meters: float = 40) -> Optional[Dict[str, Any]]:
    """
    Check if the given location is near any stop within radius_meters.
    Returns the nearest stop if within radius, None otherwise.
    """
    conn = get_conn()
    stops = conn.execute("SELECT * FROM stops ORDER BY seq").fetchall()
    conn.close()
    
    nearest_stop = None
    min_distance = float('inf')
    
    for stop in stops:
        distance = calculate_distance(lat, lon, stop['lat'], stop['lon'])
        if distance <= radius_meters and distance < min_distance:
            min_distance = distance
            nearest_stop = dict(stop)
    
    return nearest_stop

def get_aggregated_location(bus_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the aggregated location for a bus based on recent user locations.
    Driver location takes priority if available.
    """
    # Get recent locations (last 60 seconds)
    locations = get_recent_locations(bus_id, 60)
    if not locations:
        return None
        
    # Check for driver location first
    driver_locations = [loc for loc in locations if loc['user_type'] == 'driver']
    if driver_locations:
        # Use most recent driver location
        driver_loc = driver_locations[0]
        return {
            'lat': driver_loc['lat'],
            'lon': driver_loc['lon'],
            'accuracy': driver_loc['accuracy'],
            'source': 'driver'
        }
    
    # Filter to student locations only
    student_locations = [loc for loc in locations if loc['user_type'] == 'student']
    if not student_locations:
        return None
        
    # Find clusters of locations (simplified - using average)
    total_lat = sum(loc['lat'] for loc in student_locations)
    total_lon = sum(loc['lon'] for loc in student_locations)
    avg_lat = total_lat / len(student_locations)
    avg_lon = total_lon / len(student_locations)
    
    # Calculate average accuracy
    avg_accuracy = sum(loc['accuracy'] for loc in student_locations) / len(student_locations)
    
    return {
        'lat': avg_lat,
        'lon': avg_lon,
        'accuracy': avg_accuracy,
        'source': 'students',
        'sample_size': len(student_locations)
    }