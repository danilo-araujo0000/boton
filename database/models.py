from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import json

db = SQLAlchemy()

class Sala(db.Model):
    __tablename__ = 'salas'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), unique=True, nullable=False, index=True)
    nome_sala = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    setor = db.Column(db.String(100), nullable=True)
    andar = db.Column(db.String(50), nullable=True)
    prioritaria = db.Column(db.Boolean, default=False, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relacionamento com logs
    logs = db.relationship('LogAlerta', backref='sala_obj', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Sala {self.hostname}: {self.nome_sala}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'nome_sala': self.nome_sala,
            'descricao': self.descricao,
            'setor': self.setor,
            'andar': self.andar,
            'prioritaria': self.prioritaria,
            'ativo': self.ativo,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }

class ClienteMestre(db.Model):
    __tablename__ = 'clientes_mestres'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), unique=True, nullable=False, index=True)
    nome = db.Column(db.String(200), nullable=True)
    setor = db.Column(db.String(100), nullable=True)
    nivel_acesso = db.Column(db.String(50), default='basico', nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    ultimo_ping = db.Column(db.DateTime, nullable=True)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ClienteMestre {self.hostname}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'nome': self.nome,
            'setor': self.setor,
            'nivel_acesso': self.nivel_acesso,
            'ativo': self.ativo,
            'ultimo_ping': self.ultimo_ping.isoformat() if self.ultimo_ping else None,
            'criado_em': self.criado_em.isoformat() if self.criado_em else None,
            'atualizado_em': self.atualizado_em.isoformat() if self.atualizado_em else None
        }
    
    def is_online(self):
        """Verifica se o cliente está online baseado no último ping"""
        if not self.ultimo_ping:
            return False
        
        # Considera online se o último ping foi nos últimos 5 minutos
        return datetime.utcnow() - self.ultimo_ping < timedelta(minutes=5)

class LogAlerta(db.Model):
    __tablename__ = 'logs_alertas'
    
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(100), nullable=False, index=True)
    sala = db.Column(db.String(200), nullable=False)
    usuario_windows = db.Column(db.String(100), nullable=False)
    codigo = db.Column(db.String(50), nullable=False)
    tipo_alerta = db.Column(db.String(20), default='alerta', nullable=False)  # 'alerta' ou 'teste'
    ip_origem = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    processado = db.Column(db.Boolean, default=True, nullable=False)
    
    # Foreign key para sala
    sala_id = db.Column(db.Integer, db.ForeignKey('salas.id'), nullable=True)
    
    def __repr__(self):
        return f'<LogAlerta {self.hostname} - {self.sala} - {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'hostname': self.hostname,
            'sala': self.sala,
            'usuario_windows': self.usuario_windows,
            'codigo': self.codigo,
            'tipo_alerta': self.tipo_alerta,
            'ip_origem': self.ip_origem,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'processado': self.processado,
            'sala_id': self.sala_id
        }

class ConfiguracaoSistema(db.Model):
    __tablename__ = 'configuracoes_sistema'
    
    id = db.Column(db.Integer, primary_key=True)
    chave = db.Column(db.String(100), unique=True, nullable=False)
    valor = db.Column(db.Text, nullable=False)
    descricao = db.Column(db.Text, nullable=True)
    tipo = db.Column(db.String(20), default='string', nullable=False)  # string, int, bool, json
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)
    atualizado_em = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ConfiguracaoSistema {self.chave}: {self.valor}>'
    
    def get_valor(self):
        """Retorna o valor convertido para o tipo apropriado"""
        if self.tipo == 'int':
            return int(self.valor)
        elif self.tipo == 'bool':
            return self.valor.lower() in ('true', '1', 'yes', 'on')
        elif self.tipo == 'json':
            return json.loads(self.valor)
        else:
            return self.valor
    
    def set_valor(self, valor):
        """Define o valor convertendo para string"""
        if self.tipo == 'json':
            self.valor = json.dumps(valor)
        else:
            self.valor = str(valor)

class StatusServidor(db.Model):
    __tablename__ = 'status_servidor'
    
    id = db.Column(db.Integer, primary_key=True)
    servidor = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'online', 'offline', 'erro'
    ultima_verificacao = db.Column(db.DateTime, default=datetime.utcnow)
    detalhes = db.Column(db.Text, nullable=True)
    
    def __repr__(self):
        return f'<StatusServidor {self.servidor}: {self.status}>' 