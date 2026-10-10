# SmartBarrage
Real-time predictive flood routing and automated gate optimization engine for flash deluge mitigation and agricultural land protection. Built with Python, Streamlit, and Plotly.
Hackathon Track: Track 2
Team Name : Xenon 

# OverView
Smart Barriage is a software-based flood management solution designed to predict incoming flood surges and support safer barrage gate operations. it uses upstream water-flow data, predictive analysis , and discharge constraints to help reduce downstream flood risk and protect agricultural land.
The system aims to make flood management more proactive, explainable ,and efficient by using existing barriage infrastructure.

# Problem Statement 
Flood surges can arrive with very little warning , creating a serious risk for downstream communities and agricultural land.
--Floodwater can exceed the safe carrying capacity of downstream rivers.
--Reactive gets operations may increase downstream flood exposure.
--Farmers may suffer crop damage , soil erosion, and financial losses.
--Limited warning time makes flood management difficult.

# Proposed Solution
Smart Barrage aims to provide a software-based monitoring and decision-support platform that:                           
--Simulates changing river inflow and hydrograph patterns.
--Receives and stores water-related telemetry.
--Monitors the recorded data for future analysis and visualization.
--Supports the development of intelligent gate-release recommendations.
--Helps engineers evaluate possible flood-management scenarios.
--Provides a foundation for future IoT sensors, dashboards, and automated decision support.

# How the Three Domains Work Together
A. Civil Engineering - Water and Flood Management
Civil Engineering provides the scientific foundation for understanding river behavior, water levels, storage capacity, and flood risk.

Main responsibilities:
--Study river inflow and outflow.
--Analyze upstream and downstream water levels.
--Understand hydrographs and flood peaks.
--Estimate barrage storage and discharge capacity.
--Assess downstream flood risks and agricultural impacts.
--Establish safe operating limits and hydraulic constraints.
--Help validate the proposed water-release strategy

Contribution to Smart Barrage: It defines the hydraulic rules and safety constraints that the software must respect.

B. Mechanical Engineering - Gates and Actuation
Mechanical Engineering focuses on the physical mechanisms that regulate the flow of water through a barrage.

Main responsibilities:
--Understand barrage gates and their operating mechanisms.
--Study actuators, motors, gear systems, and gate movement.
--Consider gate-opening percentage and operating speed.
--Evaluate mechanical limits and equipment reliability.
--Identify the requirements for sensors and actuator feedback.
--Design fail-safe mechanisms and emergency operating procedures.

Contribution to Smart Barrage: It connects software recommendations to the physical gate mechanisms required for real-world implementation.

C. Computer Science - Software, IoT, and Intelligence
Computer Science develops the software platform that processes sensor data, stores readings, and presents information for monitoring and decision support.
.
Main responsibilities:
--Develop the sensor data ingestion engine.
--Generate simulated water-flow data.
--Receive telemetry through an API.
--Store readings in a database.
--Build the web dashboard and visualization layer.
--Develop analytics and future prediction models.
--Implement decision-support logic and system integration.

Technologies used:

Python - simulation and backend processing.
FastAPI - telemetry API.
Uvicorn - backend server.
NumPy - numerical computation.
Pydantic - data validation.
SQLite - telemetry storage.
HTML5 and CSS3 -web interface structure and styling.
React and JavaScript - interactive frontend development.
ESP32/IoT - planned physical sensor integration.

# System Architecture and Data Flow
The proposed system follows this workflow:
Data generation: A mathematical hydrograph simulator generates sample water-flow readings.
Sensor integration: In a future deployment, physical sensors connected through an IoT device such as an ESP32 can provide telemetry.
API ingestion: FastAPI is designed to receive telemetry through the /api/v1/telemetry endpoint.
Data processing: The ingestion module processes readings, associates timestamps and source information, and prepares the data for storage.
Database storage: SQLite stores telemetry in barrage_state.db, in the sensor_telemetry table.
Monitoring and analysis: Stored data can support a dashboard, trend analysis, and future flood-risk calculations.
Decision support: A future hydraulic decision module can combine the data with civil engineering constraints to recommend gate operations.
Physical implementation: A future mechanical and IoT integration can connect validated recommendations to gate actuators, with suitable safety checks and operator authorization.

# Key Backend Module: sensor_api.py
The sensor_api.py module is the data ingestion engine of Smart Barrage.
It supports two operating modes:
Mode 1 - Simulation Mode
Generates artificial hydrograph readings.
Helps test the system without physical sensors.
Provides repeatable sample data for development and demonstrations.

Mode 2 -Hardware Telemetry Mode
Provides a FastAPI endpoint for receiving sensor readings.
Is designed for integration with physical IoT hardware.
Processes and stores incoming telemetry.
The module records readings in SQLite so that subsequent modules can retrieve the data for analysis.

# Expected Benefits
--Earlier awareness of changing water conditions.
--More organized monitoring of incoming telemetry.
--Easier testing of flood-management scenarios.
--Better coordination between civil, mechanical, and software engineering.
--A foundation for data-driven water-release planning.
--Potential reduction of downstream flood impacts when validated and deployed appropriately.
These are intended benefits; real-world flood reduction must be demonstrated through hydraulic validation, field testing, and operational evaluation.

# Project Limitations
--Simulated readings do not replace real river measurements.
--The ingestion module does not independently predict floods.
--Real hydraulic behavior and barrage storage constraints require engineering validation.
--Physical gate actuation and hardware feedback are not implemented by the ingestion module.
--The complete system requires field testing, fail-safe mechanisms, and authorized operator oversight before operational deployment.

# Future Scope
--Integrate real water-level and flow sensors.
--Connect ESP32 or other IoT devices to the telemetry API.
--Develop a live dashboard with charts and alerts.
--Add validated flood forecasting and inflow prediction.
--Develop hydraulic simulation and gate-release optimization.
--Integrate gate-position feedback and actuator monitoring.
--Add authentication, audit logs, and secure communication.
--Test the system using historical flood data and field measurements.

# Recommended order for running your project

| Terminal | Command                                                         | Purpose                                            |
| -------- | --------------------------------------------------------------- | -------------------------------------------------- |
| 1        | `uvicorn sensor_api:app --host 0.0.0.0 --port 8000 --reload`    | Start the backend API                              |
| 2        | `python sensor_api.py`                                          | Generate simulated sensor data                     |
| 3        | `streamlit run dashboard.py`                                    | Display the dashboard                              |
| 4        | `python controller_model.py`                                    | Run the controller, if it is an independent script |

# WORKFLOW DIAGRAM
====================================================================================================
                              SMART BARRAGE SCADA SYSTEM WORKFLOW
====================================================================================================

 [ PHYSICAL HARDWARE ]        [ SIMULATED HYDROGRAPH ]         [ MANUAL CSV LOG REPLAY ]
   - Radar Gauges               - Lean Flow: 15k-48k cusecs      - Bulk CSV file upload
   - Ultrasonic Level           - Monsoon Spike: up to 230k      - Step-by-step playback
   - IoT / RTU Stations         - Recession: decay curve         - Operator field logs
             │                             │                               │
             └───────────────────────┬─────┴───────────────────────────────┘
                                     │ HTTP POST / Ingestion
                                     ▼
                  ┌─────────────────────────────────────┐
                  │          sensor_stream.py           │
                  │   FastAPI Ingestion & Telemetry     │
                  └──────────────────┬──────────────────┘
                                     │ SQL INSERT
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│                            barrage_state.db (SQLite Shared Bus - WAL Mode)                       │
│                                                                                                  │
│  [sensor_telemetry]             [system_control]                 [gate_decisions]                │
│  - timestamp                    - mode ('AUTO' / 'MANUAL')       - downstream_cusecs             │
│  - station_id                   - manual_downstream              - diversion_cusecs              │
│  - inflow_cusecs                - manual_diversion               - gate_action                   │
│  - source_type                  - controller_heartbeat           - reason / operator audit       │
└──────────────┬──────────────────────────────▲─────────────────────────────────────▲───────────────┘
               │                              │                                     │
               │ SELECT rolling 15 steps      │ Read Mode / Heartbeat               │ INSERT decisions
               ▼                              │                                     │
┌─────────────────────────────────────────────┴─────────────────────────────────────┴──────────────┐
│                                       controller_model.py                                        │
│                                    Autonomous Decision Engine                                    │
│                                                                                                  │
│  1. Heartbeat Pulse: Emits timestamp every 2 seconds to prove process health                     │
│  2. Supervisory Check: Is mode 'MANUAL_OVERRIDE'?                                                │
│       ├── YES: Bypass math ──► Enforce human setpoints ──► Log operator audit                    │
│       └── NO:  Run Predictive Model:                                                             │
│                 - Peak lookahead: max(rolling_window)                                            │
│                 - If Peak > 75,000: Cap river at 67,500 cusecs (90% target limit)                │
│                 - Gate Slew Limiter: Clamp flow change to ±8,000 cusecs/step                     │
│                 - Balance: Divert excess discharge into retention basin                          │
└────────────────────────────────────────────────┬─────────────────────────────────────────────────┘
                                                 │
                                                 │ Acts on
                                                 ▼
                                     ┌───────────────────────┐
                                     │   BARRAGE ACTUATORS   │
                                     │ Main Spillway & Canal │
                                     └───────────────────────┘
                                                 ▲
                                                 │ Reads state / Sends manual override
                                                 │
┌────────────────────────────────────────────────┴─────────────────────────────────────────────────┐
│                                        dashboard_app.py                                          │
│                                Streamlit SCADA & Monitoring UI                                   │
│                                                                                                  │
│  • Live Hydrograph Routing Curves (Plotly interactive charts)                                    │
│  • Watchdog Health Monitor (Triggers 'OFFLINE / CRASHED' if controller halts > 6 seconds)        │
│  • Manual Override Console (Emergency takeover form with sliders & reason logging)              │
│  • CSV File Uploader & Step-by-Step Replayer                                                     │
│  • Full Chronological Audit Trail                                                                │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
====================================================================================================
