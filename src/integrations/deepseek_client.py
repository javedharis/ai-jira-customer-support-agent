"""
DeepSeek AI integration for issue analysis and action planning
"""

import logging
import json
from typing import Dict, Any, List, Literal
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import httpx
from pydantic import BaseModel, Field
from langchain_core.output_parsers import JsonOutputParser

from ..core.config import DeepSeekConfig
from ..core.ticket_processor import TicketData
import traceback


@dataclass
class IssueAnalysis:
    ticket_id: str
    issue_summary: str
    issue_category: str  # 'bug', 'feature_request', 'configuration', 'user_error', 'system_error'
    severity: str  # 'low', 'medium', 'high', 'critical'
    technical_details: Dict[str, Any]
    affected_components: List[str]
    user_actions: List[str]
    error_patterns: List[str]
    confidence_score: float
    customer_info: Dict[str, Any]  # Contains customer emails, alpaca_id, bank_relationship_code
    issue_timeframe: Dict[str, Any]  # Contains estimated issue occurrence window and reasoning




# Pydantic models for parsing API responses
class TechnicalDetailsPydantic(BaseModel):
    error_messages: List[str] = Field(description="List of specific error messages")
    affected_features: List[str] = Field(description="List of features mentioned")
    user_environment: str = Field(description="Description of user's environment")
    reproduction_steps: List[str] = Field(description="Steps to reproduce if available")


class CustomerInfoPydantic(BaseModel):
    primary_email: str = Field(default="", description="The most likely correct customer email address")
    all_emails: List[str] = Field(default=[], description="All email addresses mentioned in the conversation")
    alpaca_id: str = Field(default="", description="Alpaca account ID if mentioned")
    bank_relationship_code: str = Field(default="", description="Bank relationship code if mentioned")
    confidence_level: Literal['high', 'medium', 'low'] = Field(
        default='low', description="Confidence in the extracted customer information"
    )


class IssueTimeframePydantic(BaseModel):
    estimated_start_date: str = Field(description="Estimated start date of the issue (ISO format)")
    estimated_end_date: str = Field(description="Estimated end date of the issue (ISO format)")
    confidence_level: Literal['high', 'medium', 'low'] = Field(description="Confidence in the time estimation")
    reasoning: str = Field(description="Explanation of how the timeframe was determined")
    time_indicators: List[str] = Field(default=[], description="Specific phrases that helped determine timing")


class IssueAnalysisPydantic(BaseModel):
    issue_summary: str = Field(description="Clear, concise summary of the actual problem")
    issue_category: Literal['bug', 'feature_request', 'configuration', 'user_error', 'system_error'] = Field(
        description="Category of the issue"
    )
    severity: Literal['low', 'medium', 'high', 'critical'] = Field(description="Severity level")
    technical_details: TechnicalDetailsPydantic = Field(description="Technical details of the issue")
    affected_components: List[str] = Field(description="List of likely system components")
    user_actions: List[str] = Field(description="List of actions user was trying to perform")
    error_patterns: List[str] = Field(description="Patterns or keywords to search for in logs")
    customer_info: CustomerInfoPydantic = Field(description="Customer identification information")
    issue_timeframe: IssueTimeframePydantic = Field(description="Estimated timeframe when the issue occurred")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")




class DeepSeekClient:
    """Client for DeepSeek AI API integration"""
    
    def __init__(self, deepseek_config: DeepSeekConfig):
        self.config = deepseek_config
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://api.deepseek.com/v1"
        
    async def analyze_ticket(self, ticket_data: TicketData) -> IssueAnalysis:
        """Analyze ticket content to understand the core issue"""
        
        # Set up the output parser
        parser = JsonOutputParser(pydantic_object=IssueAnalysisPydantic)
        
        # Prepare conversation context
        conversation_text = self._format_conversation(ticket_data.conversation)
        
        # Create analysis prompt with format instructions
        prompt = f"""
You are an expert customer support analyst. Analyze this JIRA ticket and provide a structured analysis.

TICKET INFO:
- ID: {ticket_data.ticket_id}
- Title: {ticket_data.title}
- Status: {ticket_data.status}
- Priority: {ticket_data.priority}
- Reporter: {ticket_data.reporter}
- Created: {ticket_data.created_date}

FULL CONVERSATION:
{conversation_text}

IMPORTANT INSTRUCTIONS:
1. Focus on extracting factual information and technical details. Be precise about error messages and system components.

2. CUSTOMER IDENTIFICATION: Carefully extract customer identification information from the conversation:
   - Look for email addresses mentioned by the customer or support staff
   - If multiple emails are mentioned, identify which one is most likely the correct customer email
   - Look for Alpaca account IDs (typically alphanumeric strings)
   - Look for bank relationship codes or account numbers
   - Rate your confidence in the extracted customer information (high/medium/low)
   - Consider the context when determining the primary email - customer-provided emails in problem descriptions are usually more reliable than email addresses mentioned in signatures or examples.

3. TIMEFRAME ANALYSIS: Analyze when the issue likely occurred for log searching purposes:
   - Ticket created: {ticket_data.created_date}
   - Look for temporal indicators in the conversation: "yesterday", "this morning", "last week", "since Monday", "started happening 3 days ago", etc.
   - Consider the urgency and how users describe the timing
   - Estimate a search window (max 1 month) that would capture relevant logs
   - If no specific timing is mentioned, use ticket creation time as reference point
   - Account for business hours vs after-hours occurrences
   - Provide reasoning for your time estimation

{parser.get_format_instructions()}
"""
        
        try:
            response = await self._call_deepseek_api(prompt)
            
            # Parse the response using LangChain parser
            parsed_response = parser.parse(response)
            
            # Map Pydantic model to dataclass
            return IssueAnalysis(
                ticket_id=ticket_data.ticket_id,
                issue_summary=parsed_response.get('issue_summary'),
                issue_category=parsed_response.get('issue_category'),
                severity=parsed_response.get('severity'),
                technical_details={
                    'error_messages': parsed_response.get('technical_details', {}).get('error_messages'),
                    'affected_features': parsed_response.get('technical_details', {}).get('affected_features'),
                    'user_environment': parsed_response.get('technical_details', {}).get('user_environment'),
                    'reproduction_steps': parsed_response.get('technical_details', {}).get('reproduction_steps')
                },
                affected_components=parsed_response.get('affected_components'),
                user_actions=parsed_response.get('user_actions'),
                error_patterns=parsed_response.get('error_patterns'),
                customer_info={
                    'primary_email': parsed_response.get('customer_info', {}).get('primary_email', ''),
                    'all_emails': parsed_response.get('customer_info', {}).get('all_emails', []),
                    'alpaca_id': parsed_response.get('customer_info', {}).get('alpaca_id', ''),
                    'bank_relationship_code': parsed_response.get('customer_info', {}).get('bank_relationship_code', ''),
                    'confidence_level': parsed_response.get('customer_info', {}).get('confidence_level', 'low')
                },
                issue_timeframe={
                    'estimated_start_date': parsed_response.get('issue_timeframe', {}).get('estimated_start_date', ''),
                    'estimated_end_date': parsed_response.get('issue_timeframe', {}).get('estimated_end_date', ''),
                    'confidence_level': parsed_response.get('issue_timeframe', {}).get('confidence_level', 'low'),
                    'reasoning': parsed_response.get('issue_timeframe', {}).get('reasoning', ''),
                    'time_indicators': parsed_response.get('issue_timeframe', {}).get('time_indicators', [])
                },
                confidence_score=parsed_response.get('confidence_score')
            )
            
        except Exception as e:
            self.logger.error("Stack trace:\n" + traceback.format_exc())
            self.logger.error(f"Failed to analyze ticket {ticket_data.ticket_id}: {str(e)}")
            raise
    
    
    async def _call_deepseek_api(self, prompt: str) -> str:
        """Make API call to DeepSeek"""
        
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers
            )
            
            if response.status_code != 200:
                self.logger.error(f"DeepSeek API HTTP error: {response.status_code}")
                self.logger.error(f"Response text: {response.text}")
                raise Exception(f"DeepSeek API error: {response.status_code} - {response.text}")
            
            try:
                result = response.json()
                self.logger.debug(f"DeepSeek API response: {result}")
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse DeepSeek response as JSON: {e}")
                self.logger.error(f"Raw response text: '{response.text}'")
                self.logger.error(f"Response headers: {response.headers}")
                raise Exception(f"Invalid JSON response from DeepSeek API: {response.text}")
            
            if 'choices' not in result or not result['choices']:
                self.logger.error(f"DeepSeek API response missing choices: {result}")
                raise Exception("Invalid response from DeepSeek API - no choices field")
            
            content = result['choices'][0]['message']['content']
            if not content:
                self.logger.error(f"Empty content in DeepSeek response: {result}")
                raise Exception("Empty content in DeepSeek API response")
                
            return content
    
    def _format_conversation(self, conversation: List) -> str:
        """Format conversation history for analysis"""
        formatted_lines = []
        
        for entry in conversation:
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
            entry_type = f"[{entry.type.upper()}]"
            formatted_lines.append(f"{timestamp} {entry_type} {entry.author}:")
            formatted_lines.append(f"{entry.content}")
            formatted_lines.append("")  # Empty line for readability
        
        return "\n".join(formatted_lines)