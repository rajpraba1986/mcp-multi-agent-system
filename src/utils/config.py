"""
Configuration management utilities for MCP Toolbox integration.

This module provides utilities for loading and managing configuration
from various sources including YAML files and environment variables.
"""

import os
import logging
from typing import Dict, Any, Optional, Union
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class DatabaseConfig(BaseModel):
    """Database configuration model."""
    host: str = "localhost"
    port: int = 5432
    database: str = "toolbox_demo"
    user: str = "demo_user"
    password: str = "demo_password"
    db_schema: str = "public"  # Renamed to avoid shadow warning
    ssl_mode: Optional[str] = None


class MCPToolboxConfig(BaseModel):
    """MCP Toolbox configuration model."""
    server_url: str = "http://localhost:5000"
    timeout: int = 30
    retry_attempts: int = 3
    tools_file: str = "config/tools.yaml"
    default_toolset: Optional[str] = None


class LLMConfig(BaseModel):
    """Language model configuration."""
    provider: str = "anthropic"
    model: str = "claude-3-haiku-20240307"
    temperature: float = 0.1
    max_tokens: Optional[int] = None
    api_key: Optional[str] = None


class ExtractionTypeConfig(BaseModel):
    """Single extraction type configuration."""
    description: str
    aliases: Optional[list] = []
    domains: list = ["*"]
    features: list = []
    use_cases: list = []
    wait_time: Optional[int] = None
    patterns: Optional[list] = []


class DomainConfig(BaseModel):
    """Domain-specific configuration."""
    extraction_type: str
    wait_time: Optional[int] = None
    scroll_to_load: bool = False
    selectors: Optional[Dict[str, str]] = {}


class ExtractionConfig(BaseModel):
    """Web extraction configuration."""
    default_extraction: Dict[str, Any] = {
        "type": "general",
        "take_screenshot": True,
        "timeout": 30000,
        "wait_for_content": 4000
    }
    extraction_types: Dict[str, ExtractionTypeConfig] = {}
    domain_configs: Dict[str, DomainConfig] = {}
    extraction_settings: Dict[str, Any] = {}


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    
    # Database configuration
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    
    # MCP Toolbox configuration
    mcp_toolbox: MCPToolboxConfig = Field(default_factory=MCPToolboxConfig)
    
    # LLM configuration
    llm: LLMConfig = Field(default_factory=LLMConfig)
    
    # Extraction configuration
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: Optional[str] = Field(default=None, env="LOG_FILE")
    
    class Config:
        env_file = ".env"
        env_nested_delimiter = "__"


class ConfigManager:
    """
    Configuration manager for the MCP Toolbox integration.
    
    This class handles loading configuration from multiple sources
    and provides a unified interface for accessing configuration values.
    """
    
    def __init__(
        self,
        config_file: Optional[str] = None,
        environment: Optional[str] = None
    ):
        """
        Initialize the configuration manager.
        
        Args:
            config_file: Path to configuration file
            environment: Environment name (development, production, etc.)
        """
        self.config_file = config_file
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        
        # Load configuration
        self._config_data = self._load_config()
        self.app_config = self._create_app_config()
        
        logger.info(f"Configuration loaded for environment: {self.environment}")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file and environment."""
        config_data = {}
        
        # Load from file if specified
        if self.config_file and Path(self.config_file).exists():
            with open(self.config_file, 'r') as file:
                file_config = yaml.safe_load(file)
                
                # Get environment-specific config
                if self.environment in file_config:
                    config_data.update(file_config[self.environment])
                
                # Get common config
                for key, value in file_config.items():
                    if key not in ["development", "production", "testing"]:
                        config_data[key] = value
        
        # Override with environment variables
        env_overrides = self._get_env_overrides()
        config_data.update(env_overrides)
        
        return config_data
    
    def _get_env_overrides(self) -> Dict[str, Any]:
        """Get configuration overrides from environment variables."""
        overrides = {}
        
        # Database overrides
        if os.getenv("DB_HOST"):
            overrides["database"] = overrides.get("database", {})
            overrides["database"]["host"] = os.getenv("DB_HOST")
        
        if os.getenv("DB_PORT"):
            overrides["database"] = overrides.get("database", {})
            overrides["database"]["port"] = int(os.getenv("DB_PORT"))
        
        if os.getenv("DB_NAME"):
            overrides["database"] = overrides.get("database", {})
            overrides["database"]["database"] = os.getenv("DB_NAME")
        
        if os.getenv("DB_USER"):
            overrides["database"] = overrides.get("database", {})
            overrides["database"]["user"] = os.getenv("DB_USER")
        
        if os.getenv("DB_PASSWORD"):
            overrides["database"] = overrides.get("database", {})
            overrides["database"]["password"] = os.getenv("DB_PASSWORD")
        
        # MCP Toolbox overrides
        if os.getenv("MCP_SERVER_URL"):
            overrides["mcp_toolbox"] = overrides.get("mcp_toolbox", {})
            overrides["mcp_toolbox"]["server_url"] = os.getenv("MCP_SERVER_URL")
        
        if os.getenv("MCP_TOOLS_FILE"):
            overrides["mcp_toolbox"] = overrides.get("mcp_toolbox", {})
            overrides["mcp_toolbox"]["tools_file"] = os.getenv("MCP_TOOLS_FILE")
        
        # LLM overrides
        if os.getenv("ANTHROPIC_API_KEY"):
            overrides["llm"] = overrides.get("llm", {})
            overrides["llm"]["api_key"] = os.getenv("ANTHROPIC_API_KEY")
            overrides["llm"]["provider"] = "anthropic"
        
        if os.getenv("OPENAI_API_KEY"):
            overrides["llm"] = overrides.get("llm", {})
            overrides["llm"]["api_key"] = os.getenv("OPENAI_API_KEY")
            overrides["llm"]["provider"] = "openai"
        
        if os.getenv("LLM_PROVIDER"):
            overrides["llm"] = overrides.get("llm", {})
            overrides["llm"]["provider"] = os.getenv("LLM_PROVIDER")
        
        if os.getenv("LLM_MODEL"):
            overrides["llm"] = overrides.get("llm", {})
            overrides["llm"]["model"] = os.getenv("LLM_MODEL")
        
        return overrides
    
    def _create_app_config(self) -> AppConfig:
        """Create the application configuration object."""
        # Flatten nested config for Pydantic
        flat_config = {}
        
        for key, value in self._config_data.items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat_config[f"{key}__{sub_key}"] = sub_value
            else:
                flat_config[key] = value
        
        # Set environment variables for Pydantic
        for key, value in flat_config.items():
            os.environ[key.upper()] = str(value)
        
        return AppConfig()
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self.app_config.database
    
    def get_mcp_config(self) -> MCPToolboxConfig:
        """Get MCP Toolbox configuration."""
        return self.app_config.mcp_toolbox
    
    def get_llm_config(self) -> LLMConfig:
        """Get LLM configuration."""
        return self.app_config.llm
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key.split('.')
        value = self._config_data
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def update_config(self, key: str, value: Any):
        """
        Update a configuration value.
        
        Args:
            key: Configuration key (supports dot notation)
            value: New value
        """
        keys = key.split('.')
        config = self._config_data
        
        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        # Set the value
        config[keys[-1]] = value
        
        # Recreate app config
        self.app_config = self._create_app_config()
        
        logger.info(f"Updated configuration: {key} = {value}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Get configuration as dictionary."""
        return self._config_data.copy()
    
    def save_to_file(self, file_path: str):
        """
        Save configuration to file.
        
        Args:
            file_path: Path to save configuration file
        """
        with open(file_path, 'w') as file:
            yaml.dump(self._config_data, file, default_flow_style=False)
        
        logger.info(f"Configuration saved to: {file_path}")


def load_config(
    config_file: Optional[str] = None,
    environment: Optional[str] = None
) -> ConfigManager:
    """
    Load configuration from file and environment.
    
    Args:
        config_file: Path to configuration file
        environment: Environment name
        
    Returns:
        ConfigManager: Configured configuration manager
    """
    # Default config file locations
    if config_file is None:
        config_files = [
            "config/app.yaml",
            "config/config.yaml",
            "app.yaml",
            "config.yaml"
        ]
        
        for file_path in config_files:
            if Path(file_path).exists():
                config_file = file_path
                break
    
    return ConfigManager(config_file, environment)


def load_extraction_config(config_file: str = "config/extraction_config.yaml") -> ExtractionConfig:
    """
    Load web extraction configuration from YAML file.
    
    Args:
        config_file: Path to extraction configuration file
        
    Returns:
        ExtractionConfig: Loaded extraction configuration
    """
    try:
        config_path = Path(config_file)
        if not config_path.exists():
            logger.warning(f"Extraction config file not found: {config_file}, using defaults")
            return ExtractionConfig()
            
        with open(config_path, 'r') as file:
            config_data = yaml.safe_load(file)
            
        # Parse extraction types
        extraction_types = {}
        for name, type_config in config_data.get("extraction_types", {}).items():
            extraction_types[name] = ExtractionTypeConfig(**type_config)
        
        # Parse domain configs
        domain_configs = {}
        for domain, domain_config in config_data.get("domain_configs", {}).items():
            domain_configs[domain] = DomainConfig(**domain_config)
        
        # Create extraction config
        extraction_config = ExtractionConfig(
            default_extraction=config_data.get("default_extraction", {}),
            extraction_types=extraction_types,
            domain_configs=domain_configs,
            extraction_settings=config_data.get("extraction_settings", {})
        )
        
        logger.info(f"Loaded extraction config with {len(extraction_types)} extraction types")
        return extraction_config
        
    except Exception as e:
        logger.error(f"Error loading extraction config: {e}")
        return ExtractionConfig()


def get_extraction_type_for_domain(domain: str, extraction_config: ExtractionConfig) -> str:
    """
    Get the appropriate extraction type for a domain.
    
    Args:
        domain: Domain name (e.g., "finance.yahoo.com")
        extraction_config: Extraction configuration
        
    Returns:
        str: Recommended extraction type
    """
    # Check for exact domain match
    if domain in extraction_config.domain_configs:
        return extraction_config.domain_configs[domain].extraction_type
    
    # Check for partial domain matches
    for config_domain, config in extraction_config.domain_configs.items():
        if config_domain in domain or domain in config_domain:
            return config.extraction_type
    
    # Return default
    return extraction_config.default_extraction.get("type", "general")


def get_extraction_aliases(extraction_type: str, extraction_config: ExtractionConfig) -> list:
    """
    Get all aliases for an extraction type.
    
    Args:
        extraction_type: Primary extraction type name
        extraction_config: Extraction configuration
        
    Returns:
        list: List of aliases including the primary name
    """
    if extraction_type in extraction_config.extraction_types:
        aliases = extraction_config.extraction_types[extraction_type].aliases or []
        return [extraction_type] + aliases
    
    # Check if the provided type is an alias
    for type_name, type_config in extraction_config.extraction_types.items():
        if extraction_type in (type_config.aliases or []):
            return [type_name] + type_config.aliases
    
    return [extraction_type]


def create_default_config_file(file_path: str = "config/app.yaml"):
    """
    Create a default configuration file.
    
    Args:
        file_path: Path where to create the config file
    """
    default_config = {
        "development": {
            "debug": True,
            "database": {
                "host": "localhost",
                "port": 5432,
                "database": "mcp_demo_dev",
                "user": "demo_user",
                "password": "demo_password"
            },
            "mcp_toolbox": {
                "server_url": "http://localhost:5000",
                "tools_file": "config/tools.yaml",
                "default_toolset": "all-tools"
            },
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-haiku-20240307",
                "temperature": 0.1
            }
        },
        "production": {
            "debug": False,
            "database": {
                "host": "${DB_HOST}",
                "port": "${DB_PORT:-5432}",
                "database": "${DB_NAME}",
                "user": "${DB_USER}",
                "password": "${DB_PASSWORD}",
                "ssl_mode": "require"
            },
            "mcp_toolbox": {
                "server_url": "${MCP_SERVER_URL:-http://localhost:5000}",
                "tools_file": "${MCP_TOOLS_FILE:-config/tools.yaml}",
                "default_toolset": "${MCP_DEFAULT_TOOLSET}"
            },
            "llm": {
                "provider": "${LLM_PROVIDER:-anthropic}",
                "model": "${LLM_MODEL:-claude-3-haiku-20240307}",
                "temperature": 0.1,
                "api_key": "${ANTHROPIC_API_KEY}"
            }
        }
    }
    
    # Ensure directory exists
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Write config file
    with open(file_path, 'w') as file:
        yaml.dump(default_config, file, default_flow_style=False)
    
    logger.info(f"Created default configuration file: {file_path}")
