"""
Transactions command for querying user transactions from the database
"""

import asyncio
import asyncpg
import sys
from pathlib import Path
import argparse
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from ..utils.colors import Colors


class TransactionsCommand:
    """Command for querying user transactions from the database"""
    
    @staticmethod
    def add_parser(subparsers):
        """Add transactions subcommand to parser"""
        txn_parser = subparsers.add_parser(
            'transactions',
            aliases=['txn', 'tx'],
            help='Query user transactions from database',
            description='Query user transaction information from the database',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s transactions --user-id 6654
  %(prog)s txn --user-id 15138 --limit 20
  %(prog)s tx --user-id 15138 --since "2025-01-01" --format json
  %(prog)s transactions --user-id 15138 --type "buy" --output user-buys.csv
  %(prog)s txn --user-id 15138 --amount-min 100 --amount-max 1000
  %(prog)s transactions --user-id 15138 --status "completed" --last 30d
            """
        )
        
        # Primary search criteria
        txn_parser.add_argument(
            '--user-id',
            required=True,
            help='User ID to get transactions for'
        )
        
        # Time filtering
        time_group = txn_parser.add_mutually_exclusive_group()
        time_group.add_argument(
            '--since',
            help='Start date/time (YYYY-MM-DD or "YYYY-MM-DD HH:MM:SS")'
        )
        time_group.add_argument(
            '--last',
            help='Last time period (e.g., 24h, 7d, 30d)'
        )
        
        txn_parser.add_argument(
            '--until',
            help='End date/time (requires --since)'
        )
        
        # Transaction filtering
        txn_parser.add_argument(
            '--type',
            help='Transaction type (e.g., buy, sell, deposit, withdraw)'
        )
        
        txn_parser.add_argument(
            '--status',
            help='Transaction status (e.g., completed, pending, failed)'
        )
        
        txn_parser.add_argument(
            '--symbol',
            help='Stock/asset symbol'
        )
        
        txn_parser.add_argument(
            '--amount-min',
            type=float,
            help='Minimum transaction amount'
        )
        
        txn_parser.add_argument(
            '--amount-max',
            type=float,
            help='Maximum transaction amount'
        )
        
        # Query options
        txn_parser.add_argument(
            '--table',
            default='mainpage_transactions',
            help='Database table name (default: mainpage_transactions)'
        )
        
        txn_parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of results (default: 50)'
        )
        
        txn_parser.add_argument(
            '--fields',
            help='Comma-separated list of fields to return (default: all)'
        )
        
        txn_parser.add_argument(
            '--order-by',
            default='created_at DESC',
            help='Order by clause (default: created_at DESC)'
        )
        
        # Output options
        txn_parser.add_argument(
            '--format',
            choices=['table', 'json', 'csv'],
            default='table',
            help='Output format (default: table)'
        )
        
        txn_parser.add_argument(
            '--output', '-o',
            help='Output file (default: stdout)'
        )
        
        txn_parser.add_argument(
            '--raw-sql',
            action='store_true',
            help='Show the SQL query that would be executed'
        )
        
        # Database options
        txn_parser.add_argument(
            '--config',
            default='config/config.yaml',
            help='Configuration file path (default: config/config.yaml)'
        )
        
        # Display options
        txn_parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
        
        txn_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show SQL query without executing it'
        )
        
        txn_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Show detailed query information'
        )
        
        # Summary options
        txn_parser.add_argument(
            '--summary',
            action='store_true',
            help='Show transaction summary statistics'
        )
    
    @staticmethod
    def execute(args):
        """Execute the transactions command"""
        if args.no_color:
            Colors.disable()
        
        try:
            # Run the async query
            return asyncio.run(TransactionsCommand._execute_async(args))
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.NC} {str(e)}")
            return 1
    
    @staticmethod
    async def _execute_async(args):
        """Execute the transactions command asynchronously"""
        try:
            # Load configuration
            config = TransactionsCommand._load_config(args.config)
            
            # Build SQL query
            sql_query, params = TransactionsCommand._build_query(args)
            
            if args.verbose or args.dry_run or args.raw_sql:
                print(f"{Colors.BLUE}[SQL]{Colors.NC} {sql_query}")
                if params:
                    print(f"{Colors.BLUE}[PARAMS]{Colors.NC} {params}")
            
            if args.dry_run:
                return 0
            
            # Execute query
            results = await TransactionsCommand._execute_query(config, sql_query, params)
            
            # Show summary if requested
            if args.summary:
                TransactionsCommand._show_summary(results)
            
            # Format and output results
            TransactionsCommand._output_results(results, args)
            
            return 0
            
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.NC} {str(e)}")
            return 1
    
    @staticmethod
    def _load_config(config_path: str) -> Config:
        """Load configuration from file"""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                # Try relative to project root
                project_root = Path(__file__).parent.parent.parent
                config_file = project_root / config_path
                
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            return Config.load(str(config_file))
        except Exception as e:
            raise Exception(f"Failed to load configuration: {str(e)}")
    
    @staticmethod
    def _build_query(args) -> tuple[str, list]:
        """Build SQL query and parameters"""
        # Select fields
        if args.fields:
            fields = args.fields.strip()
        else:
            fields = "*"
        
        # Base query
        query = f"SELECT {fields} FROM {args.table}"
        params = []
        where_conditions = []
        param_count = 1
        
        # Always filter by user_id
        where_conditions.append(f"user_id = ${param_count}")
        params.append(int(args.user_id))
        param_count += 1
        
        # Time filtering
        if args.since:
            since_time = TransactionsCommand._format_time(args.since)
            where_conditions.append(f"created_at >= ${param_count}")
            params.append(since_time)
            param_count += 1
            
            if args.until:
                until_time = TransactionsCommand._format_time(args.until)
                where_conditions.append(f"created_at <= ${param_count}")
                params.append(until_time)
                param_count += 1
        elif args.last:
            since_time = TransactionsCommand._parse_relative_time(args.last)
            where_conditions.append(f"created_at >= ${param_count}")
            params.append(since_time)
            param_count += 1
        
        # Transaction type filter
        if args.type:
            where_conditions.append(f"transaction_type ILIKE ${param_count}")
            params.append(args.type)
            param_count += 1
        
        # Status filter
        if args.status:
            where_conditions.append(f"status ILIKE ${param_count}")
            params.append(args.status)
            param_count += 1
        
        # Symbol filter
        if args.symbol:
            where_conditions.append(f"symbol ILIKE ${param_count}")
            params.append(args.symbol.upper())
            param_count += 1
        
        # Amount filters
        if args.amount_min is not None:
            where_conditions.append(f"amount >= ${param_count}")
            params.append(args.amount_min)
            param_count += 1
        
        if args.amount_max is not None:
            where_conditions.append(f"amount <= ${param_count}")
            params.append(args.amount_max)
            param_count += 1
        
        # Add WHERE clause
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        # Add ORDER BY (use 'time' instead of 'created_at')
        if args.order_by:
            # Replace created_at with time in order by clause
            order_clause = args.order_by.replace('created_at', 'time')
            query += f" ORDER BY {order_clause}"
        
        # Add LIMIT
        query += f" LIMIT {args.limit}"
        
        return query, params
    
    @staticmethod
    def _format_time(time_str):
        """Format time string for database query"""
        # If it's just a date, add time
        if len(time_str) == 10 and '-' in time_str:  # YYYY-MM-DD
            return f"{time_str} 00:00:00"
        return time_str
    
    @staticmethod
    def _parse_relative_time(relative_str):
        """Parse relative time string and return timestamp"""
        import re
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
    async def _execute_query(config: Config, query: str, params: list) -> List[Dict[str, Any]]:
        """Execute the database query"""
        print(f"{Colors.GREEN}[INFO]{Colors.NC} Connecting to database...")
        
        try:
            # Connect to database
            conn = await asyncpg.connect(config.database.connection_string)
            
            print(f"{Colors.GREEN}[INFO]{Colors.NC} Executing transactions query...")
            
            # Execute query
            rows = await conn.fetch(query, *params)
            
            # Convert to list of dictionaries
            results = [dict(row) for row in rows]
            
            await conn.close()
            
            print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} Found {len(results)} transaction(s)")
            
            return results
            
        except Exception as e:
            raise Exception(f"Database query failed: {str(e)}")
    
    @staticmethod
    def _show_summary(results: List[Dict[str, Any]]):
        """Show transaction summary statistics"""
        if not results:
            return
        
        print(f"\n{Colors.BOLD}=== TRANSACTION SUMMARY ==={Colors.NC}")
        print(f"Total transactions: {len(results)}")
        
        # Try to calculate totals by type if amount field exists
        try:
            total_amount = sum(float(r.get('amount', 0) or 0) for r in results)
            print(f"Total amount: ${total_amount:,.2f}")
            
            # Group by transaction type
            type_counts = {}
            type_amounts = {}
            for txn in results:
                txn_type = txn.get('transaction_type', 'unknown')
                amount = float(txn.get('amount', 0) or 0)
                
                type_counts[txn_type] = type_counts.get(txn_type, 0) + 1
                type_amounts[txn_type] = type_amounts.get(txn_type, 0) + amount
            
            print(f"\nBy transaction type:")
            for txn_type, count in type_counts.items():
                amount = type_amounts[txn_type]
                print(f"  {txn_type}: {count} transactions, ${amount:,.2f}")
            
            # Group by status
            status_counts = {}
            for txn in results:
                status = txn.get('status', 'unknown')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            if len(status_counts) > 1:
                print(f"\nBy status:")
                for status, count in status_counts.items():
                    print(f"  {status}: {count} transactions")
        
        except (ValueError, TypeError, KeyError):
            # If we can't calculate amounts, just show basic info
            pass
        
        print()
    
    @staticmethod
    def _output_results(results: List[Dict[str, Any]], args):
        """Output results in the specified format"""
        if not results and not args.summary:
            print(f"{Colors.YELLOW}[WARNING]{Colors.NC} No transactions found")
            return
        
        if args.format == 'json':
            output = TransactionsCommand._format_json(results)
        elif args.format == 'csv':
            output = TransactionsCommand._format_csv(results)
        else:  # table
            output = TransactionsCommand._format_table(results)
        
        # Output to file or stdout
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} Results saved to {args.output}")
            except Exception as e:
                print(f"{Colors.RED}[ERROR]{Colors.NC} Failed to write to {args.output}: {str(e)}")
        else:
            if output.strip():  # Only print if there's content
                print(output)
    
    @staticmethod
    def _format_json(results: List[Dict[str, Any]]) -> str:
        """Format results as JSON"""
        # Convert datetime and other non-serializable objects to strings
        def json_serializer(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            return str(obj)
        
        return json.dumps(results, indent=2, default=json_serializer, ensure_ascii=False)
    
    @staticmethod
    def _format_csv(results: List[Dict[str, Any]]) -> str:
        """Format results as CSV"""
        if not results:
            return ""
        
        import csv
        from io import StringIO
        
        output = StringIO()
        
        # Get all field names
        fieldnames = list(results[0].keys())
        
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        
        for row in results:
            # Convert non-string values to strings
            str_row = {k: str(v) if v is not None else '' for k, v in row.items()}
            writer.writerow(str_row)
        
        return output.getvalue()
    
    @staticmethod
    def _format_table(results: List[Dict[str, Any]]) -> str:
        """Format results as a table"""
        if not results:
            return ""
        
        # Get all field names
        fields = list(results[0].keys())
        
        # For transactions, prioritize important fields for display
        priority_fields = ['id', 'created_at', 'transaction_type', 'symbol', 'amount', 'status']
        display_fields = []
        
        # Add priority fields first if they exist
        for field in priority_fields:
            if field in fields:
                display_fields.append(field)
        
        # Add remaining fields
        for field in fields:
            if field not in display_fields:
                display_fields.append(field)
        
        # Limit displayed fields if there are too many
        if len(display_fields) > 8:
            display_fields = display_fields[:8]
            print(f"{Colors.YELLOW}[INFO]{Colors.NC} Showing first 8 fields. Use --fields to specify columns.")
        
        # Calculate column widths
        widths = {}
        for field in display_fields:
            widths[field] = max(
                len(str(field)),
                max(len(str(row.get(field, ''))) for row in results)
            )
            # Limit column width for readability
            widths[field] = min(widths[field], 30)
        
        # Build table
        output = []
        
        # Header
        header = " | ".join(f"{field:<{widths[field]}}" for field in display_fields)
        output.append(f"{Colors.BOLD}{header}{Colors.NC}")
        
        # Separator
        separator = "-+-".join("-" * widths[field] for field in display_fields)
        output.append(separator)
        
        # Data rows
        for row in results:
            row_str = " | ".join(
                f"{str(row.get(field, ''))[:widths[field]]:<{widths[field]}}" 
                for field in display_fields
            )
            output.append(row_str)
        
        return "\n".join(output)