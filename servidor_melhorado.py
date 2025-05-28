import socket
import threading
import json
import time
import logging
import signal
import sys
from datetime import datetime
from typing import Dict, Set
from config import Config
from database.models import db, Sala, ClienteMestre, LogAlerta
from database.database_manager import DatabaseManager
from flask import Flask

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('servidor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ServidorBotaoPanico:
    def __init__(self):
        self.config = Config()
        self.db_manager = DatabaseManager()
        self.running = False
        self.server_socket = None
        
        # Dicionários para cache e controle de conexões
        self.salas_cache = {}
        self.clientes_mestres_cache = set()
        self.clientes_mestres_conectados = {}
        self.conexoes_ativas = set()
        
        # Controle de threads
        self.threads_ativas = []
        self.lock = threading.Lock()
        
        # Configurar Flask para operações de banco
        self.app = Flask(__name__)
        self.app.config['SQLALCHEMY_DATABASE_URI'] = self.config.get_database_url()
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(self.app)
        
        # Configurar handlers de sinal para shutdown gracioso
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de sistema para shutdown gracioso"""
        logger.info(f"Recebido sinal {signum}. Iniciando shutdown gracioso...")
        self.shutdown()
        sys.exit(0)
    
    def inicializar_banco(self):
        """Inicializa o banco de dados e faz migração se necessário"""
        try:
            # Criar banco se não existir
            if not self.db_manager.create_database_if_not_exists():
                logger.error("Falha ao criar/verificar banco de dados")
                return False
            
            with self.app.app_context():
             
                db.create_all()
                logger.info("Tabelas do banco de dados criadas/verificadas")           
                self._atualizar_cache()
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar banco de dados: {e}")
            return False
    

    
    def _atualizar_cache(self):
        """Atualiza o cache com dados do banco de dados"""
        try:
            with self.app.app_context():
                self.salas_cache = self.db_manager.get_salas_dict()
                self.clientes_mestres_cache = set(self.db_manager.get_clientes_mestres_list())
                logger.info(f"Cache atualizado: {len(self.salas_cache)} salas, {len(self.clientes_mestres_cache)} clientes mestres")
        except Exception as e:
            logger.error(f"Erro ao atualizar cache: {e}")
    
    def _thread_atualizacao_cache(self):
        """Thread para atualizar cache periodicamente"""
        while self.running:
            try:
                time.sleep(300)  # Atualiza a cada 5 minutos
                if self.running:
                    self._atualizar_cache()
            except Exception as e:
                logger.error(f"Erro na thread de atualização de cache: {e}")
    
    def processar_mensagem(self, mensagem, addr):
        """Processa mensagem recebida do cliente"""
        try:
            partes = mensagem.split('|')
            if len(partes) >= 3:
                hostname, codigo, usuario_windows = partes[0], partes[1], partes[2]
                
                if codigo.lower().startswith("codigo violeta"):
                    # Buscar sala no cache
                    sala = self.salas_cache.get(hostname, "Sala Desconhecida")
                    
                    # Salvar log no banco de dados
                    with self.app.app_context():
                        sucesso = self.db_manager.salvar_log_alerta(
                            hostname=hostname,
                            codigo=codigo,
                            usuario_windows=usuario_windows,
                            ip_origem=addr[0] if addr else None
                        )
                    
                    if sucesso:
                        comando = f"ABRIR_TELA|{sala}|{codigo}|{usuario_windows}"
                        logger.info(f"Alerta processado: {hostname} - {sala} - {usuario_windows}")
                        return comando
                    else:
                        logger.error(f"Falha ao salvar log para {hostname}")
                        return None
            
            logger.warning(f"Mensagem inválida recebida de {addr}: {mensagem}")
            return None
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de {addr}: {e}")
            return None
    
    def handle_client(self, client_socket, addr):
        """Gerencia conexão de cliente"""
        try:
            with self.lock:
                self.conexoes_ativas.add(client_socket)
            
            logger.info(f"Nova conexão de {addr}")
            
            # Receber mensagem inicial
            client_socket.settimeout(30.0)  # Timeout de 30 segundos
            mensagem = client_socket.recv(1024).decode('utf-8').strip()
            
            if not mensagem:
                logger.warning(f"Mensagem vazia recebida de {addr}")
                return
            
            logger.info(f"Mensagem recebida de {addr}: {mensagem}")
            
            if '|' in mensagem:  # Cliente simples enviando alerta
                comando = self.processar_mensagem(mensagem, addr)
                
                if comando:
                    # Enviar comando para todos os clientes mestres conectados
                    clientes_desconectados = []
                    
                    with self.lock:
                        for hostname, cliente_mestre in self.clientes_mestres_conectados.items():
                            try:
                                cliente_mestre.send(comando.encode('utf-8'))
                                logger.info(f"Comando enviado para cliente mestre {hostname}")
                            except Exception as e:
                                logger.error(f"Erro ao enviar comando para {hostname}: {e}")
                                clientes_desconectados.append(hostname)
                    
                    # Remover clientes desconectados
                    for hostname in clientes_desconectados:
                        with self.lock:
                            if hostname in self.clientes_mestres_conectados:
                                del self.clientes_mestres_conectados[hostname]
                                logger.info(f"Cliente mestre {hostname} removido (desconectado)")
                    
                    # Enviar confirmação ao cliente
                    try:
                        client_socket.send("Alerta processado com sucesso".encode('utf-8'))
                    except:
                        pass  # Cliente pode ter desconectado
                
                else:
                    try:
                        client_socket.send("Erro ao processar alerta".encode('utf-8'))
                    except:
                        pass
            
            else:  # Cliente mestre se conectando
                hostname = mensagem
                
                if hostname in self.clientes_mestres_cache:
                    with self.lock:
                        self.clientes_mestres_conectados[hostname] = client_socket
                    
                    logger.info(f"Cliente mestre conectado: {hostname}")
                    
                    # Atualizar último ping no banco
                    with self.app.app_context():
                        self.db_manager.atualizar_ping_cliente_mestre(hostname)
                    
                    # Manter conexão ativa
                    try:
                        while self.running:
                            # Enviar ping a cada 30 segundos
                            client_socket.send(b"PING")
                            time.sleep(30)
                            
                            # Atualizar ping no banco
                            with self.app.app_context():
                                self.db_manager.atualizar_ping_cliente_mestre(hostname)
                                
                    except Exception as e:
                        logger.info(f"Cliente mestre {hostname} desconectado: {e}")
                    finally:
                        with self.lock:
                            if hostname in self.clientes_mestres_conectados:
                                del self.clientes_mestres_conectados[hostname]
                else:
                    logger.warning(f"Cliente não autorizado tentou se conectar: {hostname}")
                    try:
                        client_socket.send("Não autorizado".encode('utf-8'))
                    except:
                        pass
        
        except socket.timeout:
            logger.warning(f"Timeout na conexão com {addr}")
        except Exception as e:
            logger.error(f"Erro ao gerenciar cliente {addr}: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
            
            with self.lock:
                self.conexoes_ativas.discard(client_socket)
    
    def iniciar_servidor(self):
        """Inicia o servidor principal"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.config.SERVER_HOST, self.config.SERVER_PORT))
            self.server_socket.listen(50)  # Aumentado para suportar mais conexões
            
            self.running = True
            
            logger.info(f"Servidor iniciado em {self.config.SERVER_HOST}:{self.config.SERVER_PORT}")
            
            # Iniciar thread de atualização de cache
            cache_thread = threading.Thread(target=self._thread_atualizacao_cache, daemon=True)
            cache_thread.start()
            
            while self.running:
                try:
                    self.server_socket.settimeout(1.0)  # Timeout para permitir verificação de self.running
                    client_socket, addr = self.server_socket.accept()
                    
                    # Criar thread para gerenciar cliente
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                    # Limpar threads finalizadas
                    self.threads_ativas = [t for t in self.threads_ativas if t.is_alive()]
                    self.threads_ativas.append(client_thread)
                    
                except socket.timeout:
                    continue  # Timeout normal, continuar loop
                except Exception as e:
                    if self.running:
                        logger.error(f"Erro ao aceitar conexão: {e}")
                        time.sleep(1)
        
        except Exception as e:
            logger.error(f"Erro crítico no servidor: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Realiza shutdown gracioso do servidor"""
        logger.info("Iniciando shutdown do servidor...")
        
        self.running = False
        
        # Fechar socket do servidor
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        # Fechar todas as conexões ativas
        with self.lock:
            for client_socket in self.conexoes_ativas.copy():
                try:
                    client_socket.close()
                except:
                    pass
            self.conexoes_ativas.clear()
            self.clientes_mestres_conectados.clear()
        
        # Aguardar threads finalizarem
        for thread in self.threads_ativas:
            if thread.is_alive():
                thread.join(timeout=5)
        
        logger.info("Shutdown concluído")
    
    def status_servidor(self):
        """Retorna status atual do servidor"""
        with self.lock:
            return {
                'running': self.running,
                'conexoes_ativas': len(self.conexoes_ativas),
                'clientes_mestres_conectados': len(self.clientes_mestres_conectados),
                'salas_cadastradas': len(self.salas_cache),
                'clientes_autorizados': len(self.clientes_mestres_cache)
            }

def main():
    """Função principal"""
    servidor = ServidorBotaoPanico()
    
    logger.info("Iniciando Servidor do Botão de Pânico...")
    
    # Inicializar banco de dados
    if not servidor.inicializar_banco():
        logger.error("Falha ao inicializar banco de dados. Encerrando...")
        return
    
    try:
        # Iniciar servidor
        servidor.iniciar_servidor()
    except KeyboardInterrupt:
        logger.info("Interrupção pelo usuário")
    except Exception as e:
        logger.error(f"Erro não tratado: {e}")
    finally:
        servidor.shutdown()

if __name__ == "__main__":
    main() 