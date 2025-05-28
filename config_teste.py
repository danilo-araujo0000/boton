import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Configurações do Banco de Dados
    DATABASE_NAME = "dbinit"
    DATABASE_HOST = "localhost"
    DATABASE_USER = "root"
    DATABASE_PASSWORD = "996639078"
    DATABASE_PORT = 3306
    
    # Configurações do Servidor - Usando 0.0.0.0 para aceitar conexões de qualquer IP
    SERVER_HOST = "0.0.0.0"  # Aceita conexões de qualquer IP
    SERVER_PORT = 13579
    
    # Configurações do WebSocket
    WEBSOCKET_HOST = "172.19.0.76"  # IP para clientes se conectarem
    WEBSOCKET_PORT = 13579
    
    # Configurações do Flask Admin
    FLASK_HOST = "0.0.0.0"
    FLASK_PORT = 5000
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'chave-secreta-super-segura-botao-panico-2024'
    
    # Configurações de Logs
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configurações de Segurança
    BCRYPT_LOG_ROUNDS = 12
    
    # Configurações de Reconexão
    RECONNECT_DELAY = 5  # segundos
    MAX_RECONNECT_ATTEMPTS = 10
    
    # Configurações de Som
    SOUND_FILE = r"C:\Botão_panico\sounds\alerta-sonoro.mp3"
    SOUND_VOLUME = 0.9
    
    @classmethod
    def get_database_url(cls):
        return f"mysql+pymysql://{cls.DATABASE_USER}:{cls.DATABASE_PASSWORD}@{cls.DATABASE_HOST}:{cls.DATABASE_PORT}/{cls.DATABASE_NAME}" 