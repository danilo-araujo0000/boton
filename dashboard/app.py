#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dashboard de Gerenciamento do Sistema de Botão de Pânico
Interface web para administração e monitoramento
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import mysql.connector
import requests
from datetime import datetime, timedelta
import dotenv
import os
import json

# Carregar variáveis de ambiente
dotenv.load_dotenv()
database_host = os.getenv('DATABASE_HOST')
database_user = os.getenv('DATABASE_USER')
database_password = os.getenv('PASSWORD')

app = Flask(__name__)
app.secret_key = 'botao_panico_dashboard_2024'

# Configuração do servidor principal
SERVER_URL = "http://localhost:9600"

def conectar_banco_de_dados():
    """Conecta ao banco de dados MySQL"""
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

def verificar_status_servidor():
    """Verifica se o servidor principal está online"""
    try:
        response = requests.get(f"{SERVER_URL}/check-health", timeout=5)
        return response.status_code == 200
    except:
        return False

@app.route('/')
def inicio():
    """Página inicial com visão geral do sistema"""
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    cursor = conn.cursor(dictionary=True)
    
    # Estatísticas gerais
    cursor.execute("SELECT COUNT(*) as total FROM salas")
    total_salas = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM usuarios")
    total_usuarios = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM RECEPTORES")
    total_receptores = cursor.fetchone()['total']
    
    # Últimos acionamentos por evento (últimos 5)
    cursor.execute("""
        SELECT nome_sala, nome_usuario, data_hora, id_evento,
               COUNT(*) as total_receptores,
               SUM(CASE WHEN status = 'Enviado' THEN 1 ELSE 0 END) as enviados_sucesso
        FROM logs_alertas 
        GROUP BY id_evento, nome_sala, nome_usuario, data_hora
        ORDER BY data_hora DESC 
        LIMIT 5
    """)
    ultimos_acionamentos = cursor.fetchall()
    
    # Logs do sistema (últimos 10)
    cursor.execute("""
        SELECT log, data_hora 
        FROM logs_sitema 
        ORDER BY data_hora DESC 
        LIMIT 10
    """)
    ultimos_logs = cursor.fetchall()
    
    # Status do servidor
    status_servidor = verificar_status_servidor()
    
    cursor.close()
    conn.close()
    
    return render_template('inicio.html', 
                         total_salas=total_salas,
                         total_usuarios=total_usuarios,
                         total_receptores=total_receptores,
                         ultimos_acionamentos=ultimos_acionamentos,
                         ultimos_logs=ultimos_logs,
                         status_servidor=status_servidor)

@app.route('/salas')
def salas():
    """Página de gerenciamento de salas"""
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM salas ORDER BY nome_sala")
    salas_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('salas.html', salas=salas_list)

@app.route('/usuarios')
def usuarios():
    """Página de gerenciamento de usuários"""
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM usuarios ORDER BY nome_usuario")
    usuarios_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('usuarios.html', usuarios=usuarios_list)

@app.route('/receptores')
def receptores():
    """Página de gerenciamento de receptores"""
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM RECEPTORES ORDER BY ip_receptor")
    receptores_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('receptores.html', receptores=receptores_list)

@app.route('/logs')
def logs():
    """Página de visualização de logs"""
    # Parâmetros de filtro
    dias = request.args.get('dias', '7')
    tipo = request.args.get('tipo', 'todos')
    
    try:
        dias_int = int(dias)
    except:
        dias_int = 7
    
    data_inicio = datetime.now() - timedelta(days=dias_int)
    
    conn = conectar_banco_de_dados()
    if not conn:
        flash('Erro ao conectar com o banco de dados', 'error')
        return render_template('erro.html')
    
    cursor = conn.cursor(dictionary=True)
    
    logs_sistema = []
    logs_alertas = []
    
    if tipo in ['todos', 'sistema']:
        cursor.execute("""
            SELECT log, data_hora 
            FROM logs_sitema 
            WHERE data_hora >= %s 
            ORDER BY data_hora DESC
        """, (data_inicio,))
        logs_sistema = cursor.fetchall()
    
    if tipo in ['todos', 'alertas']:
        cursor.execute("""
            SELECT ip_receptor, hostname_chamador, nome_usuario, nome_sala, 
                   data_hora, status, id_evento 
            FROM logs_alertas 
            WHERE data_hora >= %s 
            ORDER BY data_hora DESC
        """, (data_inicio,))
        logs_alertas = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('logs.html', 
                         logs_sistema=logs_sistema,
                         logs_alertas=logs_alertas,
                         dias_selecionado=dias,
                         tipo_selecionado=tipo)

# APIs para CRUD

@app.route('/api/salas', methods=['POST'])
def adicionar_sala():
    """Adiciona uma nova sala"""
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO salas (nome_sala, hostname, setor) 
            VALUES (%s, %s, %s)
        """, (data['nome_sala'], data['hostname'], data.get('setor', '')))
        conn.commit()
        flash('Sala adicionada com sucesso!', 'success')
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/salas/<int:sala_id>', methods=['PUT'])
def editar_sala(sala_id):
    """Edita uma sala existente"""
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE salas 
            SET nome_sala = %s, hostname = %s, setor = %s 
            WHERE id = %s
        """, (data['nome_sala'], data['hostname'], data.get('setor', ''), sala_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/salas/<int:sala_id>', methods=['DELETE'])
def deletar_sala(sala_id):
    """Deleta uma sala"""
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM salas WHERE id = %s", (sala_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/usuarios', methods=['POST'])
def adicionar_usuario():
    """Adiciona um novo usuário"""
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO usuarios (nome_usuario, USERNAME) 
            VALUES (%s, %s)
        """, (data['nome_usuario'], data['USERNAME']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/usuarios/<int:usuario_id>', methods=['PUT'])
def editar_usuario(usuario_id):
    """Edita um usuário existente"""
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE usuarios 
            SET nome_usuario = %s, USERNAME = %s 
            WHERE id = %s
        """, (data['nome_usuario'], data['USERNAME'], usuario_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
def deletar_usuario(usuario_id):
    """Deleta um usuário"""
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM usuarios WHERE id = %s", (usuario_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/receptores', methods=['POST'])
def adicionar_receptor():
    """Adiciona um novo receptor"""
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO RECEPTORES (ip_receptor, nome_receptor, setor) 
            VALUES (%s, %s, %s)
        """, (data['ip_receptor'], data.get('nome_receptor', ''), 
              data.get('setor', '')))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/receptores/<int:receptor_id>', methods=['PUT'])
def editar_receptor(receptor_id):
    """Edita um receptor existente"""
    data = request.get_json()
    
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE RECEPTORES 
            SET ip_receptor = %s, nome_receptor = %s, setor = %s 
            WHERE id = %s
        """, (data['ip_receptor'], data.get('nome_receptor', ''), 
              data.get('setor', ''), receptor_id))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/receptores/<int:receptor_id>', methods=['DELETE'])
def deletar_receptor(receptor_id):
    """Deleta um receptor"""
    conn = conectar_banco_de_dados()
    if not conn:
        return jsonify({'error': 'Erro ao conectar com o banco'}), 500
    
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM RECEPTORES WHERE id = %s", (receptor_id,))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8100, debug=True) 