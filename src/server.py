#!/usr/bin/env python3
from datetime import datetime
import random
import string
from flask import Flask, request, jsonify
import mysql.connector
import requests
import threading
import dotenv
import os
import json


dotenv.load_dotenv()
database_host = os.getenv('DATABASE_HOST')
database_user = os.getenv('DATABASE_USER')
database_password = os.getenv('PASSWORD')

app = Flask(__name__)

def gerar_combo(tamanho=6):

  caracteres = string.ascii_letters + string.digits
  combo = ''.join(random.choices(caracteres, k=tamanho))

  return combo


@app.route('/alerta5656/enviar', methods=['POST'])
def receber_acao():
    global hostname
    global id_evento
    global request_ip
    id_evento = gerar_combo()
    request_ip = request.remote_addr
    data = request.get_json()
    
    if data is None:
        salvar_logs_sitema(f"Nenhum dado JSON foi recebido por {request_ip} - {id_evento}")
        return jsonify({"error": "Nenhum dado JSON foi recebido"}), 400
    
    print(f"data: {data}")
    
    if 'hostname' not in data or 'usuario' not in data or 'codigo' not in data:
        salvar_logs_sitema(f"Dados obrigatórios ausentes (hostname, usuario, codigo) por {request_ip} - {id_evento}")
        return jsonify({"error": "Dados obrigatórios ausentes (hostname, usuario, codigo)"}), 400
    
    hostname = data['hostname']
    print(f"hostname: {hostname}")
    usuario = data['usuario']
    print(f"usuario: {usuario}")
    codigo = data['codigo']
    print(f"codigo: {codigo}")
    
    nome_usuario = localizar_usuario(usuario)
    if nome_usuario is None:
        nome_usuario = usuario
    nome_sala = localizar_sala(hostname)
    if nome_sala is None:
        nome_sala = "Sala não encontrada"
    enviar_alerta(nome_usuario, nome_sala)
    salvar_logs_sitema(f"Ação recebida com sucesso por {request_ip} para o usuário {nome_usuario} na sala {nome_sala}")
    return jsonify({"message": "Ação recebida com sucesso"}), 200

@app.route('/check-health', methods=['GET'])
def check_health():
    return jsonify({"status": "ok"}), 200

def enviar_alerta(nome_usuario, nome_sala):
    salvar_logs_sitema(f"Enviando alerta do usuário {nome_usuario} da sala {nome_sala} - {id_evento}")
    
    lista_receptores = localizar_receptores()
    print(f"Lista de receptores: {lista_receptores}")
    
    if not lista_receptores:
        print("Nenhum receptor encontrado")
        salvar_logs_sitema(f"Nenhum receptor encontrado")
        return
    
    threads = []
    
    for receptor in lista_receptores:
        ip_receptor = receptor[0]
        thread = threading.Thread(
            target=enviar_para_receptor, 
            args=(ip_receptor, nome_usuario, nome_sala)
        )
        threads.append(thread)
        thread.start()
        salvar_logs_sitema(f"Thread iniciada para receptor: {ip_receptor} - {id_evento}")
    
    try:
        for thread in threads:
            thread.join(timeout=30)
        salvar_logs_sitema(f"Envio massivo concluído para {len(lista_receptores)} receptores")
    except Exception as e:
        salvar_logs_sitema(f"Erro ao aguardar threads: {e}")
    


def enviar_para_receptor(ip_receptor, nome_usuario, nome_sala):
    hostname_chamador = hostname
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "Erro"
    
    try:
        print(f"Enviando para receptor: {ip_receptor}")
        
        response = requests.post(
            f"http://{ip_receptor}:9090/alerta5656/enviar", 
            json={"sala": nome_sala, "usuario": nome_usuario, "codigo": "alerta5656"},
            timeout=4
        )
        
        print(f"Resposta do receptor {ip_receptor}: {response.status_code}")
        
        if response.status_code == 200:
            status = "Enviado"
            print(f"✓ Alerta enviado com sucesso para o receptor {ip_receptor}")
            salvar_logs_sitema(f"Alerta enviado com sucesso para o receptor {ip_receptor}")
        else:
            status = "Erro_HTTP"
            print(f"✗ Erro ao enviar alerta para o receptor {ip_receptor} - Status: {response.status_code}")
            salvar_logs_sitema(f"Erro ao enviar alerta para o receptor {ip_receptor} - Status: {response.status_code}")
            
    except requests.exceptions.ConnectTimeout:
        status = "Timeout"
        print(f"✗ Timeout ao enviar para receptor {ip_receptor}")
        salvar_logs_sitema(f"Timeout ao enviar para receptor {ip_receptor}")
        
    except requests.exceptions.ConnectionError:
        status = "Erro_Conexao"
        print(f"✗ Erro de conexão com receptor {ip_receptor}")
        salvar_logs_sitema(f"Erro de conexão com receptor {ip_receptor}")
        
    except Exception as e:
        status = "Erro_Geral"
        print(f"✗ Erro inesperado ao enviar para receptor {ip_receptor}: {e}")
        salvar_logs_sitema(f"Erro inesperado ao enviar para receptor {ip_receptor}: {e}")
    
    salvar_log_alertas(ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status, id_evento)



def conectar_banco_de_dados():
    try:
        conn = mysql.connector.connect(
            host=database_host,
            user=database_user,
            password=database_password,
            database='botao_panico'
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def salvar_log_alertas(ip_receptor, hostname_chamador, nome_usuario, nome_sala , data_hora, status, id_evento):
    conn = conectar_banco_de_dados()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs_alertas (ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status, id_evento) VALUES (%s, %s, %s, %s, %s, %s, %s)", (ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status, id_evento))
        conn.commit()
        cursor.close()
        conn.close()


def localizar_usuario(usuario):
    conn = conectar_banco_de_dados()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nome_usuario FROM usuarios WHERE USERNAME = %s", (usuario,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0]
    else:
        return None

def localizar_sala(hostname):
    conn = conectar_banco_de_dados()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nome_sala FROM salas WHERE hostname = %s", (hostname,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0]
    else:
        return None

def localizar_receptores():
    conn = conectar_banco_de_dados()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ip_receptor FROM RECEPTORES")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result

def salvar_logs_sitema(log):
    conn = conectar_banco_de_dados()
    data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs_sitema (log, data_hora) VALUES (%s, %s)", (log, data_hora))
        conn.commit()
        cursor.close()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9600)