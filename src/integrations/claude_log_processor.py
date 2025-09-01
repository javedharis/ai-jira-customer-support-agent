"""
Claude log processor that uses DeepSeek to generate JIRA responses
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field

from langchain_core.output_parsers import JsonOutputParser

from ..core.config import DeepSeekConfig
from ..core.ticket_processor import TicketData
from ..integrations.deepseek_client import IssueAnalysis, DeepSeekClient
from ..integrations.claude_executor import ClaudeExecutionResult


# Pydantic model for JIRA response
class JiraResponsePydantic(BaseModel):
    response_message: str = Field(description="Complete response message for JIRA ticket")
    resolution_type: str = Field(description="Type of resolution: fixed, investigated, guidance, escalation")
    confidence_level: str = Field(description="Confidence in the resolution: high, medium, low")
    next_steps: list = Field(default=[], description="Any follow-up actions needed")
    technical_summary: str = Field(default="", description="Technical summary for internal use")


@dataclass
class JiraResponse:
    message: str
    resolution_type: str  # 'fixed', 'investigated', 'guidance', 'escalation'
    confidence_level: str  # 'high', 'medium', 'low'
    next_steps: list
    technical_summary: str
    pr_urls: list


class ClaudeLogProcessor:
    """Processes Claude logs and generates JIRA responses using DeepSeek"""
    
    def __init__(self, deepseek_config: DeepSeekConfig):
        self.config = deepseek_config
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://api.deepseek.com/v1"
        
    async def generate_jira_response(
        self,
        ticket_data: TicketData,
        issue_analysis: IssueAnalysis,
        claude_result: ClaudeExecutionResult
    ) -> JiraResponse:
        """Generate JIRA response from Claude logs using DeepSeek"""
        
        try:
            # Read Claude logs
            claude_logs = self._read_claude_logs(claude_result.log_file_path)
            
            # Generate response using DeepSeek
            jira_response_data = await self._call_deepseek_for_response(
                ticket_data, issue_analysis, claude_result, claude_logs
            )
            
            # Format final message
            final_message = self._format_final_message(
                jira_response_data.response_message,
                claude_result.pr_urls,
                claude_logs
            )
            
            return JiraResponse(
                message=final_message,
                resolution_type=jira_response_data.resolution_type,
                confidence_level=jira_response_data.confidence_level,
                next_steps=jira_response_data.next_steps,
                technical_summary=jira_response_data.technical_summary,
                pr_urls=claude_result.pr_urls or []
            )
            
        except Exception as e:
            self.logger.error(f"Failed to generate JIRA response: {str(e)}")
            
            # Only return fallback response for successful Claude runs with processing errors
            if claude_result.success:
                # Read Claude logs for the fallback response too
                claude_logs = self._read_claude_logs(claude_result.log_file_path)
                fallback_message = self._generate_fallback_response(claude_result, ticket_data, issue_analysis)
                final_fallback_message = self._format_final_message(fallback_message, claude_result.pr_urls, claude_logs)
                
                return JiraResponse(
                    message=final_fallback_message,
                    resolution_type="investigated",
                    confidence_level="medium",
                    next_steps=["Follow up with customer if needed"],
                    technical_summary=f"Analysis completed but response processing failed: {str(e)}",
                    pr_urls=claude_result.pr_urls or []
                )
            else:
                # For failed Claude runs, don't generate any JIRA response
                raise Exception(f"Claude execution failed, no JIRA update needed: {str(e)}")
    
    def _read_claude_logs(self, log_file_path: str) -> str:
        """Read and return Claude log content"""
        try:
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Limit content size to avoid token limits
            max_length = 50000  # Adjust based on DeepSeek limits
            if len(content) > max_length:
                content = content[:max_length] + "\n\n[LOG TRUNCATED - Content too long]"
            
            return content
            
        except Exception as e:
            self.logger.error(f"Failed to read Claude logs: {str(e)}")
            return f"ERROR: Could not read Claude logs from {log_file_path}"
    
    async def _call_deepseek_for_response(
        self,
        ticket_data: TicketData,
        issue_analysis: IssueAnalysis,
        claude_result: ClaudeExecutionResult,
        claude_logs: str
    ) -> JiraResponsePydantic:
        """Call DeepSeek to generate JIRA response"""
        
        # Set up the output parser
        parser = JsonOutputParser(pydantic_object=JiraResponsePydantic)
        
        # Build prompt for DeepSeek
        prompt = f"""
You are an expert customer support agent. Based on the Claude Code analysis results, write a professional response for the JIRA ticket.

ORIGINAL TICKET:
================
ID: {ticket_data.ticket_id}
Title: {ticket_data.title}
Reporter: {ticket_data.reporter}
Created: {ticket_data.created_date}

ISSUE ANALYSIS SUMMARY:
======================
Category: {issue_analysis.issue_category}
Severity: {issue_analysis.severity}
Summary: {issue_analysis.issue_summary}
Customer: {issue_analysis.customer_info.get('primary_email', 'Unknown')}

CLAUDE CODE ANALYSIS RESULTS:
=============================
Execution Status: {"Successful" if claude_result.success else "Failed"}
Exit Code: {claude_result.exit_code}
Execution Time: {claude_result.execution_time_seconds:.2f} seconds
Pull Requests Created: {len(claude_result.pr_urls or [])}

CLAUDE ANALYSIS LOGS:
====================
{claude_logs}

INSTRUCTIONS:
=============
1. Write a professional response message for the JIRA ticket
2. Start the message with "AI Generated Message:" 
3. Summarize what was analyzed and any actions taken
4. If code fixes were made, mention the pull requests
5. If investigation was done, summarize findings
6. Be clear about what was resolved vs what needs human attention
7. Use professional, helpful tone appropriate for customer support
8. Include any relevant technical details the customer should know
9. Suggest next steps if applicable
10. Also assist the customer support agent about what he reply to the customer

RESPONSE GUIDELINES:
===================
- Keep the main message customer-friendly but technically accurate
- If Claude created pull requests, mention them prominently
- If issues were found but not fixed, explain clearly
- If no issues were found, explain the analysis done
- Always be honest about limitations and what requires human review

{parser.get_format_instructions()}
"""
        
        # Use the existing DeepSeek client method
        deepseek_client = DeepSeekClient(self.config)
        response = await deepseek_client._call_deepseek_api(prompt)
        
        # Parse the response
        parsed_response = parser.parse(response)
        
        return parsed_response
    
    def _format_final_message(self, base_message: str, pr_urls: list, claude_logs: str = None) -> str:
        """Format the final JIRA message with PR links and raw Claude analysis"""
        
        # Ensure message starts with AI Generated Message
        if not base_message.startswith("AI Generated Message:"):
            base_message = f"AI Generated Message:\n\n{base_message}"
        
        # Add PR links if any
        if pr_urls:
            pr_section = "\n\n**Pull Requests Created:**\n"
            for i, pr_url in enumerate(pr_urls, 1):
                pr_section += f"{i}. {pr_url}\n"
            base_message += pr_section
        
        # Add raw Claude analysis results if available
        # if claude_logs and claude_logs.strip():
        #     base_message += "\n\n**Raw Claude Analysis Results:**\n"
        #     base_message += "```\n"
        #     base_message += claude_logs
        #     base_message += "\n```"
        
        return base_message
    
    def _generate_fallback_response(self, claude_result: ClaudeExecutionResult, ticket_data: TicketData = None, issue_analysis: IssueAnalysis = None) -> str:
        """Generate a meaningful fallback response based on ticket analysis"""
        
        base_message = "AI Generated Message:\n\n"
        
        if claude_result.success:
            # Generate response based on ticket analysis instead of generic message
            if issue_analysis:
                base_message += f"I have analyzed your {issue_analysis.issue_category.lower()} issue regarding {ticket_data.title if ticket_data else 'your request'}.\n\n"
                
                # Add issue summary
                base_message += f"**Issue Summary:** {issue_analysis.issue_summary}\n\n"
                
                # Add technical details if available
                if issue_analysis.technical_details.get('error_messages'):
                    base_message += f"**Error Details:** {', '.join(issue_analysis.technical_details['error_messages'][:2])}\n\n"
                
                # Add affected features
                if issue_analysis.technical_details.get('affected_features'):
                    base_message += f"**Affected Areas:** {', '.join(issue_analysis.technical_details['affected_features'])}\n\n"
                
                # Add customer info if available
                if issue_analysis.customer_info.get('primary_email'):
                    base_message += f"**Account:** {issue_analysis.customer_info['primary_email']}\n\n"
                
                # Add findings or next steps
                if issue_analysis.severity in ['high', 'critical']:
                    base_message += "**Priority:** This issue has been marked as high priority and requires immediate attention.\n\n"
                
                base_message += "I have completed the initial analysis and investigation. "
                
                if claude_result.pr_urls:
                    base_message += "Code fixes have been implemented and pull requests have been created.\n\n"
                else:
                    base_message += "Based on my analysis, this issue may require manual review or additional investigation.\n\n"
            else:
                base_message += "I have completed the analysis of your support request.\n\n"
            
            # Add PR links if any
            if claude_result.pr_urls:
                base_message += "**Pull Requests Created:**\n"
                for i, pr_url in enumerate(claude_result.pr_urls, 1):
                    base_message += f"{i}. {pr_url}\n"
                base_message += "\n"
                
            base_message += "A customer support representative will follow up with additional details if needed."
        else:
            base_message += "I was unable to complete the automated analysis of your ticket. A human agent will review this manually and provide assistance. Thank you for your patience."
        
        return base_message