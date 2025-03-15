"""
Dark Epoch Bot - Core Bot Logic
Koşullu içe aktarma ile hem Replit hem de Windows'ta çalışabilir.
"""

import os
import time
import logging
import json
import threading
import platform

# Koşullu modül içe aktarma
try:
    import pyautogui
    from client_manager import ClientManager
    from image_recognition import ImageRecognition
    from utils import safe_wait, calculate_distance, random_offset
    HAS_GUI_SUPPORT = True
except ImportError:
    HAS_GUI_SUPPORT = False
    # Simüle edilmiş sınıflar ve işlevler oluştur
    class DummyClientManager:
        def __init__(self, *args, **kwargs):
            self.active_clients = []
            self.found_windows = []
            self.processes = []
            self.client_tasks = {}
            self.use_process_management = False
            self.max_client_processes = 2
            
        def scan_for_clients(self):
            return []
            
        def get_active_clients(self):
            return []
            
        def focus_client(self, *args):
            pass
            
        def get_client_rect(self, *args):
            return (0, 0, 800, 600)
            
        def get_client_center(self, *args):
            return (400, 300)
            
        def arrange_clients(self):
            pass
            
        def capture_client_screenshot(self, *args):
            return None
            
        def start_client_process(self):
            return False
            
        def stop_client_process(self, *args):
            return False
            
        def get_process_info(self):
            return []
            
        def check_client_processes(self):
            return 0
            
        def assign_task_to_client(self, client, task):
            # Burada bir şekilde görev kaydı tutulabilir
            client_id = "dummy_client" 
            self.client_tasks[client_id] = task
            return True
            
        def get_client_task(self, client):
            return self.client_tasks.get("dummy_client")
        
    class DummyImageRecognition:
        def __init__(self):
            pass
            
        def find_template(self, *args, **kwargs):
            return None
            
        def find_all_templates(self, *args, **kwargs):
            return []
            
        def detect_login_screen(self, *args):
            return False
            
        def detect_main_menu(self, *args):
            return False
            
        def detect_in_game(self, *args):
            return True  # Oyunda olduğunu varsay
            
        def detect_low_health(self, *args):
            return False
            
        def detect_full_inventory(self, *args):
            return False
            
        def find_login_button(self, *args):
            return None
            
        def find_play_button(self, *args):
            return None
            
        def find_resource_nodes(self, *args, **kwargs):
            # Rastgele kaynak düğümleri simüle et
            import random
            if random.random() > 0.3:  # %70 ihtimalle kaynak bul
                return [(random.randint(100, 700), random.randint(100, 500)) for _ in range(random.randint(1, 3))]
            return []
            
        def find_enemies(self, *args, **kwargs):
            return []
            
        def find_mission_objectives(self, *args):
            return None
            
        def find_mission_panel(self, *args):
            return None
            
        def find_upgrade_indicators(self, *args):
            return []
            
        def find_confirm_button(self, *args):
            return None
        
    def safe_wait(min_time, max_time=None):
        """Dummy safe_wait function"""
        time.sleep(0.1)
        
    def calculate_distance(p1, p2):
        """Dummy distance calculation"""
        return 0
        
    def random_offset(x, y, max_offset=5):
        """Dummy random offset"""
        return x, y

# Loglama yapılandırması
logger = logging.getLogger('DarkEpochBot.Core')

class DarkEpochBot:
    def __init__(self, config):
        """
        Initialize the Dark Epoch Bot with the given configuration.
        
        Args:
            config (dict): Configuration dictionary for the bot
        """
        self.config = config
        self.running = False
        self.paused = False
        self.error_count = 0
        self.current_task = None
        
        # Koşullu olarak bileşenleri başlat
        if HAS_GUI_SUPPORT:
            self.client_manager = ClientManager(config)
            self.image_recognition = ImageRecognition()
        else:
            self.client_manager = DummyClientManager(config)
            self.image_recognition = DummyImageRecognition()
        
        # Bot thread'i
        self.bot_thread = None
        
        logger.info("Dark Epoch Bot initialized")
    
    def is_supported(self):
        """Sistemin botu destekleyip desteklemediğini kontrol et"""
        return HAS_GUI_SUPPORT and platform.system() == "Windows"
    
    def start(self):
        """Start the bot operation"""
        if self.running:
            logger.warning("Bot already running")
            return False
        
        if not self.is_supported():
            logger.error("Bot not supported on this platform")
            return False
        
        self.running = True
        self.paused = False
        
        # Bot thread'ini başlat
        self.bot_thread = threading.Thread(target=self._bot_loop)
        self.bot_thread.daemon = True
        self.bot_thread.start()
        
        logger.info("Bot started")
        return True
    
    def stop(self):
        """Stop the bot operation"""
        if not self.running:
            logger.warning("Bot already stopped")
            return False
        
        self.running = False
        self.paused = False
        
        # Thread'in durmasını bekle
        if self.bot_thread and self.bot_thread.is_alive():
            self.bot_thread.join(timeout=5.0)
        
        logger.info("Bot stopped")
        return True
    
    def pause(self):
        """Pause the bot operation"""
        if not self.running:
            logger.warning("Cannot pause: Bot not running")
            return False
        
        if self.paused:
            logger.warning("Bot already paused")
            return False
        
        self.paused = True
        logger.info("Bot paused")
        return True
    
    def resume(self):
        """Resume the bot operation"""
        if not self.running:
            logger.warning("Cannot resume: Bot not running")
            return False
        
        if not self.paused:
            logger.warning("Bot not paused")
            return False
        
        self.paused = False
        logger.info("Bot resumed")
        return True
    
    def _bot_loop(self):
        """Main bot loop"""
        while self.running:
            try:
                if not self.paused:
                    self.run_cycle()
                
                # Döngü gecikmesi
                safe_wait(
                    float(self.config.get('cycle_delay_min', 1.0)),
                    float(self.config.get('cycle_delay_max', 3.0))
                )
            except Exception as e:
                logger.error(f"Error in bot loop: {str(e)}")
                self.error_count += 1
                
                # Hata eşiği aşılırsa botu durdur
                if self.error_count >= int(self.config.get('error_threshold', 5)):
                    logger.critical(f"Error threshold reached ({self.error_count}). Stopping bot.")
                    self.running = False
                    break
        
        logger.info("Bot loop exited")
    
    def run_cycle(self):
        """Run a single cycle of the bot operation"""
        if not HAS_GUI_SUPPORT:
            logger.warning("GUI support not available - simulating bot cycle")
            return
        
        logger.debug("Running bot cycle")
        
        # İstemci pencerelerini tara
        self.client_manager.scan_for_clients()
        
        # Aktif istemcileri al (en fazla 2 aktif istemci)
        active_clients = self.client_manager.get_active_clients()
        
        if not active_clients:
            logger.warning("No active clients found")
            self.error_count += 1
            return
        
        # Hata sayacını sıfırla
        self.error_count = 0
        
        # Her istemci için görevleri gerçekleştir
        for idx, client in enumerate(active_clients):
            try:
                self.client_manager.focus_client(client)
                self._perform_client_tasks(client, idx)
            except Exception as e:
                logger.error(f"Error while processing client {idx}: {str(e)}")
    
    def _perform_client_tasks(self, client, client_index):
        """
        Perform tasks for a specific client.
        
        Args:
            client: The client object/window
            client_index: Index of the client
        """
        # Ekran görüntüsü al
        screen = None  # self.image_recognition.get_screen()
        
        # Ekran durumunu tespit et
        if self.image_recognition.detect_login_screen(screen):
            logger.info(f"Client {client_index}: Login screen detected")
            self._handle_login(client)
        elif self.image_recognition.detect_main_menu(screen):
            logger.info(f"Client {client_index}: Main menu detected")
            self._handle_main_menu(client)
        elif self.image_recognition.detect_in_game(screen):
            logger.info(f"Client {client_index}: In-game detected")
            self._handle_in_game(client, client_index)
        else:
            logger.warning(f"Client {client_index}: Unknown screen state")
            self._handle_unknown_screen(client)
    
    def _handle_login(self, client):
        """Handle login screen"""
        # Login button'u bul ve tıkla
        login_pos = self.image_recognition.find_login_button()
        if login_pos:
            self._safe_click(*login_pos)
            logger.info("Clicked login button")
        else:
            logger.warning("Login button not found")
    
    def _handle_main_menu(self, client):
        """Handle main menu screen"""
        # Play button'u bul ve tıkla
        play_pos = self.image_recognition.find_play_button()
        if play_pos:
            self._safe_click(*play_pos)
            logger.info("Clicked play button")
        else:
            logger.warning("Play button not found")
    
    def _handle_in_game(self, client, client_index):
        """
        Handle in-game actions based on client index.
        Each client might have different tasks based on database task definitions.
        
        Args:
            client: Client object
            client_index: Index of client (0 or 1 for active clients)
        """
        # İstemciye atanmış görevi kontrol et
        client_task = self.client_manager.get_client_task(client)
        
        if client_task:
            # İstemciye özel görev var, onu çalıştır
            task_type = client_task.get('type', '')
            task_params = client_task.get('parameters', {})
            task_name = client_task.get('name', 'Unknown Task')
            
            self.current_task = task_name
            logger.info(f"Executing assigned task for client {client_index}: {task_name}")
            
            if task_type == 'resource_gathering':
                self._perform_resource_gathering(client, task_params)
            elif task_type == 'combat':
                self._perform_combat_actions(client, task_params)
            elif task_type == 'mission':
                self._perform_mission_tasks(client, task_params)
            else:
                logger.warning(f"Unknown task type: {task_type}")
                self._perform_character_maintenance(client)
        else:
            # Varsayılan görevler - client indexe göre
            if client_index == 0:
                # İlk istemci için görevler
                self.current_task = "Resource Gathering"
                logger.info(f"Executing default task for client {client_index}: Resource Gathering")
                self._perform_resource_gathering(client)
            elif client_index == 1:
                # İkinci istemci için görevler
                self.current_task = "Combat"
                logger.info(f"Executing default task for client {client_index}: Combat")
                self._perform_combat_actions(client)
            else:
                # Diğer istemciler için varsayılan görevler
                self.current_task = "Basic Maintenance"
                logger.info(f"Executing default task for client {client_index}: Basic Maintenance")
                self._perform_character_maintenance(client)
    
    def _handle_unknown_screen(self, client):
        """Handle unknown screen by trying common actions"""
        # ESC tuşuna bas
        if HAS_GUI_SUPPORT:
            pyautogui.press('esc')
            safe_wait(1.0, 2.0)
        
        # Rastgele bir yere tıkla
        # TODO: Implement random click logic
    
    def _perform_resource_gathering(self, client=None, task_params=None):
        """
        Perform resource gathering actions
        
        Args:
            client: Client window to perform actions on
            task_params: Parameters for the resource gathering task
        """
        # Veritabanından görev parametrelerini al veya varsayılanları kullan
        if task_params is None:
            task_params = {
                'resource_types': ['ore', 'herb', 'wood'],
                'max_gather_time': 120,
                'return_to_base': True,
                'gather_count': 10  # Bir döngüde toplanacak maksimum kaynak sayısı
            }
        
        # İstemci değişkenini kontrol et
        if client is None and len(self.client_manager.active_clients) > 0:
            client = self.client_manager.active_clients[0]
            
        # İstemciye odaklan (varsa)
        if client and HAS_GUI_SUPPORT:
            self.client_manager.focus_client(client)
            safe_wait(0.5, 1.0)
        
        # Kaynak düğümlerini bul
        resource_types = task_params.get('resource_types', ['ore', 'herb', 'wood'])
        logger.info(f"Searching for resource nodes: {resource_types}")
        resource_positions = self.image_recognition.find_resource_nodes(limit=5)
        
        if not resource_positions:
            logger.warning("No resource nodes found, performing random movement to search")
            self._random_movement()
            return False
        
        # Mevcut pozisyonu al (istemci merkezi veya ekran merkezi)
        if client and HAS_GUI_SUPPORT:
            center_x, center_y = self.client_manager.get_client_center(client)
        else:
            # Ekran merkezini kullan
            if HAS_GUI_SUPPORT:
                import pyautogui
                center_x, center_y = pyautogui.size()
                center_x //= 2
                center_y //= 2
            else:
                center_x, center_y = 400, 300  # Varsayılan merkez
        
        # En yakın kaynağı bul
        closest_resource = resource_positions[0]
        min_distance = calculate_distance((center_x, center_y), closest_resource)
        
        for pos in resource_positions[1:]:
            dist = calculate_distance((center_x, center_y), pos)
            if dist < min_distance:
                min_distance = dist
                closest_resource = pos
        
        # En yakın kaynağa tıkla
        logger.info(f"Moving to nearest resource at {closest_resource}")
        self._safe_click(*closest_resource)
        
        # Toplama işleminin başlamasını bekle
        safe_wait(1.0, 2.0)
        
        # Toplama animasyonunun tamamlanmasını bekle
        gather_wait_time = min(5.0, task_params.get('gather_time', 3.0))
        logger.debug(f"Waiting for gathering animation ({gather_wait_time}s)")
        safe_wait(gather_wait_time, gather_wait_time + 1.0)
        
        # İşlem sonrası kontroller
        
        # 1. Envanter doluluk kontrolü
        if self.image_recognition.detect_full_inventory():
            logger.info("Inventory is full")
            
            # Üsse dönme ayarı varsa
            if task_params.get('return_to_base', False):
                logger.info("Returning to base to empty inventory")
                self._return_to_base(client)
            else:
                logger.info("Stopping resource gathering due to full inventory")
            
            return True
        
        # 2. Düşük sağlık kontrolü
        if self.image_recognition.detect_low_health():
            logger.warning("Low health detected during resource gathering")
            self._use_health_items()
            
            # Sağlık çok düşükse üsse dön
            health_percent = task_params.get('retreat_health_percent', 30)
            if health_percent < 30:  # 30% altı kritik seviye
                logger.warning(f"Health below critical level ({health_percent}%), returning to base")
                self._return_to_base(client)
                return False
        
        # Başarılı toplama
        logger.info("Successfully gathered resources")
        return True
    
    def _perform_character_maintenance(self, client=None, task_params=None):
        """
        Perform character maintenance actions
        
        Args:
            client: Client window to perform actions on
            task_params: Parameters for the maintenance task
        """
        if task_params is None:
            task_params = {
                'check_inventory': True,
                'check_health': True,
                'upgrade_equipment': True
            }
        
        # İstemciye odaklan (varsa)
        if client and HAS_GUI_SUPPORT:
            self.client_manager.focus_client(client)
            safe_wait(0.5, 1.0)
            
        # Envanteri kontrol et
        if task_params.get('check_inventory', True):
            logger.debug("Checking inventory")
            self._check_inventory(client)
        
        # Sağlık kontrolü
        if task_params.get('check_health', True) and self.image_recognition.detect_low_health():
            logger.info("Low health detected - using health items")
            self._use_health_items(client)
        
        # Ekipman yükseltme
        if task_params.get('upgrade_equipment', True):
            logger.debug("Checking for equipment upgrades")
            self._upgrade_equipment(client)
            
        return True
    
    def _perform_combat_actions(self, client=None, task_params=None):
        """
        Perform combat related actions
        
        Args:
            client: Client window to perform actions on
            task_params: Parameters for the combat task
        """
        if task_params is None:
            task_params = {
                'enemy_types': ['wolf', 'boar', 'bandit'],
                'max_combat_time': 60,
                'retreat_health_percent': 30
            }
        
        # İstemciye odaklan (varsa)
        if client and HAS_GUI_SUPPORT:
            self.client_manager.focus_client(client)
            safe_wait(0.5, 1.0)
            
        # Düşmanları bul
        enemy_types = task_params.get('enemy_types', ['wolf', 'boar', 'bandit'])
        logger.info(f"Searching for enemies: {enemy_types}")
        enemy_positions = self.image_recognition.find_enemies(limit=3)
        
        if not enemy_positions:
            logger.warning("No enemies found, performing random movement to search")
            self._random_movement()
            return False
        
        # En yakın düşmanı seç (ilk örnek için basitleştirilmiş)
        closest_enemy = enemy_positions[0]
        logger.info(f"Engaging enemy at {closest_enemy}")
        
        # Düşmana tıkla
        self._safe_click(*closest_enemy)
        safe_wait(1.0, 2.0)
        
        # Dövüş yeteneklerini kullan
        self._use_combat_abilities(client, task_params)
        
        # Düşük sağlık kontrolü
        if self.image_recognition.detect_low_health():
            logger.warning("Low health detected during combat")
            
            # Sağlık yüzdesi kontrolü
            health_percent = task_params.get('retreat_health_percent', 30)
            
            # Sağlık itemlerini kullan
            self._use_health_items(client)
            
            # Çok düşük sağlık varsa geri çekil
            if health_percent < 30:  # 30% altı kritik seviye
                logger.warning(f"Health below critical level ({health_percent}%), retreating")
                
                # Kaçma tuşu (ESC)
                if HAS_GUI_SUPPORT:
                    pyautogui.press('esc')
                    safe_wait(0.5, 1.0)
                
                # Rastgele yönde kaç
                self._random_movement()
                
                # Üsse dön
                self._return_to_base(client)
                return False
        
        return True
    
    def _perform_mission_tasks(self, client=None, task_params=None):
        """
        Perform mission related tasks
        
        Args:
            client: Client window to perform actions on
            task_params: Parameters for mission tasks
        """
        if task_params is None:
            task_params = {
                'mission_type': 'main',
                'max_travel_time': 120,
                'abort_on_combat': False
            }
        
        # İstemciye odaklan (varsa)
        if client and HAS_GUI_SUPPORT:
            self.client_manager.focus_client(client)
            safe_wait(0.5, 1.0)
            
        # Oyunda olup olmadığımızı kontrol et
        if not self.image_recognition.detect_in_game():
            logger.warning("Not in game, cannot perform mission tasks")
            return False
            
        # Görev panelini aç
        logger.info("Opening mission panel")
        mission_panel_pos = self.image_recognition.find_mission_panel()
        
        if mission_panel_pos:
            logger.debug(f"Found mission panel at {mission_panel_pos}, clicking")
            self._safe_click(*mission_panel_pos)
            safe_wait(0.5, 1.0)
        else:
            # Görev paneli bulunamadıysa kısayol tuşunu dene
            if HAS_GUI_SUPPORT:
                logger.debug("Mission panel not found, trying shortcut key")
                pyautogui.press('q')  # Görev paneli kısayolu - oyuna göre değişebilir
                safe_wait(0.5, 1.0)
        
        # Görev türünü seç (ana görev, yan görev, vb.)
        mission_type = task_params.get('mission_type', 'main')
        logger.info(f"Selecting mission type: {mission_type}")
        
        # Görev listesini kontrol et
        mission_list_pos = self.image_recognition.find_template(f"mission_{mission_type}")
        if mission_list_pos:
            logger.debug(f"Found mission list at {mission_list_pos}, clicking")
            self._safe_click(*mission_list_pos)
            safe_wait(0.5, 1.0)
        
        # Görev hedeflerini bul
        logger.info("Searching for mission objectives")
        objective_positions = self.image_recognition.find_mission_objectives()
        
        if not objective_positions:
            logger.warning("No mission objectives found")
            return False
        
        logger.info(f"Found {len(objective_positions)} mission objectives")
        
        # İlk hedefe odaklan
        active_objective = objective_positions[0]
        logger.info(f"Focusing on mission objective at {active_objective}")
        
        # Hedefe tıkla
        self._safe_click(*active_objective)
        safe_wait(1.0, 2.0)
        
        # Onay düğmesini bul ve tıkla
        confirm_pos = self.image_recognition.find_confirm_button()
        if confirm_pos:
            logger.debug(f"Found confirmation button at {confirm_pos}, clicking")
            self._safe_click(*confirm_pos)
            
            # Yolculuk/navigasyon varsa bekle
            max_travel_time = min(120, task_params.get('max_travel_time', 60))
            logger.info(f"Waiting for mission travel/navigation (max {max_travel_time}s)")
            
            # Gerçek uygulamada burada görevin ilerlemesini kontrol etmek için
            # image_recognition ile döngüsel kontroller yapılabilir
            safe_wait(3.0, 5.0)
            
            return True
        
        logger.warning("Could not find confirmation button for mission objective")
        return False
    
    def _check_inventory(self, client=None):
        """
        Check inventory and manage items
        
        Args:
            client: Client window to perform actions on
        """
        if not HAS_GUI_SUPPORT:
            logger.debug("Simulated inventory check")
            return
            
        # İstemciye odaklan (varsa)
        if client:
            self.client_manager.focus_client(client)
            safe_wait(0.3, 0.5)
            
        try:
            # Envanteri aç - genellikle 'i' tuşu
            logger.debug("Opening inventory")
            pyautogui.press('i')
            safe_wait(0.5, 1.0)
            
            # Öğeleri kontrol et ve düzenle
            # Örnek: Değerli eşyaları kullan veya düşür
            
            # Envanteri kapat
            logger.debug("Closing inventory")
            pyautogui.press('esc')
            
        except Exception as e:
            logger.error(f"Error checking inventory: {str(e)}")
    
    def _use_health_items(self, client=None):
        """
        Use health items if needed
        
        Args:
            client: Client window to perform actions on
        """
        if not HAS_GUI_SUPPORT:
            logger.debug("Simulated health item usage")
            return
            
        # İstemciye odaklan (varsa)
        if client:
            self.client_manager.focus_client(client)
            safe_wait(0.3, 0.5)
            
        try:
            # Sağlık potion kısayolu - genellikle bir fonksiyon tuşu
            logger.info("Using health potion")
            pyautogui.press('h')  # Sağlık potunu genellikle 'h' tuşu ile kullanabilirsiniz
            
            # Alternatif olarak envanterden potion kullanma
            inventory_health_item = self.image_recognition.find_template("health_potion")
            if inventory_health_item:
                logger.debug(f"Found health potion at {inventory_health_item}, clicking")
                self._safe_click(*inventory_health_item)
                
                # Onay tuşu varsa tıkla
                confirm = self.image_recognition.find_template("use_item_confirm")
                if confirm:
                    self._safe_click(*confirm)
            
        except Exception as e:
            logger.error(f"Error using health items: {str(e)}")
    
    def _upgrade_equipment(self, client=None):
        """
        Check and upgrade equipment
        
        Args:
            client: Client window to perform actions on
        """
        if not HAS_GUI_SUPPORT:
            logger.debug("Simulated equipment upgrade")
            return
            
        # İstemciye odaklan (varsa)
        if client:
            self.client_manager.focus_client(client)
            safe_wait(0.3, 0.5)
            
        try:
            # Yükseltme göstergelerini bul
            logger.debug("Searching for upgrade indicators")
            upgrade_positions = self.image_recognition.find_upgrade_indicators()
            
            if not upgrade_positions:
                logger.debug("No equipment upgrades available")
                return
            
            logger.info(f"Found {len(upgrade_positions)} potential equipment upgrades")
            
            # İlk 2 yükseltmeyi uygula
            for pos in upgrade_positions[:2]:
                logger.debug(f"Clicking upgrade indicator at {pos}")
                self._safe_click(*pos)
                safe_wait(0.5, 1.0)
                
                # Onay düğmesini bul ve tıkla
                confirm_pos = self.image_recognition.find_confirm_button()
                if confirm_pos:
                    logger.debug(f"Clicking upgrade confirmation at {confirm_pos}")
                    self._safe_click(*confirm_pos)
                    safe_wait(1.0, 1.5)  # Yükseltme animasyonunu bekle
                    
        except Exception as e:
            logger.error(f"Error upgrading equipment: {str(e)}")
    
    def _use_combat_abilities(self, client=None, combat_params=None):
        """
        Use combat abilities
        
        Args:
            client: Client window to perform actions on
            combat_params: Parameters for combat
        """
        if not HAS_GUI_SUPPORT:
            logger.debug("Simulated combat ability usage")
            return
            
        # Varsayılan yetenek tuşları
        ability_keys = combat_params.get('ability_keys', ['1', '2', '3', '4'])
        
        # İstemciye odaklan (varsa)
        if client:
            self.client_manager.focus_client(client)
            safe_wait(0.3, 0.5)
            
        try:
            logger.debug(f"Using combat abilities: {ability_keys}")
            
            for key in ability_keys:
                # Yeteneği kullan
                pyautogui.press(key)
                safe_wait(0.5, 1.0)
                
                # Düşman sağlık durumunu kontrol et
                # İleride şöyle bir şey eklenebilir: if self.image_recognition.detect_enemy_dead(): break
                
        except Exception as e:
            logger.error(f"Error using combat abilities: {str(e)}")
    
    def _random_movement(self):
        """Perform random movement"""
        # TODO: Implement random movement logic
        if HAS_GUI_SUPPORT:
            # WASD ile rastgele hareket
            movement_keys = ['w', 'a', 's', 'd']
            key = movement_keys[int(time.time()) % len(movement_keys)]
            pyautogui.keyDown(key)
            safe_wait(0.5, 1.5)
            pyautogui.keyUp(key)
            
    def _return_to_base(self, client=None):
        """
        Return to base to empty inventory or heal
        
        Args:
            client: Client window to perform actions on
            
        Returns:
            bool: True if successfully returned to base
        """
        logger.info("Attempting to return to base")
        
        if not HAS_GUI_SUPPORT:
            logger.debug("Simulated return to base")
            return True
        
        # İstemciye odaklan (varsa)
        if client:
            self.client_manager.focus_client(client)
            safe_wait(0.5, 1.0)
            
        # Haritayı aç
        logger.debug("Opening map")
        pyautogui.press('m')
        safe_wait(1.0, 1.5)
        
        # Haritada şehir ikonunu bul
        city_pos = self.image_recognition.find_template("city_icon")
        if city_pos:
            logger.debug(f"Found city at {city_pos}, clicking")
            self._safe_click(*city_pos)
            safe_wait(0.5, 1.0)
            
            # Hızlı seyahat düğmesini bul
            travel_button = self.image_recognition.find_template("travel_button")
            if travel_button:
                logger.debug(f"Found travel button at {travel_button}, clicking")
                self._safe_click(*travel_button)
                
                # Seyahat süresini bekle
                logger.info("Traveling to base, waiting...")
                safe_wait(5.0, 10.0)
                
                # Başarılı dönüş
                logger.info("Successfully returned to base")
                return True
        
        # Haritayı kapat - manuel dönüş yap
        logger.warning("Could not use fast travel, attempting manual return")
        pyautogui.press('esc')
        safe_wait(0.5, 1.0)
        
        # Kuzey yönünde 10-15 saniye boyunca ilerle (oyun tasarımına göre değişebilir)
        logger.debug("Moving north for 10-15 seconds")
        pyautogui.keyDown('w')
        safe_wait(10.0, 15.0)
        pyautogui.keyUp('w')
        
        # Başarısız/belirsiz dönüş
        logger.warning("Manual return to base completed (success unknown)")
        return False
    
    def _safe_click(self, x, y, button='left'):
        """
        Safely click at given coordinates with slight random offset
        to avoid detection patterns.
        
        Args:
            x: x-coordinate
            y: y-coordinate
            button: mouse button to click
        """
        if not HAS_GUI_SUPPORT:
            logger.debug(f"Simulated click at ({x}, {y})")
            return
        
        # Rastgele offset ekle
        x, y = random_offset(x, y, max_offset=5)
        
        # Tıklama
        pyautogui.click(x=x, y=y, button=button)
        
        # İki tıklama arasında bekleme
        safe_wait(
            float(self.config.get('click_delay_min', 0.2)), 
            float(self.config.get('click_delay_max', 0.5))
        )