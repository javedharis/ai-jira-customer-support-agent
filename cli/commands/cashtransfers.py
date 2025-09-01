"""
Cash transfers command for querying cash transfer details from the database
"""

import asyncio
import asyncpg
import sys
from pathlib import Path
import argparse
import json
from typing import Optional, List, Dict, Any

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.config import Config
from ..utils.colors import Colors


class CashTransfersCommand:
    """Command for querying cash transfer details from the database"""
    
    @staticmethod
    def add_parser(subparsers):
        """Add cashtransfers subcommand to parser"""
        cashtransfers_parser = subparsers.add_parser(
            'cashtransfers',
            help='Query cash transfer details from database',
            description='Query cash transfer information from the database using user ID',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s cashtransfers --user-id 6654
  %(prog)s cashtransfers --user-id 6654 --format json
  %(prog)s cashtransfers --user-id 6654 --status completed
  %(prog)s cashtransfers --user-id 6654 --type deposit
  %(prog)s cashtransfers --user-id 6654 --output cashtransfers.json
            """
        )
        
        # Search criteria
        cashtransfers_parser.add_argument(
            '--user-id',
            required=True,
            help='User ID to query cash transfers for'
        )
        
        # Filter options
        cashtransfers_parser.add_argument(
            '--status',
            help='Filter by status (e.g., completed, pending, failed)'
        )
        
        cashtransfers_parser.add_argument(
            '--type',
            help='Filter by type (e.g., deposit, withdrawal)'
        )
        
        cashtransfers_parser.add_argument(
            '--origin-account-id',
            help='Filter by origin account ID'
        )
        
        cashtransfers_parser.add_argument(
            '--destination-account-id',
            help='Filter by destination account ID'
        )
        
        # Query options
        cashtransfers_parser.add_argument(
            '--table',
            default='mainpage_cashtransfers',
            help='Database table name (default: mainpage_cashtransfers)'
        )
        
        cashtransfers_parser.add_argument(
            '--limit',
            type=int,
            default=50,
            help='Maximum number of results (default: 50)'
        )
        
        cashtransfers_parser.add_argument(
            '--fields',
            help='Comma-separated list of fields to return (default: all)'
        )
        
        # Output options
        cashtransfers_parser.add_argument(
            '--format',
            choices=['table', 'json', 'csv'],
            default='table',
            help='Output format (default: table)'
        )
        
        cashtransfers_parser.add_argument(
            '--output', '-o',
            help='Output file (default: stdout)'
        )
        
        cashtransfers_parser.add_argument(
            '--raw-sql',
            action='store_true',
            help='Show the SQL query that would be executed'
        )
        
        # Database options
        cashtransfers_parser.add_argument(
            '--config',
            default='config/config.yaml',
            help='Configuration file path (default: config/config.yaml)'
        )
        
        # Display options
        cashtransfers_parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
        
        cashtransfers_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show SQL query without executing it'
        )
        
        cashtransfers_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Show detailed query information'
        )
    
    @staticmethod
    def execute(args):
        """Execute the cashtransfers command"""
        if args.no_color:
            Colors.disable()
        
        try:
            # Run the async query
            return asyncio.run(CashTransfersCommand._execute_async(args))
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.NC} {str(e)}")
            return 1
    
    @staticmethod
    async def _execute_async(args):
        """Execute the cashtransfers command asynchronously"""
        try:
            # Load configuration
            config = CashTransfersCommand._load_config(args.config)
            
            # Build SQL query
            sql_query, params = CashTransfersCommand._build_query(args)
            
            if args.verbose or args.dry_run or args.raw_sql:
                print(f"{Colors.BLUE}[SQL]{Colors.NC} {sql_query}")
                if params:
                    print(f"{Colors.BLUE}[PARAMS]{Colors.NC} {params}")
            
            if args.dry_run:
                return 0
            
            # Execute query
            results = await CashTransfersCommand._execute_query(config, sql_query, params)
            
            # Format and output results
            CashTransfersCommand._output_results(results, args)
            
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
        
        # Build WHERE clause
        where_conditions = []
        param_count = 1
        
        # User ID is required
        where_conditions.append(f"user_id = ${param_count}")
        params.append(int(args.user_id))
        param_count += 1
        
        # Optional filters
        if args.status:
            where_conditions.append(f"status = ${param_count}")
            params.append(args.status)
            param_count += 1
            
        if args.type:
            where_conditions.append(f"type = ${param_count}")
            params.append(args.type)
            param_count += 1
            
        if args.origin_account_id:
            where_conditions.append(f"origin_account_id = ${param_count}")
            params.append(args.origin_account_id)
            param_count += 1
            
        if args.destination_account_id:
            where_conditions.append(f"destination_account_id = ${param_count}")
            params.append(args.destination_account_id)
            param_count += 1
        
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)
        
        # Add ORDER BY for consistent results (most recent first)
        query += " ORDER BY created_at DESC"
        
        # Add LIMIT
        query += f" LIMIT {args.limit}"
        
        return query, params
    
    @staticmethod
    async def _execute_query(config: Config, query: str, params: list) -> List[Dict[str, Any]]:
        """Execute the database query"""
        print(f"{Colors.GREEN}[INFO]{Colors.NC} Connecting to database...")
        
        try:
            # Connect to database
            conn = await asyncpg.connect(config.database.connection_string)
            
            print(f"{Colors.GREEN}[INFO]{Colors.NC} Executing query...")
            
            # Execute query
            rows = await conn.fetch(query, *params)
            
            # Convert to list of dictionaries
            results = [dict(row) for row in rows]
            
            await conn.close()
            
            print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} Found {len(results)} result(s)")
            
            return results
            
        except Exception as e:
            raise Exception(f"Database query failed: {str(e)}")
    
    @staticmethod
    def _output_results(results: List[Dict[str, Any]], args):
        """Output results in the specified format"""
        if not results:
            print(f"{Colors.YELLOW}[WARNING]{Colors.NC} No cash transfers found")
            return
        
        if args.format == 'json':
            output = CashTransfersCommand._format_json(results)
        elif args.format == 'csv':
            output = CashTransfersCommand._format_csv(results)
        else:  # table
            output = CashTransfersCommand._format_table(results)
        
        # Output to file or stdout
        if args.output:
            try:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(output)
                print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} Results saved to {args.output}")
            except Exception as e:
                print(f"{Colors.RED}[ERROR]{Colors.NC} Failed to write to {args.output}: {str(e)}")
        else:
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
        
        # Calculate column widths
        widths = {}
        for field in fields:
            widths[field] = max(
                len(str(field)),
                max(len(str(row.get(field, ''))) for row in results)
            )
        
        # Build table
        output = []
        
        # Header
        header = " | ".join(f"{field:<{widths[field]}}" for field in fields)
        output.append(f"{Colors.BOLD}{header}{Colors.NC}")
        
        # Separator
        separator = "-+-".join("-" * widths[field] for field in fields)
        output.append(separator)
        
        # Data rows
        for row in results:
            row_str = " | ".join(
                f"{str(row.get(field, '')):<{widths[field]}}" 
                for field in fields
            )
            output.append(row_str)
        
        return "\n".join(output)