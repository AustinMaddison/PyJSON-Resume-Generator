import json
import os
from jinja2 import Environment, FileSystemLoader
import time
from flask import Flask, send_from_directory, Response
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import queue

# Create Flask app
app = Flask(__name__, static_folder='static')

# Queue to store SSE clients
sse_clients = []

def load_json_file(file_path):
    """Load and parse a JSON file."""
    with open(file_path, 'r') as f:
        return json.load(f)

def get_selected_projects(projects_data, position):
    """Get projects relevant for the specified position."""
    for position_map in projects_data.get("job-positions-project", []):
        if position in position_map:
            project_names = position_map[position]
            
            selected_projects = []
            for name in project_names:
                for project in projects_data.get("projects", []):
                    if project["name"] == name:
                        selected_projects.append(project)
                        break
            
            return selected_projects
    
    return []

def generate_resume(base_data, projects_data, position, output_dir):
    """Generate a resume for the specified position."""
    # Get relevant projects for the position
    selected_projects = get_selected_projects(projects_data, position)
    
    # Set up Jinja environment
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('resume_template.html')
    
    # Prepare data for the template
    template_data = base_data.copy()
    template_data['selected_projects'] = selected_projects
    template_data['position_title'] = position
    
    # Render the template
    output = template.render(**template_data)
    
    # Create the output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Write the output to a file
    output_file = os.path.join(output_dir, f"resume_{position.replace(' ', '_').lower()}.html")
    with open(output_file, 'w') as f:
        f.write(output)
    
    return output_file

def generate_all_resumes():
    """Generate resumes for all positions in the JSON data."""
    print("Generating all resumes...")
    
    # Load the JSON data
    base_data = load_json_file('base.json')
    projects_data = load_json_file('projects.json')
    
    # Get all available positions
    positions = [pos['title'] for pos in projects_data.get('job-positions', [])]
    output_dir = 'resumes'
    
    # Generate resumes for all positions
    for position in positions:
        output_file = generate_resume(base_data, projects_data, position, output_dir)
        print(f"Generated: {output_file}")
    
    # Generate an index page
    generate_index_page(positions)
    
    # Notify clients to refresh their browsers
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

def generate_index_page(positions):
    """Generate an index page listing all available resumes."""
    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('index_template.html')
    
    output = template.render(positions=positions)
    
    with open('resumes/index.html', 'w') as f:
        f.write(output)

class FileChangeHandler(FileSystemEventHandler):
    # Class-level variable for the timer
    _timer = None
    # Debounce time in seconds
    DEBOUNCE_SECONDS = 1.0
    
    def on_modified(self, event):
        if event.src_path.endswith('.json') or (event.src_path.startswith('./templates/') and event.src_path.endswith('.html')) or (event.src_path.startswith('./static/css/') and event.src_path.endswith('.css')):
            print(f"Detected change in {event.src_path}, waiting for changes to stabilize...")
            
            # Cancel the timer if it's already running
            if self._timer:
                self._timer.cancel()
            
            # Create a new timer that will regenerate resumes after the debounce period
            self._timer = threading.Timer(self.DEBOUNCE_SECONDS, self._regenerate_resumes)
            self._timer.start()
    
    def _regenerate_resumes(self):
        print("Changes stabilized, regenerating resumes...")
        generate_all_resumes()

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
    return send_from_directory('resumes', 'index.html')

@app.route('/<path:path>')
def serve_file(path):
    return send_from_directory('resumes', path)

@app.route('/css/<path:path>')
def serve_css(path):
    return send_from_directory('static/css', path)

def watch_files():
    event_handler = FileChangeHandler()
    observer = Observer()
    observer.schedule(event_handler, '.', recursive=True)
    observer.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    
    observer.join()

if __name__ == "__main__":
    # Make sure the static directories exist
    os.makedirs('static/css', exist_ok=True)
    
    # Generate all resumes initially
    positions = generate_all_resumes()
    
    # Start the file watcher in a separate thread
    watcher_thread = threading.Thread(target=watch_files)
    watcher_thread.daemon = True
    watcher_thread.start()
    
    print("Starting server at http://localhost:5000")
    print("Available positions:")
    for pos in positions:
        print(f"- {pos} (http://localhost:5000/resume_{pos.replace(' ', '_').lower()}.html)")
    
    # Start the Flask server
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)