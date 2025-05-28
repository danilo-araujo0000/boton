import os
from dotenv import load_dotenv
import pathlib

# Obter o caminho absoluto do diretório do projeto
BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()

# Carregar variáveis de ambiente
env_path = os.path.join(BASE_DIR, 'env_config', 'env_settings.env')
load_dotenv(dotenv_path=env_path)

class Config:
    # Configurações do Banco de Dados
    DATABASE_NAME = os.getenv("DATABASE_NAME", "dbinit")
    DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_USER = os.getenv("DATABASE_USER", "root")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "")
    DATABASE_PORT = int(os.getenv("DATABASE_PORT", "3306"))
    
    # Configurações do Servidor
    SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
    SERVER_PORT = int(os.getenv("SERVER_PORT", "13579"))
    
    # Configurações do WebSocket
    WEBSOCKET_HOST = os.getenv("WEBSOCKET_HOST", "localhost")
    WEBSOCKET_PORT = int(os.getenv("WEBSOCKET_PORT", "13579"))
    
    # Configurações do Flask Admin
    FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
    FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
    SECRET_KEY = os.getenv("SECRET_KEY", "chave-padrao-substituir-em-producao")
    
    # Configurações de Logs
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Configurações de Segurança
    BCRYPT_LOG_ROUNDS = int(os.getenv("BCRYPT_LOG_ROUNDS", "12"))
    
    # Configurações de Reconexão
    RECONNECT_DELAY = int(os.getenv("RECONNECT_DELAY", "5"))
    MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "10"))
    
    # Configurações de Som
    SOUND_FILE = os.getenv("SOUND_FILE", "")
    SOUND_VOLUME = float(os.getenv("SOUND_VOLUME", "0.9"))
    
    @classmethod
    def get_database_url(cls):
        return f"mysql+pymysql://{cls.DATABASE_USER}:{cls.DATABASE_PASSWORD}@{cls.DATABASE_HOST}:{cls.DATABASE_PORT}/{cls.DATABASE_NAME}" 