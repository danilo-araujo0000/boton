import socket
import subprocess
import time
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import threading
import os
import pygame
import logging
import signal
import sys
from datetime import datetime
from config import Config

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cliente_receptor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Inicializar pygame mixer
pygame.mixer.init()

class ClienteReceptor:
    def __init__(self):
        self.config = Config()
        self.running = False
        self.socket = None
        self.hostname = socket.gethostname()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = self.config.MAX_RECONNECT_ATTEMPTS
        
        # Carregar som
        self.sound_loaded = False
        self.alerta_sound = None
        self._carregar_som()
        
        # Configurar handlers de sinal
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handler para sinais de sistema"""
        logger.info(f"Recebido sinal {signum}. Encerrando cliente...")
        self.shutdown()
        sys.exit(0)
    
    def _carregar_som(self):
        """Carrega o arquivo de som"""
        try:
            if os.path.exists(self.config.SOUND_FILE):
                self.alerta_sound = pygame.mixer.Sound(self.config.SOUND_FILE)
                self.alerta_sound.set_volume(self.config.SOUND_VOLUME)
                self.sound_loaded = True
                logger.info("Arquivo de som carregado com sucesso")
            else:
                logger.warning(f"Arquivo de som não encontrado: {self.config.SOUND_FILE}")
        except Exception as e:
            logger.error(f"Erro ao carregar arquivo de som: {e}")
    
    def conectar_ao_servidor(self):
        """Conecta ao servidor com retry automático"""
        while self.running and self.reconnect_attempts < self.max_reconnect_attempts:
            try:
                logger.info(f"Tentativa de conexão {self.reconnect_attempts + 1}/{self.max_reconnect_attempts}")
                
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(30.0)  # Timeout de 30 segundos
                
                # Conectar ao servidor
                self.socket.connect((self.config.WEBSOCKET_HOST, self.config.WEBSOCKET_PORT))
                
                # Enviar hostname para identificação
                self.socket.send(self.hostname.encode('utf-8'))
                logger.info(f"Conectado ao servidor como {self.hostname}")
                
                # Reset contador de tentativas
                self.reconnect_attempts = 0
                
                # Loop principal de recepção
                self._loop_recepcao()
                
            except socket.timeout:
                logger.warning("Timeout na conexão")
                self.reconnect_attempts += 1
            except ConnectionRefused:
                logger.error("Conexão recusada pelo servidor")
                self.reconnect_attempts += 1
            except Exception as e:
                logger.error(f"Erro na conexão: {e}")
                self.reconnect_attempts += 1
            finally:
                self._fechar_socket()
            
            if self.running and self.reconnect_attempts < self.max_reconnect_attempts:
                delay = min(self.config.RECONNECT_DELAY * (2 ** self.reconnect_attempts), 60)
                logger.info(f"Aguardando {delay} segundos antes da próxima tentativa...")
                time.sleep(delay)
        
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Número máximo de tentativas de reconexão atingido")
    
    def _loop_recepcao(self):
        """Loop principal para receber comandos do servidor"""
        while self.running:
            try:
                # Receber comando do servidor
                comando = self.socket.recv(1024).decode('utf-8')
                
                if not comando:
                    logger.warning("Conexão fechada pelo servidor")
                    break
                
                if comando == "PING":
                    # Responder ao ping
                    self.socket.send(b"PONG")
                    continue
                
                logger.info(f"Comando recebido: {comando}")
                
                if comando.startswith("ABRIR_TELA"):
                    self._processar_comando_tela(comando)
                
            except socket.timeout:
                logger.warning("Timeout na recepção de dados")
                break
            except Exception as e:
                logger.error(f"Erro na recepção: {e}")
                break
    
    def _processar_comando_tela(self, comando):
        """Processa comando para abrir tela de alerta"""
        try:
            partes = comando.split('|')
            if len(partes) >= 4:
                _, sala, codigo, usuario = partes[:4]
                
                logger.info(f"Abrindo tela para: Sala={sala}, Usuário={usuario}")
                
                # Determinar tipo de alerta
                tipo = "teste" if usuario.lower().strip() == "teste" else "alerta"
                
                # Abrir tela em thread separada
                threading.Thread(
                    target=self._abrir_tela,
                    args=(sala, usuario, tipo),
                    daemon=True
                ).start()
                
                # Tocar som
                if self.sound_loaded:
                    threading.Thread(target=self._tocar_som, daemon=True).start()
            
        except Exception as e:
            logger.error(f"Erro ao processar comando de tela: {e}")
    
    def _abrir_tela(self, sala, usuario, tipo="alerta"):
        """Abre a tela de alerta"""
        try:
            root = tk.Tk()
            
            if tipo == "teste":
                app = TelaTest(root, sala, usuario)
            else:
                app = TelaAlerta(root, sala, usuario)
            
            root.mainloop()
            
        except Exception as e:
            logger.error(f"Erro ao abrir tela: {e}")
    
    def _tocar_som(self):
        """Toca o som de alerta"""
        try:
            if self.sound_loaded and self.alerta_sound:
                for _ in range(3):
                    self.alerta_sound.play()
                    time.sleep(1)
        except Exception as e:
            logger.error(f"Erro ao tocar som: {e}")
    
    def _fechar_socket(self):
        """Fecha o socket de forma segura"""
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
    
    def iniciar(self):
        """Inicia o cliente receptor"""
        self.running = True
        logger.info("Cliente receptor iniciado")
        
        try:
            self.conectar_ao_servidor()
        except KeyboardInterrupt:
            logger.info("Interrupção pelo usuário")
        except Exception as e:
            logger.error(f"Erro não tratado: {e}")
        finally:
            self.shutdown()
    
    def shutdown(self):
        """Encerra o cliente de forma graceful"""
        logger.info("Encerrando cliente receptor...")
        self.running = False
        self._fechar_socket()

class TelaAlerta:
    def __init__(self, master, sala, usuario):
        self.master = master
        self.master.title("ALERTA - Código Violeta")
        
        # Configurações da janela
        self.master.attributes('-fullscreen', True)
        self.master.protocol("WM_DELETE_WINDOW", self.nao_fechar)
        self.master.attributes('-topmost', True)
        self.master.focus_force()
        self.master.bind("<FocusOut>", self.manter_foco)
        
        # Configurar fontes
        self._configurar_fontes()
        
        # Criar interface
        self._criar_interface(sala, usuario)
        
        # Iniciar efeitos
        self.piscar_contador = 0
        self.piscar()
    
    def _configurar_fontes(self):
        """Configura as fontes da interface"""
        self.icone_fonte = tkfont.Font(family="Arial", size=120, weight="bold")
        self.texto_fonte = tkfont.Font(family="Arial", size=48, weight="bold")
        self.sala_fonte = tkfont.Font(family="Helvetica", size=52, weight="bold")
        self.usuario_fonte = tkfont.Font(family="Arial", size=36, weight="bold")
        self.botao_fonte = tkfont.Font(family="Helvetica", size=24, weight="bold")
    
    def _criar_interface(self, sala, usuario):
        """Cria a interface da tela de alerta"""
        self.frame = tk.Frame(self.master, bg="#B22222")
        self.frame.pack(expand=True, fill="both")

        # Ícone de alerta
        self.icone_alerta = tk.Label(
            self.frame, text="⚠", font=self.icone_fonte, 
            fg="#FFD700", bg="#B22222"
        )
        self.icone_alerta.pack(pady=(50, 20))

        # Texto de aviso
        self.texto_aviso = tk.Label(
            self.frame, text="ATENÇÃO!\n\nCÓDIGO VIOLETA!\n\n", 
            font=self.texto_fonte, fg="white", bg="#B22222", justify="center"
        )
        self.texto_aviso.pack(pady=(0, 10))

        # Nome da sala
        self.texto_sala = tk.Label(
            self.frame, text=f"SALA: {sala.upper()}", 
            font=self.sala_fonte, fg="#FFF3B0", bg="#B22222", justify="center"
        )
        self.texto_sala.pack(pady=(0, 30))
        
        # Nome do usuário
        self.nome_usuario_label = tk.Label(
            self.frame, text=f"Usuário: {usuario}", 
            font=self.usuario_fonte, fg="white", bg="#B22222"
        )
        self.nome_usuario_label.pack(pady=(0, 5))

        # Timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.timestamp_label = tk.Label(
            self.frame, text=f"Horário: {timestamp}", 
            font=("Arial", 24), fg="white", bg="#B22222"
        )
        self.timestamp_label.pack(pady=(0, 30))
 
        # Botão fechar
        self._criar_botao_fechar()
        
        # Label de status
        self.label = tk.Label(
            self.frame, text="", font=("Arial", 18), bg="#B22222", fg="white"
        )
        self.label.pack(pady=30)
    
    def _criar_botao_fechar(self):
        """Cria o botão de fechar"""
        botao_frame = tk.Frame(self.frame, bg="#B22222")
        botao_frame.pack(side="bottom", pady=(0, 50))

        self.botao = tk.Button(
            botao_frame, text="FECHAR", 
            font=self.botao_fonte,
            bg="#1E1E1E", fg="#FFFFFF",
            activebackground="#2C2C2C", activeforeground="#FFFFFF",
            relief="flat", borderwidth=0,
            command=self.fechar_aplicacao, 
            padx=50, pady=15, cursor="hand2"
        )
        
        # Efeitos hover
        def on_enter(e):
            self.botao.config(bg="#404040")
            
        def on_leave(e):
            self.botao.config(bg="#1E1E1E")
        
        self.botao.bind("<Enter>", on_enter)
        self.botao.bind("<Leave>", on_leave)
        self.botao.pack()

    def piscar(self):
        """Efeito de piscar da tela"""
        if self.piscar_contador < 8:  # 4 segundos
            cor_atual = self.frame.cget("background")
            nova_cor = "#CD5C5C" if cor_atual == "#B22222" else "#B22222"
            
            # Atualizar cores de todos os elementos
            elementos = [
                self.frame, self.icone_alerta, self.texto_aviso,
                self.texto_sala, self.nome_usuario_label, 
                self.timestamp_label, self.label
            ]
            
            for elemento in elementos:
                elemento.configure(bg=nova_cor)
            
            self.piscar_contador += 1
            self.master.after(500, self.piscar)

    def fechar_aplicacao(self):
        """Fecha a aplicação"""
        self.label.config(text="Fechando...")
        self.master.after(1000, self.master.destroy)

    def nao_fechar(self):
        """Impede fechamento pela janela"""
        self.label.config(text="Use o botão FECHAR!")

    def manter_foco(self, event):
        """Mantém o foco na janela"""
        self.master.focus_force()

class TelaTest(TelaAlerta):
    def __init__(self, master, sala, usuario):
        self.master = master
        self.master.title("TESTE - Sistema de Alerta")
        
        # Configurações da janela
        self.master.attributes('-fullscreen', True)
        self.master.protocol("WM_DELETE_WINDOW", self.nao_fechar)
        self.master.attributes('-topmost', True)
        self.master.focus_force()
        self.master.bind("<FocusOut>", self.manter_foco)
        
        # Configurar fontes
        self._configurar_fontes()
        
        # Criar interface de teste
        self._criar_interface_teste(sala, usuario)
    
    def _criar_interface_teste(self, sala, usuario):
        """Cria interface específica para teste"""
        self.frame = tk.Frame(self.master, bg="#2E8B57")  # Verde
        self.frame.pack(expand=True, fill="both")

        # Ícone de check
        self.icone_check = tk.Label(
            self.frame, text="✓", font=self.icone_fonte, 
            fg="#98FB98", bg="#2E8B57"
        )
        self.icone_check.pack(pady=(50, 20))

        # Texto de teste
        self.texto_aviso = tk.Label(
            self.frame, text="TESTE\n\nSistema funcionando!\n", 
            font=self.texto_fonte, fg="white", bg="#2E8B57", justify="center"
        )
        self.texto_aviso.pack(pady=(0, 10))

        # Informações
        self.texto_info = tk.Label(
            self.frame, text="Por favor, informe ao TI\nque recebeu esta tela de teste.", 
            font=("Arial", 36, "bold"), fg="#E0FFFF", bg="#2E8B57", justify="center"
        )
        self.texto_info.pack(pady=(0, 30))

        # Nome da sala
        self.texto_sala = tk.Label(
            self.frame, text=f"SALA: {sala.upper()}", 
            font=self.sala_fonte, fg="#98FB98", bg="#2E8B57", justify="center"
        )
        self.texto_sala.pack(pady=(0, 30))
        
        # Nome do usuário
        self.nome_usuario_label = tk.Label(
            self.frame, text=f"Usuário: {usuario}", 
            font=self.usuario_fonte, fg="white", bg="#2E8B57"
        )
        self.nome_usuario_label.pack(pady=(0, 5))

        # Timestamp
        timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        self.timestamp_label = tk.Label(
            self.frame, text=f"Horário: {timestamp}", 
            font=("Arial", 24), fg="white", bg="#2E8B57"
        )
        self.timestamp_label.pack(pady=(0, 30))

        # Botão fechar (adaptado para verde)
        botao_frame = tk.Frame(self.frame, bg="#2E8B57")
        botao_frame.pack(side="bottom", pady=(0, 50))

        self.botao = tk.Button(
            botao_frame, text="FECHAR", 
            font=self.botao_fonte,
            bg="#1E1E1E", fg="#FFFFFF",
            activebackground="#2C2C2C", activeforeground="#FFFFFF",
            relief="flat", borderwidth=0,
            command=self.fechar_aplicacao, 
            padx=50, pady=15, cursor="hand2"
        )
        
        def on_enter(e):
            self.botao.config(bg="#404040")
            
        def on_leave(e):
            self.botao.config(bg="#1E1E1E")
        
        self.botao.bind("<Enter>", on_enter)
        self.botao.bind("<Leave>", on_leave)
        self.botao.pack()

        # Label de status
        self.label = tk.Label(
            self.frame, text="", font=("Arial", 18), bg="#2E8B57", fg="white"
        )
        self.label.pack(pady=30)

def main():
    """Função principal"""
    cliente = ClienteReceptor()
    
    try:
        cliente.iniciar()
    except Exception as e:
        logger.error(f"Erro crítico: {e}")
    finally:
        cliente.shutdown()

if __name__ == "__main__":
    main() 