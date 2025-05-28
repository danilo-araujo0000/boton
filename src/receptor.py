#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Receptor de Alertas do Sistema de Botão de Pânico
Recebe e apresenta alertas enviados pelo servidor
"""

import socket
import threading
import time
import logging
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
import os
import sys
import argparse
from datetime import datetime
import winsound
import subprocess
from src.config import Config

# Configuração de logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs_data')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, Config().LOG_LEVEL),
    format=Config().LOG_FORMAT,
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'receptor.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("receptor")

class ReceptorAlerta:
    def __init__(self, modo_gui=True):
        self.config = Config()
        self.running = False
        self.socket = None
        self.hostname = os.environ.get('COMPUTERNAME', 'RECEPTOR-DESCONHECIDO')
        self.reconexao_tentativas = 0
        self.max_tentativas = self.config.MAX_RECONNECT_ATTEMPTS
        self.delay_reconexao = self.config.RECONNECT_DELAY
        
        # Modo de interface (GUI ou terminal)
        self.modo_gui = modo_gui
        
        # Interface gráfica (se no modo GUI)
        if self.modo_gui:
            self.root = tk.Tk()
            self.setup_gui()
        
        # Thread de conexão
        self.thread_conexao = None
        
        # Estatísticas
        self.alertas_recebidos = 0
        self.ultima_conexao = None
        self.tempo_inicio = datetime.now()
        
    def setup_gui(self):
        """Configura a interface gráfica"""
        self.root.title(f"Receptor de Alertas - {self.hostname}")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Configurar estilo
        style = ttk.Style()
        style.theme_use('clam')
        
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar grid
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        
        # Título
        title_label = ttk.Label(main_frame, text=" RECEPTOR", 
                               font=('Arial', 16, 'bold'))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Status de conexão
        status_frame = ttk.LabelFrame(main_frame, text="Status da Conexão", padding="10")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        status_frame.columnconfigure(1, weight=1)
        
        ttk.Label(status_frame, text="Status:").grid(row=0, column=0, sticky=tk.W)
        self.status_var = tk.StringVar(value="Desconectado")
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, 
                                     font=('Arial', 10, 'bold'))
        self.status_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Servidor:").grid(row=1, column=0, sticky=tk.W)
        server_info = f"{self.config.WEBSOCKET_HOST}:{self.config.WEBSOCKET_PORT}"
        ttk.Label(status_frame, text=server_info).grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(status_frame, text="Hostname:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(status_frame, text=self.hostname).grid(row=2, column=1, sticky=tk.W, padx=(10, 0))
        
        # Controles
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=2, column=0, columnspan=3, pady=(0, 10))
        
        self.btn_conectar = ttk.Button(control_frame, text="🔌 Conectar", 
                                      command=self.conectar, style='Accent.TButton')
        self.btn_conectar.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_desconectar = ttk.Button(control_frame, text="🔌 Desconectar", 
                                         command=self.desconectar, state='disabled')
        self.btn_desconectar.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_teste = ttk.Button(control_frame, text="🧪 Teste de Som", 
                                   command=self.teste_som)
        self.btn_teste.pack(side=tk.LEFT, padx=(0, 5))
        
        self.btn_limpar = ttk.Button(control_frame, text="🗑️ Limpar Log", 
                                    command=self.limpar_log)
        self.btn_limpar.pack(side=tk.LEFT, padx=(0, 5))
        
        # Estatísticas
        stats_frame = ttk.LabelFrame(main_frame, text="Estatísticas", padding="10")
        stats_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        stats_inner = ttk.Frame(stats_frame)
        stats_inner.pack(fill=tk.X)
        
        # Primeira linha de estatísticas
        stats_row1 = ttk.Frame(stats_inner)
        stats_row1.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(stats_row1, text="Alertas Recebidos:").pack(side=tk.LEFT)
        self.alertas_var = tk.StringVar(value="0")
        ttk.Label(stats_row1, textvariable=self.alertas_var, 
                 font=('Arial', 10, 'bold')).pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(stats_row1, text="Última Conexão:").pack(side=tk.LEFT)
        self.ultima_conexao_var = tk.StringVar(value="Nunca")
        ttk.Label(stats_row1, textvariable=self.ultima_conexao_var).pack(side=tk.LEFT, padx=(5, 0))
        
        # Segunda linha de estatísticas
        stats_row2 = ttk.Frame(stats_inner)
        stats_row2.pack(fill=tk.X)
        
        ttk.Label(stats_row2, text="Tempo Online:").pack(side=tk.LEFT)
        self.tempo_online_var = tk.StringVar(value="00:00:00")
        ttk.Label(stats_row2, textvariable=self.tempo_online_var).pack(side=tk.LEFT, padx=(5, 20))
        
        ttk.Label(stats_row2, text="Tentativas de Reconexão:").pack(side=tk.LEFT)
        self.tentativas_var = tk.StringVar(value="0")
        ttk.Label(stats_row2, textvariable=self.tentativas_var).pack(side=tk.LEFT, padx=(5, 0))
        
        # Log de eventos
        log_frame = ttk.LabelFrame(main_frame, text="Log de Eventos", padding="10")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=15, width=80)
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configurar tags para cores
        self.log_text.tag_configure("INFO", foreground="blue")
        self.log_text.tag_configure("WARNING", foreground="orange")
        self.log_text.tag_configure("ERROR", foreground="red")
        self.log_text.tag_configure("SUCCESS", foreground="green")
        self.log_text.tag_configure("ALERT", foreground="red", font=('Arial', 10, 'bold'))
        
        # Iniciar atualização de estatísticas
        self.atualizar_estatisticas()
        
    def log_message(self, message, level="INFO"):
        """Adiciona mensagem ao log da interface ou terminal"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        if self.modo_gui:
            # Log na interface gráfica
            self.log_text.insert(tk.END, formatted_message + "\n", level)
            self.log_text.see(tk.END)
            
            # Manter apenas as últimas 1000 linhas
            lines = self.log_text.get("1.0", tk.END).split('\n')
            if len(lines) > 1000:
                self.log_text.delete("1.0", f"{len(lines)-1000}.0")
        else:
            # Log no terminal
            if level == "ERROR":
                print(f"\033[91m{formatted_message}\033[0m")  # Vermelho
            elif level == "WARNING":
                print(f"\033[93m{formatted_message}\033[0m")  # Amarelo
            elif level == "SUCCESS":
                print(f"\033[92m{formatted_message}\033[0m")  # Verde
            elif level == "ALERT":
                print(f"\033[91m\033[1m{formatted_message}\033[0m")  # Vermelho negrito
            else:
                print(formatted_message)
        
        # Log também no arquivo
        if level == "ERROR":
            logger.error(message)
        elif level == "WARNING":
            logger.warning(message)
        else:
            logger.info(message)
    
    def conectar(self):
        """Inicia conexão com o servidor"""
        if self.running:
            return
        
        self.running = True
        self.btn_conectar.config(state='disabled')
        self.btn_desconectar.config(state='normal')
        
        self.thread_conexao = threading.Thread(target=self.thread_conexao_servidor, daemon=True)
        self.thread_conexao.start()
        
        self.log_message("Iniciando conexão com o servidor...", "INFO")
    
    def desconectar(self):
        """Desconecta do servidor"""
        self.running = False
        
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
        
        self.btn_conectar.config(state='normal')
        self.btn_desconectar.config(state='disabled')
        self.status_var.set("Desconectado")
        self.status_label.config(foreground='red')
        
        self.log_message("Desconectado do servidor", "WARNING")
    
    def thread_conexao_servidor(self):
        """Thread principal de conexão"""
        while self.running:
            try:
                self.conectar_servidor()
                
                if self.socket:
                    self.log_message(f"✅ Conectado como cliente mestre: {self.hostname}", "SUCCESS")
                    if self.modo_gui:
                        self.status_var.set("Conectado")
                        self.status_label.config(foreground='green')
                    self.ultima_conexao = datetime.now()
                    if self.modo_gui:
                        self.ultima_conexao_var.set(self.ultima_conexao.strftime("%H:%M:%S"))
                    self.reconexao_tentativas = 0
                    
                    # Enviar hostname para identificação
                    self.socket.send(self.hostname.encode('utf-8'))
                    
                    # Loop de recebimento de mensagens
                    self.loop_recebimento()
                
            except Exception as e:
                self.log_message(f"❌ Erro na conexão: {e}", "ERROR")
                if self.modo_gui:
                    self.status_var.set("Erro de Conexão")
                    self.status_label.config(foreground='red')
                
                if self.running:
                    self.reconexao_tentativas += 1
                    if self.modo_gui:
                        self.tentativas_var.set(str(self.reconexao_tentativas))
                    
                    if self.reconexao_tentativas <= self.max_tentativas:
                        self.log_message(f"🔄 Tentativa de reconexão {self.reconexao_tentativas}/{self.max_tentativas} em {self.delay_reconexao}s...", "WARNING")
                        time.sleep(self.delay_reconexao)
                    else:
                        self.log_message("❌ Máximo de tentativas de reconexão atingido", "ERROR")
                        self.running = False
                        break
            
            finally:
                if self.socket:
                    try:
                        self.socket.close()
                    except:
                        pass
                    self.socket = None
        
        # Atualizar interface quando sair do loop (apenas no modo GUI)
        if self.modo_gui:
            self.root.after(0, self.desconectar)
    
    def conectar_servidor(self):
        """Estabelece conexão com o servidor"""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(10.0)
        self.socket.connect((self.config.WEBSOCKET_HOST, self.config.WEBSOCKET_PORT))
    
    def loop_recebimento(self):
        """Loop principal de recebimento de mensagens"""
        while self.running and self.socket:
            try:
                # Receber dados do servidor
                data = self.socket.recv(1024)
                
                if not data:
                    self.log_message("⚠️ Servidor fechou a conexão", "WARNING")
                    break
                
                mensagem = data.decode('utf-8').strip()
                
                if mensagem == "PING":
                    # Responder ao ping do servidor
                    self.socket.send(b"PONG")
                    continue
                
                # Processar comando de alerta
                if mensagem.startswith("ABRIR_TELA|"):
                    self.processar_alerta(mensagem)
                else:
                    self.log_message(f"📨 Mensagem recebida: {mensagem}", "INFO")
                
            except socket.timeout:
                continue
            except Exception as e:
                self.log_message(f"❌ Erro ao receber dados: {e}", "ERROR")
                break
    
    def processar_alerta(self, comando):
        """Processa um alerta recebido"""
        try:
            # Formato: ABRIR_TELA|sala|codigo|usuario
            partes = comando.split('|')
            if len(partes) >= 4:
                _, sala, codigo, usuario = partes[:4]
                
                self.alertas_recebidos += 1
                if self.modo_gui:
                    self.alertas_var.set(str(self.alertas_recebidos))
                
                timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                alerta_msg = f"🚨 ALERTA RECEBIDO!\n📍 Sala: {sala}\n🔴 Código: {codigo}\n👤 Usuário: {usuario}\n🕐 Horário: {timestamp}"
                
                self.log_message(alerta_msg, "ALERT")
                
                # Tocar som de alerta
                self.tocar_som_alerta()
                
                # Mostrar janela de alerta (apenas no modo GUI)
                if self.modo_gui:
                    self.mostrar_janela_alerta(sala, codigo, usuario, timestamp)
                
            else:
                self.log_message(f"⚠️ Formato de comando inválido: {comando}", "WARNING")
                
        except Exception as e:
            self.log_message(f"❌ Erro ao processar alerta: {e}", "ERROR")
    
    def tocar_som_alerta(self):
        """Toca som de alerta"""
        try:
            # No modo terminal em Linux, usar o comando beep se disponível
            if not self.modo_gui and sys.platform.startswith('linux'):
                try:
                    subprocess.call(['beep', '-f', '1000', '-l', '500', '-r', '3'])
                    return
                except:
                    pass
            
            # Tentar tocar arquivo de som personalizado
            if os.path.exists(self.config.SOUND_FILE):
                # Usar pygame se disponível
                try:
                    import pygame
                    pygame.mixer.init()
                    pygame.mixer.music.load(self.config.SOUND_FILE)
                    pygame.mixer.music.play()
                except ImportError:
                    # Fallback para winsound no Windows
                    if sys.platform.startswith('win'):
                        winsound.PlaySound(self.config.SOUND_FILE, winsound.SND_FILENAME | winsound.SND_ASYNC)
            else:
                # Som padrão do sistema (Windows)
                if sys.platform.startswith('win'):
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                
        except Exception as e:
            self.log_message(f"⚠️ Erro ao tocar som: {e}", "WARNING")
    
    def mostrar_janela_alerta(self, sala, codigo, usuario, timestamp):
        """Mostra janela popup de alerta"""
        try:
            # Criar janela de alerta
            alerta_window = tk.Toplevel(self.root)
            alerta_window.title("🚨 ALERTA DE EMERGÊNCIA")
            alerta_window.geometry("500x300")
            alerta_window.resizable(False, False)
            alerta_window.configure(bg='red')
            
            # Manter sempre no topo
            alerta_window.attributes('-topmost', True)
            alerta_window.focus_force()
            
            # Centralizar na tela
            alerta_window.transient(self.root)
            alerta_window.grab_set()
            
            # Frame principal
            main_frame = tk.Frame(alerta_window, bg='red', padx=20, pady=20)
            main_frame.pack(fill=tk.BOTH, expand=True)
            
            # Título
            title_label = tk.Label(main_frame, text="🚨 ALERTA DE EMERGÊNCIA 🚨", 
                                  font=('Arial', 18, 'bold'), 
                                  fg='white', bg='red')
            title_label.pack(pady=(0, 20))
            
            # Informações do alerta
            info_frame = tk.Frame(main_frame, bg='white', relief=tk.RAISED, bd=2)
            info_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
            
            info_text = f"""
📍 SALA: {sala}

🔴 CÓDIGO: {codigo}

👤 USUÁRIO: {usuario}

🕐 HORÁRIO: {timestamp}
            """
            
            info_label = tk.Label(info_frame, text=info_text, 
                                 font=('Arial', 12), 
                                 justify=tk.LEFT, 
                                 bg='white', fg='black')
            info_label.pack(expand=True, pady=20, padx=20)
            
            # Botões
            btn_frame = tk.Frame(main_frame, bg='red')
            btn_frame.pack(fill=tk.X)
            
            btn_ok = tk.Button(btn_frame, text="✅ CIENTE", 
                              font=('Arial', 12, 'bold'),
                              bg='green', fg='white',
                              command=alerta_window.destroy)
            btn_ok.pack(side=tk.LEFT, padx=(0, 10))
            
            btn_teste = tk.Button(btn_frame, text="🧪 TESTE", 
                                 font=('Arial', 12, 'bold'),
                                 bg='blue', fg='white',
                                 command=lambda: self.marcar_como_teste(alerta_window))
            btn_teste.pack(side=tk.LEFT)
            
            # Auto-fechar após 30 segundos
            alerta_window.after(30000, alerta_window.destroy)
            
        except Exception as e:
            self.log_message(f"❌ Erro ao mostrar janela de alerta: {e}", "ERROR")
    
    def marcar_como_teste(self, window):
        """Marca alerta como teste"""
        self.log_message("🧪 Alerta marcado como TESTE", "INFO")
        window.destroy()
    
    def teste_som(self):
        """Testa o som de alerta"""
        self.log_message("🧪 Testando som de alerta...", "INFO")
        self.tocar_som_alerta()
    
    def limpar_log(self):
        """Limpa o log da interface"""
        self.log_text.delete("1.0", tk.END)
        self.log_message("Log limpo", "INFO")
    
    def atualizar_estatisticas(self):
        """Atualiza estatísticas na interface"""
        if self.running and self.ultima_conexao:
            tempo_online = datetime.now() - self.ultima_conexao
            horas = int(tempo_online.total_seconds() // 3600)
            minutos = int((tempo_online.total_seconds() % 3600) // 60)
            segundos = int(tempo_online.total_seconds() % 60)
            self.tempo_online_var.set(f"{horas:02d}:{minutos:02d}:{segundos:02d}")
        
        # Agendar próxima atualização
        self.root.after(1000, self.atualizar_estatisticas)
    
    def on_closing(self):
        """Callback para fechamento da janela"""
        if self.running:
            if messagebox.askokcancel("Sair", "Deseja realmente sair do receptor?"):
                self.desconectar()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """Executa a aplicação no modo GUI"""
        if not self.modo_gui:
            raise ValueError("O método run() só pode ser chamado no modo GUI")
            
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Log inicial
        self.log_message("🚀 Receptor de Alertas iniciado", "SUCCESS")
        self.log_message(f"💻 Hostname: {self.hostname}", "INFO")
        self.log_message(f"🌐 Servidor: {self.config.WEBSOCKET_HOST}:{self.config.WEBSOCKET_PORT}", "INFO")
        
        # Iniciar interface
        self.root.mainloop()

def main():
    """Função principal"""
    try:
        # Configurar parser de argumentos
        parser = argparse.ArgumentParser(description='Receptor de Alertas - Sistema de Recepção de Alertas de Emergência')
        parser.add_argument('--debug', action='store_true', help='Iniciar com interface gráfica (sem este parâmetro iniciará em modo terminal)')
        args = parser.parse_args()
        
        # Determinar se deve usar GUI ou modo terminal
        modo_gui = args.debug
        
        if modo_gui:
            # Modo GUI
            receptor = ReceptorAlerta(modo_gui=True)
            receptor.run()
        else:
            # Modo terminal
            print("=== RECEPTOR DE ALERTAS - MODO TERMINAL ===")
            print(f"Hostname: {os.environ.get('COMPUTERNAME', 'RECEPTOR-DESCONHECIDO')}")
            print(f"Servidor: {Config().WEBSOCKET_HOST}:{Config().WEBSOCKET_PORT}")
            print("Iniciando conexão...")
            
            receptor = ReceptorAlerta(modo_gui=False)
            # Iniciar conexão automaticamente
            receptor.running = True
            receptor.thread_conexao = threading.Thread(target=receptor.thread_conexao_servidor, daemon=True)
            receptor.thread_conexao.start()
            
            # Manter aplicação rodando
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nEncerrando receptor...")
                receptor.running = False
                if receptor.socket:
                    try:
                        receptor.socket.close()
                    except:
                        pass
    except Exception as e:
        logger.error(f"Erro crítico: {e}")
        if 'receptor' in locals() and hasattr(receptor, 'modo_gui') and receptor.modo_gui:
            messagebox.showerror("Erro", f"Erro crítico na aplicação: {e}")
        else:
            print(f"ERRO CRÍTICO: {e}")

if __name__ == "__main__":
    main() 