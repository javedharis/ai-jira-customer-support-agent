"""
Logs command for retrieving server logs
"""

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
import argparse
import re

from ..utils.colors import Colors


class LogsCommand:
    """Command for retrieving and filtering server logs"""
    
    @staticmethod
    def add_parser(subparsers):
        """Add logs subcommand to parser"""
        logs_parser = subparsers.add_parser(
            'logs',
            help='Retrieve server logs',
            description='Retrieve and filter logs from the production server',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s logs --user-id 15138 --since "2025-05-01" --until "2025-05-19"
  %(prog)s logs --user-id 15138 --last 24h --output user-15138-logs.log
  %(prog)s logs --user-id 15138 --last 7d --service gunicorn --grep ERROR
  %(prog)s logs --service nginx --since "2025-05-01 14:30:00" --tail 100
            """
        )
        
        # Server connection
        logs_parser.add_argument(
            '--server',
            default='quantbase-prod',
            help='SSH server name (default: quantbase-prod)'
        )
        
        # Time range options (mutually exclusive)
        time_group = logs_parser.add_mutually_exclusive_group(required=True)
        time_group.add_argument(
            '--since',
            help='Start time (YYYY-MM-DD or "YYYY-MM-DD HH:MM:SS")'
        )
        time_group.add_argument(
            '--last',
            help='Last time period (e.g., 24h, 7d, 30m)'
        )
        
        logs_parser.add_argument(
            '--until',
            help='End time (YYYY-MM-DD or "YYYY-MM-DD HH:MM:SS", requires --since)'
        )
        
        # Service and filtering
        logs_parser.add_argument(
            '--service',
            default='gunicorn.service',
            help='Systemd service name (default: gunicorn.service)'
        )
        
        logs_parser.add_argument(
            '--user-id',
            help='Filter logs by user ID'
        )
        
        logs_parser.add_argument(
            '--grep',
            help='Additional grep filter'
        )
        
        # Output options
        logs_parser.add_argument(
            '--output', '-o',
            help='Output file (default: qb-output.log)'
        )
        
        logs_parser.add_argument(
            '--tail',
            type=int,
            help='Show only last N lines'
        )
        
        logs_parser.add_argument(
            '--follow', '-f',
            action='store_true',
            help='Follow log output (like tail -f)'
        )
        
        # Display options
        logs_parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
        
        logs_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show command that would be executed without running it'
        )
        
        logs_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Show detailed command information'
        )
    
    @staticmethod
    def execute(args):
        """Execute the logs command"""
        if args.no_color:
            Colors.disable()
        
        try:
            # Build the SSH command
            ssh_command = LogsCommand._build_ssh_command(args)
            
            if args.verbose or args.dry_run:
                print(f"{Colors.BLUE}[CMD]{Colors.NC} {ssh_command}")
            
            if args.dry_run:
                return 0
            
            # Execute the command
            return LogsCommand._execute_ssh_command(ssh_command, args)
            
        except Exception as e:
            print(f"{Colors.RED}Error: {str(e)}{Colors.NC}")
            return 1
    
    @staticmethod
    def _build_ssh_command(args):
        """Build the SSH command for log retrieval"""
        # Parse time arguments
        since_time, until_time = LogsCommand._parse_time_args(args)
        
        # Build journalctl command
        journalctl_parts = ['sudo', 'journalctl', '-u', args.service]
        
        if since_time:
            journalctl_parts.extend(['--since', f'"{since_time}"'])
        
        if until_time:
            journalctl_parts.extend(['--until', f'"{until_time}"'])
        
        if args.follow:
            journalctl_parts.append('-f')
        elif args.tail:
            journalctl_parts.extend(['-n', str(args.tail)])
        
        # Build filter pipeline
        filters = []
        
        if args.user_id:
            filters.append(f'grep "/{args.user_id}/"')
        
        if args.grep:
            # Escape special characters for shell
            escaped_grep = args.grep.replace('"', '\\"').replace('$', '\\$')
            filters.append(f'grep "{escaped_grep}"')
        
        # Combine journalctl with filters
        command_parts = [' '.join(journalctl_parts)]
        if filters:
            command_parts.extend(filters)
        
        remote_command = ' | '.join(command_parts)
        
        # Build full SSH command
        ssh_command = f"ssh {args.server} '{remote_command}'"
        
        # Add output redirection if specified
        if args.output and not args.follow:
            ssh_command += f" > {args.output}"
        
        return ssh_command
    
    @staticmethod
    def _parse_time_args(args):
        """Parse time arguments and return formatted strings"""
        since_time = None
        until_time = None
        
        if args.since:
            since_time = LogsCommand._format_time(args.since)
            if args.until:
                until_time = LogsCommand._format_time(args.until)
            else:
                # Default to now if only since is specified
                until_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
        elif args.last:
            # Parse relative time (e.g., 24h, 7d, 30m)
            since_time = LogsCommand._parse_relative_time(args.last)
            until_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        return since_time, until_time
    
    @staticmethod
    def _format_time(time_str):
        """Format time string for journalctl"""
        # If it's just a date, add time
        if re.match(r'^\d{4}-\d{2}-\d{2}$', time_str):
            return f"{time_str} 00:00:00"
        return time_str
    
    @staticmethod
    def _parse_relative_time(relative_str):
        """Parse relative time string (e.g., 24h, 7d) and return absolute time"""
        match = re.match(r'^(\d+)([hdmw])$', relative_str.lower())
        if not match:
            raise ValueError(f"Invalid time format: {relative_str}. Use format like 24h, 7d, 30m")
        
        amount, unit = match.groups()
        amount = int(amount)
        
        now = datetime.now()
        
        if unit == 'm':  # minutes
            delta = timedelta(minutes=amount)
        elif unit == 'h':  # hours
            delta = timedelta(hours=amount)
        elif unit == 'd':  # days
            delta = timedelta(days=amount)
        elif unit == 'w':  # weeks
            delta = timedelta(weeks=amount)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")
        
        since_time = now - delta
        return since_time.strftime("%Y-%m-%d %H:%M:%S")
    
    @staticmethod
    def _execute_ssh_command(ssh_command, args):
        """Execute the SSH command"""
        print(f"{Colors.GREEN}[INFO]{Colors.NC} Retrieving logs from {args.server}...")
        
        if args.output and not args.follow:
            print(f"{Colors.GREEN}[INFO]{Colors.NC} Output will be saved to: {args.output}")
        
        try:
            # Execute command
            result = subprocess.run(
                ssh_command,
                shell=True,
                capture_output=False,
                text=True
            )
            
            if result.returncode == 0:
                if args.output and not args.follow:
                    # Check if file was created and show stats
                    output_path = Path(args.output)
                    if output_path.exists():
                        size = output_path.stat().st_size
                        lines = sum(1 for _ in output_path.open())
                        print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} Logs saved to {args.output}")
                        print(f"{Colors.BLUE}[INFO]{Colors.NC} File size: {size} bytes, Lines: {lines}")
                    else:
                        print(f"{Colors.YELLOW}[WARNING]{Colors.NC} Output file {args.output} was not created")
                else:
                    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} Log retrieval completed")
                
                return 0
            else:
                print(f"{Colors.RED}[ERROR]{Colors.NC} SSH command failed with exit code {result.returncode}")
                return result.returncode
                
        except subprocess.CalledProcessError as e:
            print(f"{Colors.RED}[ERROR]{Colors.NC} Command failed: {str(e)}")
            return e.returncode
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.NC} Unexpected error: {str(e)}")
            return 1