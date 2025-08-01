#!/usr/bin/env python3
"""
Web Server Command Line Tool

A command line utility to start, stop, and manage a web server in the background.
"""

import argparse
import json
import os
import signal
import socket
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

def is_port_available(host, port):
    """Check if a port is available for binding"""
    try:
        # First check if we can bind to the specific host:port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind((host, port))
        
        # Also check if anything is listening on 0.0.0.0:port (all interfaces)
        # which would conflict with our binding
        if host != '0.0.0.0':
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    # Try to connect to see if something is listening on all interfaces
                    sock.settimeout(1)
                    result = sock.connect_ex((host, port))
                    if result == 0:
                        # Something is listening and accepting connections
                        return False
            except:
                pass
        
        return True
    except (socket.error, OSError):
        return False

def find_available_port(host, start_port, max_attempts=10):
    """Find an available port starting from start_port"""
    for port in range(start_port, start_port + max_attempts):
        if is_port_available(host, port):
            return port
    return None

def get_port_usage_info(host, port):
    """Get information about what's using a specific port"""
    try:
        if sys.platform == "win32":
            # Windows - use netstat to find what's using the port
            result = subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            lines = result.stdout.split('\n')
            for line in lines:
                if f':{port}' in line and 'LISTENING' in line:
                    parts = line.split()
                    if len(parts) >= 5:
                        pid = parts[-1]
                        # Try to get process name
                        try:
                            proc_result = subprocess.run(['tasklist', '/FI', f'PID eq {pid}'], 
                                                       capture_output=True, text=True)
                            proc_lines = proc_result.stdout.split('\n')
                            for proc_line in proc_lines:
                                if pid in proc_line:
                                    proc_name = proc_line.split()[0]
                                    return f"Process: {proc_name} (PID: {pid})"
                        except:
                            pass
                        return f"PID: {pid}"
        else:
            # Unix-like systems - use lsof or netstat
            try:
                result = subprocess.run(['lsof', '-i', f':{port}'], capture_output=True, text=True)
                if result.stdout:
                    lines = result.stdout.strip().split('\n')
                    if len(lines) > 1:  # Skip header
                        parts = lines[1].split()
                        if len(parts) >= 2:
                            return f"Process: {parts[0]} (PID: {parts[1]})"
            except FileNotFoundError:
                # lsof not available, try netstat
                result = subprocess.run(['netstat', '-tlnp'], capture_output=True, text=True)
                lines = result.stdout.split('\n')
                for line in lines:
                    if f':{port} ' in line and 'LISTEN' in line:
                        parts = line.split()
                        if len(parts) >= 7:
                            proc_info = parts[-1]
                            return f"Process info: {proc_info}"
    except Exception:
        pass
    return "Unknown process"

def start_server(host=None, port=None, force=False):
    """Start the web server"""
    global DEFAULT_HOST, DEFAULT_PORT
    if host:
        DEFAULT_HOST = host
    if port:
        DEFAULT_PORT = port
        
    # Check if our server is already running
    pid_info = read_pid_file()
    if pid_info and is_process_running(pid_info['pid']):
        print(f"Server is already running (PID: {pid_info['pid']})")
        print(f"Access it at: http://{pid_info['host']}:{pid_info['port']}")
        return False
    
    # Remove stale PID file
    remove_pid_file()
    
    # Check if the requested port is available (unless forced)
    if not force and not is_port_available(DEFAULT_HOST, DEFAULT_PORT):
        port_usage = get_port_usage_info(DEFAULT_HOST, DEFAULT_PORT)
        print(f"❌ Port {DEFAULT_PORT} is already in use!")
        print(f"   Used by: {port_usage}")
        
        # Try to find an alternative port
        alternative_port = find_available_port(DEFAULT_HOST, DEFAULT_PORT + 1)
        if alternative_port:
            print(f"💡 Suggested alternative: --port {alternative_port}")
            
            # Ask user if they want to use the alternative port
            try:
                response = input(f"Would you like to use port {alternative_port} instead? (y/N): ").strip().lower()
                if response in ['y', 'yes']:
                    DEFAULT_PORT = alternative_port
                    print(f"✅ Using port {alternative_port}")
                else:
                    print("❌ Server startup cancelled")
                    print("💡 Tip: Use --force to override port protection")
                    return False
            except (KeyboardInterrupt, EOFError):
                print("\n❌ Server startup cancelled")
                return False
        else:
            print("❌ No alternative ports found in the range")
            print("   Try specifying a different port with --port <number>")
            print("💡 Tip: Use --force to override port protection")
            return False
    elif force and not is_port_available(DEFAULT_HOST, DEFAULT_PORT):
        port_usage = get_port_usage_info(DEFAULT_HOST, DEFAULT_PORT)
        print(f"⚠️  Warning: Port {DEFAULT_PORT} is busy (used by: {port_usage})")
        print(f"🔧 Force mode enabled - attempting to start anyway...")
    
    print(f"Starting production server on {DEFAULT_HOST}:{DEFAULT_PORT}...")
    
    # Start server in background
    if sys.platform == "win32":
        # Windows
        cmd = [sys.executable, __file__, '_run_server', '--host', DEFAULT_HOST, '--port', str(DEFAULT_PORT)]
        subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        # Unix-like systems
        pid = os.fork()
        if pid == 0:
            # Child process
            os.setsid()
            _run_server_process()
            sys.exit(0)
    
    # Wait a moment for server to start
    time.sleep(3)
    
    # Verify server started
    pid_info = read_pid_file()
    if pid_info and is_process_running(pid_info['pid']):
        print(f"✅ Server started successfully (PID: {pid_info['pid']})")
        print(f"🌐 Access it at: http://{DEFAULT_HOST}:{DEFAULT_PORT}")
        return True
    else:
        print("❌ Failed to start server")
        if force:
            print("   This might be due to the port conflict that was ignored")
        return False

def _run_server_process():
    """Run the production server process"""
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
            print("Error: Production WSGI server not available!")
            print("Please install with: pip install waitress")
            print("Exiting...")
            sys.exit(1)
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

def check_port(host=None, port=None):
    """Check if a port is available"""
    if not host:
        host = DEFAULT_HOST
    if not port:
        port = DEFAULT_PORT
    
    print(f"Checking port {port} on {host}...")
    
    if is_port_available(host, port):
        print(f"✅ Port {port} is available")
        return True
    else:
        port_usage = get_port_usage_info(host, port)
        print(f"❌ Port {port} is busy")
        print(f"   Used by: {port_usage}")
        
        # Suggest alternatives
        print(f"\n🔍 Looking for alternative ports...")
        alternatives = []
        for i in range(1, 11):
            alt_port = port + i
            if is_port_available(host, alt_port):
                alternatives.append(alt_port)
                if len(alternatives) >= 3:  # Show up to 3 alternatives
                    break
        
        if alternatives:
            print(f"💡 Available alternatives: {', '.join(map(str, alternatives))}")
        else:
            print("❌ No nearby alternatives found")
        
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
        
        # Also check if the port is still available (someone else might have taken it)
        if not is_port_available(pid_info['host'], pid_info['port']):
            print("✅ Port is properly bound")
        else:
            print("⚠️  Warning: Port appears to be available (server might not be listening)")
        
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
  %(prog)s start                    Start the production server in background
  %(prog)s start --force            Start even if port is busy
  %(prog)s stop                     Stop the running server
  %(prog)s status                   Check server status
  %(prog)s restart                  Restart the server
  %(prog)s check-port               Check if default port is available
  %(prog)s check-port --port 9000   Check if specific port is available
        """
    )
    
    parser.add_argument('command', 
                       choices=['start', 'stop', 'status', 'restart', 'check-port', '_run_server'],
                       help='Command to execute')
    
    parser.add_argument('--host', 
                       default=DEFAULT_HOST,
                       help=f'Host to bind to (default: {DEFAULT_HOST})')
    
    parser.add_argument('--port', 
                       type=int, 
                       default=DEFAULT_PORT,
                       help=f'Port to bind to (default: {DEFAULT_PORT})')
    
    parser.add_argument('--force', 
                       action='store_true',
                       help='Force start even if port is already in use')
    
    args = parser.parse_args()
    
    if args.command == 'start':
        success = start_server(args.host, args.port, args.force)
        sys.exit(0 if success else 1)
        
    elif args.command == 'stop':
        success = stop_server()
        sys.exit(0 if success else 1)
        
    elif args.command == 'status':
        success = status_server()
        sys.exit(0 if success else 1)
        
    elif args.command == 'check-port':
        success = check_port(args.host, args.port)
        sys.exit(0 if success else 1)
        
    elif args.command == 'restart':
        print("Restarting server...")
        stop_server()
        time.sleep(1)
        success = start_server(args.host, args.port, args.force)
        sys.exit(0 if success else 1)
        
    elif args.command == '_run_server':
        # Internal command for Windows background process
        DEFAULT_HOST = args.host
        DEFAULT_PORT = args.port
        _run_server_process()

if __name__ == '__main__':
    main()