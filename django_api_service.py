#!/usr/bin/env python3
"""
Django API Service - REST API server for Teltonika data
Runs separately from the main teltonika_service.py
"""

import os
import sys
import signal
import logging
import django
from django.core.management import execute_from_command_line
from django.conf import settings

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'teltonika_db.settings')
django.setup()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/teltonika/django_api.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('django_api_service')

class DjangoAPIService:
    """Django API Service Manager"""
    
    def __init__(self):
        self.running = True
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, shutting down Django API service...")
        self.running = False
        sys.exit(0)
    
    def start_server(self, host='0.0.0.0', port='8000'):
        """Start the Django development server"""
        try:
            logger.info("🚀 Starting Django API Service")
            logger.info(f"📡 API Server: http://{host}:{port}/api/")
            logger.info(f"🔧 Admin Panel: http://{host}:{port}/admin/")
            logger.info(f"📁 Logs: /var/log/teltonika/django_api.log")
            
            # Start Django development server
            sys.argv = ['manage.py', 'runserver', f'{host}:{port}']
            execute_from_command_line(sys.argv)
            
        except KeyboardInterrupt:
            logger.info("Django API service stopped by user")
        except Exception as e:
            logger.error(f"Django API service error: {e}")
            sys.exit(1)
    
    def start_production_server(self, host='0.0.0.0', port='8000', workers=4):
        """Start production server with Gunicorn"""
        try:
            import gunicorn.app.wsgiapp as wsgi
            
            logger.info("🚀 Starting Django API Service (Production)")
            logger.info(f"📡 API Server: http://{host}:{port}/api/")
            logger.info(f"👥 Workers: {workers}")
            
            # Configure Gunicorn
            sys.argv = [
                'gunicorn',
                '--bind', f'{host}:{port}',
                '--workers', str(workers),
                '--worker-class', 'sync',
                '--timeout', '30',
                '--keep-alive', '2',
                '--max-requests', '1000',
                '--max-requests-jitter', '50',
                '--log-level', 'info',
                '--access-logfile', '/var/log/teltonika/django_access.log',
                '--error-logfile', '/var/log/teltonika/django_error.log',
                'teltonika_db.wsgi:application'
            ]
            
            wsgi.run()
            
        except ImportError:
            logger.warning("Gunicorn not available, falling back to development server")
            self.start_server(host, port)
        except Exception as e:
            logger.error(f"Production server error: {e}")
            sys.exit(1)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Django API Service for Teltonika Tracking')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to (default: 0.0.0.0)')
    parser.add_argument('--port', default='8000', help='Port to bind to (default: 8000)')
    parser.add_argument('--workers', type=int, default=4, help='Number of workers for production (default: 4)')
    parser.add_argument('--production', action='store_true', help='Run in production mode with Gunicorn')
    parser.add_argument('--dev', action='store_true', help='Run in development mode (default)')
    
    args = parser.parse_args()
    
    # Create log directory if it doesn't exist
    os.makedirs('/var/log/teltonika', exist_ok=True)
    
    service = DjangoAPIService()
    
    if args.production:
        service.start_production_server(args.host, args.port, args.workers)
    else:
        service.start_server(args.host, args.port)


if __name__ == "__main__":
    main() 