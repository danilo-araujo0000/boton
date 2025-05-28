import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
from playsound import playsound
import threading
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

        self.texto_sala = tk.Label(self.frame, text=f"{sala.upper()}", 
                                   font=sala_fonte, fg="#000000", bg="#B22222", justify="center")
        self.texto_sala.pack(pady=(0, 30))
        
        self.nome_usuario_fonte = tkfont.Font(family="Arial", size=36, weight="bold")
        self.nome_usuario_label = tk.Label(self.frame, text=f"Nome do Usuário: {usuario}", 
                                           font=self.nome_usuario_fonte, fg="white", bg="#B22222")
        self.nome_usuario_label.pack(pady=(0, 5))
 
        botao_frame = tk.Frame(self.frame, bg="#B22222")
        botao_frame.pack(side="bottom", pady=(0, 50))

      
        self.botao = tk.Button(botao_frame, text="FECHAR", font=botao_fonte,
                               bg="#c2c2c2", fg="white", activebackground="#000",
                               activeforeground="white", relief=tk.FLAT,
                               command=self.fechar_aplicacao, padx=30, pady=15)
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
        self.master.after(100, self.master.destroy)

    def nao_fechar(self):
        self.label.config(text=" FECHAR!")

    def manter_foco(self, event):
        self.master.focus_force() # trazer janela para frente 

    def tocar_som_inicial(self):
        for _ in range(3):
            playsound(sound_file)

def tocar_som():
    sound_file = r"C:\Botão_panico\sound\alerta-sonoro.mp3"
    for _ in range(2):
        playsound(sound_file)


def abrir_tela(sala, usuario):
  
    global root, app
    root = tk.Tk()
    app = Tela(root, sala, usuario)
    root.mainloop()
   

if __name__ == "__main__":
    abrir_tela("teste","teste")
