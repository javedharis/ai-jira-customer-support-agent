"""
Log reader module for SSH-based log analysis
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import paramiko
import asyncssh

from ..core.config import SSHServerConfig


@dataclass
class LogEntry:
    timestamp: datetime
    server: str
    log_file: str
    level: str
    message: str
    context: Dict[str, Any]


@dataclass
class LogSearchResult:
    server: str
    total_entries: int
    entries: List[LogEntry]
    search_summary: str
    errors: List[str]


class LogReader:
    """SSH-based log reader for distributed systems"""
    
    def __init__(self, ssh_servers: List[SSHServerConfig]):
        self.ssh_servers = ssh_servers
        self.logger = logging.getLogger(__name__)
        
        # Common log file paths
        self.log_paths = [
            '/var/log/application/*.log',
            '/var/log/app/*.log',
            '/opt/app/logs/*.log',
            '/home/app/logs/*.log',
            '/var/log/syslog',
            '/var/log/messages'
        ]
    
    async def search_logs(self, date_range: Tuple[datetime, datetime], search_terms: List[str]) -> Dict[str, LogSearchResult]:
        """Search logs across all configured servers"""
        start_date, end_date = date_range
        
        self.logger.info(f"Searching logs from {start_date} to {end_date} for terms: {search_terms}")
        
        # Run searches on all servers concurrently
        tasks = []
        for server in self.ssh_servers:
            task = self._search_server_logs(server, start_date, end_date, search_terms)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results
        search_results = {}
        for i, result in enumerate(results):
            server_name = self.ssh_servers[i].host
            
            if isinstance(result, Exception):
                self.logger.error(f"Error searching {server_name}: {str(result)}")
                search_results[server_name] = LogSearchResult(
                    server=server_name,
                    total_entries=0,
                    entries=[],
                    search_summary=f"Error: {str(result)}",
                    errors=[str(result)]
                )
            else:
                search_results[server_name] = result
        
        return search_results
    
    async def _search_server_logs(self, server: SSHServerConfig, start_date: datetime, 
                                end_date: datetime, search_terms: List[str]) -> LogSearchResult:
        """Search logs on a specific server"""
        
        try:
            async with asyncssh.connect(
                server.host,
                port=server.port,
                username=server.username,
                client_keys=[server.key_path] if server.key_path else None,
                known_hosts=None  # Disable host key checking for automation
            ) as conn:
                
                log_entries = []
                errors = []
                
                # Search each log path
                for log_path in self.log_paths:
                    try:
                        entries = await self._search_log_path(conn, log_path, start_date, end_date, search_terms, server.host)
                        log_entries.extend(entries)
                    except Exception as e:
                        errors.append(f"Error searching {log_path}: {str(e)}")
                
                # Sort by timestamp
                log_entries.sort(key=lambda x: x.timestamp)
                
                search_summary = self._generate_search_summary(log_entries, search_terms)
                
                return LogSearchResult(
                    server=server.host,
                    total_entries=len(log_entries),
                    entries=log_entries,
                    search_summary=search_summary,
                    errors=errors
                )
                
        except Exception as e:
            self.logger.error(f"Failed to connect to {server.host}: {str(e)}")
            raise
    
    async def _search_log_path(self, conn, log_path: str, start_date: datetime, 
                             end_date: datetime, search_terms: List[str], server_name: str) -> List[LogEntry]:
        """Search a specific log path on the server"""
        
        entries = []
        
        # Check if log path exists
        result = await conn.run(f'ls {log_path} 2>/dev/null', check=False)
        if result.exit_status != 0:
            return entries  # Path doesn't exist, skip
        
        # Build search command
        search_pattern = '|'.join([f'"{term}"' for term in search_terms])
        date_filter = self._build_date_filter(start_date, end_date)
        
        # Use grep with date filtering
        command = f"""
        find {log_path} -type f -name "*.log" -exec sh -c '
            for file; do
                grep -H -n -E "({search_pattern})" "$file" | {date_filter}
            done
        ' _ {{}} + 2>/dev/null || true
        """
        
        try:
            result = await conn.run(command, check=False)
            
            if result.stdout:
                entries = self._parse_log_output(result.stdout, server_name)
            
        except Exception as e:
            self.logger.debug(f"Error searching {log_path} on {server_name}: {str(e)}")
        
        return entries
    
    def _build_date_filter(self, start_date: datetime, end_date: datetime) -> str:
        """Build date filter for log entries"""
        # Simple approach: filter by date strings in common formats
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        # This is a simplified filter - in production, you'd want more robust date parsing
        return f'grep -E "({start_str}|{end_str})" || true'
    
    def _parse_log_output(self, output: str, server_name: str) -> List[LogEntry]:
        """Parse grep output into structured log entries"""
        entries = []
        
        for line in output.strip().split('\n'):
            if not line.strip():
                continue
            
            try:
                # Parse grep output: filename:line_number:log_content
                parts = line.split(':', 3)
                if len(parts) >= 3:
                    filename = parts[0]
                    log_content = parts[2] if len(parts) == 3 else ':'.join(parts[2:])
                    
                    # Try to extract timestamp and log level
                    timestamp, level, message = self._parse_log_line(log_content)
                    
                    entry = LogEntry(
                        timestamp=timestamp,
                        server=server_name,
                        log_file=filename,
                        level=level,
                        message=message,
                        context={'raw_line': log_content}
                    )
                    
                    entries.append(entry)
                    
            except Exception as e:
                self.logger.debug(f"Failed to parse log line '{line}': {str(e)}")
                continue
        
        return entries
    
    def _parse_log_line(self, log_line: str) -> Tuple[datetime, str, str]:
        """Parse individual log line to extract timestamp, level, and message"""
        
        # Common log patterns
        import re
        
        # ISO timestamp pattern
        iso_pattern = r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)'
        
        # Log level pattern
        level_pattern = r'\b(DEBUG|INFO|WARN|WARNING|ERROR|FATAL|CRITICAL)\b'
        
        timestamp = datetime.now()  # Default timestamp
        level = 'INFO'  # Default level
        message = log_line  # Default message
        
        # Extract timestamp
        timestamp_match = re.search(iso_pattern, log_line)
        if timestamp_match:
            try:
                timestamp_str = timestamp_match.group(1)
                # Handle various timestamp formats
                timestamp_str = timestamp_str.replace('T', ' ').replace('Z', '+00:00')
                if '+' not in timestamp_str and timestamp_str.count(':') == 2:
                    timestamp_str += '+00:00'
                timestamp = datetime.fromisoformat(timestamp_str)
            except:
                pass
        
        # Extract log level
        level_match = re.search(level_pattern, log_line, re.IGNORECASE)
        if level_match:
            level = level_match.group(1).upper()
        
        # Message is the full line for now
        message = log_line.strip()
        
        return timestamp, level, message
    
    def _generate_search_summary(self, entries: List[LogEntry], search_terms: List[str]) -> str:
        """Generate a summary of search results"""
        
        if not entries:
            return "No log entries found matching search terms"
        
        # Count by log level
        level_counts = {}
        for entry in entries:
            level_counts[entry.level] = level_counts.get(entry.level, 0) + 1
        
        # Time range
        timestamps = [entry.timestamp for entry in entries]
        time_range = f"{min(timestamps)} to {max(timestamps)}"
        
        summary_parts = [
            f"Found {len(entries)} log entries",
            f"Time range: {time_range}",
            f"Log levels: {', '.join([f'{level}({count})' for level, count in level_counts.items()])}"
        ]
        
        return " | ".join(summary_parts)