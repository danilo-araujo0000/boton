#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import logging
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from config import Config
from database.models import db, Sala, ClienteMestre, LogAlerta
from database.database_manager import DatabaseManager

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('admin.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY
app.config['SQLALCHEMY_DATABASE_URI'] = Config.get_database_url()
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
db_manager = DatabaseManager()

@app.route('/')
def dashboard():
    """Dashboard principal"""
    try:
        with app.app_context():
            # Estatísticas gerais
            total_salas = Sala.query.count()
            total_clientes = ClienteMestre.query.count()
            
            # Alertas de hoje
            hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            alertas_hoje = LogAlerta.query.filter(LogAlerta.timestamp >= hoje).count()
            
            # Alertas de ontem para comparação
            ontem = hoje - timedelta(days=1)
            alertas_ontem = LogAlerta.query.filter(
                LogAlerta.timestamp >= ontem,
                LogAlerta.timestamp < hoje
            ).count()
            
            # Alertas da última semana
            semana_passada = hoje - timedelta(days=7)
            alertas_semana = LogAlerta.query.filter(LogAlerta.timestamp >= semana_passada).count()
            
            # Últimos alertas
            ultimos_alertas = LogAlerta.query.order_by(LogAlerta.timestamp.desc()).limit(10).all()
            
            # Clientes online
            clientes_online = sum(1 for c in ClienteMestre.query.all() if c.is_online())
            
            return render_template('dashboard.html',
                                 total_salas=total_salas,
                                 total_clientes=total_clientes,
                                 alertas_hoje=alertas_hoje,
                                 alertas_ontem=alertas_ontem,
                                 alertas_semana=alertas_semana,
                                 ultimos_alertas=ultimos_alertas,
                                 clientes_online=clientes_online)
    except Exception as e:
        logger.error(f"Erro no dashboard: {e}")
        flash(f"Erro ao carregar dashboard: {e}", "error")
        return render_template('dashboard.html',
                             total_salas=0, total_clientes=0, alertas_hoje=0,
                             alertas_ontem=0, alertas_semana=0, ultimos_alertas=[],
                             clientes_online=0)

@app.route('/salas')
def salas():
    """Lista todas as salas"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Filtros
        hostname = request.args.get('hostname', '').strip()
        nome = request.args.get('nome', '').strip()
        setor = request.args.get('setor', '').strip()
        
        query = Sala.query
        
        if hostname:
            query = query.filter(Sala.hostname.contains(hostname))
        if nome:
            query = query.filter(Sala.nome_sala.contains(nome))
        if setor:
            query = query.filter(Sala.setor == setor)
        
        salas = query.order_by(Sala.nome_sala).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('salas.html', salas=salas)
    except Exception as e:
        logger.error(f"Erro ao listar salas: {e}")
        flash(f"Erro ao carregar salas: {e}", "error")
        return redirect(url_for('dashboard'))

@app.route('/salas/nova', methods=['GET', 'POST'])
def nova_sala():
    """Criar nova sala"""
    if request.method == 'POST':
        try:
            hostname = request.form.get('hostname', '').strip()
            nome = request.form.get('nome', '').strip()
            descricao = request.form.get('descricao', '').strip()
            setor = request.form.get('setor', '').strip()
            andar = request.form.get('andar', '').strip()
            ativo = 'ativo' in request.form
            prioritaria = 'prioritaria' in request.form
            
            if not hostname or not nome:
                flash("Hostname e nome são obrigatórios", "error")
                return render_template('sala_form.html')
            
            # Verificar se hostname já existe
            if Sala.query.filter_by(hostname=hostname).first():
                flash("Hostname já existe", "error")
                return render_template('sala_form.html')
            
            sala = Sala(
                hostname=hostname,
                nome_sala=nome,
                descricao=descricao or None,
                setor=setor or None,
                andar=andar or None,
                ativo=ativo,
                prioritaria=prioritaria
            )
            
            db.session.add(sala)
            db.session.commit()
            
            flash(f"Sala '{nome}' criada com sucesso!", "success")
            return redirect(url_for('salas'))
            
        except Exception as e:
            logger.error(f"Erro ao criar sala: {e}")
            db.session.rollback()
            flash(f"Erro ao criar sala: {e}", "error")
    
    return render_template('sala_form.html')

@app.route('/salas/<int:id>/editar', methods=['GET', 'POST'])
def editar_sala(id):
    """Editar sala existente"""
    sala = Sala.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            sala.nome_sala = request.form.get('nome', '').strip()
            sala.descricao = request.form.get('descricao', '').strip() or None
            sala.setor = request.form.get('setor', '').strip() or None
            sala.andar = request.form.get('andar', '').strip() or None
            sala.ativo = 'ativo' in request.form
            sala.prioritaria = 'prioritaria' in request.form
            sala.atualizado_em = datetime.now(timezone.utc)
            
            if not sala.nome_sala:
                flash("Nome é obrigatório", "error")
                return render_template('sala_form.html', sala=sala)
            
            db.session.commit()
            flash(f"Sala '{sala.nome_sala}' atualizada com sucesso!", "success")
            return redirect(url_for('salas'))
            
        except Exception as e:
            logger.error(f"Erro ao atualizar sala: {e}")
            db.session.rollback()
            flash(f"Erro ao atualizar sala: {e}", "error")
    
    return render_template('sala_form.html', sala=sala)

@app.route('/salas/<int:id>/excluir', methods=['POST'])
def excluir_sala(id):
    """Excluir sala"""
    try:
        sala = Sala.query.get_or_404(id)
        nome = sala.nome_sala
        
        db.session.delete(sala)
        db.session.commit()
        
        flash(f"Sala '{nome}' excluída com sucesso!", "success")
    except Exception as e:
        logger.error(f"Erro ao excluir sala: {e}")
        db.session.rollback()
        flash(f"Erro ao excluir sala: {e}", "error")
    
    return redirect(url_for('salas'))

@app.route('/clientes')
def clientes():
    """Lista todos os clientes mestres"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = 20
        
        # Filtros
        hostname = request.args.get('hostname', '').strip()
        nome = request.args.get('nome', '').strip()
        setor = request.args.get('setor', '').strip()
        status = request.args.get('status', '').strip()
        
        query = ClienteMestre.query
        
        if hostname:
            query = query.filter(ClienteMestre.hostname.contains(hostname))
        if nome:
            query = query.filter(ClienteMestre.nome.contains(nome))
        if setor:
            query = query.filter(ClienteMestre.setor == setor)
        if status == 'ativo':
            query = query.filter(ClienteMestre.ativo == True)
        elif status == 'inativo':
            query = query.filter(ClienteMestre.ativo == False)
        
        clientes = query.order_by(ClienteMestre.nome).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return render_template('clientes.html', clientes=clientes)
    except Exception as e:
        logger.error(f"Erro ao listar clientes: {e}")
        flash(f"Erro ao carregar clientes: {e}", "error")
        return redirect(url_for('dashboard'))

@app.route('/clientes/novo', methods=['GET', 'POST'])
def novo_cliente():
    """Criar novo cliente mestre"""
    if request.method == 'POST':
        try:
            hostname = request.form.get('hostname', '').strip()
            nome = request.form.get('nome', '').strip()
            setor = request.form.get('setor', '').strip()
            nivel_acesso = request.form.get('nivel_acesso', 'basico').strip()
            ativo = 'ativo' in request.form
            
            if not hostname or not nome:
                flash("Hostname e nome são obrigatórios", "error")
                return render_template('cliente_form.html')
            
            # Verificar se hostname já existe
            if ClienteMestre.query.filter_by(hostname=hostname).first():
                flash("Hostname já existe", "error")
                return render_template('cliente_form.html')
            
            cliente = ClienteMestre(
                hostname=hostname,
                nome=nome,
                setor=setor or None,
                nivel_acesso=nivel_acesso,
                ativo=ativo
            )
            
            db.session.add(cliente)
            db.session.commit()
            
            flash('Cliente mestre adicionado com sucesso', 'success')
            return redirect(url_for('clientes'))
        
        except Exception as e:
            logger.error(f"Erro ao adicionar cliente: {e}")
            flash(f"Erro ao adicionar cliente: {e}", 'error')
            db.session.rollback()
    
    return render_template('cliente_form.html')

@app.route('/clientes/<int:id>/editar', methods=['GET', 'POST'])
def editar_cliente(id):
    """Edita um cliente mestre existente"""
    cliente = ClienteMestre.query.get_or_404(id)
    
    if request.method == 'POST':
        try:
            hostname = request.form['hostname'].strip()
            nome = request.form['nome'].strip()
            setor = request.form.get('setor', '').strip()
            nivel_acesso = request.form.get('nivel_acesso', 'basico').strip()
            ativo = 'ativo' in request.form
            
            if not hostname:
                flash('Hostname é obrigatório', 'error')
                return render_template('cliente_form.html', cliente=cliente)
            
            # Verificar se hostname já existe (exceto para o cliente atual)
            cliente_existente = ClienteMestre.query.filter(
                ClienteMestre.hostname == hostname,
                ClienteMestre.id != id
            ).first()
            
            if cliente_existente:
                flash('Hostname já existe', 'error')
                return render_template('cliente_form.html', cliente=cliente)
            
            cliente.hostname = hostname
            cliente.nome = nome if nome else None
            cliente.setor = setor or None
            cliente.nivel_acesso = nivel_acesso
            cliente.ativo = ativo
            cliente.atualizado_em = datetime.now(timezone.utc)
            
            db.session.commit()
            
            flash('Cliente mestre atualizado com sucesso', 'success')
            return redirect(url_for('clientes'))
        
        except Exception as e:
            logger.error(f"Erro ao editar cliente: {e}")
            flash(f"Erro ao editar cliente: {e}", 'error')
            db.session.rollback()
    
    return render_template('cliente_form.html', cliente=cliente)

@app.route('/clientes/<int:id>/deletar', methods=['POST'])
def deletar_cliente(id):
    """Deleta um cliente mestre"""
    try:
        cliente = ClienteMestre.query.get_or_404(id)
        db.session.delete(cliente)
        db.session.commit()
        
        flash('Cliente mestre deletado com sucesso', 'success')
        
    except Exception as e:
        logger.error(f"Erro ao deletar cliente: {e}")
        flash(f"Erro ao deletar cliente: {e}", 'error')
        db.session.rollback()
    
    return redirect(url_for('clientes'))

@app.route('/logs')
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
            query = query.filter(LogAlerta.tipo_alerta == tipo)
        
        if data_inicio:
            try:
                data_inicio_dt = datetime.strptime(data_inicio, '%Y-%m-%d')
                query = query.filter(LogAlerta.timestamp >= data_inicio_dt)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim_dt = datetime.strptime(data_fim, '%Y-%m-%d') + timedelta(days=1)
                query = query.filter(LogAlerta.timestamp < data_fim_dt)
            except ValueError:
                pass
        
        logs = query.order_by(LogAlerta.timestamp.desc()).paginate(
            page=page, per_page=50, error_out=False
        )
        
        return render_template('logs.html', 
                             logs=logs, 
                             search=search, 
                             tipo=tipo,
                             data_inicio=data_inicio,
                             data_fim=data_fim)
    
    except Exception as e:
        logger.error(f"Erro ao listar logs: {e}")
        flash(f"Erro ao carregar logs: {e}", 'error')
        return redirect(url_for('dashboard'))

@app.route('/api/cliente/<int:id>/testar', methods=['POST'])
def testar_cliente(id):
    """Testa a conexão com um cliente mestre"""
    try:
        cliente = ClienteMestre.query.get_or_404(id)
        
        # Aqui seria implementada a lógica para testar a conexão
        # Como exemplo, apenas verificamos se o cliente está online pelo último ping
        if cliente.is_online():
            # Atualizar o último ping
            cliente.ultimo_ping = datetime.now(timezone.utc)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Cliente está online'})
        else:
            return jsonify({'success': False, 'message': 'Cliente não responde'})
    
    except Exception as e:
        logger.error(f"Erro ao testar cliente {id}: {e}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'})

@app.route('/api/cliente/<int:id>/detalhes', methods=['GET'])
def cliente_detalhes(id):
    """Retorna detalhes de um cliente mestre em formato JSON para AJAX"""
    try:
        cliente = ClienteMestre.query.get_or_404(id)
        
        # Construir HTML para detalhes do cliente
        html = f"""
        <div class="row">
            <div class="col-md-6">
                <h5><i class="fa-solid fa-info-circle"></i> Informações Básicas</h5>
                <table class="table table-striped">
                    <tr>
                        <th>ID:</th>
                        <td>{cliente.id}</td>
                    </tr>
                    <tr>
                        <th>Hostname:</th>
                        <td>{cliente.hostname}</td>
                    </tr>
                    <tr>
                        <th>Nome:</th>
                        <td>{cliente.nome or '-'}</td>
                    </tr>
                    <tr>
                        <th>Setor:</th>
                        <td>{cliente.setor or '-'}</td>
                    </tr>
                    <tr>
                        <th>Nível Acesso:</th>
                        <td>{cliente.nivel_acesso}</td>
                    </tr>
                </table>
            </div>
            <div class="col-md-6">
                <h5><i class="fa-solid fa-clock"></i> Status e Tempos</h5>
                <table class="table table-striped">
                    <tr>
                        <th>Status:</th>
                        <td>
                            {'<span class="badge bg-success">Online</span>' if cliente.is_online() else 
                             '<span class="badge bg-warning">Offline</span>'}
                        </td>
                    </tr>
                    <tr>
                        <th>Ativo:</th>
                        <td>
                            {'<span class="badge bg-success">Sim</span>' if cliente.ativo else 
                             '<span class="badge bg-danger">Não</span>'}
                        </td>
                    </tr>
                    <tr>
                        <th>Último Ping:</th>
                        <td>{cliente.ultimo_ping.strftime('%d/%m/%Y %H:%M:%S') if cliente.ultimo_ping else 'Nunca'}</td>
                    </tr>
                    <tr>
                        <th>Criado em:</th>
                        <td>{cliente.criado_em.strftime('%d/%m/%Y %H:%M:%S') if cliente.criado_em else '-'}</td>
                    </tr>
                    <tr>
                        <th>Atualizado em:</th>
                        <td>{cliente.atualizado_em.strftime('%d/%m/%Y %H:%M:%S') if cliente.atualizado_em else '-'}</td>
                    </tr>
                </table>
            </div>
        </div>
        """
        
        return jsonify({
            'success': True,
            'html': html
        })
    
    except Exception as e:
        logger.error(f"Erro ao obter detalhes do cliente {id}: {e}")
        return jsonify({
            'success': False,
            'message': str(e),
            'html': f'<div class="alert alert-danger">Erro ao carregar detalhes: {str(e)}</div>'
        })

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
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/logs/limpar', methods=['POST'])
def limpar_logs():
    """Remove logs antigos (mais de 30 dias)"""
    try:
        # Calcular data limite (30 dias atrás)
        data_limite = datetime.now(timezone.utc) - timedelta(days=30)
        
        # Obter logs antigos
        logs_antigos = LogAlerta.query.filter(LogAlerta.timestamp < data_limite).all()
        
        if not logs_antigos:
            return jsonify({
                'success': True,
                'message': 'Não há logs antigos para remover',
                'count': 0
            })
        
        # Remover logs antigos
        count = len(logs_antigos)
        for log in logs_antigos:
            db.session.delete(log)
        
        db.session.commit()
        
        logger.info(f"Removidos {count} logs antigos")
        
        return jsonify({
            'success': True,
            'message': f'{count} logs antigos foram removidos com sucesso',
            'count': count
        })
    
    except Exception as e:
        logger.error(f"Erro ao limpar logs antigos: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'message': f'Erro ao limpar logs: {str(e)}'
        }), 500

if __name__ == '__main__':
    with app.app_context():
        # Criar banco se não existir
        db_manager.create_database_if_not_exists()
        
        # Criar tabelas
        db.create_all()
        
        # Migrar dados se necessário
        if Sala.query.count() == 0:
            logger.info("Iniciando migração dos dados...")
            db_manager.migrate_from_txt_files(app)
    
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=True) 