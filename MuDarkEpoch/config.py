"""
Dark Epoch Bot - Configuration
Loads and validates configuration for the Dark Epoch bot.
"""

import os
import json
import logging
import platform
from datetime import datetime

# Loglama yapılandırması
logger = logging.getLogger('DarkEpochBot.Config')

# Varsayılan konfigürasyon
DEFAULT_CONFIG = {
    "client_window_titles": ["game", "LDPlayer"],
    "confidence_threshold": 0.7,
    "click_delay_min": 0.2,
    "click_delay_max": 0.5,
    "cycle_delay_min": 1.0,
    "cycle_delay_max": 3.0,
    "error_threshold": 5,
    "web_api_url": "http://localhost:5000",
    "api_key": "",
    "reference_images_dir": "reference_images",
    "screenshots_dir": "screenshots",
    "logs_dir": "logs"
}

def load_config(config_path="config.json"):
    """
    Load configuration from file, or create default if it doesn't exist.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        dict: Configuration dictionary
    """
    # Veritabanından konfigürasyonu al (Replit ortamında)
    if is_replit():
        try:
            from app import BotConfig, db
            
            # Veritabanına bağlan
            with db.session.begin():
                configs = BotConfig.query.all()
                
                if configs:
                    # Konfigürasyonu oluştur
                    config = {}
                    for cfg in configs:
                        config[cfg.key] = cfg.get_value()
                    
                    logger.info(f"Configuration loaded from database: {len(config)} entries")
                    return config
                else:
                    logger.warning("No configuration found in database, using defaults")
        except Exception as e:
            logger.error(f"Error loading configuration from database: {str(e)}")
    
    # Dosyadan konfigürasyonu yükle
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            logger.info(f"Configuration loaded from {config_path}")
            
            # Varsayılan değerleri ekle
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            
            return config
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {str(e)}")
    
    # Konfigürasyon dosyası yoksa varsayılan oluştur ve kaydet
    logger.info(f"Creating default configuration file at {config_path}")
    save_config(DEFAULT_CONFIG, config_path)
    
    return DEFAULT_CONFIG.copy()

def save_config(config, config_path="config.json"):
    """
    Save configuration to file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to configuration file
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Replit veritabanı modu
    if is_replit():
        try:
            from app import BotConfig, db
            
            # Veritabanına kaydet
            with db.session.begin():
                for key, value in config.items():
                    # Mevcut konfigürasyon var mı kontrol et
                    cfg = BotConfig.query.filter_by(key=key).first()
                    
                    if cfg:
                        # Mevcut konfigürasyonu güncelle
                        cfg.value = str(value) if not isinstance(value, str) else value
                        if isinstance(value, bool):
                            cfg.value_type = "bool"
                        elif isinstance(value, int):
                            cfg.value_type = "int"
                        elif isinstance(value, float):
                            cfg.value_type = "float"
                        elif isinstance(value, (list, dict)):
                            cfg.value_type = "json"
                            cfg.value = json.dumps(value)
                        else:
                            cfg.value_type = "string"
                    else:
                        # Yeni konfigürasyon oluştur
                        value_type = "string"
                        value_str = str(value)
                        
                        if isinstance(value, bool):
                            value_type = "bool"
                        elif isinstance(value, int):
                            value_type = "int"
                        elif isinstance(value, float):
                            value_type = "float"
                        elif isinstance(value, (list, dict)):
                            value_type = "json"
                            value_str = json.dumps(value)
                        
                        cfg = BotConfig(
                            key=key,
                            value=value_str,
                            value_type=value_type,
                            description=f"Configuration value for {key}"
                        )
                        db.session.add(cfg)
            
            logger.info(f"Configuration saved to database: {len(config)} entries")
            return True
        except Exception as e:
            logger.error(f"Error saving configuration to database: {str(e)}")
            return False
    
    # Dosyaya kaydet
    try:
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
        
        logger.info(f"Configuration saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration to {config_path}: {str(e)}")
        return False

def validate_config(config):
    """
    Validate configuration values.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        tuple: (is_valid, errors) - Boolean validity and list of errors
    """
    errors = []
    
    # Gerekli alanlar
    required_fields = [
        "client_window_titles",
        "confidence_threshold",
        "click_delay_min",
        "click_delay_max",
        "cycle_delay_min",
        "cycle_delay_max",
        "error_threshold"
    ]
    
    # Gerekli alanları kontrol et
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
    
    # Alan tiplerini ve değer aralıklarını kontrol et
    if "confidence_threshold" in config:
        if not isinstance(config["confidence_threshold"], (int, float)):
            errors.append("confidence_threshold must be a number")
        elif not (0 <= config["confidence_threshold"] <= 1):
            errors.append("confidence_threshold must be between 0 and 1")
    
    # Delay değerlerini kontrol et
    delay_pairs = [
        ("click_delay_min", "click_delay_max"),
        ("cycle_delay_min", "cycle_delay_max")
    ]
    
    for min_field, max_field in delay_pairs:
        if min_field in config and max_field in config:
            min_val = config[min_field]
            max_val = config[max_field]
            
            if not isinstance(min_val, (int, float)) or not isinstance(max_val, (int, float)):
                errors.append(f"{min_field} and {max_field} must be numbers")
            elif min_val < 0 or max_val < 0:
                errors.append(f"{min_field} and {max_field} must be positive")
            elif min_val > max_val:
                errors.append(f"{min_field} must be less than or equal to {max_field}")
    
    # client_window_titles'ı kontrol et
    if "client_window_titles" in config:
        if not isinstance(config["client_window_titles"], list):
            if isinstance(config["client_window_titles"], str):
                # JSON dizisi olabilir
                try:
                    titles = json.loads(config["client_window_titles"])
                    if not isinstance(titles, list):
                        errors.append("client_window_titles must be a list of strings")
                except json.JSONDecodeError:
                    errors.append("client_window_titles is not a valid JSON array")
            else:
                errors.append("client_window_titles must be a list of strings")
        elif len(config["client_window_titles"]) == 0:
            errors.append("client_window_titles cannot be empty")
    
    # error_threshold kontrol et
    if "error_threshold" in config:
        if not isinstance(config["error_threshold"], int):
            errors.append("error_threshold must be an integer")
        elif config["error_threshold"] < 1:
            errors.append("error_threshold must be at least 1")
    
    is_valid = len(errors) == 0
    return (is_valid, errors)

def is_replit():
    """
    Check if running on Replit.
    
    Returns:
        bool: True if running on Replit, False otherwise
    """
    return os.environ.get('REPL_ID') is not None