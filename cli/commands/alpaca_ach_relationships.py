"""
Alpaca ACH relationships command for querying bank account connection details from Alpaca Broker API
"""

import os
import sys
import base64
import json
import argparse
import requests
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from cli.utils.colors import Colors


class AlpacaAchRelationshipsCommand:
    """Command for querying ACH relationships details from Alpaca Broker API"""
    
    @staticmethod
    def add_parser(subparsers):
        """Add alpaca-ach-relationships subcommand to parser"""
        alpaca_ach_parser = subparsers.add_parser(
            'alpaca-ach-relationships',
            help='Query bank account connection details from Alpaca Broker API',
            description='Query ACH relationships information from Alpaca Broker API using account ID',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s alpaca-ach-relationships --account-id 56846fba-222e-4dd3-b124-622c8b3d4f53
  %(prog)s alpaca-ach-relationships --account-id 56846fba-222e-4dd3-b124-622c8b3d4f53 --format json
  %(prog)s alpaca-ach-relationships --account-id 56846fba-222e-4dd3-b124-622c8b3d4f53 --output ach_relationships.json
            """
        )
        
        # Required arguments
        alpaca_ach_parser.add_argument(
            '--account-id',
            required=True,
            help='Alpaca account ID to query ACH relationships for'
        )
        
        # Output options
        alpaca_ach_parser.add_argument(
            '--format',
            choices=['table', 'json'],
            default='table',
            help='Output format (default: table)'
        )
        
        alpaca_ach_parser.add_argument(
            '--output', '-o',
            help='Output file (default: stdout)'
        )
        
        # Display options
        alpaca_ach_parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
        
        alpaca_ach_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Show detailed request information'
        )
        
        # Environment options
        alpaca_ach_parser.add_argument(
            '--env-file',
            default='.env',
            help='Path to environment file (default: .env)'
        )
    
    @staticmethod
    def execute(args):
        """Execute the alpaca-ach-relationships command"""
        if args.no_color:
            Colors.disable()
        
        try:
            return AlpacaAchRelationshipsCommand._execute_request(args)
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.NC} {str(e)}")
            return 1
    
    @staticmethod
    def _execute_request(args):
        """Execute the Alpaca API request"""
        try:
            # Load environment variables
            env_file_path = Path(args.env_file)
            if not env_file_path.is_absolute():
                # Try relative to project root
                project_root = Path(__file__).parent.parent.parent
                env_file_path = project_root / args.env_file
            
            if not env_file_path.exists():
                raise FileNotFoundError(f"Environment file not found: {args.env_file}")
            
            load_dotenv(str(env_file_path))
            
            # Get credentials from environment
            username = os.getenv('ALPACA_BROKER_USERNAME')
            password = os.getenv('ALPACA_BROKER_PASSWORD')
            
            if not username or not password:
                raise ValueError("Missing ALPACA_BROKER_USERNAME or ALPACA_BROKER_PASSWORD in environment file")
            
            # Create basic auth header
            credentials = f"{username}:{password}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            # Build request URL
            url = f"https://broker-api.alpaca.markets/v1/accounts/{args.account_id}/ach_relationships"
            
            headers = {
                'accept': 'application/json',
                'authorization': f'Basic {encoded_credentials}'
            }
            
            if args.verbose:
                print(f"{Colors.BLUE}[REQUEST]{Colors.NC} GET {url}")
                print(f"{Colors.BLUE}[HEADERS]{Colors.NC} {json.dumps({k: v if k != 'authorization' else 'Basic ***' for k, v in headers.items()}, indent=2)}")
            
            print(f"{Colors.GREEN}[INFO]{Colors.NC} Making request to Alpaca API...")
            
            # Make the request
            response = requests.get(url, headers=headers, timeout=30)
            
            if args.verbose:
                print(f"{Colors.BLUE}[RESPONSE]{Colors.NC} Status: {response.status_code}")
            
            # Handle response
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} Retrieved {len(data) if isinstance(data, list) else 1} ACH relationship(s)")
                    
                    # Format and output results
                    AlpacaAchRelationshipsCommand._output_results(data, args)
                    return 0
                    
                except json.JSONDecodeError as e:
                    raise Exception(f"Failed to parse JSON response: {str(e)}")
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', 'Unknown error')
                except:
                    error_msg = response.text or f"HTTP {response.status_code}"
                
                raise Exception(f"API request failed (HTTP {response.status_code}): {error_msg}")
                
        except requests.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
        except Exception as e:
            raise Exception(f"Failed to execute request: {str(e)}")
    
    @staticmethod
    def _output_results(data, args):
        """Output results in the specified format"""
        if not data:
            print(f"{Colors.YELLOW}[WARNING]{Colors.NC} No ACH relationships found")
            return
        
        if args.format == 'json':
            output = AlpacaAchRelationshipsCommand._format_json(data)
        else:  # table
            output = AlpacaAchRelationshipsCommand._format_table(data)
        
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
    def _format_json(data) -> str:
        """Format results as JSON"""
        return json.dumps(data, indent=2, ensure_ascii=False)
    
    @staticmethod
    def _format_table(data) -> str:
        """Format results as a table"""
        if not data:
            return ""
        
        # Handle both single object and array responses
        if isinstance(data, dict):
            relationships = [data]
        elif isinstance(data, list):
            relationships = data
        else:
            return str(data)
        
        if not relationships:
            return "No ACH relationships found"
        
        # Get all field names from the first relationship
        first_relationship = relationships[0]
        if not isinstance(first_relationship, dict):
            return json.dumps(relationships, indent=2)
        
        fields = list(first_relationship.keys())
        
        # Calculate column widths
        widths = {}
        for field in fields:
            widths[field] = max(
                len(str(field)),
                max(len(str(relationship.get(field, ''))) for relationship in relationships)
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
        for relationship in relationships:
            row_str = " | ".join(
                f"{str(relationship.get(field, '')):<{widths[field]}}" 
                for field in fields
            )
            output.append(row_str)
        
        return "\n".join(output)