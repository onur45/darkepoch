"""
Dark Epoch Bot - Client Manager
Manages multiple client windows for the Dark Epoch game.
Supports both window-based and process-based client management.
"""

import os
import logging
import platform
import time
import json
import subprocess
import threading
import re
import random

# Replit ortamı kontrolü için utils modülünü içe aktar
try:
    from utils import is_replit, is_windows
except ImportError:
    # Utils modülü yoksa basit kontrol fonksiyonları
    def is_replit():
        """
        Replit ortamında çalışıp çalışmadığını kontrol et
        """
        return os.environ.get('REPL_ID') is not None

    def is_windows():
        """
        Windows işletim sisteminde çalışıp çalışmadığını kontrol et
        """
        return platform.system() == "Windows"

# Koşullu modül içe aktarma
try:
    import pyautogui
    if is_windows():
        import win32gui
        import win32con
        import win32process
        import psutil
        HAS_WIN32_SUPPORT = True
    else:
        HAS_WIN32_SUPPORT = False
    HAS_GUI_SUPPORT = True
except ImportError:
    HAS_GUI_SUPPORT = False
    HAS_WIN32_SUPPORT = False

# Loglama yapılandırması
logger = logging.getLogger('DarkEpochBot.ClientManager')

class ClientManager:
    def __init__(self, config):
        """
        Initialize the Client Manager with the given configuration.

        Args:
            config (dict): Configuration dictionary containing client settings
        """
        self.config = config
        self.window_titles = config.get('client_window_titles', ['game', 'LDPlayer', 'Python', 'python.exe', 'flask'])

        if isinstance(self.window_titles, str):
            try:
                self.window_titles = json.loads(self.window_titles)
            except json.JSONDecodeError:
                self.window_titles = [self.window_titles]

        # Oyun çalıştırma yolu ayarı
        self.game_path = config.get('game_path', '')
        self.game_process_name = config.get('game_process_name', 'DarkEpoch.exe')

        # Yeni eklenen özellikler: Process-based client management
        self.processes = []
        self.use_process_management = config.get('use_process_management', False)
        self.max_client_processes = config.get('max_client_processes', 2)

        # Bulunan pencereleri depolama
        self.found_windows = []
        self.active_clients = []

        # Görev takibi için
        self.client_tasks = {}  # Her client için görevleri takip eder

        # Platform kontrolü
        if not (HAS_GUI_SUPPORT and platform.system() == "Windows"):
            logger.warning("Client Manager requires Windows with GUI support")
            self.supported = False
        else:
            if HAS_WIN32_SUPPORT:
                self.supported = True
                logger.info("Client Manager initialized with window management support")
            else:
                self.supported = False
                logger.warning("Window management not available, process management may still work")

    def scan_for_clients(self):
        """
        Scan for client windows matching the configured window titles.

        Returns:
            list: List of window handles for found clients
        """
        if not self.supported:
            logger.warning("Client Manager not supported on this platform")
            return []

        # Windows'ta değilsek veya Win32 API yoksa boş liste döndür
        if not HAS_WIN32_SUPPORT:
            logger.info("Client tarama devre dışı: Win32 API desteklenmiyor")
            return []

        # Yapılandırılmış pencere başlıklarını al
        try:
            window_titles = self.config.get("client_window_titles", [])
            if isinstance(window_titles, str):
                window_titles = [window_titles]  # Tek değeri listeye çevir

            if not window_titles:
                logger.warning("Yapılandırılmış pencere başlığı bulunamadı")
                # Varsayılan pencere başlıkları
                window_titles = ["Dark Epoch", "LDPlayer"]
        except Exception as e:
            logger.error(f"Pencere başlıkları alınırken hata: {str(e)}")
            window_titles = ["Dark Epoch", "LDPlayer"]

        logger.info(f"Aranan pencere başlıkları: {window_titles}")

        try:
            self.found_windows = []

            # Tüm pencereleri tara
            def win_enum_callback(hwnd, results):
                try:
                    if not win32gui.IsWindowVisible(hwnd):
                        return True

                    try:
                        window_text = win32gui.GetWindowText(hwnd)
                    except Exception as e:
                        logger.error(f"Error getting window text: {str(e)}")
                        return True

                    # Pencere başlığının aranacak başlıklardan biriyle eşleşip eşleşmediğini kontrol et
                    for title in window_titles:
                        if title.lower() in window_text.lower():
                            try:
                                # Pencere bilgilerini al
                                rect = win32gui.GetWindowRect(hwnd)
                                width = rect[2] - rect[0]
                                height = rect[3] - rect[1]

                                if width > 50 and height > 50:  # Çok küçük pencereleri yoksay
                                    logger.info(f"Client penceresi bulundu: {window_text} (HWND: {hwnd})")

                                    client_info = {
                                        "title": window_text,
                                        "hwnd": str(hwnd),  # Sayıyı stringe çevir
                                        "width": width,
                                        "height": height,
                                        "position_x": rect[0],
                                        "position_y": rect[1]
                                    }

                                    results.append(client_info)
                            except Exception as e:
                                logger.error(f"Error getting window information: {str(e)}")
                            break

                except Exception as e:
                    logger.error(f"Error in win_enum_callback: {str(e)}")
                return True

            # Özel callback ile tara
            win32gui.EnumWindows(lambda hwnd, param: win_enum_callback(hwnd, self.found_windows), None)

            num_found = len(self.found_windows)
            logger.info(f"Found {num_found} client windows")

            # Aktif istemcileri belirle
            self._update_active_clients()

            # Web API'ye client bilgilerini gönder
            if hasattr(self, '_update_web_api_clients'):
                self._update_web_api_clients(self.found_windows)

            return self.found_windows
        except Exception as e:
            logger.error(f"Error scanning for client windows: {str(e)}")
            return []

    def _enum_windows_callback(self, hwnd, _):
        """Callback function for EnumWindows"""
        if not HAS_WIN32_SUPPORT:
            return

        try:
            if hwnd == 0 or not win32gui.IsWindowVisible(hwnd):
                return

            # Pencere başlığını al
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return

            # Pencere boyutunu al
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]

            # Çok küçük pencereleri atla
            if width < 100 or height < 100:
                return

            # Konfigüre edilmiş pencere başlıklarıyla eşleştir
            for window_title in self.window_titles:
                if window_title.lower() in title.lower():
                    logger.debug(f"Found window: {title} (hwnd: {hwnd}, size: {width}x{height})")

                    window_info = {
                        'hwnd': hwnd,
                        'title': title,
                        'width': width,
                        'height': height,
                        'position_x': rect[0],
                        'position_y': rect[1]
                    }

                    self.found_windows.append(window_info)
                    break

        except Exception as e:
            logger.error(f"Error in window enumeration: {str(e)}")


    def _update_active_clients(self):
        """Update the list of active clients"""
        self.active_clients = self.found_windows[:2]  # En fazla 2 aktif istemci

        if len(self.active_clients) > 0:
            logger.info(f"Active clients: {len(self.active_clients)}")
            for idx, client in enumerate(self.active_clients):
                logger.debug(f"Client {idx}: {client['title']} (hwnd: {client['hwnd']})")

    def get_active_clients(self):
        """
        Get the active clients for bot operation.

        Returns:
            list: List of active client window handles (2 active, 1 passive)
        """
        return self.active_clients

    def focus_client(self, client):
        """
        Focus on a specific client window.

        Args:
            client: Window handle or client info dictionary
        """
        if not self.supported:
            logger.warning("Client Manager not supported on this platform")
            return

        if not HAS_WIN32_SUPPORT:
            logger.warning("Cannot focus client: Win32 API not available")
            return

        try:
            # Client parametresi bir sözlük ise hwnd'yi çıkar
            hwnd = client['hwnd'] if isinstance(client, dict) else client

            # Pencereyi öne getir
            win32gui.SetForegroundWindow(hwnd)

            # Hareket halindeyse bekle
            time.sleep(0.1)

            logger.debug(f"Focused on client window: {hwnd}")
        except Exception as e:
            logger.error(f"Error focusing client window: {str(e)}")

    def get_client_rect(self, client):
        """
        Get the rectangle coordinates of a client window.

        Args:
            client: Window handle or client info dictionary

        Returns:
            tuple: (left, top, right, bottom) coordinates of the window
        """
        if not self.supported:
            logger.warning("Client Manager not supported on this platform")
            return (0, 0, 800, 600)  # Varsayılan boyut

        if not HAS_WIN32_SUPPORT:
            logger.warning("Cannot get client rect: Win32 API not available")
            return (0, 0, 800, 600)  # Varsayılan boyut

        try:
            # Client parametresi bir sözlük ise hwnd'yi çıkar
            hwnd = client['hwnd'] if isinstance(client, dict) else client

            # Pencere koordinatlarını al
            return win32gui.GetWindowRect(hwnd)
        except Exception as e:
            logger.error(f"Error getting client rectangle: {str(e)}")
            return (0, 0, 800, 600)  # Hata durumunda varsayılan boyut

    def get_client_center(self, client):
        """
        Get the center coordinates of a client window.

        Args:
            client: Window handle or client info dictionary

        Returns:
            tuple: (x, y) coordinates of the window center
        """
        rect = self.get_client_rect(client)
        center_x = (rect[0] + rect[2]) // 2
        center_y = (rect[1] + rect[3]) // 2
        return (center_x, center_y)

    def arrange_clients(self):
        """
        Arrange client windows for optimal visibility.
        Not critical for functionality but can help organize the workspace.
        """
        if not self.supported or len(self.found_windows) == 0:
            logger.warning("Cannot arrange windows: either not supported or no windows found")
            return

        if not HAS_WIN32_SUPPORT or not HAS_GUI_SUPPORT:
            logger.warning("Cannot arrange windows: Window management not available")
            return

        try:
            # Ekran boyutlarını al
            screen_width, screen_height = pyautogui.size()

            if len(self.found_windows) == 1:
                # Tek pencere varsa, ekranın merkezine yerleştir
                client = self.found_windows[0]
                hwnd = client['hwnd']
                width, height = client['width'], client['height']

                # Yeni pozisyonları hesapla
                left = (screen_width - width) // 2
                top = (screen_height - height) // 2

                # Pencereyi taşı
                win32gui.SetWindowPos(
                    hwnd, win32con.HWND_TOP,
                    left, top, width, height,
                    win32con.SWP_SHOWWINDOW
                )

                logger.info(f"Arranged single window to center: {client['title']}")

            elif len(self.found_windows) >= 2:
                # İki pencere varsa, yan yana yerleştir
                for idx, client in enumerate(self.found_windows[:2]):
                    hwnd = client['hwnd']

                    # İlk pencere sol tarafa, ikinci pencere sağ tarafa
                    if idx == 0:
                        # Sol pencere
                        left = 0
                        top = 0
                        width = screen_width // 2
                        height = screen_height
                    else:
                        # Sağ pencere
                        left = screen_width // 2
                        top = 0
                        width = screen_width // 2
                        height = screen_height

                    # Pencereyi taşı
                    win32gui.SetWindowPos(
                        hwnd, win32con.HWND_TOP,
                        left, top, width, height,
                        win32con.SWP_SHOWWINDOW
                    )

                logger.info(f"Arranged {min(2, len(self.found_windows))} windows side by side")

        except Exception as e:
            logger.error(f"Error arranging client windows: {str(e)}")

    def capture_client_screenshot(self, client):
        """
        Capture a screenshot of a specific client window.

        Args:
            client: Window handle or client info dictionary

        Returns:
            PIL.Image: Screenshot of the client window
        """
        if not HAS_GUI_SUPPORT:
            logger.warning("Cannot capture screenshot: GUI support not available")
            return None

        try:
            # Client parametresi bir sözlük ise hwnd'yi ve boyutları çıkar
            if isinstance(client, dict):
                hwnd = client['hwnd']
                left, top = client['position_x'], client['position_y']
                width, height = client['width'], client['height']
            else:
                hwnd = client
                left, top, right, bottom = self.get_client_rect(hwnd)
                width, height = right - left, bottom - top

            # İstemciye odaklan
            self.focus_client(hwnd)

            # Pencere bölgesinin ekran görüntüsünü al
            screenshot = pyautogui.screenshot(region=(left, top, width, height))

            return screenshot
        except Exception as e:
            logger.error(f"Error capturing client screenshot: {str(e)}")
            return None

    # Process-based client management methods
    def start_client_process(self):
        """
        Start a new client process if maximum not reached.

        Returns:
            bool: True if process started successfully, False otherwise
        """
        if not self.use_process_management:
            logger.warning("Process management is disabled in configuration")
            return False

        # Replit'te çalışıyorsa sadece simüle et
        if is_replit():
            logger.info("Replit ortamında gerçek client process başlatılamaz, simüle ediliyor")
            # Sahte process bilgisi
            fake_pid = int(time.time() * 1000) % 10000
            self.processes.append({
                'pid': fake_pid,
                'process': None,
                'start_time': time.time(),
                'status': 'simulated'
            })
            logger.info(f"Simulated client process with fake PID {fake_pid}")
            return True

        if len(self.processes) >= self.max_client_processes:
            logger.warning(f"Maximum number of client processes ({self.max_client_processes}) already running")
            return False

        if not self.game_path:
            logger.error("Game path not configured")
            return False

        try:
            # Check if game executable exists
            if not os.path.exists(self.game_path):
                logger.error(f"Game executable not found at {self.game_path}")
                return False

            # Start a new process
            if platform.system() == "Windows":
                # Windows'ta yeni konsol penceresinde başlat
                process = subprocess.Popen(
                    [self.game_path],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    creationflags=subprocess.CREATE_NEW_CONSOLE
                )
            else:
                # Linux/Mac'te başlat
                process = subprocess.Popen(
                    [self.game_path],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

            # Add to processes list
            self.processes.append({
                'pid': process.pid,
                'process': process,
                'start_time': time.time(),
                'status': 'starting'
            })

            logger.info(f"Started new client process with PID {process.pid}")

            # Wait a bit for the process to initialize
            time.sleep(3.0)

            # Scan for windows to update our list
            self.scan_for_clients()

            return True
        except Exception as e:
            logger.error(f"Error starting client process: {str(e)}")
            return False

    def stop_client_process(self, process_idx=None):
        """
        Stop a client process.

        Args:
            process_idx: Index of the process to stop, or None to stop the last one

        Returns:
            bool: True if process stopped successfully, False otherwise
        """
        if not self.use_process_management:
            logger.warning("Process management is disabled in configuration")
            return False

        if not self.processes:
            logger.warning("No client processes to stop")
            return False

        try:
            # Determine which process to stop
            if process_idx is None:
                process_idx = len(self.processes) - 1

            if process_idx < 0 or process_idx >= len(self.processes):
                logger.error(f"Invalid process index: {process_idx}")
                return False

            process_info = self.processes[process_idx]
            pid = process_info['pid']

            # Replit'te çalışıyorsa sadece simüle et
            if is_replit() or process_info.get('status') == 'simulated' or process_info.get('process') is None:
                logger.info(f"Simulated client process with PID {pid} stopped")
                self.processes.pop(process_idx)
                return True

            process = process_info['process']

            # Try to terminate gracefully
            process.terminate()

            # Wait for process to terminate
            try:
                process.wait(timeout=5)
                logger.info(f"Successfully stopped client process with PID {pid}")
            except subprocess.TimeoutExpired:
                # If still running, kill it
                process.kill()
                logger.warning(f"Forcefully killed client process with PID {pid}")

            # Remove from processes list
            self.processes.pop(process_idx)

            # Scan for windows to update our list
            self.scan_for_clients()

            return True
        except Exception as e:
            logger.error(f"Error stopping client process: {str(e)}")
            return False

    def get_process_info(self):
        """
        Get information about running client processes.

        Returns:
            list: List of dictionaries with process information
        """
        if not self.use_process_management:
            return []

        result = []
        for proc_info in self.processes:
            try:
                pid = proc_info['pid']

                # Replit ortamında veya simüle edilmiş ise farklı bilgi döndür
                if is_replit() or proc_info.get('status') == 'simulated' or proc_info.get('process') is None:
                    result.append({
                        'pid': pid,
                        'status': 'simulated',
                        'cpu_percent': random.randint(10, 30),  # Simüle edilmiş CPU kullanımı
                        'memory_mb': random.randint(50, 150),  # Simüle edilmiş bellek kullanımı
                        'run_time': time.time() - proc_info['start_time']
                    })
                    continue

                proc = proc_info['process']
                # Check if process is still running
                if proc and proc.poll() is not None:
                    proc_info['status'] = 'stopped'
                    continue

                # Get process info using psutil if available
                if HAS_WIN32_SUPPORT and 'psutil' in globals():
                    try:
                        p = psutil.Process(pid)
                        cpu_percent = p.cpu_percent(interval=0.1)
                        memory_info = p.memory_info()
                        result.append({
                            'pid': pid,
                            'status': 'running',
                            'cpu_percent': cpu_percent,
                            'memory_mb': memory_info.rss / (1024 * 1024),
                            'run_time': time.time() - proc_info['start_time']
                        })
                    except Exception as e:
                        logger.error(f"Error getting process info using psutil: {str(e)}")
                        result.append({
                            'pid': pid,
                            'status': 'running',
                            'run_time': time.time() - proc_info['start_time']
                        })
                else:
                    result.append({
                        'pid': pid,
                        'status': 'running',
                        'run_time': time.time() - proc_info['start_time']
                    })
            except Exception as e:
                logger.error(f"Error getting process info: {str(e)}")

        return result

    def check_client_processes(self):
        """
        Check status of all client processes and update internal state.

        Returns:
            int: Number of active running processes
        """
        if not self.use_process_management:
            return 0

        # Replit ortamında her zaman aktif göster
        if is_replit():
            return len(self.processes)

        active_count = 0
        for i, proc_info in enumerate(self.processes[:]):
            try:
                # Simüle edilmiş process'ler her zaman çalışıyor kabul edilir
                if proc_info.get('status') == 'simulated' or proc_info.get('process') is None:
                    active_count += 1
                    continue

                proc = proc_info['process']

                # Check if process is still running
                if proc and proc.poll() is not None:
                    logger.info(f"Client process with PID {proc_info['pid']} has exited")
                    self.processes.remove(proc_info)
                else:
                    active_count += 1
            except Exception as e:
                logger.error(f"Error checking process {i}: {str(e)}")

        # Scan for windows to update our list if needed
        if active_count > 0 and not self.found_windows:
            self.scan_for_clients()

        return active_count

    def assign_task_to_client(self, client, task):
        """
        Assign a task to a specific client.

        Args:
            client: Client window or process info
            task: Task to assign

        Returns:
            bool: True if task assigned successfully
        """
        try:
            if isinstance(client, dict) and 'hwnd' in client:
                client_id = client['hwnd']
            elif isinstance(client, dict) and 'pid' in client:
                client_id = client['pid']
            else:
                client_id = str(client)

            self.client_tasks[client_id] = task
            logger.info(f"Assigned task to client {client_id}: {task.get('name', 'Unknown')}")
            return True
        except Exception as e:
            logger.error(f"Error assigning task to client: {str(e)}")
            return False

    def get_client_task(self, client):
        """
        Get the currently assigned task for a client.

        Args:
            client: Client window or process info

        Returns:
            dict: Task information or None if no task assigned
        """
        try:
            if isinstance(client, dict) and 'hwnd' in client:
                client_id = client['hwnd']
            elif isinstance(client, dict) and 'pid' in client:
                client_id = client['pid']
            else:
                client_id = str(client)

            return self.client_tasks.get(client_id)
        except Exception as e:
            logger.error(f"Error getting client task: {str(e)}")
            return None