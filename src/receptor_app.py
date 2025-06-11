#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from flask import Flask, request, jsonify
import threading
import time
import os
import sys
import queue
import subprocess
from datetime import datetime

# Adicionar pygame se disponível
try:
    from pygame import mixer
    PYGAME_DISPONIVEL = True
except ImportError:
    PYGAME_DISPONIVEL = False
    print("Pygame não disponível - som desabilitado")

class ReceptorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Receptor - Botão de Pânico")
        self.root.geometry("400x300")
        self.root.resizable(False, False)
        
        # Configurar ícone se existir
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "..", "data", "icons", "client.png")
            if os.path.exists(icon_path):
                self.root.iconphoto(False, tk.PhotoImage(file=icon_path))
        except:
            pass
        
        self.app = Flask(__name__)
        self.chave = 'alerta5656'
        self.fila_alertas = queue.Queue()
        self.servidor_rodando = False
        
        self.setup_gui()
        self.setup_routes()
        
        # Iniciar servidor Flask em thread separada
        self.iniciar_servidor()
        
        # Configurar fechamento da aplicação
        self.root.protocol("WM_DELETE_WINDOW", self.fechar_aplicacao)

    def setup_gui(self):
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Título
        title_label = ttk.Label(main_frame, text="Receptor - Botão de Pânico", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # Status do servidor
        ttk.Label(main_frame, text="Status do Servidor:").grid(row=1, column=0, sticky=tk.W)
        self.status_label = ttk.Label(main_frame, text="Iniciando...", foreground="orange")
        self.status_label.grid(row=1, column=1, sticky=tk.W)
        
        # Porta
        ttk.Label(main_frame, text="Porta:").grid(row=2, column=0, sticky=tk.W)
        ttk.Label(main_frame, text="9090").grid(row=2, column=1, sticky=tk.W)
        
        # Último alerta
        ttk.Label(main_frame, text="Último Alerta:").grid(row=3, column=0, sticky=tk.W, pady=(10, 0))
        self.ultimo_alerta_label = ttk.Label(main_frame, text="Nenhum", foreground="gray")
        self.ultimo_alerta_label.grid(row=3, column=1, sticky=tk.W, pady=(10, 0))
        
        # Log de atividades
        ttk.Label(main_frame, text="Log de Atividades:").grid(row=4, column=0, columnspan=2, 
                                                              sticky=tk.W, pady=(20, 5))
        
        # Text widget para log
        self.log_text = tk.Text(main_frame, height=8, width=50, wrap=tk.WORD)
        self.log_text.grid(row=5, column=0, columnspan=2, pady=(0, 10))
        
        # Scrollbar para o log
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=5, column=2, sticky=(tk.N, tk.S))
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Botões
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(10, 0))
        
        ttk.Button(button_frame, text="Limpar Log", 
                  command=self.limpar_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Teste de Alerta", 
                  command=self.teste_alerta).pack(side=tk.LEFT)
        
        # Adicionar log inicial
        self.adicionar_log("Aplicação iniciada")

    def setup_routes(self):
        @self.app.route('/check-health', methods=['GET'])
        def check_health():
            return jsonify({"status": "ok"}), 200

        @self.app.route(f'/{self.chave}/enviar', methods=['POST'])
        def receber_mensagem():
            try:
                data = request.json
                if data and data.get('codigo') == self.chave:
                    sala = data.get('sala', 'Desconhecida')
                    usuario = data.get('usuario', 'Desconhecido')
                    
                    # Adicionar à fila de alertas
                    self.fila_alertas.put((sala, usuario))
                    
                    # Processar alerta em thread separada
                    threading.Thread(target=self.processar_alerta, 
                                   args=(sala, usuario), daemon=True).start()
                    
                    return jsonify({"status": "success"}), 200
                else:
                    self.adicionar_log("Chave inválida recebida")
                    return jsonify({"error": "Chave inválida"}), 400
            except Exception as e:
                self.adicionar_log(f"Erro ao receber mensagem: {e}")
                return jsonify({"error": "Erro interno"}), 500

    def iniciar_servidor(self):
        def run_server():
            try:
                self.app.run(host='0.0.0.0', port=9090, debug=False, use_reloader=False)
            except Exception as e:
                self.adicionar_log(f"Erro no servidor: {e}")
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        # Verificar se o servidor iniciou
        self.root.after(2000, self.verificar_servidor)

    def verificar_servidor(self):
        try:
            import requests
            response = requests.get("http://localhost:9090/check-health", timeout=2)
            if response.status_code == 200:
                self.status_label.config(text="Online", foreground="green")
                self.servidor_rodando = True
                self.adicionar_log("Servidor Flask iniciado com sucesso na porta 9090")
            else:
                self.status_label.config(text="Erro", foreground="red")
        except:
            self.status_label.config(text="Offline", foreground="red")
            self.adicionar_log("Erro ao iniciar servidor Flask")

    def processar_alerta(self, sala, usuario):
        try:
            # Atualizar GUI
            self.root.after(0, lambda: self.atualizar_ultimo_alerta(sala, usuario))
            self.root.after(0, lambda: self.adicionar_log(f"ALERTA RECEBIDO: {sala} - {usuario}"))
            
            # Abrir tela de alerta
            self.abrir_tela_alerta(sala, usuario)
            
        except Exception as e:
            self.root.after(0, lambda: self.adicionar_log(f"Erro ao processar alerta: {e}"))

    def abrir_tela_alerta(self, sala, usuario):
        try:
            # Criar script temporário para a tela de alerta
            script_temp = self.criar_script_alerta_temp(sala, usuario)
            
            if script_temp:
                # Executar como processo separado
                subprocess.Popen([sys.executable, script_temp], 
                               creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0)
                
        except Exception as e:
            self.adicionar_log(f"Erro ao abrir tela de alerta: {e}")

    def criar_script_alerta_temp(self, sala, usuario):
        try:
            import tempfile
            
            temp_dir = tempfile.gettempdir()
            script_path = os.path.join(temp_dir, f"alerta_gui_{int(time.time())}.py")
            
            codigo_gui = f'''#!/usr/bin/env python3
import tkinter as tk
import tkinter.font as tkfont
import threading
import time
import os

# Pygame opcional
try:
    from pygame import mixer
    PYGAME_DISPONIVEL = True
except ImportError:
    PYGAME_DISPONIVEL = False

class TelaAlerta:
    def __init__(self, master, sala, usuario):
        self.master = master
        self.som_tocando = True
        self.mixer_inicializado = False
        
        self.master.title("ALERTA - BOTÃO DE PÂNICO")
        self.master.attributes('-fullscreen', True)
        self.master.protocol("WM_DELETE_WINDOW", self.nao_fechar)
        self.master.attributes('-topmost', True)
        self.master.focus_force()
        self.master.bind("<FocusOut>", self.manter_foco)
        self.master.configure(bg="#B22222")
        
        # Configurar fontes
        try:
            botao_fonte = tkfont.Font(family="Arial", size=28, weight="bold")
            icone_fonte = tkfont.Font(family="Arial", size=120, weight="bold")
            texto_fonte = tkfont.Font(family="Arial", size=48, weight="bold")
            local_fonte = tkfont.Font(family="Helvetica", size=45, weight="bold")
        except:
            botao_fonte = ("Arial", 28, "bold")
            icone_fonte = ("Arial", 120, "bold")
            texto_fonte = ("Arial", 48, "bold")
            local_fonte = ("Helvetica", 45, "bold")
        
        self.frame = tk.Frame(self.master, bg="#B22222")
        self.frame.pack(expand=True, fill="both")

        self.icone_alerta = tk.Label(self.frame, text="⚠", font=icone_fonte, fg="#FFD700", bg="#B22222")
        self.icone_alerta.pack(pady=(50, 20))

        self.texto_aviso = tk.Label(self.frame, text="ATENÇÃO!\\n\\nCÓDIGO VIOLETA!\\n\\n", 
                                    font=texto_fonte, fg="white", bg="#B22222", justify="center")
        self.texto_aviso.pack(pady=(0, 10))

        self.texto_sala = tk.Label(self.frame, text=f"LOCAL: {sala.upper()}", 
                                   font=local_fonte, fg="#000000", bg="#B22222")
        self.texto_sala.pack(pady=(0, 30))
        
        self.nome_usuario_label = tk.Label(self.frame, text=f"USUÁRIO: {usuario.upper()}", 
                                           font=local_fonte, fg="white", bg="#B22222")
        self.nome_usuario_label.pack(pady=(0, 5))
 
        botao_frame = tk.Frame(self.frame, bg="#B22222")
        botao_frame.pack(side="bottom", pady=(0, 50))

        self.botao = tk.Button(botao_frame, text="AGUARDE...", font=botao_fonte,
                               bg="#666666", fg="white", activebackground="#666666",
                               activeforeground="white", relief=tk.FLAT,
                               command=self.tentar_fechar, padx=30, pady=15,
                               state="disabled")
        self.botao.pack()
        
        self.label = tk.Label(self.frame, text="", 
                             font=("Arial", 18), bg="#B22222", fg="white")
        self.label.pack(pady=30)

        self.piscar_contador = 0
        self.piscar()
        
        # Iniciar som
        if PYGAME_DISPONIVEL:
            threading.Thread(target=self.tocar_som_inicial, daemon=True).start()
        else:
            self.master.after(10000, self.habilitar_botao_fechar)

    def piscar(self):
        if self.piscar_contador < 8:
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
        self.som_tocando = False
        self.botao.config(text="FECHAR", bg="#c2c2c2", state="normal")
        self.label.config(text="")

    def tentar_fechar(self):
        if not self.som_tocando:
            self.fechar_aplicacao()

    def fechar_aplicacao(self):
        self.label.config(text="Fechando...")
        try:
            if PYGAME_DISPONIVEL and self.mixer_inicializado:
                mixer.music.stop()
                mixer.quit()
        except:
            pass
        self.master.after(100, self.master.destroy)

    def nao_fechar(self):
        if not self.som_tocando:
            self.fechar_aplicacao()

    def manter_foco(self, event):
        self.master.focus_force()

    def tocar_som_inicial(self):
        if not PYGAME_DISPONIVEL:
            return
            
        try:
            mixer.init()
            self.mixer_inicializado = True
            
            caminhos_som = [
                r"C:\\Botão_panico\\sounds\\alerta-sonoro.mp3",
                r"sounds\\alerta-sonoro.mp3",
                r".\\sounds\\alerta-sonoro.mp3"
            ]
            
            arquivo_som = None
            for caminho in caminhos_som:
                if os.path.exists(caminho):
                    arquivo_som = caminho
                    break
            
            if arquivo_som is None:
                self.master.after(0, self.habilitar_botao_fechar)
                return
                
            mixer.music.load(arquivo_som)
            
            for i in range(4):
                mixer.music.play()
                while mixer.music.get_busy():
                    time.sleep(0.1)
                
                if i < 3:
                    time.sleep(0.5)
            
            self.master.after(0, self.habilitar_botao_fechar)
            
        except Exception as e:
            self.master.after(0, self.habilitar_botao_fechar)

if __name__ == "__main__":
    root = tk.Tk()
    app = TelaAlerta(root, "{sala}", "{usuario}")
    root.mainloop()
'''
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(codigo_gui)
            
            return script_path
            
        except Exception as e:
            self.adicionar_log(f"Erro ao criar script temporário: {e}")
            return None

    def atualizar_ultimo_alerta(self, sala, usuario):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.ultimo_alerta_label.config(text=f"{sala} - {usuario} ({timestamp})", 
                                       foreground="red")

    def adicionar_log(self, mensagem):
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {mensagem}\\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # Limitar o log a 100 linhas
        lines = self.log_text.get("1.0", tk.END).split("\\n")
        if len(lines) > 100:
            self.log_text.delete("1.0", "2.0")

    def limpar_log(self):
        self.log_text.delete("1.0", tk.END)
        self.adicionar_log("Log limpo")

    def teste_alerta(self):
        self.processar_alerta("SALA TESTE", "USUÁRIO TESTE")

    def fechar_aplicacao(self):
        self.adicionar_log("Fechando aplicação...")
        self.root.quit()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = ReceptorApp()
    app.run() 