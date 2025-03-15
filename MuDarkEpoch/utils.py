"""
Dark Epoch Bot - Utility Functions
Various utility functions for the Dark Epoch bot.
"""

import os
import time
import random
import math
import logging
import platform
from datetime import datetime

# Koşullu olarak grafik kütüphanelerini içe aktar
try:
    import pyautogui
    HAS_GUI_SUPPORT = True
except ImportError:
    HAS_GUI_SUPPORT = False

# Loglama yapılandırması
logger = logging.getLogger('DarkEpochBot.Utils')

def safe_wait(min_seconds, max_seconds=None):
    """
    Wait for a random amount of time within the given range.
    Helps avoid detection by adding human-like randomness.
    
    Args:
        min_seconds: Minimum seconds to wait
        max_seconds: Maximum seconds to wait (if None, use min_seconds)
    """
    if max_seconds is None:
        max_seconds = min_seconds
        
    wait_time = min_seconds + (random.random() * (max_seconds - min_seconds))
    time.sleep(wait_time)
    return wait_time

def calculate_distance(point1, point2):
    """
    Calculate Euclidean distance between two points.
    
    Args:
        point1: (x, y) coordinates of first point
        point2: (x, y) coordinates of second point
        
    Returns:
        float: Distance between the points
    """
    return math.sqrt((point2[0] - point1[0])**2 + (point2[1] - point1[1])**2)

def get_screen_dimensions():
    """
    Get the screen dimensions.
    
    Returns:
        tuple: (width, height) of screen
    """
    if not HAS_GUI_SUPPORT:
        logger.warning("Cannot get screen dimensions: GUI support not available")
        return (1920, 1080)  # Varsayılan boyut
        
    try:
        return pyautogui.size()
    except Exception as e:
        logger.error(f"Error getting screen dimensions: {str(e)}")
        return (1920, 1080)  # Hata durumunda varsayılan boyut

def is_valid_click_position(x, y):
    """
    Check if a position is valid for clicking.
    
    Args:
        x: X coordinate
        y: Y coordinate
        
    Returns:
        bool: True if position is valid, False otherwise
    """
    if not HAS_GUI_SUPPORT:
        return True
        
    try:
        screen_width, screen_height = pyautogui.size()
        return 0 <= x < screen_width and 0 <= y < screen_height
    except Exception as e:
        logger.error(f"Error checking click position: {str(e)}")
        return False

def random_offset(x, y, max_offset=5):
    """
    Add a small random offset to coordinates.
    Makes clicking patterns more human-like.
    
    Args:
        x: X coordinate
        y: Y coordinate
        max_offset: Maximum pixel offset
        
    Returns:
        tuple: (new_x, new_y) with random offset applied
    """
    offset_x = random.randint(-max_offset, max_offset)
    offset_y = random.randint(-max_offset, max_offset)
    
    return (x + offset_x, y + offset_y)

def save_screenshot(filename=None):
    """
    Save a screenshot with optional filename.
    
    Args:
        filename: Optional filename (if None, generate based on timestamp)
        
    Returns:
        str: Path to saved screenshot
    """
    if not HAS_GUI_SUPPORT:
        logger.warning("Cannot save screenshot: GUI support not available")
        return None
        
    try:
        # Screenshots dizinini oluştur (yoksa)
        screenshots_dir = "screenshots"
        if not os.path.exists(screenshots_dir):
            os.makedirs(screenshots_dir)
        
        # Dosya adı oluştur
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
        
        # Tam dosya yolu
        filepath = os.path.join(screenshots_dir, filename)
        
        # Ekran görüntüsü al ve kaydet
        screenshot = pyautogui.screenshot()
        screenshot.save(filepath)
        
        logger.info(f"Screenshot saved to {filepath}")
        return filepath
        
    except Exception as e:
        logger.error(f"Error saving screenshot: {str(e)}")
        return None

def human_like_movement(start_x, start_y, end_x, end_y, duration=None):
    """
    Move mouse in a more human-like pattern.
    
    Args:
        start_x: Starting X coordinate
        start_y: Starting Y coordinate
        end_x: Ending X coordinate
        end_y: Ending Y coordinate
        duration: Optional duration of movement (if None, calculate based on distance)
        
    Returns:
        tuple: Final (x, y) position
    """
    if not HAS_GUI_SUPPORT:
        logger.debug(f"Simulated human-like movement from ({start_x}, {start_y}) to ({end_x}, {end_y})")
        return (end_x, end_y)
        
    try:
        # Mesafeye göre süre hesapla (varsayılan)
        if duration is None:
            distance = calculate_distance((start_x, start_y), (end_x, end_y))
            duration = 0.1 + (distance / 2000)  # Mesafeye dayalı süre (deneysel)
        
        # İnsan benzeri hareket için eğri oluştur
        # Basit bir bezier eğrisi kullanabilir ya da PyAutoGUI'nin easeInOutQuad gibi
        # mevcut fonksiyonlarını kullanabilirsiniz
        pyautogui.moveTo(end_x, end_y, duration=duration, tween=pyautogui.easeInOutQuad)
        
        return (end_x, end_y)
        
    except Exception as e:
        logger.error(f"Error during human-like movement: {str(e)}")
        return (end_x, end_y)

def is_replit():
    """
    Check if the environment is Replit.
    
    Returns:
        bool: True if running on Replit, False otherwise
    """
    return os.environ.get('REPL_ID') is not None

def is_windows():
    """
    Check if the environment is Windows.
    
    Returns:
        bool: True if running on Windows, False otherwise
    """
    return platform.system() == "Windows"