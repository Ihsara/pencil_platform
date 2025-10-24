"""
Hierarchical configuration loader with inheritance.

Implements base + override pattern:
1. Look for config in experiment directory
2. If not found, check base_config
3. Merge configurations if both exist
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from loguru import logger


class ConfigLoader:
    """Load configurations with inheritance support.
    
    Features:
    - Hierarchical configuration loading (base + override pattern)
    - Circular dependency detection
    - Deep merging of dictionaries (lists are replaced, not merged)
    - Caching for performance
    - UTF-8 encoding support
    """
    
    def __init__(self, experiment_name: str, config_root: Path):
        """
        Args:
            experiment_name: Name of experiment (e.g., 'shocktube_phase1')
            config_root: Root config directory (usually DIRS.config)
        """
        self.experiment_name = experiment_name
        self.config_root = config_root
        self.experiment_dir = config_root / experiment_name
        self.base_dir = None
        self.cache = {}
        self._inheritance_chain = []  # Track inheritance to detect circular dependencies
        
        if not self.experiment_dir.exists():
            raise FileNotFoundError(
                f"Experiment directory not found: {self.experiment_dir}"
            )
    
    def load_analysis_config(self) -> Dict:
        """Load main analysis configuration."""
        return self._load_config('analysis_config.yaml')
    
    def load_unit_system(self, filename: str = 'unit_system.yaml') -> Dict:
        """Load unit system configuration."""
        return self._load_config(filename)
    
    def load_analytical_config(self, filename: str = 'analytical.yaml') -> Dict:
        """Load analytical solution configuration."""
        return self._load_config(filename)
    
    def _load_config(self, filename: str) -> Dict:
        """
        Load a config file with inheritance.
        
        Resolution order:
        1. Check experiment directory
        2. If has base_config and file not in experiment dir, check base
        3. Merge if needed
        """
        # Check cache
        cache_key = f"{self.experiment_name}/{filename}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Try experiment directory first
        experiment_file = self.experiment_dir / filename
        
        # Load base_config reference if not already loaded
        if self.base_dir is None:
            self._resolve_base_dir()
        
        # Determine which files exist
        has_experiment_file = experiment_file.exists()
        has_base_file = False
        
        if self.base_dir is not None:
            base_file = self.base_dir / filename
            has_base_file = base_file.exists()
        
        # Load and merge
        config = {}
        
        if has_base_file:
            logger.debug(f"Loading base config: {base_file}")
            with open(base_file, encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
        
        if has_experiment_file:
            logger.debug(f"Loading experiment config: {experiment_file}")
            with open(experiment_file, encoding='utf-8') as f:
                experiment_config = yaml.safe_load(f) or {}
            
            # Merge (experiment overrides base)
            config = self._deep_merge(config, experiment_config)
            logger.info(f"Using experiment override: {filename}")
        elif has_base_file:
            logger.info(f"Using base config: {filename}")
        else:
            raise FileNotFoundError(
                f"Config file '{filename}' not found in experiment "
                f"'{self.experiment_name}' or its base"
            )
        
        # Cache and return
        self.cache[cache_key] = config
        return config
    
    def _resolve_base_dir(self):
        """Determine base configuration directory with circular dependency detection."""
        # Check for circular dependencies
        if self.experiment_name in self._inheritance_chain:
            chain_str = ' -> '.join(self._inheritance_chain + [self.experiment_name])
            raise ValueError(
                f"Circular dependency detected in configuration inheritance: {chain_str}"
            )
        
        # Add current experiment to inheritance chain
        self._inheritance_chain.append(self.experiment_name)
        
        # Load analysis_config to check for base_config
        analysis_file = self.experiment_dir / 'analysis_config.yaml'
        
        if not analysis_file.exists():
            logger.debug(f"No analysis_config.yaml in {self.experiment_name}")
            return
        
        with open(analysis_file, encoding='utf-8') as f:
            analysis_config = yaml.safe_load(f)
        
        base_config_name = analysis_config.get('base_config') if analysis_config else None
        
        if base_config_name:
            # Check if base would create circular dependency
            if base_config_name in self._inheritance_chain:
                chain_str = ' -> '.join(self._inheritance_chain + [base_config_name])
                raise ValueError(
                    f"Circular dependency detected: {chain_str}. "
                    f"'{base_config_name}' is already in the inheritance chain."
                )
            
            self.base_dir = self.config_root / base_config_name
            if not self.base_dir.exists():
                logger.warning(f"Base config directory not found: {self.base_dir}")
                self.base_dir = None
            else:
                logger.info(f"Base config: {base_config_name}")
                logger.debug(f"Inheritance chain: {' -> '.join(self._inheritance_chain + [base_config_name])}")
                
                # Recursively check the base's base to detect indirect circular dependencies
                self._check_base_chain(base_config_name)
        else:
            logger.debug(f"No base_config specified for {self.experiment_name}")
    
    def _check_base_chain(self, config_name: str):
        """Recursively check base configuration chain for circular dependencies."""
        config_dir = self.config_root / config_name
        analysis_file = config_dir / 'analysis_config.yaml'
        
        if not analysis_file.exists():
            return
        
        with open(analysis_file, encoding='utf-8') as f:
            analysis_config = yaml.safe_load(f)
        
        base_config_name = analysis_config.get('base_config') if analysis_config else None
        
        if base_config_name:
            # Check if this base would create a circular dependency
            if base_config_name in self._inheritance_chain:
                chain_str = ' -> '.join(self._inheritance_chain + [base_config_name])
                raise ValueError(
                    f"Circular dependency detected: {chain_str}. "
                    f"'{base_config_name}' is already in the inheritance chain."
                )
            
            # Add to chain and continue checking
            self._inheritance_chain.append(base_config_name)
            logger.debug(f"Checking base chain: {' -> '.join(self._inheritance_chain)}")
            
            # Recursively check the next level
            self._check_base_chain(base_config_name)
    
    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries.
        
        override values take precedence over base.
        Lists are replaced, not merged.
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursive merge for nested dicts
                result[key] = self._deep_merge(result[key], value)
            else:
                # Override (including lists)
                result[key] = value
        
        return result


def create_config_loader(experiment_name: str, config_root: Path) -> ConfigLoader:
    """Factory to create ConfigLoader."""
    return ConfigLoader(experiment_name, config_root)
