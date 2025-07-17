/**
 * Universal Report Generator - Frontend JavaScript
 * Chatbot UI 스타일과 클로드 데스크톱의 코드 뷰 기능을 구현
 */

class ChatApplication {
    constructor() {
        this.currentSessionId = null;
        this.currentView = 'chat';
        this.isProcessing = false;
        this.messages = [];
        this.chatHistory = [];
        this.tools = [];
        this.reports = [];
        
        this.initializeElements();
        this.setupEventListeners();
        this.loadInitialData();
    }

    // DOM 요소 초기화
    initializeElements() {
        // 사이드바 요소
        this.sidebar = document.getElementById('sidebar');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.menuBtn = document.getElementById('menuBtn');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.chatList = document.getElementById('chatList');
        this.toolsList = document.getElementById('toolsList');
        this.reportsList = document.getElementById('reportsList');

        // 헤더 요소
        this.currentChatTitle = document.getElementById('currentChatTitle');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.chatViewBtn = document.getElementById('chatViewBtn');
        this.codeViewBtn = document.getElementById('codeViewBtn');
        this.splitViewBtn = document.getElementById('splitViewBtn');

        // 채팅 요소
        this.chatArea = document.getElementById('chatArea');
        this.chatMessages = document.getElementById('chatMessages');
        this.messageInput = document.getElementById('messageInput');
        this.sendBtn = document.getElementById('sendBtn');

        // 코드 뷰 요소
        this.codeArea = document.getElementById('codeArea');
        this.codeDisplay = document.getElementById('codeDisplay');
        this.copyCodeBtn = document.getElementById('copyCodeBtn');
        this.downloadCodeBtn = document.getElementById('downloadCodeBtn');
        this.previewCodeBtn = document.getElementById('previewCodeBtn');

        // 오버레이 및 모달
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.loadingText = document.getElementById('loadingText');
        this.previewModal = document.getElementById('previewModal');
        this.modalClose = document.getElementById('modalClose');
        this.previewFrame = document.getElementById('previewFrame');
    }

    // 이벤트 리스너 설정
    setupEventListeners() {
        // 사이드바 토글
        this.sidebarToggle?.addEventListener('click', () => this.toggleSidebar());
        this.menuBtn?.addEventListener('click', () => this.toggleSidebar());

        // 새 채팅
        this.newChatBtn?.addEventListener('click', () => this.startNewChat());

        // 뷰 모드 변경
        this.chatViewBtn?.addEventListener('click', () => this.setView('chat'));
        this.codeViewBtn?.addEventListener('click', () => this.setView('code'));
        this.splitViewBtn?.addEventListener('click', () => this.setView('split'));

        // 메시지 입력
        this.messageInput?.addEventListener('input', () => this.handleInputChange());
        this.messageInput?.addEventListener('keydown', (e) => this.handleKeyDown(e));
        this.sendBtn?.addEventListener('click', () => this.sendMessage());

        // 예시 프롬프트 클릭
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('example-prompt')) {
                const prompt = e.target.dataset.prompt;
                this.messageInput.value = prompt;
                this.handleInputChange();
                this.sendMessage();
            }
        });

        // 코드 액션
        this.copyCodeBtn?.addEventListener('click', () => this.copyCode());
        this.downloadCodeBtn?.addEventListener('click', () => this.downloadCode());
        this.previewCodeBtn?.addEventListener('click', () => this.previewCode());

        // 모달 제어
        this.modalClose?.addEventListener('click', () => this.closeModal());
        this.previewModal?.addEventListener('click', (e) => {
            if (e.target === this.previewModal) this.closeModal();
        });

        // 키보드 단축키
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') this.closeModal();
            if (e.ctrlKey || e.metaKey) {
                if (e.key === 'n') {
                    e.preventDefault();
                    this.startNewChat();
                }
                if (e.key === '1') {
                    e.preventDefault();
                    this.setView('chat');
                }
                if (e.key === '2') {
                    e.preventDefault();
                    this.setView('code');
                }
                if (e.key === '3') {
                    e.preventDefault();
                    this.setView('split');
                }
            }
        });

        // 윈도우 크기 변경
        window.addEventListener('resize', () => this.handleResize());
    }

    // 초기 데이터 로드
    async loadInitialData() {
        try {
            await Promise.all([
                this.loadTools(),
                this.loadReports(),
                this.loadChatHistory(),
                this.loadDynamicPrompts()
            ]);
            this.updateStatus('ready', '준비');
        } catch (error) {
            console.error('초기 데이터 로드 실패:', error);
            this.updateStatus('error', '연결 오류');
        }
    }
    
    // 동적 프롬프트 로드
    async loadDynamicPrompts() {
        try {
            const response = await fetch('/api/prompts');
            const data = await response.json();
            
            if (data.prompts && data.prompts.length) {
                this.updateExamplePrompts(data.prompts);
            }
        } catch (error) {
            console.error('동적 프롬프트 로드 실패:', error);
            // 오류가 있어도 기본 프롬프트를 사용하므로 계속 진행
        }
    }
    
    // 예시 프롬프트 업데이트
    updateExamplePrompts(prompts) {
        const examplePromptsContainer = document.querySelector('.example-prompts');
        if (examplePromptsContainer && prompts.length >= 3) {
            // 첫 3개 프롬프트로 업데이트
            const promptElements = examplePromptsContainer.querySelectorAll('.example-prompt');
            
            prompts.slice(0, Math.min(3, promptElements.length)).forEach((prompt, index) => {
                if (promptElements[index]) {
                    promptElements[index].setAttribute('data-prompt', prompt);
                    // 짧은 제목으로 변환
                    const shortTitle = this.createShortTitle(prompt);
                    promptElements[index].textContent = shortTitle;
                }
            });
        }
    }
    
    // 긴 프롬프트를 짧은 제목으로 변환
    createShortTitle(prompt) {
        if (prompt.includes('아파트') || prompt.includes('부동산')) {
            return '🏠 부동산 분석';
        } else if (prompt.includes('매출') || prompt.includes('매출')) {
            return '📈 매출 분석';
        } else if (prompt.includes('고객') || prompt.includes('만족도')) {
            return '📊 고객 분석';
        } else if (prompt.includes('차트') || prompt.includes('시각화')) {
            return '📊 데이터 시각화';
        } else {
            // 첫 몇 단어만 사용
            const words = prompt.split(' ');
            if (words.length > 3) {
                return words.slice(0, 3).join(' ') + '...';
            }
            return prompt;
        }
    }

    // 도구 목록 로드
    async loadTools() {
        try {
            const response = await fetch('/tools');
            const data = await response.json();
            
            if (data.success) {
                this.tools = data.tools;
                this.renderTools();
            }
        } catch (error) {
            console.error('도구 로드 실패:', error);
            this.toolsList.innerHTML = '<div class="loading">도구 로드 실패</div>';
        }
    }

    // 리포트 목록 로드
    async loadReports() {
        try {
            const response = await fetch('/reports');
            const data = await response.json();
            
            this.reports = data.reports || [];
            this.renderReports();
        } catch (error) {
            console.error('리포트 로드 실패:', error);
            this.reportsList.innerHTML = '<div class="loading">리포트 로드 실패</div>';
        }
    }

    // 채팅 히스토리 로드 (로컬 스토리지에서)
    loadChatHistory() {
        try {
            const history = localStorage.getItem('chatHistory');
            this.chatHistory = history ? JSON.parse(history) : [];
            this.renderChatHistory();
        } catch (error) {
            console.error('채팅 히스토리 로드 실패:', error);
            this.chatHistory = [];
        }
    }

    // 도구 목록 렌더링
    renderTools() {
        if (!this.tools.length) {
            this.toolsList.innerHTML = '<div class="loading">도구가 없습니다</div>';
            return;
        }

        const grouped = this.tools.reduce((acc, tool) => {
            const server = tool.server || 'builtin';
            if (!acc[server]) acc[server] = [];
            acc[server].push(tool);
            return acc;
        }, {});

        this.toolsList.innerHTML = Object.entries(grouped)
            .map(([server, tools]) => `
                <div class="tool-group">
                    <div class="tool-server">${server}</div>
                    ${tools.map(tool => `
                        <div class="tool-item">
                            <div class="tool-name">${tool.name}</div>
                            <div class="tool-server">${tool.server}</div>
                        </div>
                    `).join('')}
                </div>
            `).join('');
    }

    // 리포트 목록 렌더링
    renderReports() {
        if (!this.reports.length) {
            this.reportsList.innerHTML = '<div class="loading">리포트가 없습니다</div>';
            return;
        }

        this.reportsList.innerHTML = this.reports
            .slice(0, 10) // 최근 10개만 표시
            .map(report => `
                <div class="report-item" onclick="window.open('/reports/${report.filename}', '_blank')">
                    <div class="report-name">${report.filename}</div>
                    <div class="report-date">${this.formatDate(report.created_at)}</div>
                </div>
            `).join('');
    }

    // 채팅 히스토리 렌더링
    renderChatHistory() {
        if (!this.chatHistory.length) {
            this.chatList.innerHTML = '<div class="loading">채팅 기록이 없습니다</div>';
            return;
        }

        this.chatList.innerHTML = this.chatHistory
            .slice(0, 20) // 최근 20개만 표시
            .map(chat => `
                <div class="chat-item" data-id="${chat.id}" onclick="app.loadChat('${chat.id}')">
                    <div class="chat-title">${chat.title}</div>
                    <div class="chat-time">${this.formatDate(chat.timestamp)}</div>
                </div>
            `).join('');
    }

    // 사이드바 토글
    toggleSidebar() {
        this.sidebar.classList.toggle('collapsed');
    }

    // 새 채팅 시작
    startNewChat() {
        this.currentSessionId = this.generateId();
        this.messages = [];
        this.currentChatTitle.textContent = '새로운 분석';
        this.renderMessages();
        this.clearCode();
        this.messageInput.focus();
    }

    // 뷰 모드 설정
    setView(view) {
        this.currentView = view;
        
        // 버튼 활성화 상태 업데이트
        document.querySelectorAll('.view-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        document.querySelector(`[data-view="${view}"]`).classList.add('active');

        // 영역 표시/숨김
        switch (view) {
            case 'chat':
                this.chatArea.classList.remove('split', 'hidden');
                this.codeArea.classList.add('hidden');
                this.codeArea.classList.remove('full');
                break;
            case 'code':
                this.chatArea.classList.add('hidden');
                this.codeArea.classList.remove('hidden');
                this.codeArea.classList.add('full');
                break;
            case 'split':
                this.chatArea.classList.add('split');
                this.chatArea.classList.remove('hidden');
                this.codeArea.classList.remove('hidden', 'full');
                break;
        }
    }

    // 입력 변경 처리
    handleInputChange() {
        const hasText = this.messageInput.value.trim().length > 0;
        this.sendBtn.disabled = !hasText || this.isProcessing;
        
        // 자동 높이 조정
        this.messageInput.style.height = 'auto';
        this.messageInput.style.height = Math.min(this.messageInput.scrollHeight, 200) + 'px';
    }

    // 키보드 입력 처리
    handleKeyDown(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            if (!this.sendBtn.disabled) {
                this.sendMessage();
            }
        }
    }

    // 메시지 전송
    async sendMessage() {
        const message = this.messageInput.value.trim();
        if (!message || this.isProcessing) return;

        // 사용자 메시지 추가
        this.addMessage('user', message);
        this.messageInput.value = '';
        this.handleInputChange();

        // 처리 상태 설정
        this.setProcessing(true);
        this.showTypingIndicator();

        try {
            // 스트리밍 연결 설정
            const response = await fetch('/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_query: message,
                    session_id: this.currentSessionId,
                    format: this.getSelectedFormat()
                })
            });

            if (!response.body) {
                throw new Error('스트리밍 응답을 받을 수 없습니다');
            }

            this.hideTypingIndicator();
            await this.handleStreamingResponse(response.body);
            
        } catch (error) {
            console.error('메시지 전송 실패:', error);
            this.hideTypingIndicator();
            this.addMessage('assistant', '죄송합니다. 오류가 발생했습니다: ' + error.message);
        } finally {
            this.setProcessing(false);
        }
    }

    // 스트리밍 응답 처리
    async handleStreamingResponse(stream) {
        const reader = stream.getReader();
        const decoder = new TextDecoder();
        
        let assistantMessage = null;
        let currentContent = '';
        let htmlCode = '';
        let toolActivities = new Map(); // 도구 활동 추적

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            
                            switch (data.type) {
                                case 'status':
                                    this.updateStatus('processing', data.message);
                                    this.addSystemMessage(data.message);
                                    break;
                                    
                                case 'tool_start':
                                    this.addToolActivity(data.tool_name, data.server_name, 'running');
                                    toolActivities.set(data.tool_name, data);
                                    break;
                                    
                                case 'tool_complete':
                                    this.updateToolActivity(data.tool_name, 'completed', data.result);
                                    break;
                                    
                                case 'tool_error':
                                    this.updateToolActivity(data.tool_name, 'error', data.error);
                                    break;
                                    
                                case 'llm_start':
                                    this.addSystemMessage(`🧠 ${data.model || 'Claude'}가 응답을 생성하고 있습니다...`);
                                    if (!assistantMessage) {
                                        assistantMessage = this.addMessage('assistant', '');
                                    }
                                    break;
                                    
                                case 'content':
                                    if (!assistantMessage) {
                                        assistantMessage = this.addMessage('assistant', '');
                                    }
                                    currentContent += data.content;
                                    this.updateMessageContent(assistantMessage, currentContent);
                                    break;
                                    
                                case 'analysis_step':
                                    this.addSystemMessage(`📊 ${data.message}`);
                                    break;
                                    
                                case 'code':
                                    htmlCode = data.code;
                                    this.updateCode(htmlCode);
                                    break;
                                    
                                case 'progress':
                                    this.updateProgress(data.value);
                                    break;
                                    
                                case 'complete':
                                    this.updateStatus('ready', '완료');
                                    if (data.report_url) {
                                        this.addReportLink(assistantMessage, data.report_url);
                                    }
                                    this.addSystemMessage('✅ 분석이 성공적으로 완료되었습니다!');
                                    break;
                                    
                                case 'error':
                                    this.updateStatus('error', '오류 발생');
                                    if (!assistantMessage) {
                                        assistantMessage = this.addMessage('assistant', `오류: ${data.message}`);
                                    }
                                    break;
                            }
                        } catch (e) {
                            console.warn('JSON 파싱 실패:', line);
                        }
                    }
                }
            }
        } finally {
            reader.releaseLock();
        }

        // 채팅 히스토리 저장
        this.saveChatToHistory();
    }

    // 메시지 추가
    addMessage(role, content) {
        const message = {
            id: this.generateId(),
            role,
            content,
            timestamp: new Date()
        };

        this.messages.push(message);
        return this.renderMessage(message);
    }

    // 메시지 렌더링
    renderMessage(message) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${message.role}`;
        messageDiv.dataset.id = message.id;

        const avatar = message.role === 'user' ? 'U' : 'AI';
        
        messageDiv.innerHTML = `
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${this.formatMessageContent(message.content)}</div>
                <div class="message-time">${this.formatTime(message.timestamp)}</div>
            </div>
        `;

        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
        
        return messageDiv;
    }

    // 모든 메시지 렌더링
    renderMessages() {
        this.chatMessages.innerHTML = '';
        
        if (this.messages.length === 0) {
            // 환영 메시지 표시
            this.showWelcomeMessage();
        } else {
            this.messages.forEach(message => this.renderMessage(message));
        }
    }

    // 환영 메시지 표시
    showWelcomeMessage() {
        this.chatMessages.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/>
                    </svg>
                </div>
                <h2>Universal Report Generator에 오신 것을 환영합니다!</h2>
                <p>데이터 분석이나 리포트 생성에 대해 무엇이든 물어보세요.</p>
                <div class="example-prompts">
                    <div class="example-prompt" data-prompt="강동구 아파트 매매분석 리포트를 작성해주세요">
                        📊 부동산 분석 리포트
                    </div>
                    <div class="example-prompt" data-prompt="최근 3개월 매출 데이터를 시각화해주세요">
                        📈 매출 데이터 시각화
                    </div>
                    <div class="example-prompt" data-prompt="고객 만족도 설문조사 결과를 분석해주세요">
                        📋 설문조사 분석
                    </div>
                </div>
            </div>
        `;
    }

    // 메시지 내용 업데이트
    updateMessageContent(messageElement, content) {
        const textElement = messageElement.querySelector('.message-text');
        if (textElement) {
            textElement.innerHTML = this.formatMessageContent(content);
            this.scrollToBottom();
        }
    }

    // 메시지 내용 포맷팅
    formatMessageContent(content) {
        // 마크다운 스타일 포맷팅
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    // 타이핑 표시기 표시
    showTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator';
        indicator.id = 'typing-indicator';
        indicator.innerHTML = `
            <div class="message-avatar">AI</div>
            <div class="message-content">
                <div class="typing-dots">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>
        `;
        
        this.chatMessages.appendChild(indicator);
        this.scrollToBottom();
    }

    // 타이핑 표시기 숨김
    hideTypingIndicator() {
        const indicator = document.getElementById('typing-indicator');
        if (indicator) {
            indicator.remove();
        }
    }

    // 코드 업데이트 (클로드 데스크톱 스타일)
    updateCode(code) {
        this.codeDisplay.textContent = code;
        
        // Prism.js 구문 강조 적용
        if (window.Prism) {
            Prism.highlightElement(this.codeDisplay);
        }

        // 코드가 있으면 분할 뷰로 자동 전환
        if (code && this.currentView === 'chat') {
            this.setView('split');
        }
    }

    // 코드 지우기
    clearCode() {
        this.codeDisplay.textContent = '<!-- 생성된 HTML 코드가 여기에 표시됩니다 -->';
    }

    // 코드 복사
    async copyCode() {
        try {
            await navigator.clipboard.writeText(this.codeDisplay.textContent);
            this.showToast('코드가 클립보드에 복사되었습니다');
        } catch (error) {
            console.error('복사 실패:', error);
            this.showToast('복사에 실패했습니다');
        }
    }

    // 코드 다운로드
    downloadCode() {
        const content = this.codeDisplay.textContent;
        const blob = new Blob([content], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `report_${Date.now()}.html`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        this.showToast('HTML 파일이 다운로드되었습니다');
    }

    // 코드 미리보기
    previewCode() {
        const content = this.codeDisplay.textContent;
        if (!content || content.includes('<!-- 생성된 HTML 코드가 여기에 표시됩니다 -->')) {
            this.showToast('미리볼 코드가 없습니다');
            return;
        }

        this.previewFrame.srcdoc = content;
        this.previewModal.classList.add('show');
    }

    // 모달 닫기
    closeModal() {
        this.previewModal.classList.remove('show');
    }

    // 리포트 링크 추가
    addReportLink(messageElement, reportUrl) {
        const textElement = messageElement.querySelector('.message-text');
        if (textElement) {
            textElement.innerHTML += `<br><br><a href="${reportUrl}" target="_blank" class="report-link">📊 생성된 리포트 보기</a>`;
        }
    }

    // 처리 상태 설정
    setProcessing(processing) {
        this.isProcessing = processing;
        this.sendBtn.disabled = processing || !this.messageInput.value.trim();
        this.messageInput.disabled = processing;
        
        if (processing) {
            this.updateStatus('processing', '처리 중...');
        }
    }

    // 상태 업데이트
    updateStatus(status, message) {
        const dot = this.statusIndicator.querySelector('.status-dot');
        const text = this.statusIndicator.querySelector('span');
        
        dot.className = `status-dot ${status}`;
        text.textContent = message;
    }

    // 로딩 오버레이 표시
    showLoading(text = '처리 중...') {
        this.loadingText.textContent = text;
        this.loadingOverlay.classList.add('show');
    }

    // 로딩 오버레이 숨김
    hideLoading() {
        this.loadingOverlay.classList.remove('show');
    }

    // 토스트 메시지 표시
    showToast(message) {
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: var(--bg-tertiary);
            color: var(--text-primary);
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 1200;
            animation: slideInUp 0.3s ease;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.style.animation = 'slideOutDown 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    // 채팅 히스토리에 저장
    saveChatToHistory() {
        if (!this.messages.length) return;

        const chatData = {
            id: this.currentSessionId,
            title: this.generateChatTitle(),
            timestamp: new Date(),
            messages: this.messages
        };

        // 기존 채팅 업데이트 또는 새 채팅 추가
        const existingIndex = this.chatHistory.findIndex(chat => chat.id === this.currentSessionId);
        if (existingIndex >= 0) {
            this.chatHistory[existingIndex] = chatData;
        } else {
            this.chatHistory.unshift(chatData);
        }

        // 최대 100개까지만 저장
        if (this.chatHistory.length > 100) {
            this.chatHistory = this.chatHistory.slice(0, 100);
        }

        localStorage.setItem('chatHistory', JSON.stringify(this.chatHistory));
        this.renderChatHistory();
    }

    // 채팅 제목 생성
    generateChatTitle() {
        const firstMessage = this.messages.find(m => m.role === 'user');
        if (firstMessage) {
            return firstMessage.content.length > 30 
                ? firstMessage.content.substring(0, 30) + '...'
                : firstMessage.content;
        }
        return '새로운 채팅';
    }

    // 채팅 로드
    loadChat(chatId) {
        const chat = this.chatHistory.find(c => c.id === chatId);
        if (!chat) return;

        this.currentSessionId = chatId;
        this.messages = chat.messages || [];
        this.currentChatTitle.textContent = chat.title;
        this.renderMessages();
        
        // 채팅 목록에서 활성화 표시
        document.querySelectorAll('.chat-item').forEach(item => {
            item.classList.remove('active');
        });
        document.querySelector(`[data-id="${chatId}"]`)?.classList.add('active');
    }

    // 선택된 포맷 가져오기
    getSelectedFormat() {
        const selected = document.querySelector('input[name="format"]:checked');
        return selected ? selected.value : 'html';
    }

    // 하단으로 스크롤
    scrollToBottom() {
        setTimeout(() => {
            this.chatMessages.scrollTop = this.chatMessages.scrollHeight;
        }, 100);
    }

    // 날짜 포맷팅
    formatDate(date) {
        const d = new Date(date);
        const now = new Date();
        const diff = now - d;
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (days === 0) {
            return this.formatTime(d);
        } else if (days === 1) {
            return '어제';
        } else if (days < 7) {
            return `${days}일 전`;
        } else {
            return d.toLocaleDateString('ko-KR');
        }
    }

    // 시간 포맷팅
    formatTime(date) {
        return new Date(date).toLocaleTimeString('ko-KR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
    }

    // 윈도우 크기 변경 처리
    handleResize() {
        // 모바일에서 사이드바 처리
        if (window.innerWidth <= 768) {
            this.sidebar.classList.remove('show');
        }
    }

    // 고유 ID 생성
    generateId() {
        return Date.now().toString(36) + Math.random().toString(36).substr(2);
    }

    // 시스템 메시지 추가
    addSystemMessage(content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'system-message';
        messageDiv.innerHTML = `
            <div class="system-content">
                <div class="system-icon">🤖</div>
                <div class="system-text">${content}</div>
                <div class="system-time">${this.formatTime(new Date())}</div>
            </div>
        `;
        
        this.chatMessages.appendChild(messageDiv);
        this.scrollToBottom();
    }

    // 도구 활동 추가
    addToolActivity(toolName, serverName, status) {
        const activityDiv = document.createElement('div');
        activityDiv.className = 'tool-activity';
        activityDiv.dataset.toolName = toolName;
        activityDiv.innerHTML = `
            <div class="tool-activity-content">
                <div class="tool-icon ${status}">
                    ${status === 'running' ? '⚙️' : status === 'completed' ? '✅' : '❌'}
                </div>
                <div class="tool-details">
                    <div class="tool-name">${toolName}</div>
                    <div class="tool-server">${serverName}</div>
                    <div class="tool-status">${this.getStatusText(status)}</div>
                </div>
                <div class="tool-spinner ${status === 'running' ? 'active' : ''}"></div>
            </div>
        `;
        
        this.chatMessages.appendChild(activityDiv);
        this.scrollToBottom();
    }

    // 도구 활동 업데이트
    updateToolActivity(toolName, status, result = '') {
        const activityElement = document.querySelector(`[data-tool-name="${toolName}"]`);
        if (!activityElement) return;

        const iconElement = activityElement.querySelector('.tool-icon');
        const statusElement = activityElement.querySelector('.tool-status');
        const spinnerElement = activityElement.querySelector('.tool-spinner');

        iconElement.className = `tool-icon ${status}`;
        iconElement.textContent = status === 'completed' ? '✅' : '❌';
        statusElement.textContent = this.getStatusText(status);
        spinnerElement.classList.remove('active');

        // 결과가 있으면 표시
        if (result) {
            const resultDiv = document.createElement('div');
            resultDiv.className = 'tool-result';
            resultDiv.textContent = result;
            activityElement.querySelector('.tool-activity-content').appendChild(resultDiv);
        }
    }

    // 상태 텍스트 반환
    getStatusText(status) {
        switch (status) {
            case 'running': return '실행 중...';
            case 'completed': return '완료';
            case 'error': return '오류';
            default: return status;
        }
    }

    // 진행률 업데이트
    updateProgress(value) {
        // 프로그레스 바 업데이트
        const progressElement = document.getElementById('progressBar');
        if (progressElement) {
            progressElement.style.width = `${value}%`;
            
            // 100%가 되면 잠시 후 숨김
            if (value >= 100) {
                setTimeout(() => {
                    progressElement.style.width = '0%';
                }, 1000);
            }
        }
        
        // 상태 표시기에 진행률 표시
        if (value < 100) {
            this.updateStatus('processing', `처리 중... (${value}%)`);
        }
    }
}

// 앱 초기화
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new ChatApplication();
});

// 전역 함수 (HTML에서 사용)
window.app = app; 