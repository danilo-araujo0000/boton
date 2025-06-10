#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Servidor principal do sistema de Botão de Pânico
Gerencia conexões com clientes e encaminha alertas
"""
from datetime import datetime
from flask import Flask, request, jsonify
import mysql.connector
import requests
import threading


app = Flask(__name__)




@app.route('/alerta5656/enviar', methods=['POST'])
def receber_acao():
    global hostname
    data = request.get_json()
    print(f"data: {data}")
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
    return jsonify({"message": "Ação recebida com sucesso"}), 200


def enviar_alerta(nome_usuario, nome_sala):
    print(f"Enviando alerta para o usuário {nome_usuario} na sala {nome_sala}")
    lista_receptores = localizar_receptores(nome_sala)
    try:
        for receptor in lista_receptores:
            response = requests.post(f"http://{receptor['ip_receptor']}:9090/alerta5656/enviar", json={"sala": nome_sala, "usuario": nome_usuario, "codigo": "alerta5656"})
            print(f"Resposta do receptor {receptor['ip_receptor']}: {response.status_code}")
            if response.status_code == 200:
                status = "Enviado"
                hostname_chamador = hostname
                nome_usuario = nome_usuario
                nome_sala = nome_sala
                data_hora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                salvar_log_alertas(receptor['ip_receptor'], hostname_chamador, nome_usuario, nome_sala, data_hora, status)
                print(f"Alerta enviado com sucesso para o receptor {receptor['ip_receptor']}")
            else:
                status = "Erro"
                print(f"Erro ao enviar alerta para o receptor {receptor['ip_receptor']}")
    except Exception as e:
        print(f"Erro ao enviar alerta para o receptor {receptor['ip_receptor']}: {e}")

#############################
# Funções de banco de dados #
#############################

def conectar_banco_de_dados():
    try:
        conn = mysql.connector.connect(
            host='172.19.0.76',
            user='apps',
            password='996639078',
            database='botao_panico'
        )
        return conn
    except mysql.connector.Error as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def salvar_log_alertas(ip_receptor, hostname_chamador, nome_usuario, nome_sala , data_hora, status):
    conn = conectar_banco_de_dados()
    if conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO logs_alertas (ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status) VALUES (%s, %s, %s, %s, %s, %s)", (ip_receptor, hostname_chamador, nome_usuario, nome_sala, data_hora, status))
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

def localizar_receptores(nome_sala):
    conn = conectar_banco_de_dados()
    if conn:
        cursor = conn.cursor()
        cursor.execute("SELECT ip_receptor FROM RECEPTORES")
        result = cursor.fetchall()
        cursor.close()
        conn.close()
        return result



if __name__ == "__main__":
    app.run(host='0.0.0.0', port=9600)