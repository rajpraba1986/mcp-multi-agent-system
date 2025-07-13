"""
LLM Initialization Utilities

This module provides utilities for initializing language models
with proper configuration and API key handling.
"""

import os
import logging
from typing import Optional
from langchain_core.language_models import BaseLanguageModel

logger = logging.getLogger(__name__)

def create_anthropic_llm(
    model: str = "claude-3-haiku-20240307",
    temperature: float = 0.1,
    api_key: Optional[str] = None,
    max_tokens: Optional[int] = None,
    streaming: bool = True
) -> BaseLanguageModel:
    """
    Create an Anthropic Claude language model.
    
    Args:
        model: Model name (default: claude-3-haiku-20240307)
        temperature: Temperature setting (default: 0.1)
        api_key: API key (defaults to ANTHROPIC_API_KEY env var)
        max_tokens: Maximum tokens (optional)
        streaming: Enable streaming (default: True)
    
    Returns:
        Configured Anthropic Claude model
    """
    try:
        from langchain_anthropic import ChatAnthropic
        
        # Get API key from parameter or environment
        if api_key is None:
            api_key = os.getenv("ANTHROPIC_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Anthropic API key not found. "
                "Please set ANTHROPIC_API_KEY environment variable or pass api_key parameter."
            )
        
        # Create model configuration
        model_kwargs = {
            "model": model,
            "temperature": temperature,
            "api_key": api_key,
            "streaming": streaming
        }
        
        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens
        
        llm = ChatAnthropic(**model_kwargs)
        
        logger.info(f"Successfully initialized Anthropic Claude model: {model}")
        return llm
        
    except ImportError:
        logger.error("langchain_anthropic not installed. Install with: pip install langchain-anthropic")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize Anthropic Claude model: {e}")
        raise

def create_openai_llm(
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.1,
    api_key: Optional[str] = None,
    max_tokens: Optional[int] = None,
    streaming: bool = True
) -> BaseLanguageModel:
    """
    Create an OpenAI language model.
    
    Args:
        model: Model name (default: gpt-3.5-turbo)
        temperature: Temperature setting (default: 0.1)
        api_key: API key (defaults to OPENAI_API_KEY env var)
        max_tokens: Maximum tokens (optional)
        streaming: Enable streaming (default: True)
    
    Returns:
        Configured OpenAI model
    """
    try:
        from langchain_openai import ChatOpenAI
        
        # Get API key from parameter or environment
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "OpenAI API key not found. "
                "Please set OPENAI_API_KEY environment variable or pass api_key parameter."
            )
        
        # Create model configuration
        model_kwargs = {
            "model": model,
            "temperature": temperature,
            "api_key": api_key,
            "streaming": streaming
        }
        
        if max_tokens:
            model_kwargs["max_tokens"] = max_tokens
        
        llm = ChatOpenAI(**model_kwargs)
        
        logger.info(f"Successfully initialized OpenAI model: {model}")
        return llm
        
    except ImportError:
        logger.error("langchain_openai not installed. Install with: pip install langchain-openai")
        raise
    except Exception as e:
        logger.error(f"Failed to initialize OpenAI model: {e}")
        raise

def create_llm_from_config(config_manager=None, **kwargs) -> BaseLanguageModel:
    """
    Create an LLM based on configuration with Anthropic Claude as default.
    
    Args:
        config_manager: Configuration manager instance
        **kwargs: Additional parameters to override config
    
    Returns:
        Configured language model
    """
    try:
        if config_manager:
            llm_config = config_manager.get_llm_config()
            provider = llm_config.provider.lower()
            model = llm_config.model
            temperature = llm_config.temperature
            api_key = llm_config.api_key
        else:
            # Use environment variables as fallback
            provider = os.getenv("LLM_PROVIDER", "anthropic").lower()
            model = os.getenv("LLM_MODEL", "claude-3-haiku-20240307")
            temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
            api_key = None
        
        # Override with any provided kwargs
        provider = kwargs.get("provider", provider)
        model = kwargs.get("model", model)
        temperature = kwargs.get("temperature", temperature)
        api_key = kwargs.get("api_key", api_key)
        
        # Create LLM based on provider
        if provider == "anthropic":
            return create_anthropic_llm(
                model=model,
                temperature=temperature,
                api_key=api_key,
                max_tokens=kwargs.get("max_tokens"),
                streaming=kwargs.get("streaming", True)
            )
        elif provider == "openai":
            return create_openai_llm(
                model=model,
                temperature=temperature,
                api_key=api_key,
                max_tokens=kwargs.get("max_tokens"),
                streaming=kwargs.get("streaming", True)
            )
        else:
            logger.warning(f"Unknown provider '{provider}', defaulting to Anthropic Claude")
            return create_anthropic_llm(
                model="claude-3-haiku-20240307",
                temperature=temperature,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                streaming=kwargs.get("streaming", True)
            )
            
    except Exception as e:
        logger.error(f"Failed to create LLM from config: {e}")
        logger.info("Falling back to default Anthropic Claude model")
        return create_anthropic_llm()

def get_available_providers() -> list:
    """Get list of available LLM providers."""
    providers = []
    
    try:
        import langchain_anthropic
        providers.append("anthropic")
    except ImportError:
        pass
    
    try:
        import langchain_openai
        providers.append("openai")
    except ImportError:
        pass
    
    return providers

def validate_api_keys() -> dict:
    """
    Validate available API keys.
    
    Returns:
        Dictionary with provider: bool mapping indicating key availability
    """
    return {
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai": bool(os.getenv("OPENAI_API_KEY"))
    }
