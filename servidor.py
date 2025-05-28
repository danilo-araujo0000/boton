import socket
import threading
import json
import time
import os
from datetime import datetime

# Função para carregar o dicionário das salas usando o arquivo json/txt
def carregar_salas():
    with open(r'\\172.16.222.76\disco C\py\BASE\botao\salas.txt', 'r') as f:
        return json.load(f)

# Função para carregar a lista de cliente mestre no arquivo permitidos.txt
def carregar_clientes_mestres():
    with open(r'\\172.16.222.76\disco C\py\BASE\botao\permitidos.txt', 'r') as f:
        return [line.strip() for line in f]

# Função para escrever o log
def escrever_log(usuario, sala):
    log_dir = r'\\172.16.222.76\disco C\py\BASE\botao\logs'
    os.makedirs(log_dir, exist_ok=True)
    
    data_atual = datetime.now().strftime("%d-%m-%Y")
    nome_arquivo = f"codigo_violeta_{data_atual}_{sala.replace(' ', '_')}.txt"
    log_file = os.path.join(log_dir, nome_arquivo)
    
    timestamp = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    log_entry = f"Botao acionado pelo usuario {usuario} na {sala} - {timestamp}\n"
    
    with open(log_file, 'a') as f:
        f.write(log_entry)

# Variáveis globais
salas = carregar_salas()
clientes_mestres = carregar_clientes_mestres()

# Dicionário para armazenar as conexões dos cliente mestre
clientes_mestres_conectados = {}

def atualizar_dados():
    global salas, clientes_mestres
    while True:
        salas = carregar_salas()
        clientes_mestres = carregar_clientes_mestres()
        print("Dados atualizados")
        time.sleep(3600)  # Atualiza a cada 1 hora

def processar_mensagem(mensagem):
    partes = mensagem.split('|')
    if len(partes) == 3:
        hostname, codigo, usuario_windows = partes
        if codigo.lower().startswith("codigo violeta!"):
            sala = salas.get(hostname)
            escrever_log(usuario_windows, sala)
            return f"ABRIR_TELA|{sala}|{codigo}|{usuario_windows}"
    return None

def handle_client(client_socket, addr):
    mensagem = client_socket.recv(1024).decode('utf-8')
    print(f"Mensagem recebida de {addr}: {mensagem}")
    
    if '|' in mensagem:  # Cliente simples
        comando = processar_mensagem(mensagem)
        print(comando)
        if comando:
            for cliente_mestre in clientes_mestres_conectados.values():
                
                cliente_mestre.send(comando.encode('utf-8'))

            # Enviar confirmação ao cliente
            client_socket.send("Mensagem recebida com sucesso".encode('utf-8'))
    else:  # Cliente mestre
        hostname = mensagem
        if hostname in clientes_mestres:
            clientes_mestres_conectados[hostname] = client_socket
            print(f"Cliente mestre conectado: {hostname}")
            #while para receber mensagem do cliente mestre
            while True:
                try:
                    mensagem = client_socket.recv(1024)  #receber mensagem do cliente mestre
                    time.sleep(3)
                except:
                    break
    
    client_socket.close()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 13579))   #ip e porta
    server.listen(10)   # definir o numero de conexoes
    print("Servidor iniciado")

    # Iniciar thread para atualizar dados
    threading.Thread(target=atualizar_dados, daemon=True).start()

    while True:
        client_socket, addr = server.accept()  #aceitar conexao
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()

if __name__ == "__main__":
    main()
