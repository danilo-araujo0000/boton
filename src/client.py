#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cliente do Sistema de Botão de Pânico
Permite disparar alertas através de botão ou atalho de teclado
"""

import socket
import threading
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import argparse
import keyboard
import platform
import subprocess
from datetime import datetime
from src.config import Config

# Configuração de logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs_data')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, Config().LOG_LEVEL),
    format=Config().LOG_FORMAT,
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'cliente.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("cliente")

class ClienteBotaoPanico:
    def __init__(self):
        """Inicializa o cliente do botão de pânico"""
        self.config = Config()
        self.sala = ""
        self.codigo = ""
        self.socket = None
        self.connected = False
        self.running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = self.config.MAX_RECONNECT_ATTEMPTS
        
        # Informações do sistema
        self.hostname = os.environ.get('COMPUTERNAME', platform.node())
        self.usuario_windows = os.environ.get('USERNAME', os.getlogin())
        
        # Configuração de atalho
        self.atalho = 'ctrl+shift+p'  # Atalho padrão
        
        # Interface gráfica
        self.root = tk.Tk()
        self.setup_gui()
        
        # Thread de conexão
        self.connection_thread = None
        
        # Registrar atalho global
        keyboard.add_hotkey(self.atalho, self.disparar_alerta_por_atalho)
    
    def setup_gui(self):
        """Configura a interface gráfica"""
        self.root.title("Botão de Pânico")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Tentar aplicar ícone
        try:
            self.root.iconbitmap("static/ico/alert.ico")
        except:
            pass
        
        # Estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Título
        title_label = ttk.Label(main_frame, text="BOTÃO DE PÂNICO", 
                               font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))
        
        # Frame de configurações
        config_frame = ttk.LabelFrame(main_frame, text="Configurações", padding="10")
        config_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Sala
        sala_frame = ttk.Frame(config_frame)
        sala_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(sala_frame, text="Sala:", width=15).pack(side=tk.LEFT)
        self.sala_var = tk.StringVar()
        self.sala_entry = ttk.Entry(sala_frame, textvariable=self.sala_var)
        self.sala_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Código
        codigo_frame = ttk.Frame(config_frame)
        codigo_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(codigo_frame, text="Código:", width=15).pack(side=tk.LEFT)
        self.codigo_var = tk.StringVar()
        self.codigo_entry = ttk.Entry(codigo_frame, textvariable=self.codigo_var)
        self.codigo_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Informações do sistema
        info_frame = ttk.LabelFrame(main_frame, text="Informações do Sistema", padding="10")
        info_frame.pack(fill=tk.X, pady=(0, 20))
        
        hostname_frame = ttk.Frame(info_frame)
        hostname_frame.pack(fill=tk.X, pady=2)
        ttk.Label(hostname_frame, text="Hostname:", width=15).pack(side=tk.LEFT)
        ttk.Label(hostname_frame, text=self.hostname).pack(side=tk.LEFT)
        
        usuario_frame = ttk.Frame(info_frame)
        usuario_frame.pack(fill=tk.X, pady=2)
        ttk.Label(usuario_frame, text="Usuário:", width=15).pack(side=tk.LEFT)
        ttk.Label(usuario_frame, text=self.usuario_windows).pack(side=tk.LEFT)
        
        servidor_frame = ttk.Frame(info_frame)
        servidor_frame.pack(fill=tk.X, pady=2)
        ttk.Label(servidor_frame, text="Servidor:", width=15).pack(side=tk.LEFT)
        ttk.Label(servidor_frame, text=f"{self.config.WEBSOCKET_HOST}:{self.config.WEBSOCKET_PORT}").pack(side=tk.LEFT)
        
        atalho_frame = ttk.Frame(info_frame)
        atalho_frame.pack(fill=tk.X, pady=2)
        ttk.Label(atalho_frame, text="Atalho:", width=15).pack(side=tk.LEFT)
        ttk.Label(atalho_frame, text=self.atalho).pack(side=tk.LEFT)
        
        # Status da conexão
        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 10))
        self.status_var = tk.StringVar(value="Desconectado")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                     font=('Arial', 10, 'bold'))
        self.status_label.pack(side=tk.LEFT)
        
        # Botão de Pânico
        panic_button = tk.Button(main_frame, text="BOTÃO DE PÂNICO", 
                               font=('Arial', 16, 'bold'),
                               bg='red', fg='white',
                               height=2,
                               command=self.disparar_alerta)
        panic_button.pack(fill=tk.X, pady=(0, 10))
        
        # Botões de controle
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X)
        
        self.btn_conectar = ttk.Button(control_frame, text="Conectar", 
                                      command=self.conectar)
        self.btn_conectar.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_desconectar = ttk.Button(control_frame, text="Desconectar", 
                                         command=self.desconectar, 
                                         state='disabled')
        self.btn_desconectar.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_salvar = ttk.Button(control_frame, text="Salvar Configurações", 
                                    command=self.salvar_configuracoes)
        self.btn_salvar.pack(side=tk.LEFT, padx=(0, 5))
        
        # Carregar configurações salvas
        self.carregar_configuracoes()
        
        # Definir protocolo de fechamento
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def carregar_configuracoes(self):
        """Carrega configurações salvas do arquivo"""
        try:
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'env_config')
            config_file = os.path.join(config_dir, 'cliente_config.json')
            
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    dados = json.load(f)
                    
                    self.sala_var.set(dados.get('sala', ''))
                    self.codigo_var.set(dados.get('codigo', ''))
                    self.sala = dados.get('sala', '')
                    self.codigo = dados.get('codigo', '')
                    
                    logger.info("Configurações carregadas com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
    
    def salvar_configuracoes(self):
        """Salva configurações em arquivo"""
        try:
            # Pegar valores atuais
            self.sala = self.sala_var.get().strip()
            self.codigo = self.codigo_var.get().strip()
            
            # Validar dados
            if not self.sala or not self.codigo:
                messagebox.showwarning("Atenção", "Preencha a Sala e o Código antes de salvar.")
                return
            
            # Preparar diretório
            config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'env_config')
            os.makedirs(config_dir, exist_ok=True)
            config_file = os.path.join(config_dir, 'cliente_config.json')
            
            # Salvar dados
            dados = {
                'sala': self.sala,
                'codigo': self.codigo,
                'hostname': self.hostname,
                'usuario': self.usuario_windows
            }
            
            with open(config_file, 'w') as f:
                json.dump(dados, f, indent=4)
            
            messagebox.showinfo("Sucesso", "Configurações salvas com sucesso!")
            logger.info("Configurações salvas com sucesso")
            
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao salvar configurações: {e}")
            logger.error(f"Erro ao salvar configurações: {e}")
    
    def conectar(self):
        """Inicia conexão com o servidor"""
        self.running = True
        self.btn_conectar.config(state='disabled')
        self.btn_desconectar.config(state='normal')
        
        # Iniciar thread de conexão
        if not self.connection_thread or not self.connection_thread.is_alive():
            self.connection_thread = threading.Thread(target=self.thread_conexao, daemon=True)
            self.connection_thread.start()
    
    def desconectar(self):
        """Desconecta do servidor"""
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.connected = False
        self.status_var.set("Desconectado")
        self.status_label.config(foreground='red')
        
        self.btn_conectar.config(state='normal')
        self.btn_desconectar.config(state='disabled')
        
        logger.info("Desconectado do servidor")
    
    def thread_conexao(self):
        """Thread de gerenciamento de conexão"""
        while self.running:
            try:
                # Tentar conectar
                if not self.connected:
                    self.status_var.set("Conectando...")
                    self.status_label.config(foreground='orange')
                    
                    self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.socket.settimeout(10.0)
                    self.socket.connect((self.config.WEBSOCKET_HOST, self.config.WEBSOCKET_PORT))
                    
                    # Enviar hostname
                    self.socket.send(self.hostname.encode('utf-8'))
                    
                    self.connected = True
                    self.reconnect_attempts = 0
                    
                    self.status_var.set("Conectado")
                    self.status_label.config(foreground='green')
                    
                    logger.info(f"Conectado ao servidor {self.config.WEBSOCKET_HOST}:{self.config.WEBSOCKET_PORT}")
                
                # Manter conexão e responder pings
                while self.connected and self.running:
                    try:
                        data = self.socket.recv(1024)
                        if not data:
                            logger.warning("Conexão fechada pelo servidor")
                            self.connected = False
                            break
                        
                        mensagem = data.decode('utf-8').strip()
                        
                        # Responder a pings
                        if mensagem == "PING":
                            self.socket.send(b"PONG")
                    
                    except socket.timeout:
                        # Timeout normal, apenas continuar
                        continue
                    except Exception as e:
                        logger.error(f"Erro na comunicação: {e}")
                        self.connected = False
                        break
            
            except Exception as e:
                self.connected = False
                self.status_var.set("Erro de Conexão")
                self.status_label.config(foreground='red')
                
                self.reconnect_attempts += 1
                
                logger.error(f"Erro de conexão: {e}")
                
                # Decidir se tenta reconectar
                if self.running:
                    if self.reconnect_attempts <= self.max_reconnect_attempts:
                        delay = self.config.RECONNECT_DELAY
                        logger.info(f"Tentando reconexão em {delay}s ({self.reconnect_attempts}/{self.max_reconnect_attempts})")
                        self.status_var.set(f"Reconectando em {delay}s...")
                        time.sleep(delay)
                    else:
                        logger.error("Máximo de tentativas de reconexão atingido")
                        self.status_var.set("Falha na Conexão")
                        self.running = False
                        
                        # Atualizar botões na thread principal
                        self.root.after(0, self.atualizar_estado_botoes)
            
            finally:
                # Fechar socket se ainda estiver aberto
                if not self.connected and self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                    self.socket = None
    
    def atualizar_estado_botoes(self):
        """Atualiza estado dos botões de acordo com o estado da conexão"""
        self.btn_conectar.config(state='normal')
        self.btn_desconectar.config(state='disabled')
    
    def disparar_alerta(self):
        """Dispara alerta de emergência via botão da interface"""
        self.enviar_alerta("GUI")
    
    def disparar_alerta_por_atalho(self):
        """Dispara alerta de emergência via atalho de teclado"""
        self.enviar_alerta("ATALHO")
    
    def enviar_alerta(self, origem):
        """Envia alerta para o servidor"""
        # Verificar se dados estão preenchidos
        if not self.sala_var.get().strip() or not self.codigo_var.get().strip():
            messagebox.showwarning("Atenção", "Preencha a Sala e o Código antes de disparar o alerta.")
            return
        
        # Atualizar variáveis
        self.sala = self.sala_var.get().strip()
        self.codigo = self.codigo_var.get().strip()
        
        # Verificar conexão
        if not self.connected or not self.socket:
            messagebox.showerror("Erro", "Não há conexão com o servidor. Conecte-se primeiro.")
            return
        
        # Montar mensagem
        mensagem = f"ALERTA|{self.sala}|{self.codigo}|{self.usuario_windows}"
        
        try:
            # Enviar para o servidor
            self.socket.send(mensagem.encode('utf-8'))
            
            # Log
            logger.warning(f"Alerta enviado: Sala={self.sala}, Código={self.codigo}, Origem={origem}")
            
            # Notificar usuário
            messagebox.showinfo("Alerta Enviado", f"Alerta enviado com sucesso!\n\nSala: {self.sala}\nCódigo: {self.codigo}")
            
        except Exception as e:
            logger.error(f"Erro ao enviar alerta: {e}")
            messagebox.showerror("Erro", f"Erro ao enviar alerta: {e}")
            self.connected = False
    
    def on_closing(self):
        """Manipula evento de fechamento da janela"""
        # Desconectar do servidor
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        
        # Remover atalho
        try:
            keyboard.remove_hotkey(self.atalho)
        except:
            pass
        
        # Fechar janela
        self.root.destroy()
    
    def run(self):
        """Executa a aplicação"""
        # Iniciar conexão automaticamente
        self.conectar()
        
        # Iniciar loop principal
        self.root.mainloop()

def main():
    """Função principal"""
    try:
        cliente = ClienteBotaoPanico()
        cliente.run()
    except Exception as e:
        logger.critical(f"Erro crítico: {e}")
        messagebox.showerror("Erro Crítico", f"Ocorreu um erro crítico: {e}")

if __name__ == "__main__":
    main() 