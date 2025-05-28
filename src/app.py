#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aplicação Web de Administração do Sistema de Botão de Pânico
Interface para gerenciar salas, clientes e visualizar logs
"""

import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import socket
import json
from src.config import Config

# Configuração de logging
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs_data')
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, Config().LOG_LEVEL),
    format=Config().LOG_FORMAT,
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'admin.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("admin")

# Inicialização da aplicação Flask
app = Flask(__name__, 
            template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))
app.config['SECRET_KEY'] = Config().SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = Config().get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Inicialização do banco de dados
db = SQLAlchemy(app)

# Inicialização do gerenciador de login
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Definição dos modelos
class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    senha_hash = db.Column(db.String(256), nullable=False)
    ativo = db.Column(db.Boolean, default=True)
    admin = db.Column(db.Boolean, default=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)
    
    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

class Sala(db.Model):
    __tablename__ = 'salas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    descricao = db.Column(db.String(255))
    setor = db.Column(db.String(100))
    andar = db.Column(db.String(20))
    prioritaria = db.Column(db.Boolean, default=False)
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

class ClienteMestre(db.Model):
    __tablename__ = 'clientes_mestre'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), unique=True, nullable=False)
    descricao = db.Column(db.String(255))
    ip = db.Column(db.String(45))
    setor = db.Column(db.String(100))
    nivel_acesso = db.Column(db.Integer, default=1)
    ativo = db.Column(db.Boolean, default=True)
    ultima_conexao = db.Column(db.DateTime)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    
    def is_online(self):
        """Verifica se o cliente está online (conectado nos últimos 5 minutos)"""
        if not self.ultima_conexao:
            return False
        limite = datetime.utcnow() - timedelta(minutes=5)
        return self.ultima_conexao >= limite

class LogAlerta(db.Model):
    __tablename__ = 'logs_alerta'
    
    id = db.Column(db.Integer, primary_key=True)
    sala = db.Column(db.String(100), nullable=False)
    hostname = db.Column(db.String(100))
    codigo = db.Column(db.String(20))
    usuario_windows = db.Column(db.String(100))
    ip_origem = db.Column(db.String(45))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    processado = db.Column(db.Boolean, default=False)
    observacoes = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Rotas de autenticação
@app.route('/')
def index():
    """Página inicial"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Página de login"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('senha')
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if usuario and usuario.verificar_senha(senha) and usuario.ativo:
            login_user(usuario)
            logger.info(f"Login bem-sucedido: {email}")
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            logger.warning(f"Tentativa de login falhou: {email}")
            flash('Email ou senha inválidos', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Encerra a sessão do usuário"""
    logger.info(f"Logout: {current_user.email}")
    logout_user()
    return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    """Página principal do dashboard"""
    # Estatísticas
    total_salas = Sala.query.count()
    salas_ativas = Sala.query.filter_by(ativo=True).count()
    total_clientes = ClienteMestre.query.count()
    
    # Alertas recentes
    ontem = datetime.utcnow() - timedelta(days=1)
    alertas_24h = LogAlerta.query.filter(LogAlerta.timestamp >= ontem).count()
    
    # Clientes online
    clientes = ClienteMestre.query.all()
    clientes_online = sum(1 for c in clientes if c.is_online())
    
    # Últimos alertas
    ultimos_alertas = LogAlerta.query.order_by(LogAlerta.timestamp.desc()).limit(5).all()
    
    return render_template('dashboard.html', 
                          total_salas=total_salas,
                          salas_ativas=salas_ativas,
                          total_clientes=total_clientes,
                          clientes_online=clientes_online,
                          alertas_24h=alertas_24h,
                          ultimos_alertas=ultimos_alertas)

# Rotas para Salas
@app.route('/salas')
@login_required
def salas():
    """Lista todas as salas"""
    salas_lista = Sala.query.all()
    return render_template('salas.html', salas=salas_lista)

@app.route('/salas/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_sala():
    """Adiciona uma nova sala"""
    if request.method == 'POST':
        nome = request.form.get('nome')
        descricao = request.form.get('descricao')
        setor = request.form.get('setor')
        andar = request.form.get('andar')
        prioritaria = 'prioritaria' in request.form
        
        try:
            nova_sala = Sala(
                nome=nome,
                descricao=descricao,
                setor=setor,
                andar=andar,
                prioritaria=prioritaria,
                ativo=True
            )
            
            db.session.add(nova_sala)
            db.session.commit()
            
            logger.info(f"Sala adicionada: {nome}")
            flash('Sala adicionada com sucesso!', 'success')
            return redirect(url_for('salas'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao adicionar sala: {e}")
            flash(f'Erro ao adicionar sala: {e}', 'danger')
    
    return render_template('sala_form.html', sala=None)

@app.route('/salas/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_sala(id):
    """Edita uma sala existente"""
    sala = Sala.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            sala.nome = request.form.get('nome')
            sala.descricao = request.form.get('descricao')
            sala.setor = request.form.get('setor')
            sala.andar = request.form.get('andar')
            sala.prioritaria = 'prioritaria' in request.form
            sala.ativo = 'ativo' in request.form
            
            db.session.commit()
            
            logger.info(f"Sala editada: {sala.nome}")
            flash('Sala atualizada com sucesso!', 'success')
            return redirect(url_for('salas'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar sala: {e}")
            flash(f'Erro ao atualizar sala: {e}', 'danger')
    
    return render_template('sala_form.html', sala=sala)

@app.route('/salas/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_sala(id):
    """Exclui uma sala"""
    sala = Sala.query.get_or_404(id)
    
    try:
        nome = sala.nome
        db.session.delete(sala)
        db.session.commit()
        
        logger.info(f"Sala excluída: {nome}")
        flash('Sala excluída com sucesso!', 'success')
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir sala: {e}")
        flash(f'Erro ao excluir sala: {e}', 'danger')
    
    return redirect(url_for('salas'))

# Rotas para Clientes Mestres
@app.route('/clientes')
@login_required
def clientes():
    """Lista todos os clientes mestres"""
    clientes_lista = ClienteMestre.query.all()
    return render_template('clientes.html', clientes=clientes_lista)

@app.route('/clientes/adicionar', methods=['GET', 'POST'])
@login_required
def adicionar_cliente():
    """Adiciona um novo cliente mestre"""
    if request.method == 'POST':
        hostname = request.form.get('hostname')
        descricao = request.form.get('descricao')
        ip = request.form.get('ip')
        setor = request.form.get('setor')
        nivel_acesso = request.form.get('nivel_acesso', 1, type=int)
        
        try:
            novo_cliente = ClienteMestre(
                hostname=hostname,
                descricao=descricao,
                ip=ip,
                setor=setor,
                nivel_acesso=nivel_acesso,
                ativo=True
            )
            
            db.session.add(novo_cliente)
            db.session.commit()
            
            logger.info(f"Cliente mestre adicionado: {hostname}")
            flash('Cliente mestre adicionado com sucesso!', 'success')
            return redirect(url_for('clientes'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao adicionar cliente mestre: {e}")
            flash(f'Erro ao adicionar cliente mestre: {e}', 'danger')
    
    return render_template('cliente_form.html', cliente=None)

@app.route('/clientes/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_cliente(id):
    """Edita um cliente mestre existente"""
    cliente = ClienteMestre.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            cliente.hostname = request.form.get('hostname')
            cliente.descricao = request.form.get('descricao')
            cliente.ip = request.form.get('ip')
            cliente.setor = request.form.get('setor')
            cliente.nivel_acesso = request.form.get('nivel_acesso', 1, type=int)
            cliente.ativo = 'ativo' in request.form
            
            db.session.commit()
            
            logger.info(f"Cliente mestre editado: {cliente.hostname}")
            flash('Cliente mestre atualizado com sucesso!', 'success')
            return redirect(url_for('clientes'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao editar cliente mestre: {e}")
            flash(f'Erro ao atualizar cliente mestre: {e}', 'danger')
    
    return render_template('cliente_form.html', cliente=cliente)

@app.route('/clientes/excluir/<int:id>', methods=['POST'])
@login_required
def excluir_cliente(id):
    """Exclui um cliente mestre"""
    cliente = ClienteMestre.query.get_or_404(id)
    
    try:
        hostname = cliente.hostname
        db.session.delete(cliente)
        db.session.commit()
        
        logger.info(f"Cliente mestre excluído: {hostname}")
        flash('Cliente mestre excluído com sucesso!', 'success')
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao excluir cliente mestre: {e}")
        flash(f'Erro ao excluir cliente mestre: {e}', 'danger')
    
    return redirect(url_for('clientes'))

@app.route('/api/cliente/<int:id>/testar', methods=['POST'])
@login_required
def testar_cliente(id):
    """Testa a conexão com um cliente mestre"""
    cliente = ClienteMestre.query.get_or_404(id)
    
    try:
        # Aqui podemos implementar a lógica de teste
        # Por exemplo, enviando um ping para o cliente
        # e verificando a resposta
        
        # Simulando teste bem-sucedido para demonstração
        if cliente.is_online():
            status = "online"
            mensagem = f"Cliente {cliente.hostname} está online e respondendo corretamente."
        else:
            status = "offline"
            mensagem = f"Cliente {cliente.hostname} está offline ou não responde."
            
        return jsonify({
            "success": True,
            "status": status,
            "mensagem": mensagem
        })
    
    except Exception as e:
        logger.error(f"Erro ao testar cliente {cliente.hostname}: {e}")
        return jsonify({
            "success": False,
            "status": "erro",
            "mensagem": f"Erro ao testar cliente: {str(e)}"
        })

@app.route('/api/cliente/<int:id>/detalhes', methods=['GET'])
@login_required
def detalhes_cliente(id):
    """Retorna detalhes de um cliente mestre via AJAX"""
    cliente = ClienteMestre.query.get_or_404(id)
    
    ultima_conexao = "Nunca" if not cliente.ultima_conexao else cliente.ultima_conexao.strftime("%d/%m/%Y %H:%M:%S")
    
    return jsonify({
        "id": cliente.id,
        "hostname": cliente.hostname,
        "descricao": cliente.descricao or "Sem descrição",
        "ip": cliente.ip or "Desconhecido",
        "setor": cliente.setor or "Não especificado",
        "nivel_acesso": cliente.nivel_acesso,
        "ativo": cliente.ativo,
        "online": cliente.is_online(),
        "ultima_conexao": ultima_conexao,
        "data_criacao": cliente.data_criacao.strftime("%d/%m/%Y %H:%M:%S")
    })

# Rotas para Logs de Alertas
@app.route('/logs')
@login_required
def listar_logs():
    """Lista todos os logs de alertas"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        tipo = request.args.get('tipo', '', type=str)
        data_inicio = request.args.get('data_inicio', '', type=str)
        data_fim = request.args.get('data_fim', '', type=str)
        
        query = LogAlerta.query
        
        if search:
            query = query.filter(
                db.or_(
                    LogAlerta.hostname.contains(search),
                    LogAlerta.sala.contains(search),
                    LogAlerta.usuario_windows.contains(search)
                )
            )
        
        if tipo:
            if tipo == 'processado':
                query = query.filter_by(processado=True)
            elif tipo == 'nao_processado':
                query = query.filter_by(processado=False)
        
        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(LogAlerta.timestamp >= data_inicio_dt)
            except:
                pass
        
        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d')
                data_fim_dt = data_fim_dt + timedelta(days=1)  # Incluir o dia inteiro
                query = query.filter(LogAlerta.timestamp <= data_fim_dt)
            except:
                pass
        
        # Ordenar por data (mais recente primeiro)
        query = query.order_by(LogAlerta.timestamp.desc())
        
        # Paginar resultados
        logs_paginados = query.paginate(page=page, per_page=20)
        
        return render_template('logs.html', 
                              logs=logs_paginados,
                              search=search,
                              tipo=tipo,
                              data_inicio=data_inicio,
                              data_fim=data_fim)
    
    except Exception as e:
        logger.error(f"Erro ao listar logs: {e}")
        flash(f'Erro ao carregar logs: {e}', 'danger')
        return render_template('logs.html', logs=None)

@app.route('/logs/<int:id>', methods=['GET', 'POST'])
@login_required
def visualizar_log(id):
    """Visualiza e edita um log específico"""
    log = LogAlerta.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            log.processado = 'processado' in request.form
            log.observacoes = request.form.get('observacoes')
            
            db.session.commit()
            
            logger.info(f"Log {id} atualizado")
            flash('Log atualizado com sucesso!', 'success')
            return redirect(url_for('listar_logs'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao atualizar log: {e}")
            flash(f'Erro ao atualizar log: {e}', 'danger')
    
    return render_template('log_detalhes.html', log=log)

@app.route('/api/logs/limpar', methods=['POST'])
@login_required
def limpar_logs():
    """Remove logs antigos (mais de 30 dias)"""
    try:
        data_limite = datetime.utcnow() - timedelta(days=30)
        
        # Remover logs antigos
        logs_antigos = LogAlerta.query.filter(LogAlerta.timestamp < data_limite).all()
        count = len(logs_antigos)
        
        for log in logs_antigos:
            db.session.delete(log)
        
        db.session.commit()
        
        logger.info(f"{count} logs antigos removidos")
        
        return jsonify({
            "success": True,
            "message": f"{count} logs antigos foram removidos com sucesso"
        })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao limpar logs antigos: {e}")
        
        return jsonify({
            "success": False,
            "message": f"Erro ao remover logs: {str(e)}"
        })

# API para status do sistema
@app.route('/api/status')
def api_status():
    """API para status do sistema"""
    try:
        # Estatísticas básicas
        total_salas = Sala.query.count()
        salas_ativas = Sala.query.filter_by(ativo=True).count()
        total_clientes = ClienteMestre.query.count()
        clientes_ativos = ClienteMestre.query.filter_by(ativo=True).count()
        
        # Logs recentes
        ontem = datetime.utcnow() - timedelta(days=1)
        logs_24h = LogAlerta.query.filter(LogAlerta.timestamp >= ontem).count()
        
        return jsonify({
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
            'estatisticas': {
                'total_salas': total_salas,
                'salas_ativas': salas_ativas,
                'total_clientes': total_clientes,
                'clientes_ativos': clientes_ativos,
                'logs_24h': logs_24h
            }
        })
    
    except Exception as e:
        logger.error(f"Erro na API de status: {e}")
        return jsonify({
            'status': 'erro',
            'mensagem': str(e)
        }), 500

if __name__ == '__main__':
    with app.app_context():
        # Criar tabelas se não existirem
        db.create_all()
        
        # Verificar se existe um usuário admin
        admin = Usuario.query.filter_by(email='admin@example.com').first()
        if not admin:
            admin = Usuario(
                nome='Administrador',
                email='admin@example.com',
                admin=True,
                ativo=True
            )
            admin.set_senha('admin123')
            db.session.add(admin)
            db.session.commit()
            logger.info("Usuário admin padrão criado")
    
    app.run(host=Config().FLASK_HOST, port=Config().FLASK_PORT, debug=True) 