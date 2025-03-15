"""
Dark Epoch Bot - Web API ve Arayüzü
Flask web uygulaması ile bot kontrolü sağlar.
"""
import os
import json
import logging
import platform
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Replit ortamında olup olmadığını kontrol etme fonksiyonu
def is_replit():
    """
    Çalışma ortamının Replit olup olmadığını kontrol et.
    
    Returns:
        bool: True if running on Replit, False otherwise
    """
    return os.environ.get('REPL_ID') is not None or platform.system() != 'Windows'

# Temel veritabanı sınıfı
class Base(DeclarativeBase):
    pass

# Flask ve veritabanı yapılandırması
db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dark_epoch_bot_secret")

# Veritabanı bağlantısı
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///darkepoch.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

# Loglama konfigürasyonu
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bot_web.log')
    ]
)
logger = logging.getLogger('DarkEpochBotWeb')

# Bot durumu için basit bir global değişken
# Gerçek bir uygulamada bu veritabanında saklanır
bot_status = {
    "running": False,
    "paused": False,
    "active_clients": 0,
    "total_clients": 0,
    "current_task": None,
    "error_count": 0,
    "last_updated": datetime.now().isoformat()
}

# Model tanımlamaları
class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    type = db.Column(db.String(50), nullable=False)  # Görev tipi: resource_gathering, combat, etc.
    parameters = db.Column(db.Text, nullable=True)  # JSON formatında görev parametreleri
    priority = db.Column(db.Integer, default=1)
    enabled = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Task {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'parameters': json.loads(self.parameters) if self.parameters else {},
            'priority': self.priority,
            'enabled': self.enabled,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class BotConfig(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    value_type = db.Column(db.String(50), default="string")  # string, int, float, bool, json
    description = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<BotConfig {self.key}>'
    
    def get_value(self):
        """Değeri doğru tipte döndürür"""
        if not self.value:
            return None
            
        if self.value_type == "int":
            return int(self.value)
        elif self.value_type == "float":
            return float(self.value)
        elif self.value_type == "bool":
            return self.value.lower() == "true"
        elif self.value_type == "json":
            return json.loads(self.value)
        else:
            return self.value

class ClientWindow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    hwnd = db.Column(db.String(100), nullable=True)  # Window handle (hex string)
    width = db.Column(db.Integer, nullable=True)
    height = db.Column(db.Integer, nullable=True)
    position_x = db.Column(db.Integer, nullable=True)
    position_y = db.Column(db.Integer, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<ClientWindow {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'hwnd': self.hwnd,
            'width': self.width,
            'height': self.height,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'is_active': self.is_active,
            'last_seen': self.last_seen.isoformat()
        }

class BotLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False, default="INFO")
    message = db.Column(db.Text, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('client_window.id'), nullable=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BotLog {self.level}: {self.message[:50]}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'level': self.level,
            'message': self.message,
            'client_id': self.client_id,
            'task_id': self.task_id,
            'created_at': self.created_at.isoformat()
        }

# Flask route'ları
@app.route('/')
def index():
    """Ana sayfa"""
    tasks = Task.query.order_by(Task.priority.desc(), Task.id).all()
    clients = ClientWindow.query.order_by(ClientWindow.is_active.desc(), ClientWindow.id).all()
    
    return render_template(
        'index.html', 
        bot_status=bot_status, 
        tasks=tasks,
        clients=clients
    )

@app.route('/tasks')
def task_list():
    """Görev listesi sayfası"""
    tasks = Task.query.order_by(Task.priority.desc(), Task.id).all()
    return render_template('tasks.html', tasks=tasks, bot_status=bot_status)

@app.route('/tasks/new', methods=['GET', 'POST'])
def new_task():
    """Yeni görev oluşturma sayfası"""
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        task_type = request.form.get('type')
        parameters = request.form.get('parameters', '{}')
        priority = int(request.form.get('priority', 1))
        enabled = bool(request.form.get('enabled', False))
        
        # JSON'u doğrula
        try:
            json_params = json.loads(parameters)
            parameters = json.dumps(json_params)  # Düzgün JSON formatına çevir
        except json.JSONDecodeError:
            flash('Parametre JSON formatında değil!', 'error')
            return render_template('task_edit.html', task=None, bot_status=bot_status)
        
        task = Task(
            name=name,
            description=description,
            type=task_type,
            parameters=parameters,
            priority=priority,
            enabled=enabled
        )
        
        db.session.add(task)
        db.session.commit()
        
        flash('Görev başarıyla oluşturuldu!', 'success')
        return redirect(url_for('task_list'))
    
    # GET isteği - form göster
    return render_template('task_edit.html', task=None, bot_status=bot_status)

@app.route('/tasks/<int:task_id>', methods=['GET', 'POST'])
def edit_task(task_id):
    """Görev düzenleme sayfası"""
    task = Task.query.get_or_404(task_id)
    
    if request.method == 'POST':
        task.name = request.form.get('name')
        task.description = request.form.get('description')
        task.type = request.form.get('type')
        parameters = request.form.get('parameters', '{}')
        task.priority = int(request.form.get('priority', 1))
        task.enabled = 'enabled' in request.form
        
        # JSON'u doğrula
        try:
            json_params = json.loads(parameters)
            task.parameters = json.dumps(json_params)  # Düzgün JSON formatına çevir
        except json.JSONDecodeError:
            flash('Parametre JSON formatında değil!', 'error')
            return render_template('task_edit.html', task=task, bot_status=bot_status)
        
        db.session.commit()
        
        flash('Görev başarıyla güncellendi!', 'success')
        return redirect(url_for('task_list'))
    
    # GET isteği - form göster
    return render_template('task_edit.html', task=task, bot_status=bot_status)

@app.route('/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """Görev silme işlemi"""
    task = Task.query.get_or_404(task_id)
    db.session.delete(task)
    db.session.commit()
    
    flash('Görev başarıyla silindi!', 'success')
    return redirect(url_for('task_list'))

@app.route('/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    """Görev etkinleştirme/devre dışı bırakma"""
    task = Task.query.get_or_404(task_id)
    task.enabled = not task.enabled
    db.session.commit()
    
    status = "etkinleştirildi" if task.enabled else "devre dışı bırakıldı"
    flash(f'Görev başarıyla {status}!', 'success')
    return redirect(url_for('task_list'))

@app.route('/config')
def config_list():
    """Konfigürasyon listesi sayfası"""
    configs = BotConfig.query.order_by(BotConfig.key).all()
    return render_template('config.html', configs=configs, bot_status=bot_status)

@app.route('/config/edit', methods=['GET', 'POST'])
def edit_config():
    """Konfigürasyon düzenleme sayfası"""
    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('config_'):
                config_key = key[7:]  # Prefix'i kaldır
                config = BotConfig.query.filter_by(key=config_key).first()
                
                if config:
                    config.value = value
                    db.session.commit()
        
        flash('Konfigürasyon başarıyla güncellendi!', 'success')
        return redirect(url_for('config_list'))
    
    return redirect(url_for('config_list'))

@app.route('/clients')
def client_list():
    """İstemci penceresi listesi sayfası"""
    clients = ClientWindow.query.order_by(ClientWindow.is_active.desc(), ClientWindow.id).all()
    return render_template('clients.html', clients=clients, bot_status=bot_status)
    
@app.route('/processes')
def process_list():
    """İstemci process'leri listesi sayfası"""
    # Process bilgileri şu anda sadece Windows platformunda gerçek veri döndürecek
    # Replit geliştirme ortamında demo veriler gösterilir
    return render_template('processes.html', bot_status=bot_status)

@app.route('/logs')
def log_list():
    """Bot log listesi sayfası"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    logs = BotLog.query.order_by(BotLog.created_at.desc()).paginate(page=page, per_page=per_page)
    return render_template('logs.html', logs=logs, bot_status=bot_status)

# API endpoint'leri
@app.route('/api/status', methods=['GET'])
def api_status():
    """Bot durum bilgisi API'si"""
    return jsonify(bot_status)

@app.route('/api/start', methods=['POST'])
def api_start():
    """Botu başlatma API'si"""
    bot_status["running"] = True
    bot_status["paused"] = False
    bot_status["last_updated"] = datetime.now().isoformat()
    
    # Log kaydı oluştur
    log = BotLog(level="INFO", message="Bot started via web API")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Bot started"})

@app.route('/api/stop', methods=['POST'])
def api_stop():
    """Botu durdurma API'si"""
    bot_status["running"] = False
    bot_status["paused"] = False
    bot_status["last_updated"] = datetime.now().isoformat()
    
    # Log kaydı oluştur
    log = BotLog(level="INFO", message="Bot stopped via web API")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Bot stopped"})

@app.route('/api/pause', methods=['POST'])
def api_pause():
    """Botu duraklatma API'si"""
    bot_status["paused"] = True
    bot_status["last_updated"] = datetime.now().isoformat()
    
    # Log kaydı oluştur
    log = BotLog(level="INFO", message="Bot paused via web API")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Bot paused"})

@app.route('/api/resume', methods=['POST'])
def api_resume():
    """Botu devam ettirme API'si"""
    bot_status["paused"] = False
    bot_status["last_updated"] = datetime.now().isoformat()
    
    # Log kaydı oluştur
    log = BotLog(level="INFO", message="Bot resumed via web API")
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"success": True, "message": "Bot resumed"})

@app.route('/api/tasks', methods=['GET'])
def api_tasks():
    """Görev listesi API'si"""
    tasks = Task.query.filter_by(enabled=True).order_by(Task.priority.desc(), Task.id).all()
    return jsonify([task.to_dict() for task in tasks])

@app.route('/api/clients', methods=['GET'])
def api_clients():
    """İstemci penceresi listesi API'si"""
    clients = ClientWindow.query.filter_by(is_active=True).all()
    return jsonify([client.to_dict() for client in clients])
    
@app.route('/api/processes', methods=['GET'])
def api_processes():
    """Process bilgisi API'si"""
    # Bu endpoint sadece bilgi sağlar, gerçek işlem Windows tarafında yapılır
    
    # Demo data (Replit için)
    if is_replit():
        processes = [
            {
                "id": 1,
                "name": "DarkEpoch.exe",
                "pid": 12345,
                "cpu_percent": 2.5,
                "memory_percent": 3.8,
                "status": "running",
                "create_time": datetime.now().isoformat()
            },
            {
                "id": 2,
                "name": "DarkEpochLauncher.exe",
                "pid": 12346,
                "cpu_percent": 0.5,
                "memory_percent": 1.2,
                "status": "running",
                "create_time": datetime.now().isoformat()
            }
        ]
        return jsonify(processes)
    
    # Gerçek process verisi (Windows için)
    # Bu kısım client_manager üzerinden alınmış process_info'yu döndürecektir
    # Ancak Replit ortamında çalışmaz
    from bot import bot_instance
    if bot_instance:
        processes = bot_instance.client_manager.get_process_info()
        return jsonify(processes)
    else:
        return jsonify([])
        
@app.route('/api/processes/start', methods=['POST'])
def api_start_process():
    """Process başlatma API'si"""
    # Bu endpoint sadece bilgi sağlar, gerçek işlem Windows tarafında yapılır
    
    # Replit için simülasyon modu
    if is_replit():
        return jsonify({
            "success": True,
            "message": "Process başlatma simüle edildi (Bu işlem sadece Windows'ta çalışır)"
        })
    
    # Windows için gerçek process başlatma
    from bot import bot_instance
    if bot_instance:
        result = bot_instance.client_manager.start_client_process()
        if result:
            return jsonify({"success": True, "message": "Process başarıyla başlatıldı"})
        else:
            return jsonify({"success": False, "message": "Process başlatılamadı"})
    else:
        return jsonify({"success": False, "message": "Bot aktif değil"})
        
@app.route('/api/processes/stop', methods=['POST'])
def api_stop_process():
    """Process durdurma API'si"""
    # Bu endpoint sadece bilgi sağlar, gerçek işlem Windows tarafında yapılır
    process_id = request.json.get('process_id')
    
    # Replit için simülasyon modu
    if is_replit():
        return jsonify({
            "success": True,
            "message": f"Process {process_id} durdurma simüle edildi (Bu işlem sadece Windows'ta çalışır)"
        })
    
    # Windows için gerçek process durdurma
    from bot import bot_instance
    if bot_instance:
        result = bot_instance.client_manager.stop_client_process(process_id)
        if result:
            return jsonify({"success": True, "message": f"Process {process_id} başarıyla durduruldu"})
        else:
            return jsonify({"success": False, "message": f"Process {process_id} durdurulamadı"})
    else:
        return jsonify({"success": False, "message": "Bot aktif değil"})

@app.route('/api/config', methods=['GET'])
def api_config():
    """Konfigürasyon API'si"""
    configs = BotConfig.query.all()
    config_dict = {}
    
    for config in configs:
        config_dict[config.key] = config.get_value()
    
    return jsonify(config_dict)

@app.route('/api/logs', methods=['POST'])
def api_log():
    """Log gönderme API'si"""
    data = request.json
    
    if not data or not data.get('message'):
        return jsonify({"success": False, "error": "Invalid log data"}), 400
    
    level = data.get('level', 'INFO')
    message = data.get('message')
    client_id = data.get('client_id')
    task_id = data.get('task_id')
    
    log = BotLog(
        level=level,
        message=message,
        client_id=client_id,
        task_id=task_id
    )
    
    db.session.add(log)
    db.session.commit()
    
    return jsonify({"success": True, "id": log.id})

@app.route('/api/clients/update', methods=['POST'])
def api_update_clients():
    """İstemci pencereleri güncelleme API'si"""
    data = request.json
    
    if not data or not isinstance(data, list):
        return jsonify({"success": False, "error": "Invalid client data"}), 400
    
    # Tüm istemcileri pasif olarak işaretle
    ClientWindow.query.update({ClientWindow.is_active: False})
    
    updated_count = 0
    for client_data in data:
        title = client_data.get('title')
        hwnd = client_data.get('hwnd')
        
        if not title or not hwnd:
            continue
        
        # Var olan istemciyi bul veya yeni oluştur
        client = ClientWindow.query.filter_by(hwnd=hwnd).first()
        
        if client:
            # Mevcut istemciyi güncelle
            client.title = title
            client.width = client_data.get('width')
            client.height = client_data.get('height')
            client.position_x = client_data.get('position_x')
            client.position_y = client_data.get('position_y')
            client.is_active = True
            client.last_seen = datetime.utcnow()
        else:
            # Yeni istemci oluştur
            client = ClientWindow(
                title=title,
                hwnd=hwnd,
                width=client_data.get('width'),
                height=client_data.get('height'),
                position_x=client_data.get('position_x'),
                position_y=client_data.get('position_y'),
                is_active=True
            )
            db.session.add(client)
        
        updated_count += 1
    
    # Veritabanını güncelle
    db.session.commit()
    
    # Bot durumunu güncelle
    active_clients = ClientWindow.query.filter_by(is_active=True).count()
    bot_status["active_clients"] = min(2, active_clients)  # En fazla 2 aktif istemci
    bot_status["total_clients"] = active_clients
    bot_status["last_updated"] = datetime.now().isoformat()
    
    return jsonify({
        "success": True, 
        "updated_count": updated_count,
        "active_clients": active_clients
    })

@app.route('/api/status/update', methods=['POST'])
def api_update_status():
    """Bot durum bilgisi güncelleme API'si"""
    data = request.json
    
    if not data:
        return jsonify({"success": False, "error": "Invalid status data"}), 400
    
    # Sadece belirli alanları güncelle
    for key in ['active_clients', 'total_clients', 'current_task', 'error_count']:
        if key in data:
            bot_status[key] = data[key]
    
    bot_status["last_updated"] = datetime.now().isoformat()
    
    return jsonify({"success": True})

# Veritabanını oluştur ve varsayılan verileri ekle
def init_db():
    # Önce veritabanı tablolarını yarat
    with app.app_context():
        # Veritabanı tablolarını oluştur
        try:
            db.create_all()
            logger.info("Veritabanı tabloları başarıyla oluşturuldu")
        except Exception as e:
            logger.error(f"Veritabanı tabloları oluşturulurken hata: {str(e)}")
            # Eğer tablo yoksa oluşturmak için SQL kullan
            try:
                from sqlalchemy import text
                
                # Task tablosu için SQL
                create_task_table = text("""
                CREATE TABLE IF NOT EXISTS task (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    description TEXT,
                    type VARCHAR(50) NOT NULL,
                    parameters TEXT,
                    priority INTEGER DEFAULT 1,
                    enabled BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # BotConfig tablosu için SQL
                create_botconfig_table = text("""
                CREATE TABLE IF NOT EXISTS bot_config (
                    id SERIAL PRIMARY KEY,
                    key VARCHAR(100) UNIQUE NOT NULL,
                    value TEXT,
                    value_type VARCHAR(50) DEFAULT 'string',
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # ClientWindow tablosu için SQL
                create_clientwindow_table = text("""
                CREATE TABLE IF NOT EXISTS client_window (
                    id SERIAL PRIMARY KEY,
                    title VARCHAR(100) NOT NULL,
                    hwnd VARCHAR(100),
                    width INTEGER,
                    height INTEGER,
                    position_x INTEGER,
                    position_y INTEGER,
                    is_active BOOLEAN DEFAULT TRUE,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """)
                
                # BotLog tablosu için SQL
                create_botlog_table = text("""
                CREATE TABLE IF NOT EXISTS bot_log (
                    id SERIAL PRIMARY KEY,
                    level VARCHAR(20) NOT NULL DEFAULT 'INFO',
                    message TEXT NOT NULL,
                    client_id INTEGER,
                    task_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (client_id) REFERENCES client_window(id) ON DELETE SET NULL,
                    FOREIGN KEY (task_id) REFERENCES task(id) ON DELETE SET NULL
                )
                """)
                
                # Tabloları oluştur
                with db.engine.connect() as conn:
                    conn.execute(create_task_table)
                    conn.execute(create_botconfig_table)
                    conn.execute(create_clientwindow_table)
                    conn.execute(create_botlog_table)
                    conn.commit()
                
                logger.info("Veritabanı tabloları SQL ile başarıyla oluşturuldu")
            except Exception as inner_e:
                logger.error(f"SQL ile tablo oluşturmada hata: {str(inner_e)}")
                raise
        
        # Varsayılan konfigürasyon değerlerini ekle
        default_configs = [
            {
                'key': 'client_window_titles', 
                'value': json.dumps(['game', 'LDPlayer']),
                'value_type': 'json',
                'description': 'Bot tarafından aranacak pencere başlıkları'
            },
            {
                'key': 'confidence_threshold', 
                'value': '0.7',
                'value_type': 'float',
                'description': 'Görüntü tanıma için güven eşiği (0-1)'
            },
            {
                'key': 'click_delay_min', 
                'value': '0.2',
                'value_type': 'float',
                'description': 'Tıklamalar arası minimum gecikme (saniye)'
            },
            {
                'key': 'click_delay_max', 
                'value': '0.5',
                'value_type': 'float',
                'description': 'Tıklamalar arası maksimum gecikme (saniye)'
            },
            {
                'key': 'cycle_delay_min', 
                'value': '1.0',
                'value_type': 'float',
                'description': 'Döngüler arası minimum gecikme (saniye)'
            },
            {
                'key': 'cycle_delay_max', 
                'value': '3.0',
                'value_type': 'float',
                'description': 'Döngüler arası maksimum gecikme (saniye)'
            },
            {
                'key': 'error_threshold', 
                'value': '5',
                'value_type': 'int',
                'description': 'Bot\'un durması için gereken ardışık hata sayısı'
            }
        ]
        
        try:
            # Konfigürasyonları ekle
            for config_data in default_configs:
                existing = BotConfig.query.filter_by(key=config_data['key']).first()
                if not existing:
                    config = BotConfig(**config_data)
                    db.session.add(config)
            
            # Varsayılan görevleri ekle
            default_tasks = [
                {
                    'name': 'Kaynak Toplama',
                    'description': 'Oyun dünyasındaki kaynakları toplama görevi',
                    'type': 'resource_gathering',
                    'parameters': json.dumps({
                        'resource_types': ['ore', 'herb', 'wood'],
                        'max_gather_time': 120,
                        'return_to_base': True
                    }),
                    'priority': 3,
                    'enabled': True
                },
                {
                    'name': 'Basit Dövüş',
                    'description': 'Yakındaki düşük seviye düşmanlarla dövüş',
                    'type': 'combat',
                    'parameters': json.dumps({
                        'enemy_types': ['wolf', 'boar', 'bandit'],
                        'max_combat_time': 60,
                        'retreat_health_percent': 30
                    }),
                    'priority': 2,
                    'enabled': True
                },
                {
                    'name': 'Envanter Yönetimi',
                    'description': 'Doluysa envanteri temizleme, gereksiz eşyaları satma',
                    'type': 'inventory_management',
                    'parameters': json.dumps({
                        'keep_items': ['health_potion', 'magic_stone', 'weapon'],
                        'sell_items': ['junk', 'gray_items'],
                        'stack_items': True
                    }),
                    'priority': 1,
                    'enabled': True
                }
            ]
            
            # Görevleri ekle
            for task_data in default_tasks:
                existing = Task.query.filter_by(name=task_data['name']).first()
                if not existing:
                    task = Task(**task_data)
                    db.session.add(task)
            
            # Değişiklikleri kaydet
            db.session.commit()
            
            logger.info("Varsayılan veriler başarıyla oluşturuldu")
        except Exception as e:
            logger.error(f"Varsayılan verileri eklerken hata: {str(e)}")
            db.session.rollback()
            raise

# Ana çalıştırma bloğu
if __name__ == "__main__":
    init_db()  # İlk çalıştırmada veritabanını oluştur
    app.run(host="0.0.0.0", port=5000, debug=True)