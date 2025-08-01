#!/usr/bin/env python3
"""
Web Server Command Line Tool

A command line utility to start, stop, and manage a web server in the background.
"""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, request

# Configuration
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8080
PID_FILE = Path(__file__).parent / 'server.pid'
LOG_FILE = Path(__file__).parent / 'server.log'

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({
        'status': 'running',
        'message': 'WiSUN Applications Server is running',
        'pid': os.getpid()
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': time.time()
    })

@app.route('/api/info')
def info():
    """Server information endpoint"""
    return jsonify({
        'server': 'WiSUN Applications Server',
        'pid': os.getpid(),
        'host': request.host,
        'uptime': time.time() - getattr(app, 'start_time', time.time())
    })

def write_pid_file(pid):
    """Write the process ID to a file"""
    try:
        with open(PID_FILE, 'w') as f:
            json.dump({
                'pid': pid,
                'start_time': time.time(),
                'host': DEFAULT_HOST,
                'port': DEFAULT_PORT
            }, f)
        return True
    except Exception as e:
        print(f"Error writing PID file: {e}")
        return False

def read_pid_file():
    """Read the process ID from file"""
    try:
        if PID_FILE.exists():
            with open(PID_FILE, 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return None

def remove_pid_file():
    """Remove the PID file"""
    try:
        if PID_FILE.exists():
            PID_FILE.unlink()
        return True
    except Exception as e:
        print(f"Error removing PID file: {e}")
        return False

def is_process_running(pid):
    """Check if a process is running"""
    try:
        if sys.platform == "win32":
            # Windows
            result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                  capture_output=True, text=True)
            return str(pid) in result.stdout
        else:
            # Unix-like systems
            os.kill(pid, 0)
            return True
    except (OSError, subprocess.SubprocessError):
        return False

def start_server(host=None, port=None, production=False):
    """Start the web server"""
    global DEFAULT_HOST, DEFAULT_PORT
    if host:
        DEFAULT_HOST = host
    if port:
        DEFAULT_PORT = port
        
    pid_info = read_pid_file()
    
    if pid_info and is_process_running(pid_info['pid']):
        print(f"Server is already running (PID: {pid_info['pid']})")
        print(f"Access it at: http://{pid_info['host']}:{pid_info['port']}")
        return False
    
    # Remove stale PID file
    remove_pid_file()
    
    server_type = "production" if production else "development"
    print(f"Starting {server_type} server on {DEFAULT_HOST}:{DEFAULT_PORT}...")
    
    # Start server in background
    if sys.platform == "win32":
        # Windows
        cmd = [sys.executable, __file__, '_run_server', '--host', DEFAULT_HOST, '--port', str(DEFAULT_PORT)]
        if production:
            cmd.append('--production')
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        # Unix-like systems
        pid = os.fork()
        if pid == 0:
            # Child process
            os.setsid()
            _run_server_process(production)
            sys.exit(0)
    
    # Wait a moment for server to start
    time.sleep(3 if production else 2)
    
    # Verify server started
    pid_info = read_pid_file()
    if pid_info and is_process_running(pid_info['pid']):
        print(f"Server started successfully (PID: {pid_info['pid']})")
        print(f"Access it at: http://{DEFAULT_HOST}:{DEFAULT_PORT}")
        return True
    else:
        print("Failed to start server")
        return False

def _run_server_process(use_production=False):
    """Run the actual server process"""
    app.start_time = time.time()
    
    # Write PID file
    write_pid_file(os.getpid())
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(signum, frame):
        print(f"\nReceived signal {signum}, shutting down...")
        remove_pid_file()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Redirect stdout/stderr to log file for background operation
        if not sys.stdout.isatty():
            log_file = open(LOG_FILE, 'a')
            sys.stdout = log_file
            sys.stderr = log_file
        
        if use_production:
            # Use production WSGI server
            try:
                if sys.platform == "win32":
                    # Use Waitress for Windows (and as fallback)
                    from waitress import serve
                    print(f"Starting production server (Waitress) on {DEFAULT_HOST}:{DEFAULT_PORT}")
                    serve(app, host=DEFAULT_HOST, port=DEFAULT_PORT)
                else:
                    # Try Gunicorn for Unix systems, fallback to Waitress
                    try:
                        import gunicorn.app.wsgiapp
                        print(f"Starting production server (Gunicorn) on {DEFAULT_HOST}:{DEFAULT_PORT}")
                        # Create Gunicorn application
                        sys.argv = [
                            'gunicorn',
                            '--bind', f'{DEFAULT_HOST}:{DEFAULT_PORT}',
                            '--workers', '4',
                            '--worker-class', 'sync',
                            '--timeout', '30',
                            '--keep-alive', '2',
                            '--max-requests', '1000',
                            '--max-requests-jitter', '100',
                            '--access-logfile', '-',
                            '--error-logfile', '-',
                            'server:app'
                        ]
                        gunicorn.app.wsgiapp.run()
                    except ImportError:
                        # Fallback to Waitress
                        from waitress import serve
                        print(f"Starting production server (Waitress) on {DEFAULT_HOST}:{DEFAULT_PORT}")
                        serve(app, host=DEFAULT_HOST, port=DEFAULT_PORT)
            except ImportError:
                print("Warning: Production WSGI server not available, falling back to development server")
                print("Install with: pip install waitress")
                app.run(host=DEFAULT_HOST, port=DEFAULT_PORT, debug=False)
        else:
            # Development server
            print(f"Starting development server on {DEFAULT_HOST}:{DEFAULT_PORT}")
            print("Note: This is a development server. Use --production for production deployment.")
            app.run(host=DEFAULT_HOST, port=DEFAULT_PORT, debug=False)
    finally:
        remove_pid_file()

def stop_server():
    """Stop the web server"""
    pid_info = read_pid_file()
    
    if not pid_info:
        print("No server appears to be running (no PID file found)")
        return False
    
    pid = pid_info['pid']
    
    if not is_process_running(pid):
        print(f"Server with PID {pid} is not running")
        remove_pid_file()
        return False
    
    print(f"Stopping server (PID: {pid})...")
    
    try:
        if sys.platform == "win32":
            # Windows
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True)
        else:
            # Unix-like systems
            os.kill(pid, signal.SIGTERM)
            
            # Wait for graceful shutdown
            for _ in range(10):
                if not is_process_running(pid):
                    break
                time.sleep(0.5)
            
            # Force kill if still running
            if is_process_running(pid):
                os.kill(pid, signal.SIGKILL)
        
        remove_pid_file()
        print("Server stopped successfully")
        return True
        
    except Exception as e:
        print(f"Error stopping server: {e}")
        return False

def status_server():
    """Check server status"""
    pid_info = read_pid_file()
    
    if not pid_info:
        print("Status: Not running (no PID file)")
        return False
    
    pid = pid_info['pid']
    
    if is_process_running(pid):
        uptime = time.time() - pid_info['start_time']
        print(f"Status: Running")
        print(f"PID: {pid}")
        print(f"Host: {pid_info['host']}")
        print(f"Port: {pid_info['port']}")
        print(f"Uptime: {uptime:.1f} seconds")
        print(f"URL: http://{pid_info['host']}:{pid_info['port']}")
        return True
    else:
        print(f"Status: Not running (PID {pid} not found)")
        remove_pid_file()
        return False

def main():
    """Main command line interface"""
    global DEFAULT_HOST, DEFAULT_PORT
    
    parser = argparse.ArgumentParser(
        description='WiSUN Applications Web Server Manager',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s start         Start the server in background
  %(prog)s stop          Stop the running server
  %(prog)s status        Check server status
  %(prog)s restart       Restart the server
        """
    )
    
    parser.add_argument('command', 
                       choices=['start', 'stop', 'status', 'restart', '_run_server'],
                       help='Command to execute')
    
    parser.add_argument('--host', 
                       default=DEFAULT_HOST,
                       help=f'Host to bind to (default: {DEFAULT_HOST})')
    
    parser.add_argument('--port', 
                       type=int, 
                       default=DEFAULT_PORT,
                       help=f'Port to bind to (default: {DEFAULT_PORT})')
    
    parser.add_argument('--production', 
                       action='store_true',
                       help='Use production WSGI server (Waitress/Gunicorn) instead of Flask dev server')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        success = start_server(args.host, args.port, args.production)
        sys.exit(0 if success else 1)
        
    elif args.command == 'stop':
        success = stop_server()
        sys.exit(0 if success else 1)
        
    elif args.command == 'status':
        success = status_server()
        sys.exit(0 if success else 1)
        
    elif args.command == 'restart':
        print("Restarting server...")
        stop_server()
        time.sleep(1)
        success = start_server(args.host, args.port, args.production)
        sys.exit(0 if success else 1)
        
    elif args.command == '_run_server':
        # Internal command for Windows background process
        DEFAULT_HOST = args.host
        DEFAULT_PORT = args.port
        _run_server_process(args.production)

if __name__ == '__main__':
    main()