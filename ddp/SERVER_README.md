# WiSUN Applications Web Server Manager

A command line tool for managing a production web server in the background.

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

This will start the production web server in the background using a production WSGI server:
- **Windows**: Uses Waitress
- **Unix/Linux**: Uses Gunicorn (with Waitress as fallback)

The server will be accessible at `http://127.0.0.1:8080` by default.

**Features**:
- ✅ Production-ready performance
- ✅ Multi-threading support  
- ✅ Proper process management
- ✅ No development server warnings
- ✅ Optimized for stability and security

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
- `--force`: Force start even if port is already in use

Examples:

```bash
# Start server on default settings
python server.py start

# Start on custom host/port
python server.py start --host 0.0.0.0 --port 8090

# Force start on busy port
python server.py start --force
```

## Production Server Features

The server always uses production-ready WSGI servers:

- **Waitress** (Windows) or **Gunicorn** (Unix/Linux)
- Multi-threaded and optimized for performance
- No Flask development server warnings
- Better stability and security
- Handles concurrent requests efficiently
- Production-grade process management

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

# Force start on busy port
python server.py start --force

# Restart server
python server.py restart

# Check port availability
python server.py check-port --port 8090
```

## Production-Ready by Default

This server tool always uses production WSGI servers, eliminating common Flask development server issues:

❌ **No more warnings** like: "This is a development server. Do not use it in a production deployment."

✅ **Always production-ready** with:
- Multi-threaded request handling
- Optimized performance
- Enhanced security
- Better stability
- Proper process management

The tool automatically selects the best WSGI server for your platform:
- **Windows**: Waitress
- **Unix/Linux/macOS**: Gunicorn (with Waitress fallback)
