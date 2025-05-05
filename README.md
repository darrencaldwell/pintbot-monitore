# API Monitoring Solution

This document outlines the architecture and implementation details for a comprehensive API monitoring solution using Docker containers.

## Architecture Overview

The monitoring solution consists of multiple Docker containers, each responsible for a specific aspect of the monitoring process:

1. **Monitor Container**: Core service that checks endpoints and API health
2. **MySQL Container**: Stores detailed API responses and historical data
3. **Prometheus Container**: Time-series database for metrics collection
4. **Alert Manager Container**: Handles alerting logic and notifications
5. **Grafana Container**: Visualization and dashboards
6. **Nginx**: Proxies requests to Grafana (existing)

## Monitoring Targets

- Ping checks: 1.1.1.1, funkydiagrams.com
- API checks: 
  - funkydiagrams.com/api/all_pints (Lists all debts in the system)
  - funkydiagrams.com/api/pints/{user_id} (Shows debts for a specific user)
- Data collection: Response times, status codes, and API responses
- Alerting: Discord notifications for downtime exceeding 5 minutes

## Container Details

### 1. Monitor Container
- **Technology**: Python with requests library, prometheus client
- **Responsibilities**:
  - Ping endpoints at regular intervals
  - Call APIs and check responses
  - Record response times and status codes
  - Send metrics to Prometheus
  - Trigger alerts when downtime exceeds thresholds

### 2. MySQL Container
- **Technology**: MySQL database
- **Responsibilities**:
  - Store complete API responses
  - Maintain historical uptime data
  - Store detailed error information

### 3. Prometheus Container
- **Technology**: Prometheus
- **Responsibilities**:
  - Collect and store metrics from the monitor container
  - Provide data source for Grafana
  - Track uptime percentages, response times, and status codes

### 4. Alert Manager Container
- **Technology**: Prometheus Alert Manager
- **Responsibilities**:
  - Receive alert triggers from Prometheus
  - Implement alert rules (e.g., 5 minute downtime threshold)
  - Send notifications to Discord with proper @ mentions
  - Differentiate between website issues (@oscar) and API issues (@brendan)

### 5. Grafana Container
- **Technology**: Grafana
- **Responsibilities**:
  - Create dashboards for uptime monitoring
  - Display response time graphs
  - Show historical uptime percentages
  - Visualize error rates

## Alert Logic

### Discord Webhook Integration

Alerts are sent directly to Discord using Discord's webhook API:

1. Alert Manager formats alerts with relevant information
2. The webhook payload includes information about the affected service
3. Discord receives the webhook and posts the message in the designated channel

### Alert Template

```
{{ if eq .Status "firing" }}🔴 **ALERT FIRING**{{ else }}🟢 **ALERT RESOLVED**{{ end }}

{{ if eq .Labels.alertname "WebsiteDown" }}
**Website Down Alert**
The entire website ({{ .Labels.domain }}) has been down for over 5 minutes.
{{ else if eq .Labels.alertname "APIDown" }}
**API Down Alert**
The API at {{ .Labels.domain }}/api is down, but the main website appears to be functioning.
{{ end }}

**Status:** {{ .Status | toUpper }}
**Started:** {{ .StartsAt.Format "2006-01-02 15:04:05" }}
{{ if eq .Status "resolved" }}**Resolved:** {{ .EndsAt.Format "2006-01-02 15:04:05" }}
**Duration:** {{ duration .StartsAt .EndsAt }}{{ end }}

{{ if .Annotations.description }}{{ .Annotations.description }}{{ end }}
```

### Smart Alerting Logic

To prevent duplicate alerts when both website and API are down:

```yaml
inhibit_rules:
  # Inhibit API alerts if the website is down
  - source_match:
      alertname: 'WebsiteDown'
    target_match:
      alertname: 'APIDown'
    equal: ['domain']
    
  # Inhibit all alerts if Cloudflare DNS (1.1.1.1) is down
  # This indicates our internet connection is likely down
  - source_match_re:
      target: 'cloudflare-dns'
      status: 'down'
    target_match_re:
      alertname: '(WebsiteDown|APIDown)'
```

This ensures:
- If only the API is down, we get notified
- If the entire website is down (including API), we only get one notification
- If 1.1.1.1 is down (indicating internet connectivity issues), no alerts are sent
- When services recover, a recovery notification is sent

## Recovery Notifications

The system sends recovery notifications when services come back online:

1. Shows a green indicator with "ALERT RESOLVED"
2. Includes when the alert started
3. Shows when the service recovered
4. Displays the total downtime duration

## Data Flow

1. Monitor container checks endpoints and APIs at regular intervals
2. Results are stored in MySQL for detailed historical data
3. Metrics are sent to Prometheus for time-series storage
4. Prometheus evaluates alert rules based on metrics
5. When thresholds are exceeded, Alert Manager sends notifications to Discord
6. Grafana pulls data from Prometheus to display dashboards
7. Nginx proxies requests to Grafana for viewing

## Implementation Steps

1. Create Docker Compose configuration
2. Configure Prometheus alert rules
3. Set up Alert Manager with Discord webhook
4. Create monitoring script for the Monitor container
5. Configure Grafana dashboards
6. Set up MySQL schema for storing detailed API responses

## Getting Started

1. Clone this repository
2. Copy `.env.example` to `.env` and set your Discord webhook URL:
   ```
   cp .env.example .env
   nano .env  # Edit to add your Discord webhook URL
   ```
3. Make the entrypoint script executable:
   ```
   chmod +x alertmanager/entrypoint.sh
   ```
4. Run `docker-compose up -d` to start all services
5. Access Grafana at http://localhost:3000 (default credentials: admin/admin)

## Configuration Files

- `docker-compose.yml`: Main Docker Compose configuration
- `monitor_service/`: Python monitoring service
- `prometheus/`: Prometheus configuration and alert rules
- `alertmanager/`: Alert Manager configuration and templates
- `grafana/`: Grafana dashboards and data sources
- `mysql/`: MySQL initialization scripts

## Future Enhancements

- Add more sophisticated API checks (content validation, not just status codes)
- Implement multi-region monitoring for global perspective
- Add SSL certificate expiration monitoring
- Implement automated recovery actions for certain types of failures
