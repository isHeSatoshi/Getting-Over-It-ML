from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import sys
import os

class CORSRequestHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

class ThreadingHTTPServerBacklog(ThreadingHTTPServer):
    request_queue_size = 512

def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    directory = sys.argv[2] if len(sys.argv) > 2 else '.'
    os.chdir(directory)
    
    server_address = ('', port)
    httpd = ThreadingHTTPServerBacklog(server_address, CORSRequestHandler)
    print(f"Serving HTTP on port {port} from directory {directory}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()

if __name__ == '__main__':
    main()
