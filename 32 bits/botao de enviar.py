import socket
import time
import os
import getpass
import tkinter as tk
from tkinter import messagebox
import threading

def enviar_mensagem():
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client_socket.connect(('172.16.222.76', 13579))
        
        hostname = socket.gethostname()
        usuario_windows = getpass.getuser()
        mensagem = f"{hostname}|codigo violeta!|teste"
        client_socket.send(mensagem.encode('utf-8'))
        print(f"Mensagem enviada: {mensagem}")
        
        resposta = client_socket.recv(1024).decode('utf-8')
        print(f"Resposta do servidor: {resposta}")
        
    except Exception as e:
        print(f"Erro ao enviar mensagem: {e}")
        tk.messagebox.showerror("Erro", f"Não foi possível enviar a mensagem: {e}")
    finally:
        client_socket.close()

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

    root.after(3000, fechar_janela)
    root.mainloop()

def executar_envio():
    thread = threading.Thread(target=enviar_mensagem)
    thread.start()
    mostrar_tela_enviado()

if __name__ == "__main__":
    executar_envio()
