# Automated Customer Support System

An AI-powered system that automatically processes JIRA customer support tickets, investigates issues through log analysis, database queries, and codebase exploration, then provides automated resolutions using Claude Code.

## Features

- **JIRA Integration**: Fetches ticket data and conversation history
- **AI Analysis**: Uses DeepSeek for issue analysis and action planning
- **Multi-source Investigation**: 
  - SSH-based log analysis across servers
  - Database queries with predefined safe functions
  - Claude CLI-powered codebase exploration
- **Automated Resolution**: Uses Claude Code for intelligent problem solving
- **Ticket Updates**: Automatically updates JIRA with findings or solutions

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Entry     │ -> │  Ticket Processor │ -> │ Issue Analyzer  │
│     Point       │    │     Module       │    │   (DeepSeek)    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         v
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Resolution    │ <- │  Data Collector  │ <- │ Action Planner  │
│    Engine       │    │     Module       │    │   (DeepSeek)    │
│ (Claude Code)   │    └──────────────────┘    └─────────────────┘
└─────────────────┘              │
                                 │
        ┌────────────────────────┼────────────────────────┐
        │                        │                        │
        v                        v                        v
┌─────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Log Reader  │    │   DB Query       │    │   Codebase      │
│  (SSH)      │    │   Functions      │    │ Explorer (CLI)  │
└─────────────┘    └──────────────────┘    └─────────────────┘
```

## Installation

1. **Clone the repository:**
   ```bash
   cd /path/to/qb-cs-utils
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual API keys and configuration
   ```

4. **Update configuration:**
   ```bash
   # Edit config/config.yaml with your specific settings
   ```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# JIRA Configuration
JIRA_API_TOKEN=your_jira_api_token_here

# DeepSeek API Configuration  
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Database Configuration
DB_CONNECTION=postgresql://user:password@localhost:5432/database_name

# Codebase Path
CODEBASE_PATH=/path/to/your/codebase
```

### Configuration File

Edit `config/config.yaml`:

```yaml
jira:
  base_url: "https://yourcompany.atlassian.net"
  username: "bot@yourcompany.com"
  api_token: "${JIRA_API_TOKEN}"

deepseek:
  api_key: "${DEEPSEEK_API_KEY}"
  model: "deepseek-chat"

claude:
  cli_path: "/usr/local/bin/claude"

ssh_servers:
  - host: "backend-server.com"
    username: "loguser"
    key_path: "/path/to/ssh/key"

database:
  connection_string: "${DB_CONNECTION}"
  query_timeout: 30

codebase:
  repo_path: "${CODEBASE_PATH}"
  git_enabled: true
```

## Usage

### Basic Commands

```bash
# Process single ticket
python main.py TICKET-123

# Process multiple tickets
python main.py TICKET-123 TICKET-456 TICKET-789

# Dry run (analysis only, no actions)
python main.py --dry-run TICKET-123

# Verbose logging
python main.py --verbose TICKET-123

# Custom config file
python main.py --config /path/to/config.yaml TICKET-123
```

### Expected Workflow

1. **Ticket Analysis**: Fetches JIRA ticket and analyzes with DeepSeek
2. **Investigation Planning**: Creates action plan for data collection
3. **Data Collection**: 
   - Searches logs via SSH
   - Queries database with safe functions
   - Explores codebase using Claude CLI
4. **Resolution**: Uses Claude Code to analyze all data and generate solution
5. **JIRA Update**: Posts findings or automated fixes back to ticket

### Example Output

```bash
$ python main.py TICKET-123

Processing TICKET-123: "User login failing after password reset"
✓ Fetched ticket data and conversation history
✓ DeepSeek analysis: Authentication flow issue
✓ Collecting investigation data
✓ Code analysis: Identified fix in auth/session.py:line 45
✓ Generated solution with Claude Code
✓ Updated JIRA: Resolution provided with detailed findings

Successfully processed 1 tickets
```

## Security Features

- **Database**: Only predefined, read-only query functions
- **Logs**: SSH access with limited commands and time-bounded searches  
- **Code**: Read-only access to repository
- **API Keys**: Secure storage with environment variable substitution
- **Input Validation**: All inputs sanitized before processing
- **Audit Trail**: Comprehensive logging of all automated actions

## Development

### Project Structure

```
qb-cs-utils/
├── main.py                 # CLI entry point
├── config/
│   └── config.yaml        # Configuration file
├── src/
│   ├── core/
│   │   ├── config.py      # Configuration management
│   │   ├── ticket_processor.py  # JIRA integration
│   │   └── resolution_engine.py # Claude Code integration
│   ├── integrations/
│   │   └── deepseek_client.py   # DeepSeek API client
│   ├── collectors/
│   │   ├── log_reader.py        # SSH log analysis
│   │   ├── db_queries.py        # Database queries
│   │   └── code_explorer.py     # Claude CLI code exploration
│   └── utils/
│       └── logger.py            # Logging utilities
├── tests/              # Test files
├── requirements.txt    # Dependencies
└── README.md          # This file
```

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements.txt

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint code  
flake8 src/ tests/

# Type checking
mypy src/
```

## Troubleshooting

### Common Issues

1. **Claude CLI not found**: Ensure Claude CLI is installed and path is correct in config
2. **SSH connection fails**: Check SSH keys and server access
3. **Database connection fails**: Verify connection string and database access
4. **API rate limits**: Check API usage and implement exponential backoff

### Logging

Logs are written to both console and file (if configured). Use `--verbose` flag for detailed logging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## License

[Add your license information here]