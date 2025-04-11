/**
 * API Service - Responsável pela comunicação com a API do backend
 * Implementa métodos para autenticação, envio de mensagens e manipulação de sessões
 */

class ApiService {
    constructor() {
        // URL base da API - Configurável para diferentes ambientes
        this.baseUrl = 'http://localhost:8000/api/v1';
        
        // Timeout para requisições (em milissegundos)
        this.timeout = 30000;
        
        // Armazenar ID da sessão atual
        this.sessionId = localStorage.getItem('energySessionId') || null;
        
        // Headers padrão para requisições
        this.headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
    }

    /**
     * Inicializa uma nova sessão com a matrícula do usuário
     * @param {string} matricula - Matrícula do cliente
     * @returns {Promise} - Promessa com dados da sessão ou erro
     */
    async iniciarSessao(matricula) {
        try {
            const response = await this._fetch('/consulta/iniciar_sessao', {
                method: 'POST',
                body: JSON.stringify({ matricula })
            });

            // Verificar se houve resposta
            if (!response) {
                throw new Error('Não foi possível conectar ao servidor');
            }

            // Verificar se o status é de sucesso
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Erro desconhecido');
            }

            // Extrair dados da sessão
            const dados = await response.json();
            
            // Armazenar ID da sessão para uso futuro
            this.sessionId = dados.sessao_id;
            localStorage.setItem('energySessionId', dados.sessao_id);
            
            return dados;
        } catch (error) {
            console.error('Erro ao iniciar sessão:', error);
            throw error;
        }
    }

    /**
     * Envia uma mensagem para o assistente na sessão atual
     * @param {string} mensagem - Texto da mensagem do usuário
     * @returns {Promise} - Promessa com a resposta do assistente ou erro
     */
    async enviarMensagem(mensagem) {
        // Verificar se há uma sessão ativa
        if (!this.sessionId) {
            throw new Error('Sessão não inicializada');
        }

        try {
            const response = await this._fetch('/consulta/enviar_mensagem', {
                method: 'POST',
                body: JSON.stringify({
                    sessao_id: this.sessionId,
                    mensagem
                })
            });

            // Verificar se houve resposta
            if (!response) {
                throw new Error('Não foi possível conectar ao servidor');
            }

            // Verificar se o status é de sucesso
            if (!response.ok) {
                // Se o erro for 404, provavelmente a sessão expirou
                if (response.status === 404) {
                    this.encerrarSessao();
                    throw new Error('Sessão expirada. Por favor, faça login novamente.');
                }
                
                const error = await response.json();
                throw new Error(error.message || 'Erro ao processar mensagem');
            }

            // Extrair dados da resposta
            return await response.json();
        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            throw error;
        }
    }

    /**
     * Verifica a saúde da API
     * @returns {Promise} - Promessa com status da API ou erro
     */
    async verificarSaude() {
        try {
            const response = await this._fetch('/health', { method: 'GET' });
            
            if (!response || !response.ok) {
                return { status: 'offline', timestamp: new Date().toISOString() };
            }
            
            return await response.json();
        } catch (error) {
            console.error('Erro ao verificar saúde da API:', error);
            return { status: 'offline', timestamp: new Date().toISOString() };
        }
    }

    /**
     * Encerra a sessão atual e limpa dados armazenados
     */
    encerrarSessao() {
        this.sessionId = null;
        localStorage.removeItem('energySessionId');
    }

    /**
     * Método utilitário para fazer requisições HTTP com tratamento de timeout
     * @param {string} endpoint - Endpoint da API
     * @param {Object} options - Opções para a requisição fetch
     * @returns {Promise} - Promessa com a resposta da requisição
     */
    async _fetch(endpoint, options = {}) {
        // Configurar URL completa
        const url = `${this.baseUrl}${endpoint}`;
        
        // Mesclar headers padrão com opções fornecidas
        const fetchOptions = {
            ...options,
            headers: {
                ...this.headers,
                ...(options.headers || {})
            }
        };
        
        // Implementar timeout
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Timeout da requisição')), this.timeout);
        });
        
        // Fazer a requisição com timeout
        return Promise.race([
            fetch(url, fetchOptions),
            timeoutPromise
        ]);
    }
}

// Criar e exportar instância única do serviço
const apiService = new ApiService();