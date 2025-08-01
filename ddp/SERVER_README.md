# WiSUN Applications Web Server Manager

A command line tool for managing a web server in the background.

## Installation

First, install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

The server manager provides several commands:

### Start the server
```bash
python server.py start
```
or on Windows:
```cmd
server.bat start
```

This will start the web server in the background. The server will be accessible at `http://127.0.0.1:8080` by default.

### Stop the server
```bash
python server.py stop
```

### Check server status
```bash
python server.py status
```

### Restart the server
```bash
python server.py restart
```

## Options

- `--host`: Specify the host to bind to (default: 127.0.0.1)
- `--port`: Specify the port to bind to (default: 8080)

Example:
```bash
python server.py start --host 0.0.0.0 --port 8090
```

## API Endpoints

When running, the server provides these endpoints:

- `GET /` - Home page with server status
- `GET /health` - Health check endpoint
- `GET /api/info` - Server information including PID and uptime

## Files Created

The tool creates these files during operation:

- `server.pid` - Contains process information (PID, start time, host, port)
- `server.log` - Server log output (when running in background)

These files are automatically cleaned up when the server is stopped properly.

## Platform Support

- **Windows**: Uses `tasklist` and `taskkill` for process management
- **Unix/Linux/macOS**: Uses standard Unix signals and process forking

## Examples

```bash
# Start server on default settings
python server.py start

# Check if server is running
python server.py status

# Stop the server
python server.py stop

# Start server on different host/port
python server.py start --host 0.0.0.0 --port 9000

# Restart server
python server.py restart
```
