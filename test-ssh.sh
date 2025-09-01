#!/bin/bash

# Simple SSH connectivity test script
# Use this to debug SSH issues before running the full deployment

echo "=== SSH Connectivity Test ==="
echo

# Test 1: Basic SSH config check
echo "1. Checking SSH configuration..."
if [ -f ~/.ssh/config ]; then
    if grep -q "Host.*qbcs" ~/.ssh/config; then
        echo "✓ Found qbcs configuration in ~/.ssh/config"
        echo "Configuration:"
        grep -A 5 "Host.*qbcs" ~/.ssh/config | sed 's/^/  /'
    else
        echo "✗ No qbcs configuration found in ~/.ssh/config"
        echo "Please add configuration like:"
        echo "Host qbcs"
        echo "    HostName your-server-ip"
        echo "    User ubuntu"
        echo "    IdentityFile ~/.ssh/your-key"
        echo "    Port 22"
    fi
else
    echo "✗ No SSH config file found at ~/.ssh/config"
fi
echo

# Test 2: SSH key check
echo "2. Checking SSH keys..."
if ssh-add -l >/dev/null 2>&1; then
    echo "✓ SSH agent is running with keys:"
    ssh-add -l | sed 's/^/  /'
else
    echo "⚠ No SSH keys loaded in agent. You may need to:"
    echo "  ssh-add ~/.ssh/your-private-key"
fi
echo

# Test 3: Basic connectivity
echo "3. Testing SSH connectivity to qbcs..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 qbcs "echo 'SSH connection successful'" 2>/dev/null; then
    echo "✓ SSH connection to qbcs successful"
else
    echo "✗ SSH connection to qbcs failed"
    echo "Trying interactive connection (you may need to enter password)..."
    if ssh -o ConnectTimeout=10 qbcs "echo 'Interactive SSH connection successful'"; then
        echo "✓ Interactive SSH worked - check your SSH keys/agent"
    else
        echo "✗ Both automated and interactive SSH failed"
        echo "Check your SSH configuration and network connectivity"
    fi
fi
echo

# Test 4: Remote server check
echo "4. Testing remote server environment..."
if ssh -o BatchMode=yes -o ConnectTimeout=5 qbcs "whoami; pwd; python3 --version" 2>/dev/null; then
    echo "✓ Remote server environment check passed"
else
    echo "✗ Could not check remote server environment"
fi
echo

echo "=== Test Complete ==="
echo "If all tests pass, you can run ./deploy.sh"
echo "If tests fail, fix the SSH configuration first"