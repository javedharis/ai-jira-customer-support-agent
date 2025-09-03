"""
Configuration management for the automated customer support system
"""

import os
import yaml
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from pathlib import Path
from dotenv import load_dotenv


@dataclass
class JiraConfig:
    base_url: str
    username: str
    api_token: str


@dataclass
class DeepSeekConfig:
    api_key: str
    model: str = "deepseek-chat"
    max_tokens: int = 4000
    temperature: float = 0.1


@dataclass
class ClaudeConfig:
    cli_path: str = "/usr/local/bin/claude"


@dataclass
class SSHServerConfig:
    host: str
    username: str
    key_path: str
    port: int = 22


@dataclass
class DatabaseConfig:
    connection_string: str
    query_timeout: int = 30
    max_connections: int = 5


@dataclass
class CodebaseConfig:
    repo_path: str
    git_enabled: bool = True


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: Optional[str] = None
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


@dataclass
class Config:
    jira: JiraConfig
    deepseek: DeepSeekConfig
    claude: ClaudeConfig
    ssh_servers: List[SSHServerConfig]
    database: DatabaseConfig
    codebase: CodebaseConfig
    logging: LoggingConfig
    dry_run: bool = False

    @classmethod
    def load(cls, config_path: str, user: Optional[str] = None) -> 'Config':
        """Load configuration from YAML file with environment variable substitution
        
        Args:
            config_path: Path to the configuration file
            user: Optional user name for selecting specific JIRA token (e.g., 'yassa')
        """
        # Load .env file if it exists
        env_file = Path('.env')
        if env_file.exists():
            load_dotenv(env_file)
        
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            raw_config = yaml.safe_load(f)
        
        # Substitute environment variables
        config_data = cls._substitute_env_vars(raw_config)
        
        # Handle user-specific JIRA token
        if user and user.lower() == 'yassa':
            # Use Yassa's JIRA token
            yassa_token = os.getenv('YASSA_JIRA_API_TOKEN')
            if yassa_token:
                config_data['jira']['api_token'] = yassa_token
                config_data['jira']['username'] = "yassa@surmount.ai"
            else:
                raise ValueError("YASSA_JIRA_API_TOKEN not found in environment variables")
        # For default or 'haris' user, use the default token (already loaded)
        
        # Parse configuration sections
        jira_config = JiraConfig(**config_data['jira'])
        deepseek_config = DeepSeekConfig(**config_data['deepseek'])
        claude_config = ClaudeConfig(**config_data.get('claude', {}))
        
        ssh_servers = [
            SSHServerConfig(**server) 
            for server in config_data['ssh_servers']
        ]
        
        database_config = DatabaseConfig(**config_data['database'])
        codebase_config = CodebaseConfig(**config_data['codebase'])
        logging_config = LoggingConfig(**config_data.get('logging', {}))
        
        return cls(
            jira=jira_config,
            deepseek=deepseek_config,
            claude=claude_config,
            ssh_servers=ssh_servers,
            database=database_config,
            codebase=codebase_config,
            logging=logging_config
        )
    
    @staticmethod
    def _substitute_env_vars(obj: Any) -> Any:
        """Recursively substitute environment variables in configuration"""
        if isinstance(obj, dict):
            return {key: Config._substitute_env_vars(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [Config._substitute_env_vars(item) for item in obj]
        elif isinstance(obj, str):
            # Handle ${VAR_NAME} substitution
            if obj.startswith('${') and obj.endswith('}'):
                env_var = obj[2:-1]
                value = os.getenv(env_var)
                if value is None:
                    raise ValueError(f"Environment variable {env_var} is not set")
                return value
            return obj
        else:
            return obj
    
    def validate(self) -> None:
        """Validate configuration settings"""
        errors = []
        
        # Validate JIRA configuration
        if not self.jira.base_url:
            errors.append("JIRA base_url is required")
        if not self.jira.api_token:
            errors.append("JIRA api_token is required")
        
        # Validate DeepSeek configuration
        if not self.deepseek.api_key:
            errors.append("DeepSeek api_key is required")
        
        # Validate Claude CLI path
        if not Path(self.claude.cli_path).exists():
            errors.append(f"Claude CLI not found at {self.claude.cli_path}")
        
        # Validate SSH servers
        for i, server in enumerate(self.ssh_servers):
            if not server.host:
                errors.append(f"SSH server {i}: host is required")
            if server.key_path and not Path(server.key_path).exists():
                errors.append(f"SSH server {i}: key file not found at {server.key_path}")
        
        # Validate database connection
        if not self.database.connection_string:
            errors.append("Database connection_string is required")
        
        # Validate codebase path
        if not Path(self.codebase.repo_path).exists():
            errors.append(f"Codebase repository not found at {self.codebase.repo_path}")
        
        if errors:
            raise ValueError("Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors))