#!/usr/bin/env python3
"""Utility script to view ticket processing database"""

import argparse
import sys
from pathlib import Path
from tabulate import tabulate

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from src.database import TicketTracker


def main():
    """Main function to view database contents"""
    parser = argparse.ArgumentParser(description='View ticket processing database')
    parser.add_argument('--db', default='ticket_processing.db', 
                       help='Database file path (default: ticket_processing.db)')
    parser.add_argument('--ticket', help='Show history for specific ticket')
    parser.add_argument('--user', help='Show statistics for specific user')
    parser.add_argument('--recent', type=int, default=10,
                       help='Number of recent tickets to show (default: 10)')
    parser.add_argument('--stats', action='store_true',
                       help='Show overall statistics')
    
    args = parser.parse_args()
    
    # Check if database exists
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Database not found: {args.db}")
        print("No tickets have been processed yet.")
        sys.exit(0)
    
    tracker = TicketTracker(args.db)
    
    if args.ticket:
        # Show ticket history
        print(f"\nHistory for ticket {args.ticket}:")
        print("=" * 80)
        history = tracker.get_ticket_history(args.ticket)
        if history:
            headers = ['Processed At', 'User', 'Success', 'Time (s)', 'PRs', 'Error']
            rows = []
            for record in history:
                rows.append([
                    record['processed_at'][:19],
                    record['user'],
                    '✓' if record['success'] else '✗',
                    f"{record['execution_time_seconds']:.1f}" if record['execution_time_seconds'] else '-',
                    len(record['pr_urls']) if record['pr_urls'] else 0,
                    record['error_message'][:30] if record['error_message'] else '-'
                ])
            print(tabulate(rows, headers=headers, tablefmt='grid'))
        else:
            print(f"No processing history found for {args.ticket}")
    
    elif args.user:
        # Show user statistics
        stats = tracker.get_user_statistics(args.user)
        print(f"\nStatistics for user: {args.user}")
        print("=" * 40)
        print(f"Total tickets processed: {stats['total_processed']}")
        print(f"Successful: {stats['successful']}")
        print(f"Failed: {stats['failed']}")
        if stats['total_processed'] > 0:
            success_rate = (stats['successful'] / stats['total_processed']) * 100
            print(f"Success rate: {success_rate:.1f}%")
        print(f"Average execution time: {stats['avg_execution_time_seconds']:.1f}s")
        print(f"Unique tickets: {stats['unique_tickets']}")
        print(f"Tickets with PRs: {stats['tickets_with_prs']}")
    
    elif args.stats:
        # Show overall statistics
        print("\nOverall Statistics")
        print("=" * 60)
        
        # Get stats for all known users
        for user in ['default', 'yassa']:
            stats = tracker.get_user_statistics(user)
            if stats['total_processed'] > 0:
                print(f"\n{user.upper()}:")
                print(f"  Total: {stats['total_processed']} | Success: {stats['successful']} | Failed: {stats['failed']}")
                if stats['total_processed'] > 0:
                    success_rate = (stats['successful'] / stats['total_processed']) * 100
                    print(f"  Success rate: {success_rate:.1f}%")
                print(f"  Avg time: {stats['avg_execution_time_seconds']:.1f}s")
                print(f"  PRs created: {stats['tickets_with_prs']} tickets")
    
    else:
        # Show recent tickets
        print(f"\nRecent Ticket Processing (last {args.recent})")
        print("=" * 100)
        
        user_filter = args.user if args.user else None
        recent = tracker.get_recent_tickets(limit=args.recent, user=user_filter)
        
        if recent:
            headers = ['Ticket ID', 'User', 'Processed At', 'Success', 'Time (s)', 'PRs', 'Labels']
            rows = []
            for record in recent:
                rows.append([
                    record['ticket_id'],
                    record['user'],
                    record['processed_at'][:19],
                    '✓' if record['success'] else '✗',
                    f"{record['execution_time_seconds']:.1f}" if record['execution_time_seconds'] else '-',
                    len(record['pr_urls']) if record['pr_urls'] else 0,
                    ', '.join(record['labels_added']) if record['labels_added'] else '-'
                ])
            print(tabulate(rows, headers=headers, tablefmt='grid'))
        else:
            print("No tickets have been processed yet.")


if __name__ == "__main__":
    main()