"""
JIRA ticket processor for fetching and updating tickets
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from jira import JIRA, Issue

from .config import JiraConfig


@dataclass
class ConversationEntry:
    author: str
    timestamp: datetime
    content: str
    type: str  # 'comment', 'status_change', 'assignment'


@dataclass
class TicketData:
    ticket_id: str
    title: str
    description: str
    priority: str
    status: str
    created_date: datetime
    updated_date: datetime
    reporter: str
    assignee: Optional[str]
    conversation: List[ConversationEntry]
    labels: List[str]
    components: List[str]
    custom_fields: Dict[str, Any]


@dataclass
class ResolutionResult:
    success: bool
    resolution_type: str  # 'auto_fix', 'human_guidance', 'customer_response'
    solution_summary: str
    detailed_findings: str
    pr_link: Optional[str] = None
    error: Optional[str] = None


class TicketProcessor:
    """Handles JIRA API interactions for ticket processing"""
    
    def __init__(self, jira_config: JiraConfig):
        self.config = jira_config
        self.logger = logging.getLogger(__name__)
        
        # Initialize JIRA client
        self.jira = JIRA(
            server=jira_config.base_url,
            basic_auth=(jira_config.username, jira_config.api_token)
        )
    
    async def fetch_ticket(self, ticket_id: str) -> TicketData:
        """Fetch comprehensive ticket data including conversation history"""
        try:
            self.logger.debug(f"Fetching ticket data for {ticket_id}")
            
            # Get the main issue
            issue = self.jira.issue(ticket_id, expand='comments,changelog,history')
            
            # Extract basic ticket information
            ticket_data = TicketData(
                ticket_id=ticket_id,
                title=issue.fields.summary,
                description=issue.fields.description or "",
                priority=getattr(issue.fields.priority, 'name', 'Unknown') if issue.fields.priority else 'Unknown',
                status=issue.fields.status.name,
                created_date=self._parse_jira_datetime(issue.fields.created),
                updated_date=self._parse_jira_datetime(issue.fields.updated),
                reporter=issue.fields.reporter.displayName if issue.fields.reporter else 'Unknown',
                assignee=issue.fields.assignee.displayName if issue.fields.assignee else None,
                conversation=[],
                labels=issue.fields.labels or [],
                components=[comp.name for comp in (issue.fields.components or [])],
                custom_fields=self._extract_custom_fields(issue)
            )
            
            # Build conversation history from comments and changelog
            conversation = []
            
            # Add initial description as first entry
            if ticket_data.description:
                conversation.append(ConversationEntry(
                    author=ticket_data.reporter,
                    timestamp=ticket_data.created_date,
                    content=f"[Initial Description]\n{ticket_data.description}",
                    type='comment'
                ))
            
            # Add comments
            for comment in issue.fields.comment.comments:
                conversation.append(ConversationEntry(
                    author=comment.author.displayName,
                    timestamp=self._parse_jira_datetime(comment.created),
                    content=comment.body,
                    type='comment'
                ))
            
            # Add changelog entries for status changes, assignments, etc.
            if hasattr(issue, 'changelog'):
                for history in issue.changelog.histories:
                    for item in history.items:
                        if item.field in ['status', 'assignee', 'priority']:
                            change_type = 'status_change' if item.field == 'status' else 'assignment'
                            content = f"{item.field.capitalize()} changed from '{item.fromString or 'None'}' to '{item.toString or 'None'}'"
                            
                            conversation.append(ConversationEntry(
                                author=history.author.displayName,
                                timestamp=self._parse_jira_datetime(history.created),
                                content=content,
                                type=change_type
                            ))
            
            # Sort conversation chronologically
            conversation.sort(key=lambda x: x.timestamp)
            ticket_data.conversation = conversation
            
            self.logger.debug(f"Successfully fetched {ticket_id} with {len(conversation)} conversation entries")
            return ticket_data
            
        except Exception as e:
            self.logger.error(f"Failed to fetch ticket {ticket_id}: {str(e)}")
            raise
    
    async def update_ticket_with_solution(self, ticket_id: str, resolution: ResolutionResult) -> None:
        """Update ticket with automated solution"""
        try:
            comment_body = f"""🤖 **Automated Resolution**

**Issue Summary:** {resolution.solution_summary}

**Resolution Type:** {resolution.resolution_type}

**Solution Details:**
{resolution.detailed_findings}
"""
            
            if resolution.pr_link:
                comment_body += f"\n**Pull Request:** {resolution.pr_link}"
            
            comment_body += "\n\n*This resolution was generated automatically by the CS Automation System.*"
            
            # Add comment to ticket
            self.jira.add_comment(ticket_id, comment_body)
            
            # If it's an auto-fix, transition ticket to resolved
            if resolution.resolution_type == 'auto_fix':
                self._transition_ticket(ticket_id, 'Resolved')
            
            self.logger.info(f"Updated {ticket_id} with automated solution")
            
        except Exception as e:
            self.logger.error(f"Failed to update ticket {ticket_id} with solution: {str(e)}")
            raise
    
    async def update_ticket_with_findings(self, ticket_id: str, resolution: ResolutionResult) -> None:
        """Update ticket with investigation findings for human review"""
        try:
            comment_body = f"""🔍 **Automated Investigation Results**

**Issue Analysis:** {resolution.solution_summary}

**Investigation Findings:**
{resolution.detailed_findings}

**Recommended Next Steps:**
- Review the findings above
- Consider the suggested approach
- Implement or modify as needed

*This analysis was generated automatically by the CS Automation System.*
"""
            
            # Add comment to ticket
            self.jira.add_comment(ticket_id, comment_body)
            
            # Add label to indicate automated analysis
            issue = self.jira.issue(ticket_id)
            current_labels = issue.fields.labels or []
            if 'automated-analysis' not in current_labels:
                current_labels.append('automated-analysis')
                issue.update(fields={'labels': current_labels})
            
            self.logger.info(f"Updated {ticket_id} with investigation findings")
            
        except Exception as e:
            self.logger.error(f"Failed to update ticket {ticket_id} with findings: {str(e)}")
            raise
    
    async def update_ticket_with_claude_response(self, ticket_id: str, jira_response) -> None:
        """Update ticket with Claude-generated response"""
        try:
            # Add the response as a comment
            self.jira.add_comment(ticket_id, jira_response.message)
            
            # Add appropriate labels
            issue = self.jira.issue(ticket_id)
            current_labels = issue.fields.labels or []
            
            labels_to_add = ['claude-analyzed']
            if jira_response.resolution_type == 'fixed':
                labels_to_add.append('auto-resolved')
            elif jira_response.pr_urls:
                labels_to_add.append('pr-created')
            
            for label in labels_to_add:
                if label not in current_labels:
                    current_labels.append(label)
            
            issue.update(fields={'labels': current_labels})
            
            # Transition ticket based on resolution type
            if jira_response.resolution_type == 'fixed' and jira_response.confidence_level == 'high':
                self._transition_ticket(ticket_id, 'Resolved')
            elif jira_response.resolution_type in ['investigated', 'guidance']:
                # Keep ticket open but mark as in progress
                self._transition_ticket(ticket_id, 'In Progress')
            
            self.logger.info(f"Updated {ticket_id} with Claude-generated response")
            
        except Exception as e:
            self.logger.error(f"Failed to update ticket {ticket_id} with Claude response: {str(e)}")
            raise
    
    def _parse_jira_datetime(self, jira_datetime_str: str) -> datetime:
        """Parse JIRA datetime string to datetime object"""
        try:
            # JIRA typically returns ISO format: 2023-01-01T12:00:00.000+0000
            return datetime.fromisoformat(jira_datetime_str.replace('Z', '+00:00'))
        except:
            # Fallback parsing
            return datetime.now()
    
    def _extract_custom_fields(self, issue: Issue) -> Dict[str, Any]:
        """Extract custom fields from JIRA issue"""
        custom_fields = {}
        
        # Common custom fields to extract
        custom_field_mappings = {
            'customfield_10000': 'epic_link',
            'customfield_10001': 'story_points',
            'customfield_10002': 'team',
            'customfield_10003': 'customer_impact',
        }
        
        for field_id, field_name in custom_field_mappings.items():
            if hasattr(issue.fields, field_id):
                value = getattr(issue.fields, field_id)
                if value is not None:
                    custom_fields[field_name] = value
        
        return custom_fields
    
    def _transition_ticket(self, ticket_id: str, target_status: str) -> None:
        """Transition ticket to target status"""
        try:
            issue = self.jira.issue(ticket_id)
            transitions = self.jira.transitions(issue)
            
            # Find transition to target status
            target_transition = None
            for transition in transitions:
                if transition['to']['name'].lower() == target_status.lower():
                    target_transition = transition
                    break
            
            if target_transition:
                self.jira.transition_issue(issue, target_transition['id'])
                self.logger.debug(f"Transitioned {ticket_id} to {target_status}")
            else:
                self.logger.warning(f"No transition found to {target_status} for {ticket_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to transition {ticket_id} to {target_status}: {str(e)}")
            # Don't raise - ticket update can continue without status change