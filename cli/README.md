# QB Customer Support CLI Tools

Command-line interface for managing QB Customer Support operations including log retrieval and deployment.

## Installation

No installation required - run directly from the project directory:

```bash
./qb-cli --help
```

Or run the Python module directly:

```bash
python cli/main.py --help
```

## Available Commands

### 1. Logs Command

Retrieve and filter logs from the production server.

#### Basic Usage

```bash
# Get logs for a specific user ID for a date range
./qb-cli logs --user-id 15138 --since "2025-05-01" --until "2025-05-19"

# Get logs from the last 24 hours
./qb-cli logs --user-id 15138 --last 24h

# Get logs from the last 7 days
./qb-cli logs --user-id 15138 --last 7d
```

#### Advanced Usage

```bash
# Filter by specific error patterns
./qb-cli logs --user-id 15138 --last 24h --grep "ERROR"

# Get nginx logs instead of gunicorn
./qb-cli logs --service nginx.service --last 1h

# Save to specific file
./qb-cli logs --user-id 15138 --last 24h --output user-15138-logs.log

# Follow logs in real-time (like tail -f)
./qb-cli logs --user-id 15138 --follow

# Get only last 100 log lines
./qb-cli logs --user-id 15138 --last 1h --tail 100

# Use different server
./qb-cli logs --server staging-server --user-id 15138 --last 1h
```

#### Time Formats

- **Absolute time**: `"2025-05-01"` or `"2025-05-01 14:30:00"`
- **Relative time**: `24h` (24 hours), `7d` (7 days), `30m` (30 minutes), `1w` (1 week)

#### Examples

```bash
# Your original command equivalent:
./qb-cli logs --user-id 15138 --since "2025-05-01" --until "2025-05-19" --output qb-output.log

# Get recent errors for a user:
./qb-cli logs --user-id 15138 --last 4h --grep "ERROR" --output errors.log

# Monitor logs in real-time:
./qb-cli logs --user-id 15138 --follow

# Get logs for debugging with specific patterns:
./qb-cli logs --user-id 15138 --last 1h --grep "500\|timeout\|failed"
```

### 2. User Command

Query user details from the database using email, user ID, or Alpaca ID.

#### Basic Usage

```bash
# Query user by email
./qb-cli user --email user@example.com

# Query user by ID
./qb-cli user --user-id 15138

# Query user by Alpaca ID
./qb-cli user --alpaca-id ALP123456
```

#### Advanced Usage

```bash
# Search with email patterns (SQL LIKE)
./qb-cli user --email "%@gmail.com" --limit 5

# Get specific fields only
./qb-cli user --email user@example.com --fields "id,email,created_at"

# Output as JSON
./qb-cli user --email user@example.com --format json

# Save to file
./qb-cli user --email user@example.com --output user-details.json

# Use different table (if needed)
./qb-cli user --email user@example.com --table mainpage_users

# Show SQL query without executing
./qb-cli user --email user@example.com --dry-run
```

#### Output Formats

- **table** (default): Human-readable table format
- **json**: JSON format for programmatic use
- **csv**: CSV format for spreadsheet import

#### Examples

```bash
# Find a specific user
./qb-cli user --email john.doe@example.com

# Find all Gmail users (limit 10)
./qb-cli user --email "%@gmail.com"

# Get user details as JSON
./qb-cli user --user-id 15138 --format json --output user-15138.json

# Search and save as CSV
./qb-cli user --email "%@company.com" --format csv --output company-users.csv

# Show only specific fields
./qb-cli user --user-id 15138 --fields "id,email,created_at,is_active"
```

### 3. Deploy Command

Deploy the application to the remote server.

#### Basic Usage

```bash
# Deploy application
./qb-cli deploy

# Test deployment without actually deploying
./qb-cli deploy --dry-run

# Test SSH connectivity only
./qb-cli deploy --test-ssh-only

# Verbose deployment with detailed logs
./qb-cli deploy --verbose
```

## Command Options

### Global Options

- `--help, -h`: Show help message
- `--version`: Show version information

### Logs Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--server` | SSH server name | `--server quantbase-prod` |
| `--since` | Start time (absolute) | `--since "2025-05-01"` |
| `--last` | Last time period (relative) | `--last 24h` |
| `--until` | End time (with --since) | `--until "2025-05-19"` |
| `--service` | Systemd service name | `--service nginx.service` |
| `--user-id` | Filter by user ID | `--user-id 15138` |
| `--grep` | Additional grep filter | `--grep "ERROR"` |
| `--output, -o` | Output file | `--output logs.txt` |
| `--tail` | Show last N lines | `--tail 100` |
| `--follow, -f` | Follow logs (real-time) | `--follow` |
| `--dry-run` | Show command without executing | `--dry-run` |
| `--verbose, -v` | Show detailed information | `--verbose` |
| `--no-color` | Disable colored output | `--no-color` |

### User Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `--email` | User email (supports SQL LIKE patterns) | `--email user@example.com` |
| `--user-id` | User ID | `--user-id 15138` |
| `--alpaca-id` | Alpaca account ID | `--alpaca-id ALP123456` |
| `--table` | Database table name | `--table mainpage_users` |
| `--limit` | Maximum results | `--limit 5` |
| `--fields` | Comma-separated field list | `--fields "id,email"` |
| `--format` | Output format (table/json/csv) | `--format json` |
| `--output, -o` | Output file | `--output users.json` |
| `--raw-sql` | Show SQL query | `--raw-sql` |
| `--config` | Configuration file | `--config config.yaml` |
| `--dry-run` | Show query without executing | `--dry-run` |
| `--verbose, -v` | Show detailed info | `--verbose` |
| `--no-color` | Disable colored output | `--no-color` |

### Deploy Command Options

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would be deployed |
| `--test-ssh-only` | Only test SSH connectivity |
| `--verbose, -v` | Show detailed deployment info |
| `--no-color` | Disable colored output |

## Configuration

The CLI tools use the same SSH configuration as your system. Make sure you have:

1. **SSH Config** in `~/.ssh/config`:
   ```
   Host quantbase-prod
       HostName your-server-ip
       User ubuntu
       IdentityFile ~/.ssh/your-key
       Port 22
   ```

2. **SSH Key** loaded:
   ```bash
   ssh-add ~/.ssh/your-private-key
   ```

## Examples by Use Case

### Debugging User Issues

```bash
# First, get user details
./qb-cli user --email user@example.com --format json --output user-info.json

# Get user by ID from logs
./qb-cli user --user-id 15138

# Get all logs for a user from the last 24 hours
./qb-cli logs --user-id 15138 --last 24h --output user-15138-debug.log

# Look for specific errors
./qb-cli logs --user-id 15138 --last 24h --grep "500\|timeout\|ERROR"

# Monitor user activity in real-time
./qb-cli logs --user-id 15138 --follow
```

### User Management

```bash
# Find user by email
./qb-cli user --email john.doe@company.com

# Search for users by domain
./qb-cli user --email "%@company.com" --limit 20 --format csv --output company-users.csv

# Get user details by Alpaca ID
./qb-cli user --alpaca-id ALP123456

# Find users and export specific fields
./qb-cli user --email "%@gmail.com" --fields "id,email,created_at,is_active" --format json
```

### System Monitoring

```bash
# Check nginx access logs
./qb-cli logs --service nginx --last 1h --tail 50

# Monitor for errors across all services
./qb-cli logs --service gunicorn.service --last 1h --grep "ERROR\|CRITICAL"

# Get system logs for a specific time window
./qb-cli logs --service systemd --since "2025-05-01 14:00:00" --until "2025-05-01 15:00:00"
```

### Application Deployment

```bash
# Test SSH connection before deploying
./qb-cli deploy --test-ssh-only

# Preview what would be deployed
./qb-cli deploy --dry-run

# Deploy with detailed logging
./qb-cli deploy --verbose
```

## File Output

When using the `--output` option, log files are saved in the current directory. The CLI will show:
- File size
- Number of lines
- Success/failure status

## Error Handling

The CLI provides detailed error messages and exit codes:
- `0`: Success
- `1`: General error
- SSH connection errors show diagnostic information
- Invalid time formats show usage examples

## Troubleshooting

### SSH Issues
```bash
# Test SSH connectivity
./qb-cli deploy --test-ssh-only

# Check SSH configuration
ssh quantbase-prod "echo 'SSH working'"
```

### Time Format Issues
```bash
# Valid formats:
./qb-cli logs --user-id 15138 --since "2025-05-01"           # Date only
./qb-cli logs --user-id 15138 --since "2025-05-01 14:30:00"  # Date and time
./qb-cli logs --user-id 15138 --last 24h                     # Relative time
```

### Permission Issues
- Ensure your SSH key has access to the server
- Check that your user can run `sudo journalctl` on the server

## Development

To extend the CLI with new commands:

1. Create new command module in `cli/commands/`
2. Add parser in the command class
3. Register in `cli/main.py`

See existing commands for examples.