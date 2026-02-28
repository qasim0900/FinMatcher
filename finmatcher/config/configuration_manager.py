"""
Configuration manager for FinMatcher v2.0 Enterprise Upgrade.

This module handles loading, validation, normalization, and hot-reload of configuration
parameters including scoring weights, thresholds, and system settings.

Validates Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
"""

import os
import yaml
import json
import logging
from typing import Callable, List, Optional, Dict, Any
from decimal import Decimal
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from finmatcher.storage.models import MatchingConfig

logger = logging.getLogger(__name__)


class ConfigFileHandler(FileSystemEventHandler):
    """
    File system event handler for configuration file changes.
    """
    
    def __init__(self, config_path: str, callback: Callable):
        """
        Initialize config file handler.
        
        Args:
            config_path: Path to configuration file
            callback: Function to call when file changes
        """
        self.config_path = Path(config_path).resolve()
        self.callback = callback
    
    def on_modified(self, event: FileModifiedEvent):
        """Handle file modification events."""
        if not event.is_directory and Path(event.src_path).resolve() == self.config_path:
            logger.info(f"Configuration file modified: {event.src_path}")
            self.callback()


class ConfigurationManager:
    """
    Manages configuration loading, validation, normalization, and hot-reload.
    
    Validates Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7
    """
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize configuration manager.
        
        Args:
            config_path: Path to configuration file (YAML or JSON)
        """
        self.config_path = config_path
        self.config_data: Dict[str, Any] = {}
        self.matching_config: Optional[MatchingConfig] = None
        self.observers: List[Callable] = []
        self.file_observer: Optional[Observer] = None
        
        # Load initial configuration
        self.load_config()
    
    def load_config(self) -> MatchingConfig:
        """
        Load and validate configuration from file.
        
        Returns:
            MatchingConfig object with validated parameters
            
        Validates Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
        """
        try:
            # Load configuration file
            if not os.path.exists(self.config_path):
                logger.warning(f"Config file not found: {self.config_path}, using defaults")
                self.config_data = self._get_default_config()
            else:
                with open(self.config_path, 'r') as f:
                    if self.config_path.endswith('.json'):
                        self.config_data = json.load(f)
                    else:  # YAML
                        self.config_data = yaml.safe_load(f)
                
                logger.info(f"Loaded configuration from {self.config_path}")
            
            # Extract matching configuration
            matching_section = self.config_data.get('matching', {})
            weights = matching_section.get('weights', {})
            thresholds = matching_section.get('thresholds', {})
            algorithm = matching_section.get('algorithm', {})
            
            # Get weights with defaults
            weight_amount = weights.get('amount', 0.4)
            weight_date = weights.get('date', 0.3)
            weight_semantic = weights.get('semantic', 0.3)
            
            # Validate and normalize weights (Requirement 12.2, 12.3)
            normalized_weights = self.validate_and_normalize_weights({
                'amount': weight_amount,
                'date': weight_date,
                'semantic': weight_semantic
            })
            
            # Create MatchingConfig
            self.matching_config = MatchingConfig(
                weight_amount=normalized_weights['amount'],
                weight_date=normalized_weights['date'],
                weight_semantic=normalized_weights['semantic'],
                amount_tolerance=Decimal(str(thresholds.get('amount_tolerance', 1.00))),
                date_variance=thresholds.get('date_variance', 3),
                exact_threshold=thresholds.get('exact_match', 0.98),
                high_threshold=thresholds.get('high_confidence', 0.85),
                lambda_decay=algorithm.get('lambda_decay', 2.0)
            )
            
            logger.info(f"Configuration loaded successfully: weights={normalized_weights}")
            return self.matching_config
            
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            logger.warning("Using default configuration")
            self.config_data = self._get_default_config()
            return self.load_config()
    
    def validate_and_normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """
        Validate that weights sum to 1.0, normalize if needed.
        
        Args:
            weights: Dictionary with 'amount', 'date', 'semantic' keys
            
        Returns:
            Normalized weights dictionary
            
        Validates Requirements: 12.2, 12.3
        """
        total = weights['amount'] + weights['date'] + weights['semantic']
        
        # Check if weights sum to 1.0 (within tolerance)
        if abs(total - 1.0) < 0.001:
            return weights
        
        # Normalize proportionally
        if total == 0:
            logger.error("All weights are zero, using equal weights")
            return {'amount': 1/3, 'date': 1/3, 'semantic': 1/3}
        
        normalized = {
            'amount': weights['amount'] / total,
            'date': weights['date'] / total,
            'semantic': weights['semantic'] / total
        }
        
        logger.warning(f"Weights normalized from {weights} to {normalized}")
        return normalized
    
    def reload_config(self):
        """
        Reload configuration and notify observers.
        
        Validates Requirement: 12.7
        """
        logger.info("Reloading configuration...")
        old_config = self.matching_config
        new_config = self.load_config()
        
        # Notify observers of configuration change
        for observer in self.observers:
            try:
                observer(old_config, new_config)
            except Exception as e:
                logger.error(f"Error notifying observer: {e}")
    
    def watch_config_file(self):
        """
        Watch configuration file for changes and auto-reload.
        
        Validates Requirement: 12.7
        """
        if self.file_observer is not None:
            logger.warning("Config file watcher already running")
            return
        
        config_dir = os.path.dirname(os.path.abspath(self.config_path))
        
        event_handler = ConfigFileHandler(self.config_path, self.reload_config)
        self.file_observer = Observer()
        self.file_observer.schedule(event_handler, config_dir, recursive=False)
        self.file_observer.start()
        
        logger.info(f"Started watching config file: {self.config_path}")
    
    def stop_watching(self):
        """Stop watching configuration file."""
        if self.file_observer is not None:
            self.file_observer.stop()
            self.file_observer.join()
            self.file_observer = None
            logger.info("Stopped watching config file")
    
    def register_observer(self, callback: Callable):
        """
        Register callback for configuration changes.
        
        Args:
            callback: Function to call when configuration changes.
                     Signature: callback(old_config, new_config)
        """
        self.observers.append(callback)
        logger.debug(f"Registered configuration observer: {callback.__name__}")
    
    def get_config_value(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key path.
        
        Args:
            key_path: Dot-separated path (e.g., 'deepseek.timeout')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        keys = key_path.split('.')
        value = self.config_data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        
        return value
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            'matching': {
                'weights': {
                    'amount': 0.4,
                    'date': 0.3,
                    'semantic': 0.3
                },
                'thresholds': {
                    'amount_tolerance': 1.00,
                    'date_variance': 3,
                    'exact_match': 0.98,
                    'high_confidence': 0.85
                },
                'algorithm': {
                    'lambda_decay': 2.0
                }
            },
            'financial_filter': {
                'enable_ai': True,
                'financial_keywords': [
                    'receipt', 'invoice', 'bill', 'payment', 'transaction',
                    'order confirmation', 'purchase', 'statement', 'total amount',
                    'amount due', 'payment received', 'order #', 'invoice #',
                    'account statement', 'payment confirmation'
                ],
                'marketing_spam_keywords': [
                    'unsubscribe', 'newsletter', 'discount', 'sale', 'offer',
                    'limited time', 'subscribe', 'click here', 'job offer',
                    'resume', 'meeting', 'promotion', 'deal', 'coupon',
                    'free shipping', '% off'
                ],
                'target_rule_based_percentage': 0.80
            },
            'deepseek': {
                'api_key': os.getenv('DEEPSEEK_API_KEY', ''),
                'timeout': 30,
                'max_tokens': 512
            },
            'parallelism': {
                'thread_pool_size': 50,
                'process_pool_size': 10
            },
            'database': {
                'path': 'finmatcher.db',
                'wal_mode': True
            },
            'checkpoints': {
                'interval': 1000
            },
            'memory': {
                'chunk_size': 1000,
                'warning_threshold': 0.80,
                'pause_threshold': 0.90
            },
            'logging': {
                'level': 'INFO',
                'max_file_size': 104857600,  # 100MB
                'retention_days': 90,
                'sanitize_pii': True
            },
            'drive': {
                'credentials_path': 'finmatcher/auth_files/credentials.json',
                'root_folder': 'FinMatcher_Excel_Reports'
            }
        }
