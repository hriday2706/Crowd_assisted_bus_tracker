# Bus Tracker - Real-Time GPS-Based Transportation Management System

A sophisticated real-time GPS tracking system for school/college bus transportation with intelligent location priority management, automatic stop detection, and role-based user interfaces.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0.3-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Location Priority Logic](#location-priority-logic)
- [User Roles](#user-roles)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [API Documentation](#api-documentation)
- [Database Schema](#database-schema)
- [Deployment](#deployment)
- [Technical Details](#technical-details)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

The Bus Tracker is a web-based real-time transportation management system designed for educational institutions. It provides live GPS tracking, intelligent stop detection, and a hierarchical location priority system that ensures accurate bus positioning through driver GPS, student GPS (when enabled), or manual controls.

### Key Capabilities

- **Intelligent Location Priority**: Driver GPS → Student GPS → Manual Controls
- **Automatic Stop Detection**: Proximity-based detection with 50-meter radius
- **Snap-to-Stop Positioning**: Clean map display with automatic coordinate snapping
- **Driver Control Panel**: Enable/disable student location sharing, manage bus position
- **Student Tracking Interface**: Real-time bus monitoring with location sharing capability
- **Daily Automatic Reset**: Returns bus to starting point at midnight
- **Responsive Mobile Design**: Optimized for smartphones and tablets
- **Session Management**: Secure, persistent multi-user sessions

## ✨ Features

### Core Functionality

#### Real-Time GPS Tracking
- **Driver Location Priority**: Highest priority source for bus position
- **Student Location Support**: Optional secondary GPS source (driver-controlled)
- **Rate Limiting**: 1 update per second per user to prevent spam
- **Accuracy Tracking**: Monitors and displays GPS accuracy for each update
- **Continuous Updates**: Real-time position tracking while GPS is active

#### Intelligent Stop Detection
- **Proximity Detection**: Automatically detects when within 50 meters of a stop
- **Snap-to-Stop**: Bus marker snaps to exact stop coordinates for clean display
- **Auto-Arrival**: Changes status to "arrived" when entering stop radius
- **Auto-Departure**: Changes status to "departing" when leaving stop radius
- **Next Stop Indication**: Shows destination stop when bus is in transit

#### Location Priority System
**Three-Tier Hierarchy:**
1. **Driver GPS** (Highest Priority): Always overrides other sources when active (<30s old)
2. **Student GPS** (Secondary): Used only when driver GPS is inactive (>30s) and enabled by driver
3. **Manual Controls** (Fallback): Buttons work only when all GPS sources are inactive (>30s)

#### Driver Control Panel
- **Student Location Toggle**: Enable/disable student GPS sharing with one click
- **Real-time Monitoring**: View current stop, next stop, and bus status
- **GPS Tracking Control**: Start/stop driver location sharing
- **Manual Override**: Departed/Arrived buttons (blocked when GPS is active)
- **Bus Reset**: Return bus to starting stop for testing or daily restart
- **Logout Access**: Convenient logout button below next stop information

#### Student Interface
- **Live Bus Tracking**: See real-time bus position on interactive map
- **Location Sharing**: Share GPS location when enabled by driver
- **Disabled State Handling**: Button automatically disabled when driver blocks sharing
- **Status Monitoring**: View bus status (at stop, moving, etc.)
- **Arrival Confirmation**: Optional button to confirm bus arrival
- **Map Navigation**: Pan, zoom, and center on bus button

#### Additional Features
- **Daily Midnight Reset**: Automatic bus reset to starting point at 00:00
- **Toast Notifications**: User-friendly feedback for all actions
- **Mobile-First Design**: Optimized spacing and touch targets
- **Session Persistence**: 7-day session lifetime with automatic cleanup
- **Interactive Maps**: Leaflet.js with OpenStreetMap tiles
- **Stop Markers**: All stops displayed on map with names

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend Layer                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Driver UI  │  │  Student UI  │  │   Login UI   │          │
│  │              │  │              │  │              │          │
│  │ • GPS Share  │  │ • GPS Share  │  │ • Auth Form  │          │
│  │ • Student    │  │   (Toggle)   │  │ • Role-Based │          │
│  │   Toggle     │  │ • Track Bus  │  │   Redirect   │          │
│  │ • Status Mon.│  │ • Confirm    │  │              │          │
│  │ • Manual Ctrl│  │   Arrival    │  │              │          │
│  │ • Reset Bus  │  │ • Map Nav    │  │              │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                   │                   │                │
│         └───────────────────┴───────────────────┘                │
│                         │                                        │
│                  Leaflet.js Maps                                 │
│                  Real-time AJAX (1s polling)                     │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                    Backend Layer (Flask)                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  app.py - Main Application Logic                         │   │
│  │  • Authentication & Session Management                   │   │
│  │  • Location Priority Engine                              │   │
│  │  • Route Handlers & API Endpoints                        │   │
│  │  • Student Location Toggle Control                       │   │
│  │  • GPS Activity Monitoring                               │   │
│  │  • Rate Limiting & Security                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  db.py - Database Layer                                  │   │
│  │  • Stop Proximity Detection (Haversine formula)          │   │
│  │  • Bus State Management                                  │   │
│  │  • User Location Storage                                 │   │
│  │  • Confirmation Tracking                                 │   │
│  │  • Distance Calculations                                 │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                   Data Layer (SQLite)                            │
│  • bus_state         - Current position, status, location source│
│  • stops             - Stop coordinates and sequence            │
│  • user_locations    - Real-time GPS data from all users        │
│  • confirmations     - Student arrival confirmations            │
│  • location_clusters - Aggregated location data (future use)    │
└─────────────────────────────────────────────────────────────────┘
```

## 🎚️ Location Priority Logic

The system implements a sophisticated three-tier priority hierarchy to ensure accurate bus positioning:

### Priority Levels

#### Level 1: Driver GPS (Highest Priority)
**When Active:**
- Bus position updates to driver's exact GPS coordinates every second
- Automatic proximity detection checks all stops within 50 meters
- Bus snaps to stop coordinates when within detection radius
- Status automatically changes to "arrived" or "departing"
- Completely blocks manual controls (Departed/Arrived buttons)
- Blocks student GPS from updating bus position

**Activation:**
- Driver clicks location sharing button (red/green pin icon)
- GPS permission granted by browser
- Active GPS watch started

**Deactivation:**
- Driver clicks stop sharing button
- GPS becomes stale (>30 seconds since last update)
- Driver manually stops GPS tracking

#### Level 2: Student GPS (Secondary Priority)
**When Active:**
- Only affects bus position if driver GPS is inactive (>30s)
- Must be explicitly enabled by driver via toggle button
- Multiple students can share location simultaneously
- Most recent student location is used for bus position
- Applies same proximity detection and snap-to-stop logic
- Blocks manual controls when active

**Activation:**
- Driver enables student location sharing via toggle
- Student clicks location sharing button
- GPS permission granted by browser

**Deactivation:**
- Driver disables student location sharing (stops all students)
- Student stops sharing manually
- GPS becomes stale (>30 seconds since last update)
- Driver GPS becomes active (overrides student GPS)

**Enforcement:**
- Backend rejects location share requests when disabled (403 error)
- Student location button automatically disabled in UI
- Visual feedback: grayed out button with explanatory tooltip
- Active GPS sessions terminated when driver disables

#### Level 3: Manual Controls (Fallback)
**When Active:**
- Only works when ALL GPS sources are inactive (>30 seconds old)
- Driver: "Departed" button sets status, "Arrived" moves to next stop
- Student: "Arrived" button records confirmation, moves bus if quorum reached

**Activation:**
- Automatically available when GPS is stale
- Error message if attempted while GPS is active

**Use Cases:**
- GPS unavailable or denied permission
- Low battery mode (GPS disabled)
- Indoor areas with poor GPS signal
- Testing and manual override scenarios

### Decision Flow

```
New Location Update Received
        │
        ├─── Is user a driver?
        │    ├─── YES → Update bus position immediately
        │    │         Set location_source = 'driver'
        │    │         Update last_driver_update timestamp
        │    │         Block manual controls for 30 seconds
        │    │         
        │    └─── NO → Is user a student?
        │              ├─── Is student sharing enabled?
        │              │    ├─── NO → Return 403 error
        │              │    └─── YES → Continue
        │              │
        │              ├─── Is driver GPS active (<30s)?
        │              │    ├─── YES → Store location but don't update bus
        │              │    └─── NO → Update bus position
        │              │              Set location_source = 'student'
        │              │              Update last_student_update timestamp
        │              │              Block manual controls for 30 seconds
        │
        └─── Manual Control Attempted?
             ├─── Check driver GPS age
             │    ├─── Active (<30s) → Return error "GPS active"
             │    └─── Inactive → Continue
             │
             ├─── Check student GPS age
             │    ├─── Active (<30s) → Return error "GPS active"
             │    └─── Inactive → Allow manual control
             │
             └─── Execute manual action
```

### Example Scenarios

**Scenario 1: Driver Using GPS**
```
1. Driver starts GPS sharing
   → Bus updates every second from driver location
   → Student GPS and manual controls blocked
   → Status auto-updates based on proximity

2. Driver approaches Stop C (within 50m)
   → Bus snaps to Stop C coordinates
   → Status changes to "At Stop C"
   
3. Driver departs (>50m from Stop C)
   → Status changes to "Moving to Stop D"
   → Bus position shows exact GPS coordinates
```

**Scenario 2: Student GPS Enabled**
```
1. Driver GPS is off (>30s old)
2. Driver enables student location sharing
3. Students start sharing GPS
   → Bus updates from most recent student location
   → Manual controls blocked while student GPS active
   → Same proximity detection as driver

4. Driver disables student sharing
   → All student GPS sessions terminated
   → Student buttons become disabled
   → Manual controls now available
```

**Scenario 3: Manual Fallback**
```
1. All GPS sources inactive (>30s)
2. Driver clicks "DEPARTED"
   → Status changes to "departing"
   → No position change
   
3. Driver clicks "ARRIVED"
   → Bus moves to next stop
   → Status cleared
```

## 👥 User Roles

### Driver Role

**Primary Responsibilities:**
- Share GPS location for real-time bus tracking
- Control student location sharing (enable/disable)
- Monitor bus status and next stop
- Use manual controls when GPS unavailable
- Reset bus position when needed

**Interface Components:**
- **Status Bar**: Current status and last update time
- **Next Stop Display**: Shows upcoming stop
- **Student Location Toggle**: Gray (disabled) or Green (enabled)
- **Logout Button**: Red button below Next Stop
- **GPS Share Button**: Red (inactive) or Green (active) circular button
- **Departed Button**: Blue rectangular button (action bar)
- **Reset Bus Button**: Small gray text button (for testing)

**Typical Workflow:**
1. Login with driver credentials
2. Start GPS sharing (red pin button)
3. Enable student location if needed (toggle button)
4. Drive route - system auto-detects stops
5. Monitor status and next stop
6. Stop GPS sharing when route complete
7. (Optional) Reset bus for next run

### Student Role

**Primary Responsibilities:**
- View real-time bus location
- Share GPS location when enabled by driver
- Confirm arrival at stops (optional)
- Navigate map to find bus

**Interface Components:**
- **Status Bar**: Bus status and last update time
- **Logout Button**: White circular button (top-right, fixed position)
- **GPS Share Button**: Red (inactive) or Green (active), gray when disabled
- **Arrived Button**: Blue rectangular button (action bar)
- **Center on Bus Button**: White circular button (action bar)
- **Interactive Map**: Pan, zoom, view stops

**Typical Workflow:**
1. Login with student credentials
2. View bus location on map
3. Share location if enabled by driver (pin button)
4. Use center button to find bus quickly
5. (Optional) Click arrived when bus reaches stop
6. Stop sharing when reached destination

### Permission Differences

| Feature | Driver | Student |
|---------|--------|---------|
| GPS Sharing | ✅ Always allowed | ✅ When enabled by driver |
| View Bus Location | ✅ Yes | ✅ Yes |
| Manual Departed | ✅ Yes (when GPS off) | ❌ No |
| Manual Arrived | ✅ Yes (when GPS off) | ✅ Yes (confirmation only) |
| Student GPS Toggle | ✅ Yes | ❌ No |
| Reset Bus | ✅ Yes | ❌ No |
| Stop Location Sharing | ✅ Own GPS only | ✅ Own GPS only |

## 📦 Prerequisites

- **Python**: 3.8 or higher
- **pip**: Python package installer
- **Browser**: Modern browser with GPS support (Chrome, Firefox, Safari, Edge)
- **GPS Device**: Smartphone or tablet with GPS capability
- **Network**: Internet connection for map tiles
- **SQLite3**: Included with Python

## 🚀 Installation

### Step 1: Clone Repository

```bash
git clone https://github.com/JKR0805/bus-tracker.git
cd bus-tracker
```

### Step 2: Create Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

**Requirements:**
- Flask==3.0.3
- gunicorn==21.2.0
- pytz==2024.1

### Step 4: Initialize Database

Database initializes automatically on first run. To manually initialize:

```bash
python -c "from db import init_db; init_db()"
```

This creates `bus.db` with all necessary tables and seed data.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in project root (optional but recommended for production):

```env
# Security
FLASK_SECRET_KEY=your-super-secret-key-change-this-in-production

# Environment
FLASK_ENV=production
FLASK_DEBUG=False

# Server (optional)
HOST=0.0.0.0
PORT=8000
```

### Default User Accounts

**Testing Credentials** (defined in `app.py`):

| Username | Password | Role | Bus Assignment |
|----------|----------|------|----------------|
| driver1 | driverpass123 | Driver | S1/A |
| student1 | studentpass123 | Student | - |
| student2 | studentpass123 | Student | - |
| student3 | studentpass123 | Student | - |

⚠️ **Security Warning**: Change these credentials before deploying to production!

### Bus Configuration

Edit in `app.py`:

```python
BUS_ID = "S1/A"  # Bus identifier
QUORUM = 1       # Confirmations needed to move bus (student mode)
MIN_UPDATE_INTERVAL = 1.0  # Seconds between GPS updates
```

### Stop Configuration

Edit in `db.py` - `SEED_STOPS` list:

```python
SEED_STOPS: List[Tuple[str, float, float, int]] = [
    ('Starting Point', 17.495643, 78.335691, 0),  # name, lat, lon, sequence
    ('Stop A', 17.495255, 78.340605, 1),
    ('Stop B', 17.496050, 78.358307, 2),
    ('Stop C', 17.496639, 78.366014, 3),
    ('Stop D', 17.497767, 78.377978, 4),
    ('Stop E', 17.498739, 78.389480, 5),
    ('Stop F', 17.511779, 78.384217, 6),
    ('Stop G', 17.528937, 78.385203, 7),
    ('VNR', 17.541772, 78.386868, 8),
]
```

**Format**: `(name, latitude, longitude, sequence_number)`

### GPS Settings

Adjust proximity detection in `app.py`:

```python
# In share_location() function
proximity_result = dbm.check_stop_proximity(bus_id, lat, lon, radius_meters=50)
```

Change `radius_meters` to adjust detection sensitivity (default: 50 meters).

## 🎯 Usage

### Starting the Application

#### Development Mode

```bash
python app.py
```

Access at: `http://localhost:5000`

#### Production Mode with Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:8000 wsgi:application
```

Access at: `http://your-server-ip:8000`

**Gunicorn Options:**
- `-w 4`: 4 worker processes
- `-b 0.0.0.0:8000`: Bind to all interfaces on port 8000
- `--timeout 120`: Request timeout (useful for long-running operations)

### Driver Guide

#### Starting a Route

1. **Login** at `/login`
   - Username: `driver1`
   - Password: `driverpass123`

2. **Review Dashboard**
   - Status bar shows current status
   - Next Stop displays upcoming destination

3. **Start GPS Tracking**
   - Click red pin button (bottom action bar)
   - Grant browser location permission
   - Button turns green when active
   - Bus position updates automatically

4. **(Optional) Enable Student Location**
   - Click "Enable Student Location" button
   - Button turns green when enabled
   - Students can now share their GPS

5. **Drive the Route**
   - System auto-detects when you enter 50m radius of stops
   - Bus snaps to stop coordinates automatically
   - Status updates: "At [Stop Name]" or "Moving to [Next Stop]"
   - Monitor next stop in info box

6. **Complete Route**
   - Click green pin button to stop GPS
   - Use "Reset Bus (Testing)" to return to start
   - Logout when finished

#### Using Manual Controls (Fallback)

If GPS unavailable:

1. **Departed**: Click when leaving a stop
   - Only works if GPS inactive >30s
   - Sets status to "departing"

2. **Arrived**: Click when reaching next stop
   - Only works if GPS inactive >30s
   - Moves bus to next stop in sequence

#### Managing Student Location

**To Enable:**
- Click gray "Enable Student Location" button
- Button turns green
- Students can now share GPS
- Their location updates bus if your GPS is off

**To Disable:**
- Click green "Disable Student Location" button
- Button turns gray
- All active student GPS sessions terminated
- Student buttons become disabled automatically

### Student Guide

#### Tracking the Bus

1. **Login** at `/login`
   - Username: `student1`, `student2`, or `student3`
   - Password: `studentpass123`

2. **View Bus Location**
   - Map shows bus position (blue bus icon)
   - All stops marked with standard markers
   - Status bar shows current status

3. **Navigate Map**
   - **Pan**: Click and drag
   - **Zoom**: Pinch or scroll wheel
   - **Center**: Click center button (circular icon)

4. **(Optional) Share Your Location**
   - Available only if driver enables it
   - Click red pin button (turns green when active)
   - Grant browser location permission
   - Your GPS helps track bus if driver GPS is off

5. **(Optional) Confirm Arrival**
   - Click "ARRIVED" button when bus reaches your stop
   - Records your confirmation
   - If enough confirmations (quorum) and GPS off, moves bus

#### Location Sharing States

| State | Button Appearance | Can Share? | Reason |
|-------|-------------------|------------|---------|
| Enabled | Red (inactive) or Green (active) | ✅ Yes | Driver enabled sharing |
| Disabled | Gray, 50% opacity | ❌ No | Driver disabled sharing |
| No Permission | Red | ❌ No | Browser permission denied |

### Confirmation System

**How It Works:**
1. Student clicks "ARRIVED" at their stop
2. System records confirmation with timestamp
3. Counts total confirmations for current stop
4. If count ≥ QUORUM and no GPS active → moves bus
5. If count ≥ QUORUM but GPS active → records but doesn't move

**Current Settings:**
- QUORUM = 1 (only 1 student needed)
- Can be increased for stricter validation
- Confirmations cleared when bus moves to next stop

## 📡 API Documentation

### Authentication Endpoints

#### POST `/login`
Authenticate user and create session.

**Request:**
```http
POST /login
Content-Type: application/x-www-form-urlencoded

username=driver1&password=driverpass123
```

**Response:**
- Success: Redirect to `/driver` or `/student` based on role
- Failure: Render login page with error message

#### GET `/logout`
Destroy session and logout user.

**Response:**
- Redirect to `/login`

### Location Sharing Endpoints

#### POST `/location/share`
Share GPS location (driver or student).

**Authentication**: Required (session-based)

**Request:**
```json
{
  "bus_id": "S1/A",
  "lat": 17.495643,
  "lon": 78.335691,
  "accuracy": 10.5
}
```

**Response (Success):**
```json
{
  "bus_id": "S1/A",
  "stop_index": 2,
  "lat": 17.496050,
  "lon": 78.358307,
  "timestamp": "2025-11-13T10:30:45Z",
  "stop_name": "Stop B",
  "stop_id": 2,
  "status": "arrived",
  "accuracy": 10.5,
  "user_type": "driver",
  "location_source": "driver",
  "updated_bus": true
}
```

**Response (Student Sharing Disabled - 403):**
```json
{
  "error": "Student location sharing is disabled"
}
```

**Response (Rate Limited - 429):**
```json
{
  "error": "Too many updates",
  "retry_after": 0.5
}
```

**Behavior:**
- **Driver**: Always updates bus position
- **Student**: Only updates if enabled and driver GPS inactive
- **Rate Limit**: 1 request per second per user
- **Proximity Check**: Auto-detects stops within 50m
- **Snap-to-Stop**: Positions bus at stop coordinates when near

#### POST `/location/stop`
Stop driver GPS tracking (driver only).

**Authentication**: Required (driver role)

**Request:**
```json
{
  "bus_id": "S1/A"
}
```

**Response:**
```json
{
  "message": "GPS tracking stopped",
  "gps_active": false
}
```

### Student Location Control Endpoints

#### POST `/driver/toggle-student-location`
Enable or disable student location sharing (driver only).

**Authentication**: Required (driver role)

**Request:**
```json
{
  "bus_id": "S1/A",
  "enabled": true
}
```

**Response:**
```json
{
  "bus_id": "S1/A",
  "student_location_enabled": true,
  "message": "Student location sharing enabled"
}
```

**Effects:**
- When enabled: Students can share GPS
- When disabled: 
  - Clears all student GPS timestamps
  - Active student sessions terminated
  - Student buttons become disabled

#### GET `/driver/student-location-status?bus_id=S1/A`
Get current student location sharing status (driver only).

**Authentication**: Required (driver role)

**Response:**
```json
{
  "bus_id": "S1/A",
  "student_location_enabled": false
}
```

#### GET `/student/location-status?bus_id=S1/A`
Check if student location sharing is enabled (student only).

**Authentication**: Required (student role)

**Response:**
```json
{
  "bus_id": "S1/A",
  "enabled": false
}
```

### Bus State Endpoints

#### GET `/bus/<bus_id>`
Get current bus state and position.

**Authentication**: Required

**Response:**
```json
{
  "bus_id": "S1/A",
  "stop_index": 2,
  "lat": 17.496050,
  "lon": 78.358307,
  "timestamp": "2025-11-13T10:30:45Z",
  "status": "departing",
  "stop_name": "Stop B",
  "stop_id": 2
}
```

#### GET `/stops`
Get all configured bus stops.

**Authentication**: Required

**Response:**
```json
[
  {
    "id": 1,
    "name": "Starting Point",
    "lat": 17.495643,
    "lon": 78.335691,
    "seq": 0
  },
  {
    "id": 2,
    "name": "Stop A",
    "lat": 17.495255,
    "lon": 78.340605,
    "seq": 1
  }
]
```

### Manual Control Endpoints

#### POST `/driver/departed`
Mark bus as departed (driver only, fallback mode).

**Authentication**: Required (driver role)

**Request:**
```json
{
  "bus_id": "S1/A"
}
```

**Response (GPS Active - 400):**
```json
{
  "error": "Using live GPS - manual control disabled",
  "message": "Bus position is being tracked via driver GPS",
  "gps_active": true,
  "gps_source": "driver"
}
```

**Response (Success):**
```json
{
  "bus_id": "S1/A",
  "stop_index": 2,
  "status": "departing",
  "gps_active": false
}
```

#### POST `/driver/arrived`
Mark bus as arrived at next stop (driver only, fallback mode).

**Authentication**: Required (driver role)

**Request:**
```json
{
  "bus_id": "S1/A",
  "action": "arrived"
}
```

**Response**: Same as `/driver/departed`

**Behavior:**
- Moves bus to next stop in sequence
- Clears status
- Only works when GPS inactive

#### POST `/driver/reset`
Reset bus to starting stop (driver only).

**Authentication**: Required (driver role)

**Request:**
```json
{
  "bus_id": "S1/A"
}
```

**Response:**
```json
{
  "bus_id": "S1/A",
  "stop_index": 0,
  "lat": 17.495643,
  "lon": 78.335691,
  "stop_name": "Starting Point",
  "stop_id": 1,
  "status": null,
  "gps_active": false
}
```

**Effects:**
- Sets bus to first stop (sequence 0)
- Clears all confirmations
- Clears status
- Useful for testing or daily restart

### Student Endpoints

#### POST `/student/arrived`
Confirm arrival at current stop (student only).

**Authentication**: Required (student role)

**Request:**
```json
{
  "bus_id": "S1/A",
  "student_id": "student1"
}
```

**Response:**
```json
{
  "confirmations": 2,
  "moved": false,
  "state": {
    "bus_id": "S1/A",
    "stop_index": 2,
    "stop_name": "Stop B"
  },
  "gps_active": true
}
```

**Behavior:**
- Always records confirmation
- If confirmations ≥ QUORUM and GPS inactive: moves bus
- If confirmations ≥ QUORUM but GPS active: records only, doesn't move

#### GET `/confirmations?bus_id=S1/A&stop_id=2`
Get confirmation count for a stop.

**Authentication**: Required

**Response:**
```json
{
  "bus_id": "S1/A",
  "stop_id": 2,
  "confirmations": 2
}
```

### Status Endpoints

#### GET `/gps/status?bus_id=S1/A`
Check if GPS is currently active.

**Authentication**: Required

**Response:**
```json
{
  "bus_id": "S1/A",
  "gps_active": true,
  "last_update": "2025-11-13T10:30:45Z"
}
```

**Definition of Active:**
- Driver GPS: Updated within last 30 seconds
- Student GPS: Updated within last 30 seconds AND driver GPS inactive

## 🗄️ Database Schema

### Tables Overview

The system uses SQLite with 5 main tables:

1. **stops**: Physical bus stop locations
2. **bus_state**: Current bus position and status
3. **user_locations**: Real-time GPS data from users
4. **confirmations**: Student arrival confirmations
5. **location_clusters**: Aggregated location data (future use)

### `stops` Table

Stores bus stop information with coordinates and sequence.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY | Unique stop identifier |
| name | TEXT | NOT NULL | Stop name (e.g., "Stop A") |
| lat | REAL | NOT NULL | Latitude (decimal degrees) |
| lon | REAL | NOT NULL | Longitude (decimal degrees) |
| seq | INTEGER | NOT NULL | Sequence order (0-based) |

**Example:**
```sql
INSERT INTO stops (name, lat, lon, seq) 
VALUES ('Starting Point', 17.495643, 78.335691, 0);
```

### `bus_state` Table

Tracks current bus position, status, and metadata.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| bus_id | TEXT | PRIMARY KEY | Bus identifier (e.g., "S1/A") |
| stop_index | INTEGER | NOT NULL | Current stop sequence number |
| lat | REAL | NOT NULL | Current latitude |
| lon | REAL | NOT NULL | Current longitude |
| timestamp | TEXT | NOT NULL | Last update time (ISO 8601) |
| status | TEXT | NULL | 'arrived', 'departing', etc. |
| location_source | TEXT | NULL | 'driver', 'students', 'last_known' |
| location_accuracy | REAL | NULL | GPS accuracy in meters |
| sample_size | INTEGER | NULL | Number of samples in aggregate |
| last_arrival_time | TEXT | NULL | Last arrival timestamp |
| last_departure_time | TEXT | NULL | Last departure timestamp |

**Notes:**
- One row per bus
- Updated every GPS update or manual control action
- `status` is NULL when at a stop, 'departing' when moving

### `user_locations` Table

Stores real-time GPS locations from all users.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique record ID |
| bus_id | TEXT | NOT NULL | Associated bus |
| user_id | TEXT | NOT NULL | Username |
| user_type | TEXT | NOT NULL | 'driver' or 'student' |
| lat | REAL | NOT NULL | Latitude |
| lon | REAL | NOT NULL | Longitude |
| accuracy | REAL | NOT NULL | GPS accuracy (meters) |
| speed | REAL | NULL | Speed (m/s) - future use |
| heading | REAL | NULL | Heading (degrees) - future use |
| timestamp | TEXT | NOT NULL | Update time (ISO 8601) |
| cluster_id | INTEGER | NULL | Associated cluster - future use |
| weight | REAL | NULL | Weight for aggregation - future use |

**Unique Constraint:** `(bus_id, user_id)` - ON CONFLICT REPLACE

**Notes:**
- Each user has only one current location
- Old locations automatically replaced
- Used for priority logic and future clustering

### `confirmations` Table

Records student arrival confirmations at stops.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Unique confirmation ID |
| bus_id | TEXT | NOT NULL | Bus identifier |
| stop_id | INTEGER | NOT NULL | Stop ID being confirmed |
| user_type | TEXT | NOT NULL | Always 'student' |
| user_id | TEXT | NOT NULL | Student username |
| timestamp | TEXT | NOT NULL | Confirmation time (ISO 8601) |

**Notes:**
- New row inserted for each confirmation
- Used to count confirmations for quorum
- Cleared when bus moves to next stop

### `location_clusters` Table

Stores aggregated location clusters (future feature).

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | INTEGER | PRIMARY KEY AUTOINCREMENT | Cluster ID |
| bus_id | TEXT | NOT NULL | Bus identifier |
| lat | REAL | NOT NULL | Cluster center latitude |
| lon | REAL | NOT NULL | Cluster center longitude |
| radius | REAL | NOT NULL | Cluster radius (meters) |
| point_count | INTEGER | NOT NULL | Points in this cluster |
| total_points | INTEGER | NOT NULL | Total points considered |
| timestamp | TEXT | NOT NULL | Creation time (ISO 8601) |
| is_majority | BOOLEAN | NOT NULL | Is this majority cluster? |

**Notes:**
- Currently populated but not actively used
- Reserved for future crowd-sourced location verification
- Would enable multi-student location consensus

### Database Initialization

On first run or manual initialization:

1. Creates all tables if they don't exist
2. Seeds stops from `SEED_STOPS` configuration
3. Creates initial bus_state entry at first stop
4. Clears any existing confirmations

**Manual initialization:**
```bash
python -c "from db import init_db; init_db()"
```

## 🚢 Deployment

### Production Checklist

Before deploying to production:

#### Security
- [ ] Change default user passwords in `app.py`
- [ ] Set strong `FLASK_SECRET_KEY` (generate with `python -c "import secrets; print(secrets.token_hex(32))"`)
- [ ] Set `FLASK_ENV=production`
- [ ] Set `FLASK_DEBUG=False`
- [ ] Configure HTTPS/SSL certificates
- [ ] Set up firewall rules (allow only 80/443)
- [ ] Enable rate limiting on API endpoints

#### Database
- [ ] Set up automated database backups
- [ ] Configure backup retention policy
- [ ] Test restore procedures
- [ ] Consider PostgreSQL for production

#### Monitoring
- [ ] Set up application logging
- [ ] Configure error tracking (Sentry, etc.)
- [ ] Set up uptime monitoring
- [ ] Configure alerts for failures

#### Performance
- [ ] Enable gzip compression
- [ ] Configure CDN for static files
- [ ] Set up caching headers
- [ ] Optimize database queries

#### Testing
- [ ] Test GPS on target devices
- [ ] Verify browser compatibility
- [ ] Test under load
- [ ] Verify daily reset timing

## 🔧 Technical Details

### Location Priority Implementation

**Key Variables:**
```python
last_driver_update = {}   # {bus_id: datetime}
last_student_update = {}  # {bus_id: datetime}
student_location_enabled = {}  # {bus_id: bool}
```

**Decision Logic:**
```python
# In /location/share endpoint
if user_type == 'driver':
    should_update_bus = True
    location_source = 'driver'
elif user_type == 'student':
    if not student_location_enabled.get(bus_id, False):
        return 403  # Forbidden
    
    if bus_id not in last_driver_update:
        should_update_bus = True
        location_source = 'student'
    else:
        seconds_since_driver = (now - last_driver_update[bus_id]).total_seconds()
        if seconds_since_driver > 30:
            should_update_bus = True
            location_source = 'student'
```

### Proximity Detection Algorithm

Uses Haversine formula for accurate distance calculation:

```python
def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters"""
    R = 6371000  # Earth radius in meters
    
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
```

**Detection Process:**
1. For each GPS update, check distance to all stops
2. If distance ≤ 50 meters to any stop:
   - Snap to that stop's exact coordinates
   - Set status to "arrived"
   - Update stop_index
3. If distance > 50 meters from current stop:
   - Use exact GPS coordinates
   - Set status to "departing"
   - Show next stop name

### Daily Reset System

**Implementation:**
```python
def daily_reset_scheduler():
    """Background thread that resets at midnight"""
    while True:
        now = datetime.now()
        tomorrow = now + timedelta(days=1)
        midnight = datetime.combine(tomorrow.date(), time(0, 0, 0))
        seconds_until_midnight = (midnight - now).total_seconds()
        
        time.sleep(seconds_until_midnight)
        
        reset_bus_to_start()
        logger.info("Daily automatic reset completed")
```

**Started at Application Launch:**
```python
@app.before_request
def ensure_init():
    global init_done
    if not init_done:
        dbm.init_db()
        reset_thread = threading.Thread(target=daily_reset_scheduler, daemon=True)
        reset_thread.start()
        init_done = True
```

### Session Management

**Features:**
- UUID-based session IDs
- 7-day session lifetime
- Automatic cleanup of inactive sessions
- Secure cookie settings

**Implementation:**
```python
# Session configuration
app.config.update(
    PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    SESSION_COOKIE_SECURE=is_production,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME='bus_tracker_session'
)

# Active session tracking
active_sessions = {}  # {session_id: {username, role, bus_id, last_active}}

def cleanup_inactive_sessions():
    now = datetime.now()
    max_age = timedelta(days=7)
    inactive = [
        sid for sid, data in active_sessions.items()
        if now - data['last_active'] > max_age
    ]
    for sid in inactive:
        active_sessions.pop(sid, None)
```

### Rate Limiting

**GPS Updates:**
- 1 update per second per user
- Prevents GPS spam
- Returns 429 error with retry_after

```python
last_update_time = {}  # {user_id: datetime}
MIN_UPDATE_INTERVAL = 1.0  # seconds

# In /location/share
if user_id in last_update_time:
    time_since_last = (now - last_update_time[user_id]).total_seconds()
    if time_since_last < MIN_UPDATE_INTERVAL:
        return jsonify({
            "error": "Too many updates",
            "retry_after": MIN_UPDATE_INTERVAL - time_since_last
        }), 429
```

### Map Implementation

**Leaflet.js Integration:**
```javascript
// Initialize map
let map = L.map('map');
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap'
}).addTo(map);

// Create bus marker
const busIcon = L.divIcon({
    html: '<div style="font-size: 36px;">🚌</div>',
    className: 'bus-marker',
    iconSize: [48, 48],
    iconAnchor: [24, 24]
});

// Update bus position (no auto-center)
busMarker.setLatLng([lat, lon]);
```

**Polling Strategy:**
- Polls `/bus/<bus_id>` every 1 second
- Updates bus marker position
- No automatic map centering
- User controls zoom/pan

## 🐛 Troubleshooting

### GPS Not Working

**Symptoms:**
- Location button doesn't work
- No GPS updates received
- "Geolocation not supported" message

**Solutions:**

1. **Check Browser Permissions:**
   - Chrome: Settings → Privacy → Site Settings → Location
   - Firefox: Settings → Privacy → Permissions → Location
   - Safari: Settings → Safari → Location Services

2. **HTTPS Required:**
   - Modern browsers require HTTPS for geolocation
   - Use localhost for development
   - Use SSL certificate in production

3. **Device GPS:**
   - Ensure device has GPS capability
   - Enable location services in device settings
   - Go outdoors for better signal

4. **Browser Console:**
   - Open developer tools (F12)
   - Check for geolocation errors
   - Look for permission denial messages

### Manual Controls Not Working

**Symptoms:**
- "Using live GPS - manual control disabled" error
- Departed/Arrived buttons show error

**Cause:**
- GPS is active (updated within last 30 seconds)
- System is using GPS for positioning

**Solution:**
- Stop GPS sharing first
- Wait 30 seconds after last GPS update
- Then manual controls will work

### Student Location Button Disabled

**Symptoms:**
- Button appears gray
- Tooltip says "Location sharing disabled by driver"
- Cannot click button

**Cause:**
- Driver has disabled student location sharing

**Solution:**
- Ask driver to enable student location sharing
- Driver clicks "Enable Student Location" toggle
- Button will become active automatically

### Bus Not Moving

**Symptoms:**
- Bus marker doesn't update
- Position stays at same location

**Possible Causes:**

1. **No GPS Active:**
   - Start driver GPS sharing
   - Or use manual controls if GPS off

2. **GPS Too Far from Route:**
   - Check if actual location is far from stops
   - Bus shows exact GPS location between stops

3. **Database Issue:**
   - Check if `bus.db` exists
   - Restart application to reinitialize

4. **Session Expired:**
   - Logout and login again
   - Check if logged in correctly

### Common Error Messages

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "Student location sharing is disabled" | Driver disabled student GPS | Ask driver to enable |
| "Using live GPS - manual control disabled" | GPS is active | Stop GPS or wait 30s |
| "Too many updates" | Rate limit exceeded | Wait 1 second between updates |
| "Could not get location" | GPS permission denied | Grant location permission |
| "Invalid coordinates" | Bad GPS data | Restart GPS sharing |
| "Bus not found" | Database issue | Restart application |
| "Unauthorized" | Wrong bus ID | Check bus assignment |

## 📝 License

This project is licensed under the MIT License.

## 👥 Authors & Acknowledgments

**Development Team:**
- **JKR0805** - Initial development and architecture

**Special Thanks:**
- Flask framework and community
- Leaflet.js for mapping functionality
- OpenStreetMap for map tiles and data
- All contributors and testers

## 📞 Support

For issues, questions, or contributions:

**GitHub Issues:**
- Report bugs: [github.com/JKR0805/bus-tracker/issues](https://github.com/JKR0805/bus-tracker/issues)
- Request features: Use "Feature Request" label
- Ask questions: Use "Question" label

---

**Note:** This is a production-ready GPS-based bus tracking system. The location priority system ensures accurate bus positioning through a three-tier hierarchy: Driver GPS (highest) → Student GPS (when enabled) → Manual Controls (fallback). All GPS sharing is optional and can be controlled by the driver. The system automatically resets at midnight daily.

**Last Updated:** January 2025
**Version:** 3.2.0
