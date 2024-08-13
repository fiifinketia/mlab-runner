"""Read the pm2 logs file to get the latest pinggy url and serve the information via https"""
from http.server import BaseHTTPRequestHandler, HTTPServer

from runner.settings import settings

class PinggyHelper(BaseHTTPRequestHandler):

    
    def _read_pm2_logs_file(self, logs_dir: str) -> str:
        # Read the pm2 logs file and find the latest pinggy url
        # This method should be implemented based on the specific pm2 logs format
        with open(logs_dir, 'r') as f:
            return f.read()
        
    def _get_latest_pinggy_urls(self) -> str | None:
        # read the lines from the file from the bottom
        # if line starts with URLs, find the content after in square brackets
        # return the URLs as a string, separated by commas
        lines = self._read_pm2_logs_file(settings.pm2_logs_dir).split('\n')
        for line in reversed(lines):
            if line.startswith('URLs:'):
                urls = line[line.find('[') + 1: line.find(']')]
                return urls.split(', ')[0]
        return None
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(self._get_latest_pinggy_urls())
    
class PinggyHelperSever:

    def start_server(self):
        server = HTTPServer((settings.host, settings.pinggy_port), PinggyHelper)
        print(f'Pinggy Helper Server started on http://{settings.host}:{settings.pinggy_port}/')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print('Server stopped by user')
        server.server_close()
        print('Pinggy Helper Server closed')
