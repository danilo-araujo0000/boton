# Dashboard - Sistema Botão de Pânico

Dashboard web profissional para gerenciamento e monitoramento do sistema de botão de pânico.

## 🚀 Funcionalidades

### 📊 **Início (Visão Geral)**
- Estatísticas gerais do sistema
- Status do servidor principal em tempo real
- Últimos acionamentos de alerta
- Logs recentes do sistema
- Atualização automática a cada 30 segundos

### 🏢 **Gerenciar Salas**
- Visualizar todas as salas cadastradas
- Adicionar novas salas
- Editar informações das salas
- Excluir salas
- Link direto para gerenciar usuários

### 👥 **Gerenciar Usuários**
- Visualizar todos os usuários cadastrados
- Adicionar novos usuários
- Editar informações dos usuários
- Excluir usuários
- Campos: Nome completo, Username, Email, Telefone

### 🖥️ **Gerenciar Receptores**
- Visualizar todos os receptores cadastrados
- Adicionar novos receptores
- Editar informações dos receptores
- Excluir receptores
- Teste de conectividade em tempo real
- Status online/offline de cada receptor

### 📋 **Logs do Sistema**
- Visualização de logs de alertas e sistema
- Filtros por período (1, 7, 30, 90 dias)
- Filtros por tipo (alertas, sistema, todos)
- Separação em abas para melhor organização
- Exportação de logs em CSV
- Estatísticas rápidas
- Atualização automática

## 🛠️ Instalação

1. **Instalar dependências:**
```bash
pip install -r requirements.txt
```

2. **Configurar variáveis de ambiente:**
Certifique-se de que o arquivo `.env` está configurado com:
```
DATABASE_HOST=seu_host
DATABASE_USER=seu_usuario
PASSWORD=sua_senha
```

3. **Executar a dashboard:**
```bash
python app.py
```

4. **Acessar a dashboard:**
Abra o navegador em: `http://localhost:8080`

## 🎨 Interface

- **Design moderno** com Bootstrap 5
- **Responsivo** para desktop e mobile
- **Sidebar com navegação** intuitiva
- **Cards interativos** com hover effects
- **Tabelas responsivas** com paginação
- **Modais para CRUD** operations
- **Toasts para feedback** do usuário
- **Ícones Bootstrap** para melhor UX

## 🔧 Tecnologias

- **Backend:** Flask (Python)
- **Frontend:** Bootstrap 5, JavaScript
- **Banco de Dados:** MySQL
- **Ícones:** Bootstrap Icons
- **Gráficos:** Chart.js (preparado para uso futuro)

## 📡 APIs Disponíveis

### Salas
- `POST /api/salas` - Adicionar sala
- `PUT /api/salas/<id>` - Editar sala
- `DELETE /api/salas/<id>` - Excluir sala

### Usuários
- `POST /api/usuarios` - Adicionar usuário
- `PUT /api/usuarios/<id>` - Editar usuário
- `DELETE /api/usuarios/<id>` - Excluir usuário

### Receptores
- `POST /api/receptores` - Adicionar receptor
- `PUT /api/receptores/<id>` - Editar receptor
- `DELETE /api/receptores/<id>` - Excluir receptor

## 🔒 Segurança

- Validação de dados no frontend e backend
- Sanitização de inputs
- Tratamento de erros robusto
- Conexões seguras com o banco de dados

## 📈 Monitoramento

- Status do servidor principal
- Conectividade com receptores
- Logs detalhados de todas as operações
- Estatísticas em tempo real

## 🚀 Execução

Para executar a dashboard:

```bash
cd dashboard
python app.py
```

A dashboard estará disponível em `http://localhost:8080`

## 📝 Notas

- A dashboard se conecta ao mesmo banco de dados do servidor principal
- Verifica automaticamente o status do servidor principal
- Testa conectividade com receptores em tempo real
- Exporta logs em formato CSV para análise externa 