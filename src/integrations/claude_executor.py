"""
Claude Code CLI integration for automated ticket resolution
"""

import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass

from src.utils.file_data_storage import build_data_file_path, log_data_to_file

from ..core.config import ClaudeConfig
from ..core.ticket_processor import TicketData
from ..integrations.deepseek_client import IssueAnalysis


@dataclass
class ClaudeExecutionResult:
    success: bool
    log_file_path: str
    execution_time_seconds: float
    exit_code: int
    error_message: Optional[str] = None
    pr_urls: list = None


class ClaudeExecutor:
    """Executes Claude Code CLI commands and captures logs"""
    
    def __init__(self, claude_config: ClaudeConfig):
        self.config = claude_config
        self.logger = logging.getLogger(__name__)
        self.base_dir = Path("fetched_data/claude")
        
    async def execute_claude_analysis(
        self, 
        ticket_data: TicketData, 
        issue_analysis: IssueAnalysis
    ) -> ClaudeExecutionResult:
        """Execute Claude Code analysis on the ticket and capture logs"""

        
        # Generate log file path
        log_file_dir = build_data_file_path(ticket_data.ticket_id, "claude_logs")
        log_file_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_file_dir / "claude_execution.log"
        
        # Prepare Claude prompt based on analysis
        claude_prompt = self._build_claude_prompt(ticket_data, issue_analysis)
        
        log_data_to_file(claude_prompt, ticket_data.ticket_id, "claude_prompt")
        
        # Execute Claude command
        start_time = datetime.now()
        
        try:
            result = await self._run_claude_command(claude_prompt, log_file_path)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Extract PR URLs from the logs if any
            pr_urls = self._extract_pr_urls_from_logs(log_file_path)
            
            return ClaudeExecutionResult(
                success=result[0] == 0,
                log_file_path=str(log_file_path),
                execution_time_seconds=execution_time,
                exit_code=result[0],
                error_message=result[1] if result[0] != 0 else None,
                pr_urls=pr_urls
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Claude execution failed: {str(e)}")
            
            return ClaudeExecutionResult(
                success=False,
                log_file_path=str(log_file_path),
                execution_time_seconds=execution_time,
                exit_code=-1,
                error_message=str(e),
                pr_urls=[]
            )
    
    def _build_claude_prompt(self, ticket_data: TicketData, issue_analysis: IssueAnalysis) -> str:
        """Build comprehensive prompt for Claude Code"""
        
        # Read instructions from QB_CS_CLAUDE.md
        claude_instructions = self._read_claude_instructions()
        
        # Format conversation
        conversation_text = ""
        for entry in ticket_data.conversation:
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            conversation_text += f"[{timestamp}] {entry.author} ({entry.type}):\n{entry.content}\n\n"
        
        # Format customer info
        customer_info = issue_analysis.customer_info
        customer_section = ""
        if customer_info.get('primary_email'):
            customer_section += f"Primary Email: {customer_info['primary_email']}\n"
        if customer_info.get('alpaca_id'):
            customer_section += f"Alpaca ID: {customer_info['alpaca_id']}\n"
        if customer_info.get('bank_relationship_code'):
            customer_section += f"Bank Relationship Code: {customer_info['bank_relationship_code']}\n"
        
        # Format timeframe
        timeframe = issue_analysis.issue_timeframe
        timeframe_section = f"""
Issue Likely Occurred Between:
- Start: {timeframe.get('estimated_start_date', 'Unknown')}
- End: {timeframe.get('estimated_end_date', 'Unknown')}
- Reasoning: {timeframe.get('reasoning', 'No specific timing indicated')}
"""
        
        prompt = f"""
{claude_instructions}

TICKET INFORMATION:
===================
Ticket ID: {ticket_data.ticket_id}
Title: {ticket_data.title}
Status: {ticket_data.status}
Priority: {ticket_data.priority}
Reporter: {ticket_data.reporter}
Created: {ticket_data.created_date}

ISSUE ANALYSIS:
===============
Category: {issue_analysis.issue_category}
Severity: {issue_analysis.severity}
Summary: {issue_analysis.issue_summary}

CUSTOMER INFORMATION:
====================
{customer_section if customer_section else "No specific customer information extracted"}

TIMEFRAME ANALYSIS:
==================
{timeframe_section}

TECHNICAL DETAILS:
==================
Error Messages: {', '.join(issue_analysis.technical_details.get('error_messages', []))}
Affected Features: {', '.join(issue_analysis.technical_details.get('affected_features', []))}
User Environment: {issue_analysis.technical_details.get('user_environment', 'Not specified')}
Affected Components: {', '.join(issue_analysis.affected_components)}

ERROR PATTERNS FOR LOG SEARCH:
==============================
{', '.join(issue_analysis.error_patterns)}

FULL CONVERSATION HISTORY:
==========================
{conversation_text}

=== CRITICAL REQUIREMENT ===
You MUST provide a comprehensive final analysis at the end of your response that includes:
1. Summary of findings from your investigation
2. Root cause analysis (if identified)
3. Actions taken or recommended resolution steps
4. Customer communication recommendations
5. Any PRs created or code changes made
6. Follow-up actions needed

This final analysis section is mandatory and must be clearly marked with "=== FINAL ANALYSIS ===" header.

Please proceed with your analysis and resolution according to the instructions above.
"""
        
        return prompt
    
    async def _run_claude_command(self, prompt: str, log_file_path: Path) -> Tuple[int, Optional[str]]:
        """Execute Claude CLI command with the given prompt"""
        
        try:
            # Prepare Claude command with --dangerously-skip-permissions, --print, and --model flags
            cmd = [
                self.config.cli_path,
                "--dangerously-skip-permissions",
                "--print",
                "--model",
                "claude-4"
            ]
            
            self.logger.info(f"Executing Claude command: {' '.join(cmd)}")
            
            # Execute command and pipe prompt via stdin
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=Path.cwd()
            )
            
            # Send prompt via stdin and get output
            stdout, _ = await process.communicate(input=prompt.encode('utf-8'))
            
            # Write all output to log file
            with open(log_file_path, 'wb') as f:
                f.write(stdout)
            
            # Check if we got meaningful output
            if not stdout or len(stdout.decode('utf-8', errors='ignore').strip()) < 50:
                error_msg = "No meaningful output from Claude execution - marking as failed"
                self.logger.warning(error_msg)
                return -1, error_msg
            
            self.logger.info(f"Claude execution completed. Logs saved to: {log_file_path}")
            
            return process.returncode, None if process.returncode == 0 else "Non-zero exit code"
            
        except Exception as e:
            error_msg = f"Failed to execute Claude command: {str(e)}"
            self.logger.error(error_msg)
            
            # Write error to log file
            with open(log_file_path, 'w', encoding='utf-8') as f:
                f.write(f"ERROR: {error_msg}\n")
                f.write(f"Original prompt:\n{prompt}\n")
            
            return -1, error_msg
    
    def _extract_pr_urls_from_logs(self, log_file_path: Path) -> list:
        """Extract PR URLs from Claude logs"""
        pr_urls = []
        
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Common patterns for PR URLs
            import re
            
            patterns = [
                r'https://github\.com/[^/]+/[^/]+/pull/\d+',
                r'Pull request: (https://[^\s]+)',
                r'PR created: (https://[^\s]+)',
                r'Created pull request: (https://[^\s]+)'
            ]
            
            for pattern in patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                pr_urls.extend(matches)
            
            # Remove duplicates
            pr_urls = list(set(pr_urls))
            
            self.logger.info(f"Extracted {len(pr_urls)} PR URLs from Claude logs")
            
        except Exception as e:
            self.logger.error(f"Failed to extract PR URLs: {str(e)}")
        
        return pr_urls
    
    def _read_claude_instructions(self) -> str:
        """Read Claude instructions from CLAUDE.md"""
        try:
            claude_md_path = Path("CLAUDE.md")
            if claude_md_path.exists():
                with open(claude_md_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                self.logger.warning("CLAUDE.md not found, using default instructions")
                return "You are a senior software engineer. Analyze the customer support ticket and resolve the issue."
        except Exception as e:
            self.logger.error(f"Failed to read CLAUDE.md: {str(e)}")
            return "You are a senior software engineer. Analyze the customer support ticket and resolve the issue."