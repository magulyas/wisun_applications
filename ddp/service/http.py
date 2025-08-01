#!/usr/bin/env python3
"""
HTTP Server Service Module

Contains the core web server functionality for WiSUN Applications.
"""

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

class HttpServer:
    """HTTP Server management class"""
    
    def __init__(self, host=None, port=None, pid_file=None, log_file=None):
        self.host = host or DEFAULT_HOST
        self.port = port or DEFAULT_PORT
        self.pid_file = pid_file or Path(__file__).parent.parent / 'server.pid'
        self.log_file = log_file or Path(__file__).parent.parent / 'server.log'
        
        # Create Flask app
        self.app = Flask(__name__)
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup Flask routes"""
        
        @self.app.route('/')
        def home():
            """Home endpoint"""
            return jsonify({
                'status': 'running',
                'message': 'WiSUN Applications Server is running',
                'pid': os.getpid()
            })

        @self.app.route('/health')
        def health():
            """Health check endpoint"""
            return jsonify({
                'status': 'healthy',
                'timestamp': time.time()
            })

        @self.app.route('/api/info')
        def info():
            """Server information endpoint"""
            return jsonify({
                'server': 'WiSUN Applications Server',
                'pid': os.getpid(),
                'host': request.host,
                'uptime': time.time() - getattr(self.app, 'start_time', time.time())
            })
    
    def write_pid_file(self, pid):
        """Write the process ID to a file"""
        try:
            with open(self.pid_file, 'w') as f:
                json.dump({
                    'pid': pid,
                    'start_time': time.time(),
                    'host': self.host,
                    'port': self.port
                }, f)
            return True
        except Exception as e:
            print(f"Error writing PID file: {e}")
            return False

    def read_pid_file(self):
        """Read the process ID from file"""
        try:
            if self.pid_file.exists():
                with open(self.pid_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    def remove_pid_file(self):
        """Remove the PID file"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True
        except Exception as e:
            print(f"Error removing PID file: {e}")
            return False

    def is_process_running(self, pid):
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

    def is_port_available(self, host=None, port=None):
        """Check if a port is available for binding"""
        host = host or self.host
        port = port or self.port
        
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

    def find_available_port(self, start_port=None, max_attempts=10):
        """Find an available port starting from start_port"""
        start_port = start_port or self.port
        for port in range(start_port, start_port + max_attempts):
            if self.is_port_available(self.host, port):
                return port
        return None

    def get_port_usage_info(self, host=None, port=None):
        """Get information about what's using a specific port"""
        host = host or self.host
        port = port or self.port
        
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

    def start(self, force=False):
        """Start the web server"""
        # Check if our server is already running
        pid_info = self.read_pid_file()
        if pid_info and self.is_process_running(pid_info['pid']):
            print(f"Server is already running (PID: {pid_info['pid']})")
            print(f"Access it at: http://{pid_info['host']}:{pid_info['port']}")
            return False
        
        # Remove stale PID file
        self.remove_pid_file()
        
        # Check if the requested port is available (unless forced)
        if not force and not self.is_port_available():
            port_usage = self.get_port_usage_info()
            print(f"⚠️  Port {self.port} is already in use (used by: {port_usage})")
            
            # Automatically find and use an alternative port
            alternative_port = self.find_available_port(self.port + 1)
            if alternative_port:
                print(f"🔄 Automatically switching to port {alternative_port}")
                self.port = alternative_port
            else:
                print("❌ No alternative ports found in the range")
                print("   Try specifying a different port with --port <number>")
                print("💡 Tip: Use --force to override port protection")
                return False
        elif force and not self.is_port_available():
            port_usage = self.get_port_usage_info()
            print(f"⚠️  Warning: Port {self.port} is busy (used by: {port_usage})")
            print(f"🔧 Force mode enabled - attempting to start anyway...")
        
        print(f"Starting production server on {self.host}:{self.port}...")
        
        # Start server in background
        if sys.platform == "win32":
            # Windows
            script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'server.py')
            cmd = [sys.executable, script_path, '_run_server', '--host', self.host, '--port', str(self.port)]
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        else:
            # Unix-like systems
            pid = os.fork()
            if pid == 0:
                # Child process
                os.setsid()
                self._run_server_process()
                sys.exit(0)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Verify server started
        pid_info = self.read_pid_file()
        if pid_info and self.is_process_running(pid_info['pid']):
            print(f"✅ Server started successfully (PID: {pid_info['pid']})")
            print(f"🌐 Access it at: http://{self.host}:{self.port}")
            return True
        else:
            print("❌ Failed to start server")
            if force:
                print("   This might be due to the port conflict that was ignored")
            return False

    def _run_server_process(self):
        """Run the production server process"""
        self.app.start_time = time.time()
        
        # Write PID file
        self.write_pid_file(os.getpid())
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            print(f"\nReceived signal {signum}, shutting down...")
            self.remove_pid_file()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Redirect stdout/stderr to log file for background operation
            if not sys.stdout.isatty():
                log_file = open(self.log_file, 'a')
                sys.stdout = log_file
                sys.stderr = log_file
            
            # Use production WSGI server
            try:
                if sys.platform == "win32":
                    # Use Waitress for Windows (and as fallback)
                    from waitress import serve
                    print(f"Starting production server (Waitress) on {self.host}:{self.port}")
                    serve(self.app, host=self.host, port=self.port)
                else:
                    # Try Gunicorn for Unix systems, fallback to Waitress
                    try:
                        import gunicorn.app.wsgiapp
                        print(f"Starting production server (Gunicorn) on {self.host}:{self.port}")
                        # Create Gunicorn application
                        sys.argv = [
                            'gunicorn',
                            '--bind', f'{self.host}:{self.port}',
                            '--workers', '4',
                            '--worker-class', 'sync',
                            '--timeout', '30',
                            '--keep-alive', '2',
                            '--max-requests', '1000',
                            '--max-requests-jitter', '100',
                            '--access-logfile', '-',
                            '--error-logfile', '-',
                            'service.http:app'
                        ]
                        gunicorn.app.wsgiapp.run()
                    except ImportError:
                        # Fallback to Waitress
                        from waitress import serve
                        print(f"Starting production server (Waitress) on {self.host}:{self.port}")
                        serve(self.app, host=self.host, port=self.port)
            except ImportError:
                print("Error: Production WSGI server not available!")
                print("Please install with: pip install waitress")
                print("Exiting...")
                sys.exit(1)
        finally:
            self.remove_pid_file()

    def stop(self):
        """Stop the web server"""
        pid_info = self.read_pid_file()
        
        if not pid_info:
            print("No server appears to be running (no PID file found)")
            return False
        
        pid = pid_info['pid']
        
        if not self.is_process_running(pid):
            print(f"Server with PID {pid} is not running")
            self.remove_pid_file()
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
                    if not self.is_process_running(pid):
                        break
                    time.sleep(0.5)
                
                # Force kill if still running
                if self.is_process_running(pid):
                    os.kill(pid, signal.SIGKILL)
            
            self.remove_pid_file()
            print("Server stopped successfully")
            return True
            
        except Exception as e:
            print(f"Error stopping server: {e}")
            return False

    def check_port(self, host=None, port=None):
        """Check if a port is available"""
        host = host or self.host
        port = port or self.port
        
        print(f"Checking port {port} on {host}...")
        
        if self.is_port_available(host, port):
            print(f"✅ Port {port} is available")
            return True
        else:
            port_usage = self.get_port_usage_info(host, port)
            print(f"❌ Port {port} is busy")
            print(f"   Used by: {port_usage}")
            
            # Suggest alternatives
            print(f"\n🔍 Looking for alternative ports...")
            alternatives = []
            for i in range(1, 11):
                alt_port = port + i
                if self.is_port_available(host, alt_port):
                    alternatives.append(alt_port)
                    if len(alternatives) >= 3:  # Show up to 3 alternatives
                        break
            
            if alternatives:
                print(f"💡 Available alternatives: {', '.join(map(str, alternatives))}")
            else:
                print("❌ No nearby alternatives found")
            
            return False

    def status(self):
        """Check server status"""
        pid_info = self.read_pid_file()
        
        if not pid_info:
            print("Status: Not running (no PID file)")
            return False
        
        pid = pid_info['pid']
        
        if self.is_process_running(pid):
            uptime = time.time() - pid_info['start_time']
            print(f"Status: Running")
            print(f"PID: {pid}")
            print(f"Host: {pid_info['host']}")
            print(f"Port: {pid_info['port']}")
            print(f"Uptime: {uptime:.1f} seconds")
            print(f"URL: http://{pid_info['host']}:{pid_info['port']}")
            
            # Also check if the port is still available (someone else might have taken it)
            if not self.is_port_available(pid_info['host'], pid_info['port']):
                print("✅ Port is properly bound")
            else:
                print("⚠️  Warning: Port appears to be available (server might not be listening)")
            
            return True
        else:
            print(f"Status: Not running (PID {pid} not found)")
            self.remove_pid_file()
            return False

    def restart(self, force=False):
        """Restart the web server"""
        print("Restarting server...")
        self.stop()
        time.sleep(1)
        return self.start(force)


# For direct execution
if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='HTTP Server Service')
    parser.add_argument('command', choices=['_run_server'], help='Internal command')
    parser.add_argument('--host', default=DEFAULT_HOST)
    parser.add_argument('--port', type=int, default=DEFAULT_PORT)
    
    args = parser.parse_args()
    
    if args.command == '_run_server':
        server = HttpServer(args.host, args.port)
        server._run_server_process()
