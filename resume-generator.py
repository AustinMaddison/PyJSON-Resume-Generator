#!/usr/bin/env python3
# filepath: /home/austin/dev/resume-generator/resume-generator.py

import json
import os
import sys
import time
import threading
import queue
import subprocess
from datetime import date, datetime
from flask import Flask, send_from_directory, Response
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from jinja2 import Environment, FileSystemLoader
import argparse
from threading import Lock
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('resume-generator')

# Create Flask app
app = Flask(__name__, static_folder='static')

# Queue and lock for SSE clients
sse_clients = []
MAX_SSE_CLIENTS = 10
sse_lock = Lock()

# Default configuration
DEFAULT_CONFIG = {
    'include_sections': ['header', 'summary', 'skills', 'experience', 'education', 'projects', 'awards', 'languages'],
    'max_projects': None,  # None means include all selected projects
    'base_json': './data/base.json',
    'projects_json': './data/projects.json',
    'positions_json': './data/positions.json',
    'output_dir': 'resumes',
    'port': 5000,
    'watch': False,
    'default_position_name': 'General Resume'
}

def parse_arguments():
    """Parse command line arguments and return config dict"""
    parser = argparse.ArgumentParser(description="Resume Generator")
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    subparsers.required = True
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build resumes')
    
    # Section control
    build_parser.add_argument('--sections', type=str, 
                        help='Comma-separated list of sections to include (default: all)')
    build_parser.add_argument('--exclude', type=str,
                        help='Comma-separated list of sections to exclude')
    
    # Project control
    build_parser.add_argument('--max-projects', type=int,
                        help=f'Maximum number of projects to include per resume')
    
    # File paths
    build_parser.add_argument('--base-json', type=str,
                        help=f'Path to base JSON file (default: {DEFAULT_CONFIG["base_json"]})')
    build_parser.add_argument('--projects-json', type=str, 
                        help=f'Path to projects JSON file (default: {DEFAULT_CONFIG["projects_json"]})')
    build_parser.add_argument('--positions-json', type=str, 
                        help=f'Path to positions JSON file (default: {DEFAULT_CONFIG["positions_json"]})')
    build_parser.add_argument('--output-dir', type=str,
                        help=f'Output directory for generated resumes (default: {DEFAULT_CONFIG["output_dir"]})')
    
    # Watch mode
    build_parser.add_argument('-w', '--watch', action='store_true',
                        help='Watch files for changes and rebuild automatically')
    
    # Server settings
    build_parser.add_argument('--port', type=int,
                        help=f'Port for the web server when watching (default: {DEFAULT_CONFIG["port"]})')
    
    # Server command (separate from build)
    server_parser = subparsers.add_parser('server', help='Run server only without building')
    server_parser.add_argument('--port', type=int, 
                        help=f'Port for the web server (default: {DEFAULT_CONFIG["port"]})')
    server_parser.add_argument('--output-dir', type=str,
                        help=f'Directory to serve files from (default: {DEFAULT_CONFIG["output_dir"]})')
    
    args = parser.parse_args()
    
    # Start with default config
    config = DEFAULT_CONFIG.copy()
    
    # Update config with provided arguments
    if args.command == 'build':
        if args.sections:
            config['include_sections'] = args.sections.split(',')
        if args.exclude:
            exclude_sections = args.exclude.split(',')
            config['include_sections'] = [s for s in config['include_sections'] if s not in exclude_sections]
        if args.max_projects is not None:
            config['max_projects'] = args.max_projects
        if args.base_json:
            config['base_json'] = args.base_json
        if args.projects_json:
            config['projects_json'] = args.projects_json
        if args.positions_json:
            config['positions_json'] = args.positions_json
        if args.output_dir:
            config['output_dir'] = args.output_dir
        if args.port:
            config['port'] = args.port
        config['watch'] = args.watch
    
    elif args.command == 'server':
        if args.port:
            config['port'] = args.port
        if args.output_dir:
            config['output_dir'] = args.output_dir
    
    return config, args.command

def load_json_file(file_path, default=None):
    """Load and parse a JSON file with error handling."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"File not found: {file_path}, using default values")
        return default if default is not None else {}
    except json.JSONDecodeError:
        logger.warning(f"Invalid JSON in {file_path}, using default values")
        return default if default is not None else {}
    except Exception as e:
        logger.warning(f"Error loading {file_path}: {e}, using default values")
        return default if default is not None else {}

def get_selected_projects(projects_data, position, position_data=None, max_projects=None):
    """Get projects relevant for the specified position."""
    # If no projects, return empty list
    if not projects_data or 'projects' not in projects_data:
        return []
        
    # If we have position-specific project order from positions.json, use it
    if position_data and 'project-order' in position_data:
        ordered_projects = []
        project_order = position_data['project-order']
        
        # First add projects in specified order
        for project_name in project_order:
            for project in projects_data.get('projects', []):
                if project.get('name') == project_name:
                    ordered_projects.append(project)
                    break
        
        # Apply max_projects limit if specified
        if max_projects is not None and max_projects > 0:
            ordered_projects = ordered_projects[:max_projects]
            
        return ordered_projects
    
    # Otherwise use old method (from projects.json)
    selected_projects = []
    selected_project_names = set()
    
    # First check job-positions-project mapping if available
    for position_map in projects_data.get("job-positions-project", []):
        if position in position_map:
            project_names = position_map[position]
            
            for name in project_names:
                selected_project_names.add(name)
                for project in projects_data.get("projects", []):
                    if project.get("name") == name:
                        selected_projects.append(project)
                        break
    
    # If no mapping or incomplete, add remaining projects
    if not selected_projects:
        selected_projects = projects_data.get("projects", [])
    
    # Apply max_projects limit if specified
    if max_projects is not None and max_projects > 0:
        selected_projects = selected_projects[:max_projects]
    
    return selected_projects

def datetime_format(value, format="%b %Y"):
    if not value:
        return "Present"
    try:
        date_data = value.split('-')
        date_data = [int(x) for x in date_data]
        return date(date_data[0], date_data[1], date_data[2]).strftime(format)
    except (ValueError, IndexError, AttributeError):
        return value  # Return original if it can't be parsed

def generate_resume(base_data, projects_data, position, output_dir, position_data=None, config=None):
    """Generate a resume for the specified position."""
    if config is None:
        config = DEFAULT_CONFIG
    
    start_time = time.time()
    
    # Get relevant projects for the position
    selected_projects = get_selected_projects(
        projects_data, 
        position, 
        position_data=position_data, 
        max_projects=config['max_projects']
    )
    
    # Set up Jinja environment
    env = Environment(loader=FileSystemLoader('templates'))
    env.filters["datetime_format"] = datetime_format
    template = env.get_template('resume_template.html')
    
    # Prepare data for the template
    template_data = base_data.copy() if base_data else {}
    template_data['selected_projects'] = selected_projects
    template_data['position_title'] = position
    template_data['sections'] = config['include_sections']
    
    # Get position summary if available
    if position_data and 'summary' in position_data:
        template_data['position_summary'] = position_data['summary']
    
    # Replace `` with " in all string values throughout the template data
    def replace_backticks(data):
        if isinstance(data, dict):
            return {k: replace_backticks(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [replace_backticks(item) for item in data]
        elif isinstance(data, str):
            return data.replace("``", "\"")
        else:
            return data

    template_data = replace_backticks(template_data)
    
    # Render the template
    output = template.render(**template_data)
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Write the output to a file
    safe_position = position.replace(' ', '_').lower()
    output_file = os.path.join(output_dir, f"resume_{safe_position}.html")
    with open(output_file, 'w') as f:
        f.write(output)
    
    end_time = time.time()
    
    return {
        'file': output_file,
        'position': position,
        'projects_count': len(selected_projects),
        'time': end_time - start_time
    }

def generate_all_resumes(config=None):
    """Generate resumes for all positions in the JSON data."""
    if config is None:
        config = DEFAULT_CONFIG
        
    logger.info("Building resumes...")
    start_time = time.time()
    
    # Load data files with error handling
    base_data = load_json_file(config['base_json'], {})
    projects_data = load_json_file(config['projects_json'], {'projects': []})
    positions_data = load_json_file(config['positions_json'], {'job-positions': []})
    
    # Extract positions from positions.json
    positions = []
    position_data_map = {}
    
    for pos in positions_data.get('job-positions', []):
        if 'title' in pos:
            positions.append(pos['title'])
            position_data_map[pos['title']] = pos
    
    # If no positions found, use default
    if not positions:
        positions = [config['default_position_name']]
    
    output_dir = config['output_dir']
    results = []
    
    # Generate resumes for all positions
    for position in positions:
        position_data = position_data_map.get(position)
        result = generate_resume(
            base_data, 
            projects_data, 
            position, 
            output_dir, 
            position_data=position_data, 
            config=config
        )
        results.append(result)
        logger.info(f"✓ {position:<30} | {result['projects_count']:>2} projects | {result['time']*1000:.2f}ms")
    
    # Generate an index page
    index_result = generate_index_page(positions, output_dir)
    results.append({
        'file': index_result,
        'position': 'index',
        'projects_count': 0,
        'time': 0  # We're not tracking this separately
    })
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Build summary statistics
    logger.info("\nBuild completed in %.2f seconds", total_time)
    logger.info(f"│ {len(results)} pages generated")
    logger.info(f"│ Avg build time: {(total_time/max(1, len(results)-1))*1000:.2f}ms per page")
    logger.info(f"│ Output directory: {os.path.abspath(output_dir)}")
    
    # Notify clients if in watch mode
    if config.get('watch'):
        notify_clients()
    
    return positions, results

def notify_clients():
    """Send a message to all SSE clients"""
    if not sse_clients:
        return
        
    message = f"data: {{\"event\": \"refresh\", \"timestamp\": {time.time()}}}\n\n"
    
    # Thread-safe client notification
    with sse_lock:
        for client in list(sse_clients):
            try:
                # Non-blocking put with timeout
                client.put(message, timeout=0.1) 
            except (queue.Full, Exception) as e:
                logger.error(f"Error sending to client: {e}")
                sse_clients.remove(client)
                
    logger.info(f"Notified {len(sse_clients)} clients")

def generate_index_page(positions, output_dir):
    """Generate an index page listing all available resumes."""
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('index_template.html')
    
    output = template.render(positions=positions)
    
    output_file = os.path.join(output_dir, 'index.html')
    with open(output_file, 'w') as f:
        f.write(output)
        
    return output_file

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, config=None):
        self._timer = None
        self.DEBOUNCE_SECONDS = 0.8
        self.config = config or DEFAULT_CONFIG
    
    def on_modified(self, event):
        if (event.src_path.endswith('.json') or 
            (event.src_path.startswith('./templates/') and event.src_path.endswith('.html')) or 
            (event.src_path.startswith('./static/css/') and event.src_path.endswith('.css'))):
        
            logger.info(f"Detected change in {event.src_path}, waiting for changes to stabilize...")
            
            if self._timer:
                self._timer.cancel()
            
            self._timer = threading.Timer(self.DEBOUNCE_SECONDS, self._regenerate_resumes)
            self._timer.start()
    
    def _regenerate_resumes(self):
        logger.info("Changes stabilized, rebuilding...")
        try:
            logger.info("Running npm build...")
            subprocess.run(["npm", "run", "build-css"], check=True)
            logger.info("CSS build completed successfully")
        except subprocess.CalledProcessError as e:
            logger.error(f"CSS build failed: {e}")
        except FileNotFoundError:
            logger.warning("npm command not found. Make sure Node.js is installed.")
        
        generate_all_resumes(self.config)

# SSE route
@app.route('/events')
def sse():
    def event_stream():
        # Check if we've hit the connection limit
        if len(sse_clients) >= MAX_SSE_CLIENTS:
            yield "data: {\"event\": \"error\", \"message\": \"Too many connections\"}\n\n"
            return
            
        # Create client queue with timeout support
        client_queue = queue.Queue()
        
        # Thread-safe client addition
        with sse_lock:
            sse_clients.append(client_queue)
        
        logger.info(f"Client connected. Active connections: {len(sse_clients)}")
        
        try:
            # Send initial message
            yield "data: {\"event\": \"connected\", \"client_count\": " + str(len(sse_clients)) + "}\n\n"
            
            # Wait for events with timeout
            while True:
                try:
                    # Use timeout to avoid blocking forever
                    message = client_queue.get(timeout=5)
                    yield message
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield "data: {\"event\": \"heartbeat\"}\n\n"
        except GeneratorExit:
            # Clean removal when client disconnects
            with sse_lock:
                if client_queue in sse_clients:
                    sse_clients.remove(client_queue)
            logger.info(f"Client disconnected. Active connections: {len(sse_clients)}")
    
    # Set cache headers to prevent proxy/browser caching
    response = Response(event_stream(), mimetype="text/event-stream")
    response.headers['Cache-Control'] = 'no-cache'
    response.headers['X-Accel-Buffering'] = 'no'
    return response

# Flask routes
@app.route('/')
def index():
    return send_from_directory(app.config['OUTPUT_DIR'], 'index.html')

@app.route('/<path:path>')
def serve_file(path):
    return send_from_directory(app.config['OUTPUT_DIR'], path)

@app.route('/css/<path:path>')
def serve_css(path):
    return send_from_directory('static/css', path)

@app.route('/fonts/<path:path>')
def serve_fonts(path):
    return send_from_directory('static/fonts', path)

def watch_files(config=None):
    if config is None:
        config = DEFAULT_CONFIG
        
    logger.info("Starting file watcher...")
    
    event_handler = FileChangeHandler(config)
    observer = Observer()
    
    # Watch JSON data files
    for file_path in [config['base_json'], config['projects_json'], config['positions_json']]:
        dir_path = os.path.dirname(file_path)
        if os.path.exists(dir_path):
            observer.schedule(event_handler, dir_path, recursive=False)
    
    # Watch templates and CSS
    if os.path.exists('./templates'):
        observer.schedule(event_handler, './templates', recursive=False)
    if os.path.exists('./static/css'):
        observer.schedule(event_handler, './static/css', recursive=False)
    
    observer.start()
    
    try:
        logger.info("File watcher running. Press Ctrl+C to stop.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

def run_server(config=None):
    if config is None:
        config = DEFAULT_CONFIG
    
    # Update Flask app configuration
    app.config['OUTPUT_DIR'] = config['output_dir']
    
    logger.info(f"Starting server at http://localhost:{config['port']}")
    logger.info(f"Serving files from: {os.path.abspath(config['output_dir'])}")
    
    # Start the Flask server
    app.run(debug=True, host='0.0.0.0', port=config['port'], threaded=True)

if __name__ == "__main__":
    # Parse command line arguments
    config, command = parse_arguments()
    
    # Make sure directories exist
    os.makedirs('static/css', exist_ok=True)
    os.makedirs(config['output_dir'], exist_ok=True)
    
    if command == 'build':
        # Build resumes
        positions, results = generate_all_resumes(config)
        
        # Print URLs to generated resumes
        logger.info("\nAvailable at:")
        for position in positions:
            safe_position = position.replace(' ', '_').lower()
            logger.info(f"│ http://localhost:{config['port']}/resume_{safe_position}.html")
        
        # Start file watcher if requested
        if config['watch']:
            logger.info("\nStarting watch mode...")
            
            # Start watcher thread
            watcher_thread = threading.Thread(target=watch_files, args=(config,))
            watcher_thread.daemon = True
            watcher_thread.start()
            
            # Run server
            run_server(config)
    
    elif command == 'server':
        # Just run the server without building
        run_server(config)