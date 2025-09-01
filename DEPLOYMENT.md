# QB Customer Support Utils - Deployment Guide

## Quick Deployment

### Prerequisites
- SSH access to the server configured as `qbcs`
- Python 3.8+ installed on the target server
- Required permissions on the target server

### One-Command Deployment
```bash
./deploy.sh
```

## What the Deployment Script Does

### 1. **Pre-deployment Checks**
- Verifies SSH connectivity to `qbcs` server
- Confirms you're running from the correct directory
- Creates deployment package (zip file)

### 2. **Backup Process**
- Checks if `/home/ubuntu/qb-cs-utils` exists on server
- If exists:
  - Copies `CLAUDE.md` and `.env` to `/home/ubuntu/backup-files/`
  - Creates timestamped backup at `/home/ubuntu/backup-files/YYYYMMDD_HHMMSS/`
  - Moves existing installation to backup directory

### 3. **Deployment Process**
- Transfers new code to server
- Extracts to `/home/ubuntu/qb-cs-utils`
- Restores `CLAUDE.md` and `.env` from backup
- Sets up Python virtual environment
- Installs dependencies from `requirements.txt`
- Sets appropriate file permissions

### 4. **Validation**
- Verifies all critical files are present
- Tests Python environment
- Confirms configuration files are restored

## Manual Deployment (Alternative)

If you prefer to deploy manually:

### 1. Create Local Package
```bash
cd /home/haris/projects/quantbase/customer-support/qb-cs-utils
zip -r qb-cs-utils.zip . -x "*.git*" "__pycache__/*" "*.pyc" ".env" "CLAUDE.md" "venv/*" ".venv/*"
```

### 2. Backup Existing Installation
```bash
ssh qbcs "
  if [ -d /home/ubuntu/qb-cs-utils ]; then
    mkdir -p /home/ubuntu/backup-files/$(date +%Y%m%d_%H%M%S)
    cp /home/ubuntu/qb-cs-utils/CLAUDE.md /home/ubuntu/backup-files/ 2>/dev/null || true
    cp /home/ubuntu/qb-cs-utils/.env /home/ubuntu/backup-files/ 2>/dev/null || true
    mv /home/ubuntu/qb-cs-utils /home/ubuntu/backup-files/$(date +%Y%m%d_%H%M%S)/
  fi
"
```

### 3. Deploy New Version
```bash
scp qb-cs-utils.zip qbcs:/tmp/
ssh qbcs "
  cd /home/ubuntu
  unzip -q /tmp/qb-cs-utils.zip -d qb-cs-utils
  rm /tmp/qb-cs-utils.zip
"
```

### 4. Restore Configuration
```bash
ssh qbcs "
  cp /home/ubuntu/backup-files/CLAUDE.md /home/ubuntu/qb-cs-utils/ 2>/dev/null || true
  cp /home/ubuntu/backup-files/.env /home/ubuntu/qb-cs-utils/ 2>/dev/null || true
"
```

### 5. Setup Environment
```bash
ssh qbcs "
  cd /home/ubuntu/qb-cs-utils
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
"
```

## Post-Deployment Steps

### 1. SSH to Server
```bash
ssh qbcs
```

### 2. Navigate to Application
```bash
cd /home/ubuntu/qb-cs-utils
```

### 3. Activate Virtual Environment
```bash
source .venv/bin/activate
```

### 4. Verify Configuration
```bash
# Check if .env file exists and has required variables
cat .env

# Test application
python main.py --help
```

### 5. Run a Test
```bash
# Test with a sample ticket (replace CS-123 with actual ticket)
python main.py CS-123
```

## Configuration Files

### `.env` File
Required environment variables:
```
JIRA_API_TOKEN=your_jira_token
DEEPSEEK_API_KEY=your_deepseek_key
DB_CONNECTION=postgresql://...
CODEBASE_PATH=/path/to/codebase
```

### `CLAUDE.md` File
Contains Claude Code configuration and project-specific settings.

### `config/config.yaml`
Main application configuration including:
- JIRA connection details
- DeepSeek API settings
- Claude CLI path
- SSH server configurations
- Database settings

## Troubleshooting

### SSH Connection Issues
- Verify SSH key is added: `ssh-add -l`
- Test connection: `ssh qbcs "echo 'Connected'"`
- Check SSH config: `~/.ssh/config`

### Permission Issues
```bash
ssh qbcs "
  cd /home/ubuntu/qb-cs-utils
  sudo chown -R ubuntu:ubuntu .
  chmod +x main.py
  chmod 600 .env
"
```

### Python Environment Issues
```bash
ssh qbcs "
  cd /home/ubuntu/qb-cs-utils
  rm -rf .venv
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
"
```

### Missing Configuration
If `.env` or `CLAUDE.md` are missing, you'll need to create them manually on the server.

## Rollback Process

If deployment fails, you can rollback:
```bash
ssh qbcs "
  BACKUP_DIR=\$(ls -t /home/ubuntu/backup-files/ | grep -E '^[0-9]{8}_[0-9]{6}$' | head -1)
  if [ -n \"\$BACKUP_DIR\" ]; then
    rm -rf /home/ubuntu/qb-cs-utils
    mv /home/ubuntu/backup-files/\$BACKUP_DIR/qb-cs-utils /home/ubuntu/
    echo \"Rolled back to \$BACKUP_DIR\"
  fi
"
```

## Directory Structure on Server

```
/home/ubuntu/
├── qb-cs-utils/          # Main application
│   ├── main.py
│   ├── src/
│   ├── config/
│   ├── .env
│   ├── CLAUDE.md
│   └── .venv/
└── backup-files/         # Backup directory
    ├── CLAUDE.md         # Latest backup
    ├── .env              # Latest backup
    └── 20241201_143022/  # Timestamped backups
        └── qb-cs-utils/
```