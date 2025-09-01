#!/bin/bash

# QB Customer Support Utils Deployment Script
# Deploys the application to the remote server via SSH

set -e  # Exit on any error

# Configuration
REMOTE_SERVER="qbcs"
REMOTE_USER="ubuntu"
REMOTE_PATH="/home/ubuntu"
LOCAL_PROJECT_PATH="/home/haris/projects/quantbase/customer-support/qb-cs-utils"
BACKUP_PATH="/home/ubuntu/backup-files"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")

# SSH options for better compatibility
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"

# Helper function for SSH commands
ssh_exec() {
    log_command "ssh $SSH_OPTS $REMOTE_SERVER \"$*\"" >&2
    ssh $SSH_OPTS $REMOTE_SERVER "$@"
}

# Helper function for SCP
scp_file() {
    log_command "scp $SSH_OPTS \"$1\" $REMOTE_SERVER:\"$2\"" >&2
    scp $SSH_OPTS "$1" $REMOTE_SERVER:"$2"
}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_command() {
    echo -e "${YELLOW}[CMD]${NC} $1"
}

# Function to check SSH connectivity
check_ssh_connection() {
    log_info "Checking SSH connection to $REMOTE_SERVER..."
    
    # Test basic SSH connectivity
    log_command "Testing SSH connection: ssh_exec \"echo 'SSH connection successful'\""
    if ssh_exec "echo 'SSH connection successful'" >/dev/null 2>&1; then
        log_success "SSH connection to $REMOTE_SERVER is working"
        return 0
    fi
    
    # If basic test failed, try some diagnostics
    log_warning "SSH connection test failed. Running diagnostics..."
    
    # Check if SSH config exists
    if [ -f ~/.ssh/config ] && grep -q "Host.*qbcs" ~/.ssh/config 2>/dev/null; then
        log_info "Found SSH config for qbcs:"
        grep -A 5 "Host.*qbcs" ~/.ssh/config
        echo
    fi
    
    # Try manual connection test
    log_info "Testing manual SSH connection (you may need to enter password/confirm)..."
    log_command "ssh -o BatchMode=no -o ConnectTimeout=10 $REMOTE_SERVER \"echo 'Manual SSH test successful'\""
    if ssh -o BatchMode=no -o ConnectTimeout=10 $REMOTE_SERVER "echo 'Manual SSH test successful'"; then
        log_warning "Manual connection worked. There might be an SSH key/authentication issue."
        log_info "Consider adding your SSH key to the server or checking SSH agent:"
        echo "  ssh-add -l  # List loaded keys"
        echo "  ssh-add ~/.ssh/your-key  # Add your key"
    else
        log_error "Manual SSH connection also failed."
    fi
    
    log_error "Cannot establish SSH connection to $REMOTE_SERVER"
    log_error "Please ensure:"
    log_error "1. SSH key is properly configured and loaded"
    log_error "2. Server '$REMOTE_SERVER' is reachable"
    log_error "3. SSH config is correct (if using config)"
    log_error "4. Try manually: ssh $REMOTE_SERVER"
    log_error ""
    log_error "If using SSH config, ensure ~/.ssh/config has:"
    echo "Host qbcs"
    echo "    HostName your-server-hostname-or-ip"
    echo "    User ubuntu"
    echo "    IdentityFile ~/.ssh/your-private-key"
    echo "    Port 22"
    exit 1
}

# Function to create local zip file
create_local_zip() {
    log_info "Creating deployment package..." >&2
    
    # Change to project directory
    log_command "cd \"$LOCAL_PROJECT_PATH\"" >&2
    cd "$LOCAL_PROJECT_PATH" || {
        log_error "Cannot access local project path: $LOCAL_PROJECT_PATH" >&2
        exit 1
    }
    
    # Create temporary zip file
    ZIP_FILE="qb-cs-utils-${TIMESTAMP}.zip"
    
    # Exclude unnecessary files and directories
    log_command "zip -r \"$ZIP_FILE\" . [excluding: git, cache, env files]" >&2
    zip -r "$ZIP_FILE" . \
        -x "*.git*" \
        -x "__pycache__/*" \
        -x "*.pyc" \
        -x "*.pyo" \
        -x ".env" \
        -x "CLAUDE.md" \
        -x "venv/*" \
        -x ".venv/*" \
        -x "*.log" \
        -x "*.tmp" \
        -x "deploy.sh" \
        -x "*.zip" \
        >/dev/null
    
    if [ -f "$ZIP_FILE" ]; then
        log_success "Created deployment package: $ZIP_FILE" >&2
        echo "$ZIP_FILE"
    else
        log_error "Failed to create deployment package" >&2
        exit 1
    fi
}

# Function to backup existing files on remote server
backup_remote_files() {
    log_info "Checking for existing installation on remote server..."
    
    # Check if qb-cs-utils exists on remote server
    if ssh_exec "test -d $REMOTE_PATH/qb-cs-utils"; then
        log_info "Existing installation found. Creating backup..."
        
        # Create backup directories
        ssh_exec "mkdir -p $BACKUP_PATH/$TIMESTAMP"
        
        # Copy CLAUDE.md and .env to backup if they exist
        ssh_exec "
            if [ -f $REMOTE_PATH/qb-cs-utils/CLAUDE.md ]; then
                cp $REMOTE_PATH/qb-cs-utils/CLAUDE.md $BACKUP_PATH/CLAUDE.md
                cp $REMOTE_PATH/qb-cs-utils/CLAUDE.md $BACKUP_PATH/$TIMESTAMP/CLAUDE.md
                echo 'Backed up CLAUDE.md'
            fi
            if [ -f $REMOTE_PATH/qb-cs-utils/.env ]; then
                cp $REMOTE_PATH/qb-cs-utils/.env $BACKUP_PATH/.env
                cp $REMOTE_PATH/qb-cs-utils/.env $BACKUP_PATH/$TIMESTAMP/.env
                echo 'Backed up .env'
            fi
        "
        
        # Move existing installation to backup
        ssh_exec "mv $REMOTE_PATH/qb-cs-utils $BACKUP_PATH/$TIMESTAMP/qb-cs-utils"
        log_success "Existing installation backed up to $BACKUP_PATH/$TIMESTAMP/"
    else
        log_info "No existing installation found"
        # Still create backup directory structure
        ssh_exec "mkdir -p $BACKUP_PATH"
    fi
}

# Function to deploy the application
deploy_application() {
    local zip_file=$1
    
    log_info "Deploying application to remote server..."
    
    # Copy zip file to remote server
    log_info "Copying deployment package to server..."
    scp_file "$zip_file" /tmp/ || {
        log_error "Failed to copy deployment package to server"
        exit 1
    }
    
    # Extract on remote server
    log_info "Extracting application on remote server..."
    ssh_exec "
        cd $REMOTE_PATH
        unzip -q /tmp/$zip_file -d qb-cs-utils
        rm /tmp/$zip_file
    " || {
        log_error "Failed to extract application on remote server"
        exit 1
    }
    
    log_success "Application extracted successfully"
}

# Function to restore configuration files
restore_config_files() {
    log_info "Restoring configuration files..."
    
    ssh_exec "
        # Restore CLAUDE.md if it exists in backup
        if [ -f $BACKUP_PATH/CLAUDE.md ]; then
            cp $BACKUP_PATH/CLAUDE.md $REMOTE_PATH/qb-cs-utils/CLAUDE.md
            echo 'Restored CLAUDE.md'
        else
            echo 'No CLAUDE.md found in backup'
        fi
        
        # Restore .env if it exists in backup
        if [ -f $BACKUP_PATH/.env ]; then
            cp $BACKUP_PATH/.env $REMOTE_PATH/qb-cs-utils/.env
            echo 'Restored .env'
        else
            echo 'WARNING: No .env found in backup - you may need to create one'
        fi
    "
    
    log_success "Configuration files restored"
}

# Function to set up Python environment
setup_python_environment() {
    log_info "Setting up Python environment on remote server..."
    
    ssh_exec "
        cd $REMOTE_PATH/qb-cs-utils
        
        # Create virtual environment if it doesn't exist
        if [ ! -d '.venv' ]; then
            python3 -m venv .venv
            echo 'Created Python virtual environment'
        fi
        
        # Activate virtual environment and install dependencies
        source .venv/bin/activate
        pip install --upgrade pip
        pip install -r requirements.txt
        
        echo 'Python environment setup complete'
    " || {
        log_warning "Python environment setup encountered issues"
        log_info "You may need to manually install dependencies on the server"
    }
    
    log_success "Python environment setup completed"
}

# Function to set permissions
set_permissions() {
    log_info "Setting appropriate file permissions..."
    
    ssh_exec "
        cd $REMOTE_PATH/qb-cs-utils
        chmod +x main.py
        chmod 600 .env 2>/dev/null || echo 'No .env file to secure'
        chown -R ubuntu:ubuntu .
    " || {
        log_warning "Some permission changes may have failed"
    }
    
    log_success "Permissions set"
}

# Function to validate deployment
validate_deployment() {
    log_info "Validating deployment..."
    
    # Check if main files exist
    ssh_exec "
        cd $REMOTE_PATH/qb-cs-utils
        
        if [ -f 'main.py' ]; then
            echo '✓ main.py found'
        else
            echo '✗ main.py missing'
            exit 1
        fi
        
        if [ -f 'requirements.txt' ]; then
            echo '✓ requirements.txt found'
        else
            echo '✗ requirements.txt missing'
            exit 1
        fi
        
        if [ -d 'src' ]; then
            echo '✓ src directory found'
        else
            echo '✗ src directory missing'
            exit 1
        fi
        
        if [ -f '.env' ]; then
            echo '✓ .env configuration found'
        else
            echo '⚠ .env configuration missing - you may need to create one'
        fi
        
        # Test Python environment
        source .venv/bin/activate 2>/dev/null
        python3 -c 'import sys; print(f\"✓ Python {sys.version_info.major}.{sys.version_info.minor} available\")'
    " || {
        log_error "Deployment validation failed"
        exit 1
    }
    
    log_success "Deployment validation passed"
}

# Function to cleanup local files
cleanup_local() {
    local zip_file=$1
    log_info "Cleaning up local deployment files..."
    log_command "rm -f \"$LOCAL_PROJECT_PATH/$zip_file\""
    rm -f "$LOCAL_PROJECT_PATH/$zip_file"
    log_success "Local cleanup completed"
}

# Function to show post-deployment instructions
show_post_deployment_info() {
    log_success "Deployment completed successfully!"
    echo
    echo "=== POST-DEPLOYMENT INFORMATION ==="
    echo
    log_info "Application deployed to: $REMOTE_SERVER:$REMOTE_PATH/qb-cs-utils"
    log_info "Backup created at: $REMOTE_SERVER:$BACKUP_PATH/$TIMESTAMP/"
    echo
    echo "=== NEXT STEPS ==="
    echo "1. SSH to the server: ssh $REMOTE_SERVER"
    echo "2. Navigate to app directory: cd $REMOTE_PATH/qb-cs-utils"
    echo "3. Activate virtual environment: source .venv/bin/activate"
    echo "4. Test the application: python main.py --help"
    echo
    if ! ssh_exec "test -f $REMOTE_PATH/qb-cs-utils/.env"; then
        log_warning "Don't forget to create/configure the .env file with your API keys!"
    fi
    echo "=== CONFIGURATION FILES ==="
    echo "- .env: Contains API keys and configuration"
    echo "- CLAUDE.md: Contains Claude-specific settings"
    echo "- config/config.yaml: Main application configuration"
    echo
}

# Main deployment function
main() {
    echo "=================================="
    echo "QB Customer Support Utils Deployer"
    echo "=================================="
    echo
    
    # Check if we're in the right directory
    if [ ! -f "main.py" ] || [ ! -d "src" ]; then
        log_error "Please run this script from the project root directory"
        log_error "Expected files: main.py, src/, requirements.txt"
        exit 1
    fi
    
    # Step 1: Check SSH connection
    log_command "Executing: check_ssh_connection"
    check_ssh_connection
    
    # Step 2: Create local deployment package
    log_command "Executing: create_local_zip"
    ZIP_FILE=$(create_local_zip)
    
    # Step 3: Backup existing remote installation
    log_command "Executing: backup_remote_files"
    backup_remote_files
    
    # Step 4: Deploy new application
    log_command "Executing: deploy_application \"$ZIP_FILE\""
    deploy_application "$ZIP_FILE"
    
    # Step 5: Restore configuration files
    log_command "Executing: restore_config_files"
    restore_config_files
    
    # Step 6: Setup Python environment
    log_command "Executing: setup_python_environment"
    setup_python_environment
    
    # Step 7: Set appropriate permissions
    log_command "Executing: set_permissions"
    set_permissions
    
    # Step 8: Validate deployment
    log_command "Executing: validate_deployment"
    validate_deployment
    
    # Step 9: Cleanup local files
    log_command "Executing: cleanup_local \"$ZIP_FILE\""
    cleanup_local "$ZIP_FILE"
    
    # Step 10: Show post-deployment information
    log_command "Executing: show_post_deployment_info"
    show_post_deployment_info
}

# Run main function
main "$@"