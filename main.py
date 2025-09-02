#!/usr/bin/env python3
"""
Automated Customer Support System
Entry point for processing JIRA tickets automatically
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import List

from src.core.config import Config
from src.core.ticket_processor import TicketProcessor
from src.integrations.deepseek_client import DeepSeekClient
from src.integrations.claude_executor import ClaudeExecutor
from src.utils.file_data_storage import log_data_to_file
from src.utils.logger import setup_logging
import traceback



async def process_ticket(ticket_id: str, config: Config) -> bool:
    """Process a single JIRA ticket using Claude Code integration"""
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"Processing {ticket_id}: Starting analysis...")
        
        # Initialize components
        ticket_processor = TicketProcessor(config.jira)
        deepseek_client = DeepSeekClient(config.deepseek)
        claude_executor = ClaudeExecutor(config.claude)
        
        # Step 1: Fetch ticket data
        logger.info(f"✓ Fetching ticket data for {ticket_id}")
        ticket_data = await ticket_processor.fetch_ticket(ticket_id)
        log_data_to_file(ticket_data, ticket_id)
        
        # Step 2: Analyze issue with DeepSeek
        logger.info(f"✓ DeepSeek analysis: Analyzing ticket content")
        issue_analysis = await deepseek_client.analyze_ticket(ticket_data)
        log_data_to_file(issue_analysis, ticket_id)
        
        # Step 3: Execute Claude Code analysis
        logger.info(f"✓ Executing Claude Code analysis")
        claude_result = await claude_executor.execute_claude_analysis(ticket_data, issue_analysis)
        
        log_data_to_file(claude_result, ticket_id)
        if claude_result.success:
            logger.info(f"✓ Claude analysis completed in {claude_result.execution_time_seconds:.2f}s")
            if claude_result.pr_urls:
                logger.info(f"✓ Pull requests created: {len(claude_result.pr_urls)}")
        else:
            logger.warning(f"⚠ Claude analysis failed: {claude_result.error_message}")
        
        # Step 4: Send Claude analysis directly to JIRA (only if successful)
        if claude_result.success:
            logger.info(f"✓ Sending Claude analysis directly to JIRA")

            # Read the Claude analysis logs
            log_file_path = claude_result.log_file_path
            with open(log_file_path, 'r', encoding='utf-8', errors='ignore') as f:
                claude_analysis = f.read()
            
            # Format the message for JIRA
            jira_message = f"""
            ** This is an AI Generated Message **
            {claude_analysis}
            """
            
            # Step 5: Update JIRA ticket with the Claude analysis
            logger.info(f"✓ Updating JIRA ticket with Claude analysis")
            await ticket_processor.add_comment_to_ticket(ticket_id, jira_message)
            
            # Add appropriate labels
            labels_to_add = ['ai-analyzed']
            if claude_result.pr_urls:
                labels_to_add.append('pr-created')
                logger.info(f"✓ PRs created: {len(claude_result.pr_urls)}")
            
            await ticket_processor.add_labels_to_ticket(ticket_id, labels_to_add)
            
            logger.info(f"Successfully processed {ticket_id}")
            return True
        else:
            logger.error(f"Claude analysis failed for {ticket_id}, skipping JIRA update")
            return False
        
    except Exception as e:
        logger.error(f"Error processing {ticket_id}: {str(e)}")
        logger.error(traceback.format_exc())
        return False



async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Automated Customer Support Ticket Processing System'
    )
    parser.add_argument(
        'ticket_ids', 
        nargs='+', 
        help='JIRA ticket IDs to process (e.g., TICKET-123)'
    )
    parser.add_argument(
        '--config', 
        default='config/config.yaml',
        help='Configuration file path'
    )
    parser.add_argument(
        '--dry-run', 
        action='store_true',
        help='Analysis only, no actions taken'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level)
    
    logger = logging.getLogger(__name__)
    
    # Load configuration
    try:
        config = Config.load(args.config)
        if args.dry_run:
            config.dry_run = True
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        sys.exit(1)
    
    # Process tickets
    success_count = 0
    total_count = len(args.ticket_ids)
    
    for ticket_id in args.ticket_ids:
        if await process_ticket(ticket_id, config):
            success_count += 1
    
    # Report results
    if success_count == total_count:
        logger.info(f"Successfully processed all {total_count} tickets")
        sys.exit(0)
    else:
        failed_count = total_count - success_count
        logger.error(f"Failed to process {failed_count} out of {total_count} tickets")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())