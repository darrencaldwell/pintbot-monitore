import requests
import time
import mysql.connector
import os
import json
from datetime import datetime
import schedule
from prometheus_client import start_http_server, Gauge, Counter
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Prometheus metrics
ping_response_time = Gauge('ping_response_time_seconds', 'Response time for ping requests', ['target'])
api_response_time = Gauge('api_response_time_seconds', 'Response time for API requests', ['endpoint'])
endpoint_up = Gauge('endpoint_up', 'Whether the endpoint is up (1) or down (0)', ['target'])
api_status_code = Gauge('api_status_code', 'HTTP status code returned by API', ['endpoint'])
check_count = Counter('check_count_total', 'Total number of checks performed', ['target'])

# MySQL configuration
MYSQL_HOST = os.environ.get('MYSQL_HOST', 'mysql')
MYSQL_USER = os.environ.get('MYSQL_USER', 'monitor')
MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', 'monitorpass')
MYSQL_DATABASE = os.environ.get('MYSQL_DATABASE', 'api_monitor')

# Monitoring targets
PING_TARGETS = [
    {'name': 'cloudflare-dns', 'host': '1.1.1.1', 'type': 'ping'},
    {'name': 'funkydiagrams-website', 'host': 'funkydiagrams.com', 'type': 'ping'}
]

API_ENDPOINTS = [
    {'name': 'all-pints-api', 'url': 'https://funkydiagrams.com/api/all_pints', 'type': 'api'},
    {'name': 'user-pints-api', 'url': 'https://funkydiagrams.com/api/pints/1', 'type': 'api'}  # Example user_id=1
]

def ping_host(target):
    """Ping a host and return response time"""
    host = target['host']
    target_name = target['name']
    
    check_count.labels(target=target_name).inc()
    
    start_time = time.time()
    try:
        # Using requests instead of actual ping for simplicity
        response = requests.get(f"https://{host}", timeout=5)
        end_time = time.time()
        response_time = end_time - start_time
        
        ping_response_time.labels(target=target_name).set(response_time)
        endpoint_up.labels(target=target_name).set(1)
        
        logger.info(f"Ping to {host} successful: {response_time:.3f}s")
        
        return {
            'target': host,
            'name': target_name,
            'status': 'up',
            'response_time': response_time,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        
        endpoint_up.labels(target=target_name).set(0)
        logger.error(f"Ping to {host} failed: {str(e)}")
        
        return {
            'target': host,
            'name': target_name,
            'status': 'down',
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def check_api(endpoint):
    """Check an API endpoint and return response"""
    url = endpoint['url']
    endpoint_name = endpoint['name']
    
    check_count.labels(target=endpoint_name).inc()
    
    start_time = time.time()
    try:
        response = requests.get(url, timeout=5)
        end_time = time.time()
        response_time = end_time - start_time
        
        api_response_time.labels(endpoint=endpoint_name).set(response_time)
        api_status_code.labels(endpoint=endpoint_name).set(response.status_code)
        
        is_up = 200 <= response.status_code < 300
        endpoint_up.labels(target=endpoint_name).set(1 if is_up else 0)
        
        logger.info(f"API check to {url} returned status {response.status_code} in {response_time:.3f}s")
        
        try:
            response_data = response.json()
        except:
            response_data = {'text': response.text[:500]}
        
        return {
            'endpoint': url,
            'name': endpoint_name,
            'status': 'up' if is_up else 'down',
            'status_code': response.status_code,
            'response_time': response_time,
            'response_data': json.dumps(response_data),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        
        endpoint_up.labels(target=endpoint_name).set(0)
        logger.error(f"API check to {url} failed: {str(e)}")
        
        return {
            'endpoint': url,
            'name': endpoint_name,
            'status': 'down',
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

def store_ping_result(result):
    """Store ping result in MySQL database"""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        
        query = """
        INSERT INTO ping_results 
        (target, name, status, response_time, error, timestamp) 
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            result['target'],
            result['name'],
            result['status'],
            result.get('response_time'),
            result.get('error'),
            result['timestamp']
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error storing ping result in database: {str(e)}")

def store_api_result(result):
    """Store API check result in MySQL database"""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        
        query = """
        INSERT INTO api_results 
        (endpoint, name, status, status_code, response_time, response_data, error, timestamp) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        cursor.execute(query, (
            result['endpoint'],
            result['name'],
            result['status'],
            result.get('status_code'),
            result.get('response_time'),
            result.get('response_data'),
            result.get('error'),
            result['timestamp']
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error storing API result in database: {str(e)}")

def run_checks():
    """Run all monitoring checks"""
    logger.info("Running monitoring checks...")
    
    # Check ping targets
    for target in PING_TARGETS:
        result = ping_host(target)
        store_ping_result(result)
    
    # Check API endpoints
    for endpoint in API_ENDPOINTS:
        result = check_api(endpoint)
        store_api_result(result)

def init_database():
    """Initialize the MySQL database with required tables"""
    try:
        conn = mysql.connector.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE
        )
        cursor = conn.cursor()
        
        # Create ping_results table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS ping_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            target VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            status VARCHAR(10) NOT NULL,
            response_time FLOAT,
            error TEXT,
            timestamp DATETIME NOT NULL
        )
        """)
        
        # Create api_results table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS api_results (
            id INT AUTO_INCREMENT PRIMARY KEY,
            endpoint VARCHAR(255) NOT NULL,
            name VARCHAR(255) NOT NULL,
            status VARCHAR(10) NOT NULL,
            status_code INT,
            response_time FLOAT,
            response_data TEXT,
            error TEXT,
            timestamp DATETIME NOT NULL
        )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise

if __name__ == "__main__":
    # Start Prometheus metrics server
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")
    
    # Initialize database
    init_database()
    
    # Schedule checks to run every minute
    schedule.every(1).minutes.do(run_checks)
    
    # Run checks immediately on startup
    run_checks()
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(1)
