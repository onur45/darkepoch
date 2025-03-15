"""
Dark Epoch Bot - Image Recognition
Handles screen recognition and analysis for the Dark Epoch game.
"""

import os
import time
import logging
import platform

# Koşullu olarak OpenCV ve numpy'ı içe aktar
try:
    import cv2
    import numpy as np
    import pyautogui
    HAS_GUI_SUPPORT = True
except ImportError:
    HAS_GUI_SUPPORT = False
    # Dummy NumPy
    class DummyNP:
        def array(self, *args, **kwargs):
            return None
    np = DummyNP()

# Loglama yapılandırması
logger = logging.getLogger('DarkEpochBot.ImageRecognition')

class ImageRecognition:
    def __init__(self):
        """Initialize the Image Recognition module"""
        self.reference_images = {}
        self.screen_cache = None
        self.screen_timestamp = 0
        self.confidence_threshold = 0.7  # Varsayılan eşik değeri
        
        # Referans resimleri yükle
        if HAS_GUI_SUPPORT:
            self._load_reference_images()
        else:
            logger.warning("GUI support not available - image recognition will be simulated")
    
    def _load_reference_images(self):
        """Load reference images from the reference_images directory"""
        ref_dir = "reference_images"
        
        if not os.path.exists(ref_dir):
            os.makedirs(ref_dir)
            logger.info(f"Created reference images directory: {ref_dir}")
            return
        
        loaded = 0
        for filename in os.listdir(ref_dir):
            if filename.endswith(('.png', '.jpg', '.jpeg')):
                try:
                    img_path = os.path.join(ref_dir, filename)
                    img = cv2.imread(img_path)
                    
                    if img is None:
                        logger.warning(f"Failed to load reference image: {filename}")
                        continue
                    
                    # Dosya adından referans adını çıkar
                    name = os.path.splitext(filename)[0]
                    self.reference_images[name] = img
                    loaded += 1
                except Exception as e:
                    logger.error(f"Error loading reference image {filename}: {str(e)}")
        
        logger.info(f"Loaded {loaded} reference images")
    
    def capture_reference_image(self, name, region=None):
        """
        Capture a reference image for future matching.
        
        Args:
            name: Name of the reference image
            region: Optional region to capture (left, top, width, height)
            
        Returns:
            bool: True if capture successful, False otherwise
        """
        if not HAS_GUI_SUPPORT:
            logger.warning("Cannot capture reference image: GUI support not available")
            return False
        
        try:
            # Ekran görüntüsü al
            if region is None:
                screenshot = pyautogui.screenshot()
            else:
                screenshot = pyautogui.screenshot(region=region)
            
            # OpenCV formatına çevir
            img = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            
            # Referans resimleri dizinini kontrol et
            ref_dir = "reference_images"
            if not os.path.exists(ref_dir):
                os.makedirs(ref_dir)
            
            # Resmi kaydet
            img_path = os.path.join(ref_dir, f"{name}.png")
            cv2.imwrite(img_path, img)
            
            # Referans resmi sözlüğüne ekle
            self.reference_images[name] = img
            
            logger.info(f"Captured reference image: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Error capturing reference image: {str(e)}")
            return False
    
    def get_screen(self, force_refresh=False):
        """
        Get the current screen as a numpy array.
        Uses caching to avoid excessive screenshots.
        
        Args:
            force_refresh: Force taking a new screenshot
            
        Returns:
            numpy.ndarray: Screenshot as a numpy array in BGR format
        """
        if not HAS_GUI_SUPPORT:
            return None
        
        current_time = time.time()
        
        # Önbelleğe alınmış ekran görüntüsü varsa ve yeterince yeniyse kullan
        if (not force_refresh and 
            self.screen_cache is not None and 
            current_time - self.screen_timestamp < 0.5):
            return self.screen_cache
        
        try:
            # Yeni ekran görüntüsü al
            screenshot = pyautogui.screenshot()
            
            # OpenCV formatına çevir
            self.screen_cache = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
            self.screen_timestamp = current_time
            
            return self.screen_cache
            
        except Exception as e:
            logger.error(f"Error capturing screenshot: {str(e)}")
            return None
    
    def find_template(self, template_name, threshold=None, screen=None):
        """
        Find a template image on the screen.
        
        Args:
            template_name: Name of the template to find
            threshold: Confidence threshold (0-1)
            screen: Optional screen image to use instead of capturing
            
        Returns:
            tuple: (x, y) position of the center of the template if found, None otherwise
        """
        if not HAS_GUI_SUPPORT:
            # Simüle edilmiş davranış - Eğitim için rastgele pozitif veya negatif sonuç
            import random
            if random.random() > 0.5:
                return (random.randint(100, 900), random.randint(100, 700))
            return None
        
        if threshold is None:
            threshold = self.confidence_threshold
        
        # Şablon kontrol et
        if template_name not in self.reference_images:
            logger.warning(f"Template '{template_name}' not found in reference images")
            return None
        
        template = self.reference_images[template_name]
        
        # Ekran görüntüsü al
        if screen is None:
            screen = self.get_screen()
        
        if screen is None:
            logger.error("Failed to capture screen")
            return None
        
        # Şablon eşleştirme yap
        try:
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val >= threshold:
                # Merkez noktayı hesapla
                h, w = template.shape[:2]
                center_x = max_loc[0] + w//2
                center_y = max_loc[1] + h//2
                
                logger.debug(f"Found template '{template_name}' at ({center_x}, {center_y}) with confidence {max_val:.2f}")
                return (center_x, center_y)
            else:
                logger.debug(f"Template '{template_name}' not found (max confidence: {max_val:.2f}, threshold: {threshold:.2f})")
                return None
                
        except Exception as e:
            logger.error(f"Error finding template '{template_name}': {str(e)}")
            return None
    
    def find_all_templates(self, template_name, threshold=None, screen=None, limit=10):
        """
        Find all occurrences of a template on the screen.
        
        Args:
            template_name: Name of the template to find
            threshold: Confidence threshold (0-1)
            screen: Optional screen image to use instead of capturing
            limit: Maximum number of matches to return
            
        Returns:
            list: List of (x, y) positions of the centers of matched templates
        """
        if not HAS_GUI_SUPPORT:
            # Simüle edilmiş davranış - Eğitim için rastgele sonuçlar
            import random
            count = random.randint(0, 5)
            return [(random.randint(100, 900), random.randint(100, 700)) for _ in range(count)]
        
        if threshold is None:
            threshold = self.confidence_threshold
        
        # Şablon kontrol et
        if template_name not in self.reference_images:
            logger.warning(f"Template '{template_name}' not found in reference images")
            return []
        
        template = self.reference_images[template_name]
        
        # Ekran görüntüsü al
        if screen is None:
            screen = self.get_screen()
        
        if screen is None:
            logger.error("Failed to capture screen")
            return []
        
        # Şablon eşleştirme yap
        try:
            result = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
            h, w = template.shape[:2]
            
            # Eşik değeriyle eşleşen konumları bul
            locations = np.where(result >= threshold)
            points = list(zip(*locations[::-1]))
            
            # Çok yakın eşleşmeleri filtrele
            filtered_points = []
            
            for point in points:
                # Merkez noktayı hesapla
                center_x = point[0] + w//2
                center_y = point[1] + h//2
                
                # Yakın noktaları kontrol et
                too_close = False
                for existing_point in filtered_points:
                    dist_x = abs(center_x - existing_point[0])
                    dist_y = abs(center_y - existing_point[1])
                    
                    if dist_x < w//2 and dist_y < h//2:
                        too_close = True
                        break
                
                if not too_close:
                    filtered_points.append((center_x, center_y))
                    
                    # Limit kontrolü
                    if len(filtered_points) >= limit:
                        break
            
            logger.debug(f"Found {len(filtered_points)} instances of template '{template_name}'")
            return filtered_points
                
        except Exception as e:
            logger.error(f"Error finding templates '{template_name}': {str(e)}")
            return []
    
    def detect_login_screen(self, screen=None):
        """
        Detect if the current screen is the login screen.
        
        Args:
            screen: Optional screen image to use instead of capturing
            
        Returns:
            bool: True if login screen detected
        """
        # Login button'u ara
        login_pos = self.find_template("login_button", screen=screen)
        return login_pos is not None
    
    def detect_main_menu(self, screen=None):
        """
        Detect if the current screen is the main menu.
        
        Args:
            screen: Optional screen image to use instead of capturing
            
        Returns:
            bool: True if main menu detected
        """
        # Play button'u ara
        play_pos = self.find_template("play_button", screen=screen)
        return play_pos is not None
    
    def detect_in_game(self, screen=None):
        """
        Detect if the current screen is in-game.
        
        Args:
            screen: Optional screen image to use instead of capturing
            
        Returns:
            bool: True if in-game detected
        """
        # Sağlık/mana barı gibi in-game UI elementlerini ara
        health_bar = self.find_template("health_bar", screen=screen)
        
        if health_bar is not None:
            return True
            
        # Alternatif UI elementleri
        for ui_element in ["minimap", "inventory_button", "character_button"]:
            if self.find_template(ui_element, screen=screen) is not None:
                return True
        
        return False
    
    def detect_low_health(self, screen=None):
        """
        Detect if health is low.
        
        Args:
            screen: Optional screen image to use instead of capturing
            
        Returns:
            bool: True if low health detected
        """
        # Düşük sağlık göstergesini ara
        return self.find_template("low_health", screen=screen) is not None
    
    def detect_full_inventory(self, screen=None):
        """
        Detect if inventory is full.
        
        Args:
            screen: Optional screen image to use instead of capturing
            
        Returns:
            bool: True if full inventory detected
        """
        # Dolu envanter göstergesini ara
        return self.find_template("inventory_full", screen=screen) is not None
    
    # Özel element bulma metodları
    def find_login_button(self, screen=None):
        """Find login button on screen"""
        return self.find_template("login_button", screen=screen)
    
    def find_play_button(self, screen=None):
        """Find play button on screen"""
        return self.find_template("play_button", screen=screen)
    
    def find_resource_nodes(self, screen=None, limit=5):
        """Find resource nodes on screen"""
        all_nodes = []
        
        # Farklı kaynak türlerini ara
        for resource_type in ["ore_node", "herb_node", "wood_node"]:
            nodes = self.find_all_templates(resource_type, screen=screen, limit=limit)
            all_nodes.extend(nodes)
        
        # Limit'e göre filtrele
        return all_nodes[:limit]
    
    def find_enemies(self, screen=None, limit=3):
        """Find enemies on screen"""
        all_enemies = []
        
        # Farklı düşman türlerini ara
        for enemy_type in ["enemy_wolf", "enemy_boar", "enemy_bandit"]:
            enemies = self.find_all_templates(enemy_type, screen=screen, limit=limit)
            all_enemies.extend(enemies)
        
        # Limit'e göre filtrele
        return all_enemies[:limit]
    
    def find_mission_objectives(self, screen=None):
        """Find mission objectives on screen"""
        return self.find_all_templates("mission_objective", screen=screen)
    
    def find_mission_panel(self, screen=None):
        """Find mission panel button on screen"""
        return self.find_template("mission_panel", screen=screen)
    
    def find_upgrade_indicators(self, screen=None):
        """Find upgrade indicators on screen"""
        return self.find_all_templates("upgrade_indicator", screen=screen)
    
    def find_confirm_button(self, screen=None):
        """Find confirm button on screen"""
        return self.find_template("confirm_button", screen=screen)