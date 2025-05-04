import json
import os
from jinja2 import Environment, FileSystemLoader
import time
from flask import Flask, send_from_directory, Response
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import queue
import subprocess
from datetime import date
import argparse

# Create Flask app
app = Flask(__name__, static_folder='static')

# Queue to store SSE clients
sse_clients = []

# Default configuration
DEFAULT_CONFIG = {
    'include_sections': ['header', 'summary', 'skills', 'experience', 'education', 'projects', 'certifications', 'languages'],
    'max_projects': None,  # None means include all selected projects
    'base_json': './data/base.json',
    'projects_json': './data/projects.json',
    'output_dir': 'resumes',
    'port': 5000
}

def parse_arguments():
    """Parse command line arguments and return config dict"""
    parser = argparse.ArgumentParser(description="Resume Generator")
    
    # Section control
    parser.add_argument('--sections', type=str, 
                        help='Comma-separated list of sections to include (default: all)')
    parser.add_argument('--exclude', type=str,
                        help='Comma-separated list of sections to exclude')
    
    # Project control
    parser.add_argument('--max-projects', type=int,
                        help='Maximum number of projects to include per resume')
    
    # File paths
    parser.add_argument('--base-json', type=str,
                        help=f'Path to base JSON file (default: {DEFAULT_CONFIG["base_json"]})')
    parser.add_argument('--projects-json', type=str, 
                        help=f'Path to projects JSON file (default: {DEFAULT_CONFIG["projects_json"]})')
    parser.add_argument('--output-dir', type=str,
                        help=f'Output directory for generated resumes (default: {DEFAULT_CONFIG["output_dir"]})')
    
    # Server settings
    parser.add_argument('--port', type=int,
                        help=f'Port for the web server (default: {DEFAULT_CONFIG["port"]})')
    
    args = parser.parse_args()
    
    # Start with default config
    config = DEFAULT_CONFIG.copy()
    
    # Update config with provided arguments
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
    if args.output_dir:
        config['output_dir'] = args.output_dir
    if args.port:
        config['port'] = args.port
    
    return config

def load_json_file(file_path):
    """Load and parse a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def get_selected_projects(projects_data, position, max_projects=None):
    """Get projects relevant for the specified position."""
    # Get the mapped projects for this position
    selected_projects = []
    selected_project_names = set()
    
    for position_map in projects_data.get("job-positions-project", []):
        if position in position_map:
            project_names = position_map[position]
            
            for name in project_names:
                selected_project_names.add(name)
                for project in projects_data.get("projects", []):
                    if project["name"] == name:
                        selected_projects.append(project)
                        break
    
    # Add any projects not in the map
    all_projects = projects_data.get("projects", [])
    for project in all_projects:
        if project["name"] not in selected_project_names:
            selected_projects.append(project)
    
    # Apply max_projects limit if specified
    if max_projects is not None and max_projects > 0:
        selected_projects = selected_projects[:max_projects]
    
    return selected_projects

def datetime_format(value, format="%b %Y"):
    date_data = value.split('-')
    date_data = [int(x) for x in date_data]
    return date(date_data[0], date_data[1], date_data[2]).strftime(format)

def generate_resume(base_data, projects_data, position, output_dir, config=None):
    """Generate a resume for the specified position."""
    if config is None:
        config = DEFAULT_CONFIG
    
    # Get relevant projects for the position
    selected_projects = get_selected_projects(projects_data, position, config['max_projects'])
    
    # Set up Jinja environment
    env = Environment(loader=FileSystemLoader('templates'))
    env.filters["datetime_format"] = datetime_format
    template = env.get_template('resume_template.html')
    
    # Prepare data for the template
    template_data = base_data.copy()
    template_data['selected_projects'] = selected_projects
    template_data['position_title'] = position
    template_data['sections'] = config['include_sections']
    
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
    output_file = os.path.join(output_dir, f"resume_{position.replace(' ', '_').lower()}.html")
    with open(output_file, 'w') as f:
        f.write(output)
    
    return output_file

def generate_all_resumes(config=None):
    """Generate resumes for all positions in the JSON data."""
    if config is None:
        config = DEFAULT_CONFIG
        
    print("Generating all resumes...")
    
    base_data = load_json_file(config['base_json'])
    projects_data = load_json_file(config['projects_json'])
    
    # Get all available positions
    positions = [pos['title'] for pos in projects_data.get('job-positions', [])]
    output_dir = config['output_dir']
    
    # Generate resumes for all positions
    for position in positions:
        output_file = generate_resume(base_data, projects_data, position, output_dir, config)
        print(f"Generated: {output_file}")
    
    # Generate an index page
    generate_index_page(positions, output_dir)
    
    print("Sending refresh event to all SSE clients")
    notify_clients()
    
    return positions

def notify_clients():
    """Send a message to all SSE clients"""
    message = f"data: {{\"event\": \"refresh\", \"timestamp\": {time.time()}}}\n\n"
    for client in list(sse_clients):
        try:
            client.put(message)
        except:
            sse_clients.remove(client)

def generate_index_page(positions, output_dir):
    """Generate an index page listing all available resumes."""
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('index_template.html')
    
    output = template.render(positions=positions)
    
    with open(f'{output_dir}/index.html', 'w') as f:
        f.write(output)

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, config=None):
        self._timer = None
        self.DEBOUNCE_SECONDS = 0.8
        self.config = config or DEFAULT_CONFIG
    
    def on_modified(self, event):
        if event.src_path.endswith('.json') or (event.src_path.startswith('./templates/') and 
            event.src_path.endswith('.html')) or (event.src_path.startswith('./static/css/') and 
            event.src_path.endswith('.css')):
        
            print(f"Detected change in {event.src_path}, waiting for changes to stabilize...")
            
            if self._timer:
                self._timer.cancel()
            
            self._timer = threading.Timer(self.DEBOUNCE_SECONDS, self._regenerate_resumes)
            self._timer.start()
            
    
    def _regenerate_resumes(self):
        print("Changes stabilized, regenerating resumes...")
        try:
            print("Running npm build...")
            subprocess.run(["npm", "run", "build-css"], check=True)
            print("Build completed successfully")
        except subprocess.CalledProcessError as e:
            print(f"Build failed: {e}")
        except FileNotFoundError:
            print("npm command not found. Make sure Node.js is installed.")
        generate_all_resumes(self.config)

# SSE route
@app.route('/events')
def sse():
    def event_stream():
        client_queue = queue.Queue()
        sse_clients.append(client_queue)
        try:
            # Send initial message
            yield "data: {\"event\": \"connected\"}\n\n"
            
            # Wait for events
            while True:
                message = client_queue.get()
                yield message
        except GeneratorExit:
            sse_clients.remove(client_queue)
    
    return Response(event_stream(), mimetype="text/event-stream")

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
        
    event_handler = FileChangeHandler(config)
    observer = Observer()
    observer.schedule(event_handler, os.path.dirname(config['base_json']), recursive=False)
    observer.schedule(event_handler, os.path.dirname(config['projects_json']), recursive=False)
    observer.schedule(event_handler, './templates', recursive=False)
    observer.schedule(event_handler, './static/css', recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    # Parse command line arguments
    config = parse_arguments()
    
    # Make sure the static directories exist
    os.makedirs('static/css', exist_ok=True)
    # os.makedirs('static/fonts', exist_ok=True)
    
    # Update Flask app configuration
    app.config['OUTPUT_DIR'] = config['output_dir']
    
    # Generate all resumes
    positions = generate_all_resumes(config)
    
    # Start file watcher
    watcher_thread = threading.Thread(target=watch_files, args=(config,))
    watcher_thread.daemon = True
    watcher_thread.start()
    
    print(f"Starting server at http://localhost:{config['port']}")
    print("Available positions:")
    for pos in positions:
        print(f"- {pos} (http://localhost:{config['port']}/resume_{pos.replace(' ', '_').lower()}.html)")
    print(f"Active sections: {', '.join(config['include_sections'])}")
    if config['max_projects']:
        print(f"Maximum projects per resume: {config['max_projects']}")
    
    # Start the Flask server
    app.run(debug=True, host='0.0.0.0', port=config['port'], threaded=True)