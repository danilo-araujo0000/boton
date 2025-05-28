import socket
import subprocess
import time
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
import threading
import os
import pygame
import agendador_de_tarefas

pygame.mixer.init()
sound_file = r'C:\Botão_panico\sounds\alerta-sonoro.mp3'

try:
    alerta_sound = pygame.mixer.Sound(sound_file)
    alerta_sound.set_volume(0.9)  # Ajusta o volume para 30% do máximo
except:
    print("Erro ao carregar arquivo de som")


def reiniciar():
    time.sleep(1)
    print("Reiniciando o processo...")
    subprocess.Popen(["C:\\Botão_panico\\agendador_de_tarefas.exe"], shell=True)   
  

class Tela:
    def __init__(self, master, sala, usuario):

        self.master = master
        self.master.title("Tela de Alerta")
        
        self.master.attributes('-fullscreen', True)
        
        self.master.protocol("WM_DELETE_WINDOW", self.nao_fechar)
        
        self.master.attributes('-topmost', True)
        
        self.master.focus_force()
        self.master.bind("<FocusOut>", self.manter_foco)
        
        botao_fonte = tkfont.Font(family="Arial", size=28, weight="bold")
        icone_fonte = tkfont.Font(family="Arial", size=120, weight="bold")
        texto_fonte = tkfont.Font(family="Arial", size=48, weight="bold")
        sala_fonte = tkfont.Font(family="Helvetica", size=52, weight="bold")  # Nova fonte para a sala
        
        self.frame = tk.Frame(self.master, bg="#B22222")
        self.frame.pack(expand=True, fill="both")

        self.icone_alerta = tk.Label(self.frame, text="⚠", font=icone_fonte, fg="#FFD700", bg="#B22222")
        self.icone_alerta.pack(pady=(50, 20))

        self.texto_aviso = tk.Label(self.frame, text="ATENÇÃO!\n\nCODIGO VIOLETA!\n\n", 
                                    font=texto_fonte, fg="white", bg="#B22222", justify="center")
        self.texto_aviso.pack(pady=(0, 10))

        # Modificando o Label para o nome da sala com nova cor
        self.texto_sala = tk.Label(self.frame, text=f"SALA: {sala.upper()}", 
                                   font=sala_fonte, fg="#FFF3B0", bg="#B22222", justify="center")
        self.texto_sala.pack(pady=(0, 30))
        
        self.nome_usuario_fonte = tkfont.Font(family="Arial", size=36, weight="bold")
        self.nome_usuario_label = tk.Label(self.frame, text=f"Nome do Usuário: {usuario}", 
                                           font=self.nome_usuario_fonte, fg="white", bg="#B22222")
        self.nome_usuario_label.pack(pady=(0, 5))
 
        # Frame para o botão com novo estilo
        botao_frame = tk.Frame(self.frame, bg="#B22222")
        botao_frame.pack(side="bottom", pady=(0, 50))

        # Estilo mais moderno para o botão
        self.botao = tk.Button(botao_frame, text="FECHAR", 
                              font=("Helvetica", 24, "bold"),
                              bg="#1E1E1E",        # Cinza escuro quase preto
                              fg="#FFFFFF",         # Texto branco
                              activebackground="#2C2C2C",  # Cinza um pouco mais claro quando clicado
                              activeforeground="#FFFFFF",
                              relief="flat",        # Remove o efeito 3D
                              borderwidth=0,        # Remove a borda
                              command=self.fechar_aplicacao, 
                              padx=50,             # Padding horizontal maior
                              pady=15,             # Padding vertical
                              cursor="hand2")      # Cursor de mão
        
        # Cria um frame para simular uma borda inferior
        self.borda_frame = tk.Frame(botao_frame, bg="#404040", height=3)
        self.borda_frame.pack(fill="x", pady=(0, 0))
        
        # Efeitos de hover mais suaves
        def on_enter(e):
            self.botao.config(bg="#404040")
            self.borda_frame.config(bg="#505050")
            
        def on_leave(e):
            self.botao.config(bg="#1E1E1E")
            self.borda_frame.config(bg="#404040")
        
        self.botao.bind("<Enter>", on_enter)
        self.botao.bind("<Leave>", on_leave)
        
        self.botao.pack()
        # Cria um rótulo (label) vazio com fonte Arial tamanho 18, fundo vermelho escuro e texto branco
        self.label = tk.Label(self.frame, text="", font=("Arial", 18), bg="#B22222", fg="white")
        self.label.pack(pady=30)

        self.piscar_contador = 0
        self.piscar()

        # tocar som ao iniciar a tela
        threading.Thread(target=self.tocar_som_inicial, daemon=True).start()

    def piscar(self):
        

        if self.piscar_contador < 8:  # 4 segundos (8 mudanças de 0.5 segundos)
            cor_atual = self.frame.cget("background")
            nova_cor = "#CD5C5C" if cor_atual == "#B22222" else "#B22222"
            self.frame.configure(background=nova_cor)
            self.icone_alerta.configure(bg=nova_cor)
            self.texto_aviso.configure(bg=nova_cor)
            self.texto_sala.configure(bg=nova_cor)
            self.label.configure(bg=nova_cor)
            self.piscar_contador += 1
            self.master.after(500, self.piscar)


    def fechar_aplicacao(self):
        self.label.config(text="Fechando...")
        self.master.after(1000, self.master.destroy)
        # Iniciar thread para executar reiniciar após fechar a janela
        reiniciar()

    def nao_fechar(self):
        self.label.config(text=" FECHAR!")

    def manter_foco(self, event):
        self.master.focus_force() # trazer janela para frente 

    def tocar_som_inicial(self):
        try:
            for _ in range(3):
                try:
                    alerta_sound.play()
                    time.sleep(1)
                except Exception as e:
                    print(f"Erro ao tocar som: {e}")
        except Exception as e:
            print(f"Erro na função tocar_som_inicial: {e}")


def tocar_som():
    try:
        for _ in range(2):
            alerta_sound.play()
            time.sleep(1)
    except Exception as e:
        print(f"Erro ao tocar som: {e}")


class TelaTest:
    def __init__(self, master, sala, usuario):
        self.master = master
        self.master.title("Tela de Teste")
        
        self.master.attributes('-fullscreen', True)
        self.master.protocol("WM_DELETE_WINDOW", self.nao_fechar)
        self.master.attributes('-topmost', True)
        self.master.focus_force()
        self.master.bind("<FocusOut>", self.manter_foco)
        
        botao_fonte = tkfont.Font(family="Arial", size=28, weight="bold")
        icone_fonte = tkfont.Font(family="Arial", size=120, weight="bold")
        texto_fonte = tkfont.Font(family="Arial", size=48, weight="bold")
        sala_fonte = tkfont.Font(family="Helvetica", size=52, weight="bold")
        
        self.frame = tk.Frame(self.master, bg="#2E8B57")  # Verde escuro agradável
        self.frame.pack(expand=True, fill="both")

        self.icone_check = tk.Label(self.frame, text="✓", font=icone_fonte, fg="#98FB98", bg="#2E8B57")
        self.icone_check.pack(pady=(50, 20))

        self.texto_aviso = tk.Label(self.frame, 
                                  text="TESTE\n\nNão se preocupe,\né apenas um teste!\n", 
                                  font=texto_fonte, fg="white", bg="#2E8B57", justify="center")
        self.texto_aviso.pack(pady=(0, 10))

        self.texto_info = tk.Label(self.frame, 
                                 text="Por favor, ligue para o TI\ne informe que recebeu esta tela.", 
                                 font=("Arial", 36, "bold"), fg="#E0FFFF", bg="#2E8B57", justify="center")
        self.texto_info.pack(pady=(0, 30))

        self.texto_sala = tk.Label(self.frame, text=f"SALA: {sala.upper()}", 
                                 font=sala_fonte, fg="#98FB98", bg="#2E8B57", justify="center")
        self.texto_sala.pack(pady=(0, 30))
        
        self.nome_usuario_fonte = tkfont.Font(family="Arial", size=36, weight="bold")
        self.nome_usuario_label = tk.Label(self.frame, text=f"Nome do Usuário: {usuario}", 
                                         font=self.nome_usuario_fonte, fg="white", bg="#2E8B57")
        self.nome_usuario_label.pack(pady=(0, 5))

        botao_frame = tk.Frame(self.frame, bg="#2E8B57")
        botao_frame.pack(side="bottom", pady=(0, 50))

        self.botao = tk.Button(botao_frame, text="FECHAR", 
                              font=("Helvetica", 24, "bold"),
                              bg="#1E1E1E",
                              fg="#FFFFFF",
                              activebackground="#2C2C2C",
                              activeforeground="#FFFFFF",
                              relief="flat",
                              borderwidth=0,
                              command=self.fechar_aplicacao,
                              padx=50,
                              pady=15,
                              cursor="hand2")
        
        self.borda_frame = tk.Frame(botao_frame, bg="#404040", height=3)
        self.borda_frame.pack(fill="x", pady=(0, 0))
        
        def on_enter(e):
            self.botao.config(bg="#404040")
            self.borda_frame.config(bg="#505050")
            
        def on_leave(e):
            self.botao.config(bg="#1E1E1E")
            self.borda_frame.config(bg="#404040")
        
        self.botao.bind("<Enter>", on_enter)
        self.botao.bind("<Leave>", on_leave)
        
        self.botao.pack()
        self.label = tk.Label(self.frame, text="", font=("Arial", 18), bg="#2E8B57", fg="white")
        self.label.pack(pady=30)

    def fechar_aplicacao(self):
        self.label.config(text="Fechando...")
        self.master.after(1000, self.master.destroy)
        reiniciar()

    def nao_fechar(self):
        self.label.config(text=" FECHAR!")

    def manter_foco(self, event):
        self.master.focus_force()


def abrir_tela(sala, usuario, tipo="alerta"):
    def criar_janela():
        global root, app
        root = tk.Tk()
        if tipo == "teste":
            app = TelaTest(root, sala, usuario)
        else:
            app = Tela(root, sala, usuario)
        root.mainloop()
    
    criar_janela()






def conectar_ao_serv():
    while True:
        print("CONECTANDO...")
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect(('172.16.222.76', 13579))
            
            hostname = socket.gethostname()
            client_socket.send(hostname.encode('utf-8'))
            print(f"CONECTADO COMO {hostname}")
            
            while True:
                comando = client_socket.recv(1024).decode('utf-8')
                if comando.startswith("ABRIR_TELA"):
                    partes = comando.split('|')
                    sala = partes[1]
                    usuario = partes[3]
                    print(f"Usuario recebido: '{usuario}'")
                    print(f"Usuario em lowercase: '{usuario.lower()}'")
                    print(f"É igual a 'teste'? {usuario.lower() == 'teste'}")
                    
                    usuario = usuario.strip()
                    tipo = "teste" if usuario.lower().strip() == "teste" else "alerta"
                    print(f"Tipo definido: {tipo}")
                    print(f"SALA: {sala}")
                    
                    abrir_tela(sala, usuario, tipo)

                    return
                    
        except Exception as e:
            print(f"Erro na conexão: {e}")
            for i in range(1, 11):
                print(f"TENTANDO RECONECTAR EM {i}")
                time.sleep(1)

if __name__ == "__main__":
    print("CLIENTE RECEPTOR INICIADO.")
    # Iniciar a thread de conexão
    threading.Thread(target=conectar_ao_serv, daemon=True).start()
    
    # Manter a thread principal livre para o Tkinter
    while True:
        time.sleep(1)
# comando para criar o executavel: pyinstaller --onefile  --icon=C:\Botão_panico\icons\sirene.png Receptor.py