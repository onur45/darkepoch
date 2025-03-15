"""
Dark Epoch Bot - Main Entry Point
Replit ve Windows ortamlarında çalışacak şekilde tasarlanmıştır.
"""

import os
import sys
import logging
import platform
import threading

# Bot instance'ı global olarak tanımla (web API için)
bot_instance = None

# Platforma göre modül içe aktarma
try:
    from app import app, init_db
    HAS_WEB_INTERFACE = True
except ImportError as e:
    print(f"Flask web arayüzü içe aktarılamadı: {e}")
    HAS_WEB_INTERFACE = False

# Çalışma ortamını kontrol et
IS_REPLIT = os.environ.get('REPL_ID') is not None

# X11 bağımlı modülleri koşullu olarak içe aktar
# Sadece Windows ortamında veya Replit olmayan ortamlarda denemeyi yap
if not IS_REPLIT and platform.system() == "Windows":
    try:
        import pyautogui
        from bot import DarkEpochBot
        HAS_GUI_SUPPORT = True
    except ImportError as e:
        HAS_GUI_SUPPORT = False
        print(f"PyAutoGUI desteklenmiyor: {e}. Bot işlevselliği sınırlı olacak.")
else:
    HAS_GUI_SUPPORT = False
    print("Replit ortamında çalışıyor, GUI desteği devre dışı.")

# Loglama yapılandırması
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot.log')
    ]
)
logger = logging.getLogger('DarkEpochBot')

def is_windows():
    """Sistemin Windows olup olmadığını kontrol et"""
    return platform.system() == "Windows"

def is_replit():
    """Çalışma ortamının Replit olup olmadığını kontrol et"""
    return os.environ.get('REPL_ID') is not None

def main():
    """Ana giriş noktası"""
    logger.info(f"Dark Epoch Bot başlatılıyor - Platform: {platform.system()}")
    
    # Çalışma modunu belirle
    if is_replit():
        logger.info("Replit ortamında çalışıyor - Web arayüzü modu etkin")
        run_web_interface()
    elif is_windows() and HAS_GUI_SUPPORT:
        logger.info("Windows ortamında çalışıyor - Tam bot modu etkin")
        run_bot_with_web_client()
    else:
        logger.warning("Desteklenmeyen platform veya gerekli bağımlılıklar eksik")
        print("Desteklenmeyen platform veya gerekli bağımlılıklar eksik")
        print("Bot, Replit (web arayüzü) veya Windows (tam bot) ortamlarında çalışacak şekilde tasarlanmıştır.")
        sys.exit(1)

def run_web_interface():
    """Flask web arayüzünü çalıştır"""
    if not HAS_WEB_INTERFACE:
        logger.error("Web arayüzü modülleri içe aktarılamadı")
        return
    
    try:
        logger.info("Veritabanı başlatılıyor...")
        init_db()
        
        # Replit'te direkt olarak Flask'ı çalıştır
        # Not: Replit'te gunicorn kullanılır, bu kod sadece lokal geliştirme için
        if __name__ == "__main__" and not is_replit():
            logger.info("Web arayüzü başlatılıyor...")
            app.run(host="0.0.0.0", port=5000, debug=True)
    except Exception as e:
        logger.error(f"Web arayüzü başlatılırken hata: {str(e)}")

def run_bot_with_web_client():
    """Bot ve web istemci modunu çalıştır"""
    global bot_instance
    
    if not HAS_GUI_SUPPORT:
        logger.error("Bot modülleri içe aktarılamadı")
        return
    
    try:
        from config import load_config
        
        # Konfigürasyon yükle
        config = load_config()
        
        # Botu başlat
        bot = DarkEpochBot(config)
        bot_instance = bot
        
        # Botu ayrı bir thread'de başlat
        bot_thread = threading.Thread(target=bot.start)
        bot_thread.daemon = True  # Ana program sonlandığında thread'i otomatik kapat
        bot_thread.start()
        
        logger.info("Bot çalıştırılıyor...")
        
        # Web arayüzünü başlat
        if HAS_WEB_INTERFACE:
            logger.info("Web arayüzü başlatılıyor...")
            # Veritabanını başlat
            init_db()
            # Web sunucusunu başlat
            app.run(host="0.0.0.0", port=5000, debug=False)
        else:
            logger.warning("Web arayüzü başlatılamadı, sadece bot çalışıyor")
            # Ana thread'i canlı tut
            bot_thread.join()
            
    except Exception as e:
        logger.error(f"Bot başlatılırken hata: {str(e)}")

if __name__ == "__main__":
    main()