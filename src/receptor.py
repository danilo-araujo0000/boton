#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Receptor de Alertas do Sistema de Botão de Pânico
Recebe e apresenta alertas enviados pelo servidor
"""

import threading
import time
from flask import Flask, request, jsonify
import tkinter as tk
import json
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from pygame import mixer
import threading
import queue

import requests

app = Flask(__name__)

chave = 'alerta5656'

# Fila para gerenciar alertas
fila_alertas = queue.Queue()
thread_gui_ativa = False

@app.route(f'/{chave}/enviar', methods=['POST'])
def receber_mensagem():
    try:
        data = request.json
        if data['codigo'] == chave:
            # Adiciona o alerta na fila
            fila_alertas.put((data['sala'], data['usuario']))
            
            # Inicia thread da GUI se não estiver ativa
            global thread_gui_ativa
            if not thread_gui_ativa:
                thread_gui = threading.Thread(target=processar_alertas, daemon=True)
                thread_gui.start()
            
            return jsonify({"message": "Mensagem recebida com sucesso"}), 200
        else:
            print("Chave inválida")
    except Exception as e:
        print(f"Erro ao receber mensagem: {e}")
    return jsonify({"message": "Erro ao processar mensagem"}), 400

def processar_alertas():
    """Processa alertas da fila em uma thread separada"""
    global thread_gui_ativa
    thread_gui_ativa = True
    
    while True:
        try:
            # Pega o próximo alerta da fila (bloqueia se vazia)
            sala, usuario = fila_alertas.get(timeout=1)
            abrir_tela(sala, usuario)
        except queue.Empty:
            # Se não há alertas por 1 segundo, continua verificando
            continue
        except Exception as e:
            print(f"Erro ao processar alerta: {e}")

class Tela:
    def __init__(self, master, sala, usuario):
        self.master = master
        self.som_tocando = True  # Controla se o som ainda está tocando
        self.mixer_inicializado = False
        
        self.master.title("Tela de Alerta")
        
        self.master.attributes('-fullscreen', True)
        
        self.master.protocol("WM_DELETE_WINDOW", self.nao_fechar)
        
        self.master.attributes('-topmost', True)
        
        self.master.focus_force()
        self.master.bind("<FocusOut>", self.manter_foco)
        
        botao_fonte = tkfont.Font(family="Arial", size=28, weight="bold")
        icone_fonte = tkfont.Font(family="Arial", size=120, weight="bold")
        texto_fonte = tkfont.Font(family="Arial", size=48, weight="bold")
        sala_fonte = tkfont.Font(family="Helvetica", size=52, weight="bold")
        
        self.frame = tk.Frame(self.master, bg="#B22222")
        self.frame.pack(expand=True, fill="both")

        self.icone_alerta = tk.Label(self.frame, text="⚠", font=icone_fonte, fg="#FFD700", bg="#B22222")
        self.icone_alerta.pack(pady=(50, 20))

        self.texto_aviso = tk.Label(self.frame, text="ATENÇÃO!\n\nCODIGO VIOLETA!\n\n", 
                                    font=texto_fonte, fg="white", bg="#B22222", justify="center")
        self.texto_aviso.pack(pady=(0, 10))

        self.texto_sala = tk.Label(self.frame, text=f"{sala.upper()}", 
                                   font=sala_fonte, fg="#000000", bg="#B22222", justify="center")
        self.texto_sala.pack(pady=(0, 30))
        
        self.nome_usuario_fonte = tkfont.Font(family="Arial", size=36, weight="bold")
        self.nome_usuario_label = tk.Label(self.frame, text=f"Nome do Usuário: {usuario}", 
                                           font=self.nome_usuario_fonte, fg="white", bg="#B22222")
        self.nome_usuario_label.pack(pady=(0, 5))
 
        botao_frame = tk.Frame(self.frame, bg="#B22222")
        botao_frame.pack(side="bottom", pady=(0, 50))

        self.botao = tk.Button(botao_frame, text="AGUARDE...", font=botao_fonte,
                               bg="#666666", fg="white", activebackground="#666666",
                               activeforeground="white", relief=tk.FLAT,
                               command=self.tentar_fechar, padx=30, pady=15,
                               state="disabled")  # Inicia desabilitado
        self.botao.pack()
        
        self.label = tk.Label(self.frame, text="", 
                             font=("Arial", 18), bg="#B22222", fg="white")
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
            self.nome_usuario_label.configure(bg=nova_cor)
            self.label.configure(bg=nova_cor)
            self.piscar_contador += 1
            self.master.after(500, self.piscar)

    def habilitar_botao_fechar(self):
        """Habilita o botão fechar após o som terminar"""
        self.som_tocando = False
        self.botao.config(text="FECHAR", bg="#c2c2c2", state="normal")
        self.label.config(text="")

    def tentar_fechar(self):
        """Tenta fechar a aplicação, só permite se o som terminou"""
        if not self.som_tocando:
            self.fechar_aplicacao()
        else:
            self.label.config(text="")

    def fechar_aplicacao(self):
        self.label.config(text="Fechando...")
        # Limpa recursos do mixer antes de fechar
        try:
            if self.mixer_inicializado:
                mixer.music.stop()
                mixer.quit()
        except:
            pass
        self.master.after(100, self.master.destroy)

    def nao_fechar(self):
        if self.som_tocando:
            self.label.config(text="")
        else:
            self.label.config(text="Use o botão FECHAR!")

    def manter_foco(self, event):
        self.master.focus_force()

    def tocar_som_inicial(self):
        try:
            mixer.init()
            self.mixer_inicializado = True
            mixer.music.load(r"C:\Botão_panico\sounds\alerta-sonoro.mp3")
            
            # Toca o som 4 vezes
            for i in range(4):
                mixer.music.play()
                # Aguarda o som terminar antes de tocar novamente
                while mixer.music.get_busy():
                    time.sleep(0.1)
                
                # Pausa entre as reproduções (exceto na última)
                if i < 3:
                    time.sleep(0.5)
            
            # Som terminou, habilita o botão fechar
            self.master.after(0, self.habilitar_botao_fechar)
            
        except Exception as e:
            print(f"Erro ao tocar som: {e}")
            # Se houver erro no som, habilita o botão imediatamente
            self.master.after(0, self.habilitar_botao_fechar)

def abrir_tela(sala, usuario):
    """Cria uma nova janela de alerta em uma thread separada"""
    def criar_janela():
        try:
            root = tk.Tk()
            app_tela = Tela(root, sala, usuario)
            root.mainloop()
        except Exception as e:
            print(f"Erro ao criar janela: {e}")
    
    thread_janela = threading.Thread(target=criar_janela, daemon=True)
    thread_janela.start()

if __name__ == "__main__":
    print("Iniciando servidor receptor...")
    
    flask_thread = threading.Thread(target=lambda: app.run(host='0.0.0.0', port=9090, debug=False), daemon=True)
    flask_thread.start()
    
    print("Servidor iniciado. Pressione Ctrl+C para sair.")
    
    try:
        # Mantém o programa rodando
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando servidor...")
 
