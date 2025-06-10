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
    mensagem =  f"{{'hostname': '{hostname}' , 'usuario': '{usuario_windows}' , 'codigo': 'alerta5656' }}"

    try:
        response = requests.post(f"http://localhost:9600/{chave}/enviar", json=mensagem)
        if response.status_code == 200:
            print("Mensagem enviada com sucesso")
        else:
            print(f"Erro ao enviar mensagem: {response.status_code}")
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")


def mostrar_tela_enviado():
    root = tk.Tk()
    root.overrideredirect(True)  # Remove a barra de título
    root.geometry("300x200+{}+{}".format(
        int(root.winfo_screenwidth()/2 - 150),
        int(root.winfo_screenheight()/2 - 100)
    ))
    root.configure(bg='#ffffff')  # Cor de fundo azul claro

    frame = tk.Frame(root, bg='#ffffff')
    frame.place(relx=0.5, rely=0.5, anchor='center')

    label = tk.Label(frame, text="enviada!", font=("Arial", 16, "bold"), bg='#ffffff', fg='#2ecc71')
    label.pack()

    # Ícone de confirmação
    check = tk.Label(frame, text="✓", font=("Arial", 48), bg='#ffffff', fg='#2ecc71')
    check.pack(pady=10)

    def fechar_janela():
        root.destroy()

    root.after(3000, fechar_janela)  # Fecha a janela após 3 segundos
    root.mainloop()

if __name__ == "__main__":
     enviar_mensagem()
     mostrar_tela_enviado()
