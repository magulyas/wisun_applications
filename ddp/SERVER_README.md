# WiSUN Applications Web Server Manager

A command line tool for managing a web server in the background.

## Installation

First, install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

The server manager provides several commands:

### Start the server (Development Mode)

```bash
python server.py start
```

or on Windows:

```cmd
server.bat start
```

This will start the web server in the background using Flask's development server. The server will be accessible at `http://127.0.0.1:8080` by default.

**Note**: You'll see a warning about using a development server. This is normal for development/testing.

### Start the server (Production Mode)

```bash
python server.py start --production
```

This starts the server using a production-ready WSGI server:

- **Windows**: Uses Waitress
- **Unix/Linux**: Uses Gunicorn (with Waitress as fallback)

Production servers provide:

- Better performance and stability
- Multi-threading support
- Proper process management
- No development server warnings

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
- `--production`: Use production WSGI server instead of Flask development server

Examples:

```bash
# Start development server
python server.py start

# Start production server
python server.py start --production

# Start on custom host/port with production server
python server.py start --host 0.0.0.0 --port 8090 --production
```

## Development vs Production Server

### Development Server (Default)

- Flask's built-in server
- **Warning displayed**: "This is a development server..."
- Single-threaded
- Good for development and testing
- Auto-reloads on code changes (when not in background mode)

### Production Server (`--production` flag)

- Uses **Waitress** (Windows) or **Gunicorn** (Unix/Linux)
- Multi-threaded and optimized
- No warnings
- Better performance and stability
- Recommended for production deployments

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
# Start development server on default settings
python server.py start

# Start production server
python server.py start --production

# Check if server is running
python server.py status

# Stop the server
python server.py stop

# Start production server on different host/port
python server.py start --production --host 0.0.0.0 --port 9000

# Restart server in production mode
python server.py restart --production
```

## Understanding the Flask Development Server Warning

When you see:

```
WARNING: This is a development server. Do not use it in a production deployment.
Use a production WSGI server instead.
```

This means you're using Flask's built-in development server, which is:

- **Single-threaded**: Can only handle one request at a time
- **Not optimized**: Lacks performance optimizations
- **Less secure**: Missing production-grade security features
- **Not scalable**: Can't handle high traffic

**Solution**: Use the `--production` flag to start with a production WSGI server that eliminates this warning and provides better performance.
