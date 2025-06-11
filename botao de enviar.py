import requests
import time
import os
import getpass
import tkinter as tk
import json
import socket




server = "localhost"
chave = "alerta5656"


def enviar_mensagem():
    hostname = socket.gethostname()
    usuario_windows = getpass.getuser()
    mostrar_tela_enviado()
    
    mensagem = {
        'hostname': hostname,
        'usuario': usuario_windows,
        'codigo': 'alerta5656'
    }
    
    print(f"Enviando mensagem: {mensagem}")

  
    requests.post(f"http://172.19.200.1:9600/{chave}/enviar", json=mensagem)
      


def mostrar_tela_enviado():
    root = tk.Tk()
    root.overrideredirect(True)  
    root.geometry("300x200+{}+{}".format(
        int(root.winfo_screenwidth()/2 - 150),
        int(root.winfo_screenheight()/2 - 100)
    ))
    root.configure(bg='#ffffff') 

    frame = tk.Frame(root, bg='#ffffff')
    frame.place(relx=0.5, rely=0.5, anchor='center')

    label = tk.Label(frame, text="enviada!", font=("Arial", 16, "bold"), bg='#ffffff', fg='#2ecc71')
    label.pack()

    check = tk.Label(frame, text="✓", font=("Arial", 48), bg='#ffffff', fg='#2ecc71')
    check.pack(pady=10)

    def fechar_janela():
        root.destroy()

    root.after(2000, fechar_janela)
    root.mainloop()

if __name__ == "__main__":
     enviar_mensagem()
     
