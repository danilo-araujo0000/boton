#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor principal do sistema de Botão de Pânico
Gerencia conexões com clientes e encaminha alertas
"""

import socket
import threading
import time
import logging
import os
import json
import signal
import sys
from datetime import datetime
from src.config import Config

# Configuração de logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs_data')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, Config().LOG_LEVEL),
    format=Config().LOG_FORMAT,
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'servidor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("servidor")

class ServidorBotaoPanico:
    def __init__(self):
        """Inicializa o servidor de botão de pânico"""
        self.config = Config()
        self.host = self.config.SERVER_HOST
        self.port = self.config.SERVER_PORT
        self.socket_servidor = None
        self.clientes = {}  # {socket: {"hostname": nome, "ultima_msg": timestamp}}
        self.clientes_mestres = {}  # {hostname: socket}
        self.running = False
        self.thread_ping = None
        self.thread_accept = None
        self.lock = threading.Lock()
        
        # Estatísticas
        self.conexoes_totais = 0
        self.alertas_totais = 0
        self.inicio_servidor = datetime.now()
        
        # Registrar funções de tratamento para sinais
        signal.signal(signal.SIGINT, self.handle_shutdown)
        signal.signal(signal.SIGTERM, self.handle_shutdown)
    
    def iniciar(self):
        """Inicia o servidor e começa a aceitar conexões"""
        try:
            self.socket_servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket_servidor.bind((self.host, self.port))
            self.socket_servidor.listen(5)
            self.running = True
            
            logger.info(f"Servidor iniciado em {self.host}:{self.port}")
            print(f"[+] Servidor iniciado em {self.host}:{self.port}")
            
            # Iniciar thread de ping
            self.thread_ping = threading.Thread(target=self.verificar_conexoes, daemon=True)
            self.thread_ping.start()
            
            # Iniciar thread de aceitação de conexões
            self.thread_accept = threading.Thread(target=self.aceitar_conexoes, daemon=True)
            self.thread_accept.start()
            
            # Manter o processo principal rodando
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"Erro ao iniciar servidor: {e}")
            self.desligar()
    
    def aceitar_conexoes(self):
        """Thread para aceitar novas conexões"""
        while self.running:
            try:
                client_socket, addr = self.socket_servidor.accept()
                client_socket.settimeout(30.0)  # 30 segundos de timeout
                
                # Registrar conexão temporariamente
                with self.lock:
                    self.clientes[client_socket] = {
                        "hostname": f"novo-cliente-{addr[0]}",
                        "addr": addr,
                        "ultima_msg": datetime.now(),
                        "identificado": False
                    }
                
                # Iniciar thread para este cliente
                threading.Thread(target=self.gerenciar_cliente, 
                                args=(client_socket,), 
                                daemon=True).start()
                
                logger.info(f"Nova conexão de {addr[0]}:{addr[1]}")
                self.conexoes_totais += 1
                
            except Exception as e:
                if self.running:
                    logger.error(f"Erro ao aceitar conexão: {e}")
    
    def gerenciar_cliente(self, client_socket):
        """Gerencia comunicação com um cliente específico"""
        try:
            # Receber hostname para identificação
            data = client_socket.recv(1024)
            if not data:
                self.remover_cliente(client_socket)
                return
            
            hostname = data.decode('utf-8').strip()
            
            # Registrar cliente com seu hostname
            with self.lock:
                self.clientes[client_socket]["hostname"] = hostname
                self.clientes[client_socket]["identificado"] = True
                self.clientes[client_socket]["ultima_msg"] = datetime.now()
                
                # Se for um cliente mestre (receptor)
                if "RECEPTOR" in hostname.upper():
                    self.clientes_mestres[hostname] = client_socket
                    logger.info(f"Cliente mestre registrado: {hostname}")
            
            logger.info(f"Cliente identificado: {hostname}")
            
            # Loop de comunicação
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    mensagem = data.decode('utf-8').strip()
                    
                    # Atualizar timestamp da última mensagem
                    with self.lock:
                        if client_socket in self.clientes:
                            self.clientes[client_socket]["ultima_msg"] = datetime.now()
                    
                    # Processar mensagem
                    if mensagem == "PONG":
                        # Resposta ao ping, ignorar
                        pass
                    elif mensagem.startswith("ALERTA|"):
                        # Processar alerta
                        self.processar_alerta(mensagem, hostname)
                    else:
                        logger.info(f"Mensagem de {hostname}: {mensagem}")
                
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Erro ao comunicar com {hostname}: {e}")
                    break
        
        except Exception as e:
            logger.error(f"Erro ao gerenciar cliente: {e}")
        
        finally:
            self.remover_cliente(client_socket)
    
    def processar_alerta(self, mensagem, origem):
        """Processa mensagem de alerta e encaminha para clientes mestres"""
        try:
            # Formato: ALERTA|sala|codigo|usuario
            partes = mensagem.split('|')
            if len(partes) >= 4:
                _, sala, codigo, usuario = partes[:4]
                
                self.alertas_totais += 1
                
                # Log do alerta
                logger.warning(f"ALERTA recebido de {origem}: Sala={sala}, Código={codigo}, Usuário={usuario}")
                print(f"[!] ALERTA: Sala={sala}, Código={codigo}, Usuário={usuario}")
                
                # Encaminhar para todos os clientes mestres
                mensagem_encaminhar = f"ABRIR_TELA|{sala}|{codigo}|{usuario}"
                self.enviar_para_clientes_mestres(mensagem_encaminhar)
            else:
                logger.warning(f"Formato de alerta inválido: {mensagem}")
        
        except Exception as e:
            logger.error(f"Erro ao processar alerta: {e}")
    
    def enviar_para_clientes_mestres(self, mensagem):
        """Envia mensagem para todos os clientes mestres"""
        with self.lock:
            for hostname, socket_cliente in list(self.clientes_mestres.items()):
                try:
                    socket_cliente.send(mensagem.encode('utf-8'))
                    logger.info(f"Alerta enviado para cliente mestre: {hostname}")
                except Exception as e:
                    logger.error(f"Erro ao enviar para cliente mestre {hostname}: {e}")
                    # Não remover aqui, deixar para o verificador de conexões
    
    def verificar_conexoes(self):
        """Thread para verificar conexões ativas e enviar pings"""
        while self.running:
            try:
                agora = datetime.now()
                com_lock = False
                
                try:
                    self.lock.acquire()
                    com_lock = True
                    
                    # Verificar todos os clientes
                    for socket_cliente, info in list(self.clientes.items()):
                        try:
                            # Verificar se está inativo por mais de 60 segundos
                            if (agora - info["ultima_msg"]).total_seconds() > 60:
                                # Enviar ping
                                socket_cliente.send(b"PING")
                                logger.debug(f"Ping enviado para {info['hostname']}")
                            
                            # Se não responder por mais de 120 segundos, considerar desconectado
                            if (agora - info["ultima_msg"]).total_seconds() > 120:
                                logger.warning(f"Cliente {info['hostname']} não responde. Removendo.")
                                self.remover_cliente_unsafe(socket_cliente)
                        
                        except Exception as e:
                            logger.error(f"Erro ao verificar cliente {info['hostname']}: {e}")
                            self.remover_cliente_unsafe(socket_cliente)
                
                finally:
                    if com_lock:
                        self.lock.release()
                
                # Aguardar próximo ciclo
                time.sleep(30)  # Verificar a cada 30 segundos
            
            except Exception as e:
                logger.error(f"Erro na verificação de conexões: {e}")
    
    def remover_cliente(self, socket_cliente):
        """Remove um cliente da lista de clientes (thread-safe)"""
        with self.lock:
            self.remover_cliente_unsafe(socket_cliente)
    
    def remover_cliente_unsafe(self, socket_cliente):
        """Remove um cliente da lista de clientes (sem lock)"""
        if socket_cliente in self.clientes:
            hostname = self.clientes[socket_cliente]["hostname"]
            
            # Remover das listas
            del self.clientes[socket_cliente]
            
            # Se for cliente mestre, remover da lista correspondente
            for host, sock in list(self.clientes_mestres.items()):
                if sock == socket_cliente:
                    del self.clientes_mestres[host]
                    logger.info(f"Cliente mestre removido: {host}")
                    break
            
            # Fechar socket
            try:
                socket_cliente.close()
            except:
                pass
            
            logger.info(f"Cliente removido: {hostname}")
    
    def status_json(self):
        """Retorna o status do servidor em formato JSON"""
        with self.lock:
            tempo_online = datetime.now() - self.inicio_servidor
            horas = int(tempo_online.total_seconds() // 3600)
            minutos = int((tempo_online.total_seconds() % 3600) // 60)
            segundos = int(tempo_online.total_seconds() % 60)
            
            status = {
                "status": "online",
                "clientes_conectados": len(self.clientes),
                "clientes_mestres": len(self.clientes_mestres),
                "conexoes_totais": self.conexoes_totais,
                "alertas_totais": self.alertas_totais,
                "tempo_online": f"{horas:02d}:{minutos:02d}:{segundos:02d}",
                "inicio": self.inicio_servidor.strftime("%d/%m/%Y %H:%M:%S"),
                "agora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "clientes": [],
                "clientes_mestres_lista": list(self.clientes_mestres.keys())
            }
            
            # Adicionar informações de cada cliente
            for socket_cliente, info in self.clientes.items():
                status["clientes"].append({
                    "hostname": info["hostname"],
                    "endereco": f"{info['addr'][0]}:{info['addr'][1]}",
                    "ultima_msg": info["ultima_msg"].strftime("%H:%M:%S"),
                    "identificado": info["identificado"],
                    "cliente_mestre": info["hostname"] in self.clientes_mestres
                })
            
            return json.dumps(status, indent=2)
    
    def handle_shutdown(self, signum, frame):
        """Manipulador para sinais de encerramento"""
        print("\nDesligando servidor...")
        self.desligar()
        sys.exit(0)
    
    def desligar(self):
        """Desliga o servidor e fecha todas as conexões"""
        self.running = False
        
        # Fechar todas as conexões
        with self.lock:
            for socket_cliente in list(self.clientes.keys()):
                try:
                    socket_cliente.close()
                except:
                    pass
            
            self.clientes.clear()
            self.clientes_mestres.clear()
        
        # Fechar socket do servidor
        if self.socket_servidor:
            try:
                self.socket_servidor.close()
            except:
                pass
        
        logger.info("Servidor desligado")
        print("[!] Servidor encerrado.")

if __name__ == "__main__":
    servidor = ServidorBotaoPanico()
    servidor.iniciar()
