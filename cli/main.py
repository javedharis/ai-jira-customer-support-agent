#!/usr/bin/env python3
"""
QB Customer Support CLI
Main command line interface for server management and log retrieval
"""

import argparse
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from cli.commands.logs import LogsCommand
from cli.commands.deploy import DeployCommand
from cli.commands.user import UserCommand
from cli.commands.transactions import TransactionsCommand
from cli.commands.autoinvestments import AutoinvestmentsCommand
from cli.commands.cashtransfers import CashTransfersCommand
from cli.commands.alpaca_transfers import AlpacaTransfersCommand
from cli.commands.alpaca_ach_relationships import AlpacaAchRelationshipsCommand
from cli.commands.alpaca_trading_account import AlpacaTradingAccountCommand
from cli.utils.colors import Colors


def create_parser():
    """Create the main argument parser"""
    parser = argparse.ArgumentParser(
        prog='qb-cli',
        description='QB Customer Support CLI Tools',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s logs --user-id 15138 --since "2025-05-01" --until "2025-05-19"
  %(prog)s logs --user-id 15138 --last 24h
  %(prog)s user --email user@example.com
  %(prog)s user --user-id 15138
  %(prog)s transactions --user-id 6654
  %(prog)s txn --user-id 15138 --last 30d --summary
  %(prog)s autoinvestments --user-id 6654
  %(prog)s autoinvestments --user-id 6654 --status active
  %(prog)s cashtransfers --user-id 6654
  %(prog)s cashtransfers --user-id 6654 --status completed
  %(prog)s alpaca-transfers --account-id 56846fba-222e-4dd3-b124-622c8b3d4f53
  %(prog)s alpaca-ach-relationships --account-id 56846fba-222e-4dd3-b124-622c8b3d4f53
  %(prog)s alpaca-trading-account --account-id 56846fba-222e-4dd3-b124-622c8b3d4f53
  %(prog)s deploy
  %(prog)s deploy --dry-run
        """
    )
    
    parser.add_argument(
        '--version', 
        action='version', 
        version='%(prog)s 1.0.0'
    )
    
    # Add subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        help='Available commands',
        metavar='COMMAND'
    )
    
    # Logs command
    LogsCommand.add_parser(subparsers)
    
    # User command
    UserCommand.add_parser(subparsers)
    
    # Transactions command
    TransactionsCommand.add_parser(subparsers)
    
    # Autoinvestments command
    AutoinvestmentsCommand.add_parser(subparsers)
    
    # Cash transfers command
    CashTransfersCommand.add_parser(subparsers)
    
    # Alpaca transfers command
    AlpacaTransfersCommand.add_parser(subparsers)
    
    # Alpaca ACH relationships command
    AlpacaAchRelationshipsCommand.add_parser(subparsers)
    
    # Alpaca trading account command
    AlpacaTradingAccountCommand.add_parser(subparsers)
    
    # Deploy command
    DeployCommand.add_parser(subparsers)
    
    return parser


def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        # Execute the appropriate command
        if args.command == 'logs':
            return LogsCommand.execute(args)
        elif args.command == 'user':
            return UserCommand.execute(args)
        elif args.command in ['transactions', 'txn', 'tx']:
            return TransactionsCommand.execute(args)
        elif args.command == 'autoinvestments':
            return AutoinvestmentsCommand.execute(args)
        elif args.command == 'cashtransfers':
            return CashTransfersCommand.execute(args)
        elif args.command == 'alpaca-transfers':
            return AlpacaTransfersCommand.execute(args)
        elif args.command == 'alpaca-ach-relationships':
            return AlpacaAchRelationshipsCommand.execute(args)
        elif args.command == 'alpaca-trading-account':
            return AlpacaTradingAccountCommand.execute(args)
        elif args.command == 'deploy':
            return DeployCommand.execute(args)
        else:
            print(f"{Colors.RED}Unknown command: {args.command}{Colors.NC}")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Operation cancelled by user{Colors.NC}")
        return 1
    except Exception as e:
        print(f"{Colors.RED}Error: {str(e)}{Colors.NC}")
        return 1


if __name__ == '__main__':
    sys.exit(main())