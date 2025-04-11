/**
 * App - Controlador principal da aplicação
 * Gerencia a interface do usuário, manipulação de eventos e interação com serviços
 */

class App {
    constructor() {
        // Referências de elementos da interface
        this.elements = {
            // Telas
            loginScreen: document.getElementById('login-screen'),
            chatInterface: document.getElementById('chat-interface'),
            
            // Elementos de login
            matriculaInput: document.getElementById('matricula-input'),
            loginButton: document.getElementById('login-button'),
            loginError: document.getElementById('login-error'),
            
            // Elementos de chat
            messageContainer: document.getElementById('message-container'),
            messageInput: document.getElementById('message-input'),
            sendButton: document.getElementById('send-button'),
            
            // Elementos de informações do cliente
            userName: document.getElementById('user-name'),
            logoutButton: document.getElementById('logout-button'),
            clientName: document.querySelector('#client-name .info-value'),
            clientId: document.querySelector('#client-id .info-value'),
            clientAddress: document.querySelector('#client-address .info-value'),
            availablePeriod: document.querySelector('#available-period .info-value'),
            
            // Elementos de sugestões
            suggestionChips: document.querySelectorAll('.suggestion-chip'),
            
            // Elementos de modal
            helpModal: document.getElementById('help-modal'),
            helpLink: document.getElementById('help-link'),
            aboutLink: document.getElementById('about-link'),
            privacyLink: document.getElementById('privacy-link'),
            closeModalButtons: document.querySelectorAll('.close-button')
        };
        
        // Estado da aplicação
        this.state = {
            isLoggedIn: false,
            userName: '',
            matricula: '',
            isProcessing: false,
            clientInfo: null,
            messageHistory: []
        };
        
        // Flag para evitar múltiplos envios
        this.isSubmitting = false;
    }

    /**
     * Inicializa a aplicação
     */
    initialize() {
        // Inicializar serviço de gráficos
        chartsService.initialize();
        
        // Verificar se há uma sessão ativa
        this.checkSession();
        
        // Configurar event listeners
        this.setupEventListeners();
        
        // Verificar saúde da API
        this.checkApiHealth();
    }

    /**
     * Configura os event listeners para elementos da interface
     */
    setupEventListeners() {
        // Login
        this.elements.loginButton.addEventListener('click', () => this.handleLogin());
        this.elements.matriculaInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.handleLogin();
        });
        
        // Envio de mensagens
        this.elements.sendButton.addEventListener('click', () => this.handleSendMessage());
        this.elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') this.handleSendMessage();
        });
        
        // Logout
        this.elements.logoutButton.addEventListener('click', () => this.handleLogout());
        
        // Sugestões de mensagens
        this.elements.suggestionChips.forEach(chip => {
            chip.addEventListener('click', () => {
                const text = chip.getAttribute('data-text');
                if (text) {
                    this.elements.messageInput.value = text;
                    this.elements.messageInput.focus();
                }
            });
        });
        
        // Modais
        this.elements.helpLink.addEventListener('click', (e) => {
            e.preventDefault();
            this.showModal(this.elements.helpModal);
        });
        
        this.elements.closeModalButtons.forEach(button => {
            button.addEventListener('click', () => {
                const modal = button.closest('.modal');
                this.hideModal(modal);
            });
        });
        
        // Fechar modal ao clicar fora
        window.addEventListener('click', (e) => {
            if (e.target.classList.contains('modal')) {
                this.hideModal(e.target);
            }
        });
    }

    /**
     * Verifica se há uma sessão ativa com base no localStorage
     */
    checkSession() {
        const sessionId = localStorage.getItem('energySessionId');
        const userName = localStorage.getItem('energyUserName');
        const matricula = localStorage.getItem('energyMatricula');
        
        if (sessionId) {
            // Restaurar estado da sessão
            this.state.isLoggedIn = true;
            this.state.userName = userName || 'Cliente';
            this.state.matricula = matricula || '';
            
            // Atualizar interface
            this.updateUserInterface();
            
            // Tentativa de envio de uma mensagem vazia para validar sessão
            this.validateSession();
        }
    }

    /**
     * Valida se a sessão armazenada ainda é válida
     */
    async validateSession() {
        try {
            // Adicionar mensagem de carregamento
            this.addSystemMessage('Verificando sua sessão...');
            
            // Enviar mensagem vazia para validar sessão
            const response = await apiService.enviarMensagem('Olá');
            
            // Remover mensagem de verificação
            this.removeLastMessage();
            
            // Adicionar mensagem do sistema com boas-vindas
            this.addSystemMessage(`Bem-vindo de volta! Como posso ajudar hoje?`);
            
            // Atualizar informações do cliente se disponíveis
            if (response.dados_adicionais && response.dados_adicionais.nome_cliente) {
                this.state.userName = response.dados_adicionais.nome_cliente;
                localStorage.setItem('energyUserName', response.dados_adicionais.nome_cliente);
                this.updateUserName();
            }
            
            // Processar dados adicionais
            this.processAdditionalData(response.dados_adicionais);
        } catch (error) {
            console.error('Erro ao validar sessão:', error);
            
            // Remover mensagem de verificação
            this.removeLastMessage();
            
            // Sessão inválida, fazer logout
            this.handleLogout();
            
            // Exibir erro
            this.showLoginError('Sessão expirada. Por favor, faça login novamente.');
        }
    }

    /**
     * Verifica a saúde da API
     */
    async checkApiHealth() {
        try {
            const health = await apiService.verificarSaude();
            
            if (health.status !== 'OK') {
                console.warn('API não está disponível:', health);
                // Exibir alerta se não estiver logado ainda
                if (!this.state.isLoggedIn) {
                    this.showLoginError('O servidor não está disponível no momento. Tente novamente mais tarde.');
                }
            }
        } catch (error) {
            console.error('Erro ao verificar saúde da API:', error);
        }
    }

    /**
     * Manipula a submissão do formulário de login
     */
    async handleLogin() {
        // Ev