import mysql.connector
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from config import Config
from database.models import db, Sala, ClienteMestre, LogAlerta, ConfiguracaoSistema

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        self.config = Config()
        
    def create_database_if_not_exists(self):
        """Cria o banco de dados se não existir"""
        try:
            connection = mysql.connector.connect(
                host=self.config.DATABASE_HOST,
                user=self.config.DATABASE_USER,
                password=self.config.DATABASE_PASSWORD,
                port=self.config.DATABASE_PORT
            )
            cursor = connection.cursor()
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {self.config.DATABASE_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            connection.commit()
            cursor.close()
            connection.close()
            logger.info(f"Banco de dados {self.config.DATABASE_NAME} criado/verificado com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao criar banco de dados: {e}")
            return False
    
    def migrate_from_txt_files(self, app):
        """Migra dados dos arquivos txt para o banco de dados"""
        with app.app_context():
            try:
                # Migrar salas do salas.txt
                self._migrate_salas()
                
                # Migrar clientes mestres do permitidos.txt
                self._migrate_clientes_mestres()
                
                # Migrar logs dos arquivos de log
                self._migrate_logs()
                
                logger.info("Migração dos dados concluída com sucesso")
                return True
                
            except Exception as e:
                logger.error(f"Erro durante a migração: {e}")
                return False
    
    def _migrate_salas(self):
        """Migra dados do arquivo salas.txt"""
        try:
            with open('salas.txt', 'r', encoding='utf-8') as f:
                salas_data = json.load(f)
            
            for hostname, nome_sala in salas_data.items():
                # Verifica se a sala já existe
                sala_existente = Sala.query.filter_by(hostname=hostname).first()
                if not sala_existente:
                    nova_sala = Sala(
                        hostname=hostname,
                        nome_sala=nome_sala,
                        ativo=True
                    )
                    db.session.add(nova_sala)
                else:
                    # Atualiza o nome se mudou
                    sala_existente.nome_sala = nome_sala
                    sala_existente.atualizado_em = datetime.utcnow()
            
            db.session.commit()
            logger.info(f"Migração de {len(salas_data)} salas concluída")
            
        except FileNotFoundError:
            logger.warning("Arquivo salas.txt não encontrado")
        except Exception as e:
            logger.error(f"Erro ao migrar salas: {e}")
            db.session.rollback()
    
    def _migrate_clientes_mestres(self):
        """Migra dados do arquivo permitidos.txt"""
        try:
            with open('permitidos.txt', 'r', encoding='utf-8') as f:
                clientes_data = [line.strip() for line in f if line.strip()]
            
            for hostname in clientes_data:
                # Verifica se o cliente já existe
                cliente_existente = ClienteMestre.query.filter_by(hostname=hostname).first()
                if not cliente_existente:
                    novo_cliente = ClienteMestre(
                        hostname=hostname,
                        ativo=True
                    )
                    db.session.add(novo_cliente)
            
            db.session.commit()
            logger.info(f"Migração de {len(clientes_data)} clientes mestres concluída")
            
        except FileNotFoundError:
            logger.warning("Arquivo permitidos.txt não encontrado")
        except Exception as e:
            logger.error(f"Erro ao migrar clientes mestres: {e}")
            db.session.rollback()
    
    def _migrate_logs(self):
        """Migra logs dos arquivos de texto"""
        import os
        import re
        
        try:
            logs_dir = 'logs'
            if not os.path.exists(logs_dir):
                logger.warning("Diretório de logs não encontrado")
                return
            
            log_files = [f for f in os.listdir(logs_dir) if f.endswith('.txt')]
            total_logs = 0
            
            for log_file in log_files:
                file_path = os.path.join(logs_dir, log_file)
                
                # Extrair informações do nome do arquivo
                # Formato: codigo_violeta_DD-MM-YYYY_SALA.txt
                match = re.match(r'codigo_violeta_(\d{2}-\d{2}-\d{4})_(.+)\.txt', log_file)
                if not match:
                    continue
                
                data_str, sala_nome = match.groups()
                sala_nome = sala_nome.replace('_', ' ')
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                    
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        
                        # Tentar extrair informações da linha de log
                        # Formato esperado: "Botao acionado pelo usuario USUARIO na SALA - DD/MM/YYYY HH:MM:SS"
                        log_match = re.search(r'Botao acionado pelo usuario (.+?) na (.+?) - (\d{2}/\d{2}/\d{4} \d{2}:\d{2}:\d{2})', line)
                        if log_match:
                            usuario, sala_log, timestamp_str = log_match.groups()
                            
                            try:
                                timestamp = datetime.strptime(timestamp_str, '%d/%m/%Y %H:%M:%S')
                            except:
                                timestamp = datetime.utcnow()
                            
                            # Verificar se o log já existe
                            log_existente = LogAlerta.query.filter_by(
                                usuario_windows=usuario,
                                sala=sala_log,
                                timestamp=timestamp
                            ).first()
                            
                            if not log_existente:
                                # Tentar encontrar o hostname pela sala
                                sala_obj = Sala.query.filter_by(nome_sala=sala_log).first()
                                hostname = sala_obj.hostname if sala_obj else 'desconhecido'
                                
                                novo_log = LogAlerta(
                                    hostname=hostname,
                                    sala=sala_log,
                                    usuario_windows=usuario,
                                    codigo='codigo violeta!',
                                    tipo_alerta='teste' if usuario.lower() == 'teste' else 'alerta',
                                    timestamp=timestamp,
                                    processado=True,
                                    sala_id=sala_obj.id if sala_obj else None
                                )
                                db.session.add(novo_log)
                                total_logs += 1
                
                except Exception as e:
                    logger.error(f"Erro ao processar arquivo {log_file}: {e}")
                    continue
            
            db.session.commit()
            logger.info(f"Migração de {total_logs} logs concluída")
            
        except Exception as e:
            logger.error(f"Erro ao migrar logs: {e}")
            db.session.rollback()
    
    def get_salas_dict(self) -> Dict[str, str]:
        """Retorna dicionário de salas no formato {hostname: nome_sala}"""
        salas = Sala.query.filter_by(ativo=True).all()
        return {sala.hostname: sala.nome_sala for sala in salas}
    
    def get_clientes_mestres_list(self) -> List[str]:
        """Retorna lista de hostnames dos clientes mestres ativos"""
        clientes = ClienteMestre.query.filter_by(ativo=True).all()
        return [cliente.hostname for cliente in clientes]
    
    def salvar_log_alerta(self, hostname: str, codigo: str, usuario_windows: str, ip_origem: str = None):
        """Salva um novo log de alerta no banco de dados"""
        try:
            # Buscar informações da sala
            sala_obj = Sala.query.filter_by(hostname=hostname).first()
            sala_nome = sala_obj.nome_sala if sala_obj else 'Sala Desconhecida'
            
            # Determinar tipo de alerta
            tipo_alerta = 'teste' if usuario_windows.lower().strip() == 'teste' else 'alerta'
            
            novo_log = LogAlerta(
                hostname=hostname,
                sala=sala_nome,
                usuario_windows=usuario_windows,
                codigo=codigo,
                tipo_alerta=tipo_alerta,
                ip_origem=ip_origem,
                timestamp=datetime.utcnow(),
                processado=True,
                sala_id=sala_obj.id if sala_obj else None
            )
            
            db.session.add(novo_log)
            db.session.commit()
            
            logger.info(f"Log salvo: {hostname} - {sala_nome} - {usuario_windows}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar log: {e}")
            db.session.rollback()
            return False
    
    def atualizar_ping_cliente_mestre(self, hostname: str):
        """Atualiza o último ping de um cliente mestre"""
        try:
            cliente = ClienteMestre.query.filter_by(hostname=hostname).first()
            if cliente:
                cliente.ultimo_ping = datetime.utcnow()
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Erro ao atualizar ping do cliente {hostname}: {e}")
            db.session.rollback()
            return False 