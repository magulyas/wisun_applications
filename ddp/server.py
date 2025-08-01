#!/usr/bin/env python3
"""
Web Server Command Line Tool

A command line utility to start, stop, and manage a web server in the background.
"""

import argparse
import sys

from service import HttpServer

# Configuration
DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 8080

def main():
    """Main command line interface"""
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
    
    # Create server instance
    server = HttpServer(args.host, args.port)
    
    if args.command == 'start':
        success = server.start(args.force)
        sys.exit(0 if success else 1)
        
    elif args.command == 'stop':
        success = server.stop()
        sys.exit(0 if success else 1)
        
    elif args.command == 'status':
        success = server.status()
        sys.exit(0 if success else 1)
        
    elif args.command == 'check-port':
        success = server.check_port(args.host, args.port)
        sys.exit(0 if success else 1)
        
    elif args.command == 'restart':
        success = server.restart(args.force)
        sys.exit(0 if success else 1)
        
    elif args.command == '_run_server':
        # Internal command for Windows background process
        server._run_server_process()

if __name__ == '__main__':
    main()
