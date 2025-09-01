"""
Deploy command for application deployment
"""

import subprocess
import sys
from pathlib import Path
import argparse

from ..utils.colors import Colors


class DeployCommand:
    """Command for deploying the application"""
    
    @staticmethod
    def add_parser(subparsers):
        """Add deploy subcommand to parser"""
        deploy_parser = subparsers.add_parser(
            'deploy',
            help='Deploy application to server',
            description='Deploy the QB Customer Support application to the remote server',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s deploy
  %(prog)s deploy --dry-run
  %(prog)s deploy --test-ssh-only
            """
        )
        
        deploy_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be deployed without actually deploying'
        )
        
        deploy_parser.add_argument(
            '--test-ssh-only',
            action='store_true',
            help='Only test SSH connectivity, do not deploy'
        )
        
        deploy_parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Show detailed deployment information'
        )
        
        deploy_parser.add_argument(
            '--no-color',
            action='store_true',
            help='Disable colored output'
        )
    
    @staticmethod
    def execute(args):
        """Execute the deploy command"""
        if args.no_color:
            Colors.disable()
        
        project_root = Path(__file__).parent.parent.parent
        
        if args.test_ssh_only:
            return DeployCommand._test_ssh(project_root)
        else:
            return DeployCommand._run_deployment(project_root, args)
    
    @staticmethod
    def _test_ssh(project_root):
        """Test SSH connectivity only"""
        ssh_test_script = project_root / "test-ssh.sh"
        
        if not ssh_test_script.exists():
            print(f"{Colors.RED}[ERROR]{Colors.NC} SSH test script not found: {ssh_test_script}")
            return 1
        
        print(f"{Colors.BLUE}[INFO]{Colors.NC} Testing SSH connectivity...")
        
        try:
            result = subprocess.run(
                [str(ssh_test_script)],
                cwd=project_root,
                check=False
            )
            return result.returncode
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.NC} Failed to run SSH test: {str(e)}")
            return 1
    
    @staticmethod
    def _run_deployment(project_root, args):
        """Run the deployment script"""
        deploy_script = project_root / "deploy.sh"
        
        if not deploy_script.exists():
            print(f"{Colors.RED}[ERROR]{Colors.NC} Deploy script not found: {deploy_script}")
            print(f"{Colors.BLUE}[INFO]{Colors.NC} Make sure you're running from the project root directory")
            return 1
        
        if args.dry_run:
            print(f"{Colors.BLUE}[INFO]{Colors.NC} DRY RUN: Would execute deployment script")
            print(f"{Colors.BLUE}[INFO]{Colors.NC} Script: {deploy_script}")
            return 0
        
        print(f"{Colors.BLUE}[INFO]{Colors.NC} Starting deployment...")
        
        try:
            # Run the deployment script
            result = subprocess.run(
                [str(deploy_script)],
                cwd=project_root,
                check=False
            )
            
            if result.returncode == 0:
                print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} Deployment completed successfully!")
            else:
                print(f"{Colors.RED}[ERROR]{Colors.NC} Deployment failed with exit code {result.returncode}")
            
            return result.returncode
            
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}[WARNING]{Colors.NC} Deployment interrupted by user")
            return 1
        except Exception as e:
            print(f"{Colors.RED}[ERROR]{Colors.NC} Failed to run deployment: {str(e)}")
            return 1