document.addEventListener('DOMContentLoaded', function() {
    console.log('页面加载完成');

    // 导航功能
    const navLinks = document.querySelectorAll('.nav-links a');
    const sections = document.querySelectorAll('.section');

    function switchSection(sectionId) {
        console.log('切换到区域:', sectionId);
        // 隐藏所有section
        sections.forEach(section => {
            section.classList.remove('active');
        });
        
        // 显示目标section
        const targetSection = document.querySelector(sectionId);
        if (targetSection) {
            targetSection.classList.add('active');
            // 如果切换到相册页面，重新初始化轮播图
            if (sectionId === '#gallery') {
                initCarousel();
            }
        }

        // 更新导航栏激活状态
        navLinks.forEach(link => {
            link.classList.remove('active');
            if (link.getAttribute('href') === sectionId) {
                link.classList.add('active');
            }
        });
    }

    // 监听导航点击
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const sectionId = this.getAttribute('href');
            switchSection(sectionId);
            // 更新URL，但不刷新页面
            history.pushState(null, '', sectionId);
        });
    });

    // 处理浏览器前进后退
    window.addEventListener('popstate', function() {
        const sectionId = window.location.hash || '#home';
        switchSection(sectionId);
    });

    // 轮播图功能
    function initCarousel() {
        const carousel = document.querySelector('.carousel');
        if (!carousel) return; // 如果没有找到轮播容器，直接返回

        const images = carousel.querySelectorAll('.carousel-inner img');
        const prevBtn = carousel.querySelector('.carousel-prev');
        const nextBtn = carousel.querySelector('.carousel-next');
        let currentIndex = 0;
        
        // 清除可能存在的旧定时器
        if (window.carouselInterval) {
            clearInterval(window.carouselInterval);
        }

        function showImage(index) {
            console.log('切换到图片:', index);
            images.forEach(img => img.classList.remove('active'));
            images[index].classList.add('active');
        }

        function nextImage() {
            currentIndex = (currentIndex + 1) % images.length;
            showImage(currentIndex);
        }

        function prevImage() {
            currentIndex = (currentIndex - 1 + images.length) % images.length;
            showImage(currentIndex);
        }

        // 设置自动轮播
        window.carouselInterval = setInterval(nextImage, 5000);

        // 鼠标悬停时暂停轮播
        carousel.addEventListener('mouseenter', () => {
            clearInterval(window.carouselInterval);
        });

        // 鼠标离开时恢复轮播
        carousel.addEventListener('mouseleave', () => {
            window.carouselInterval = setInterval(nextImage, 5000);
        });

        // 按钮点击事件
        prevBtn.addEventListener('click', (e) => {
            e.preventDefault();
            prevImage();
        });

        nextBtn.addEventListener('click', (e) => {
            e.preventDefault();
            nextImage();
        });

        // 初始显示第一张图片
        showImage(0);

        // 调试信息
        console.log('轮播图初始化完成，图片数量:', images.length);
        images.forEach((img, index) => {
            console.log(`图片 ${index + 1} 路径:`, img.src);
        });
    }

    // 初始化显示当前URL对应的section
    const initialSection = window.location.hash || '#home';
    switchSection(initialSection);

    // 聊天功能
    const chatMessages = document.getElementById('chatMessages');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendMessage');

    // 自动调整输入框高度
    messageInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // 修改聊天功能相关的代码
    async function handleSend() {
        const message = messageInput.value.trim();
        if (message) {
            // 显示用户消息
            addMessage(message, true);
            
            // 清空输入框
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // 显示加载状态
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'message assistant';
            loadingDiv.innerHTML = '<div class="message-content">正在思考...</div>';
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            try {
                // 通过 Flask 服务器调用
                const response = await fetch(`${API_BASE_URL}/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ message: message })
                });
                
                const data = await response.json();
                
                // 移除加载状态
                chatMessages.removeChild(loadingDiv);
                
                if (data.success) {
                    // 显示 AI 回复
                    addMessage(data.response, false);
                } else {
                    addMessage('抱歉，我遇到了一些问题：' + data.error, false);
                }
            } catch (error) {
                console.error('Error:', error);
                // 移除加载状态
                chatMessages.removeChild(loadingDiv);
                addMessage('抱歉，发生了错误。', false);
            }
        }
    }

    sendButton.addEventListener('click', handleSend);

    messageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });

    // 在 DOMContentLoaded 事件处理函数中添加
    const audioButton = document.getElementById('playAudio');
    const audio = document.getElementById('myAudio');

    if (audioButton && audio) {
        audioButton.addEventListener('click', function() {
            if (audio.paused) {
                audio.play();
                this.querySelector('.button-text').textContent = '暂停';
            } else {
                audio.pause();
                audio.currentTime = 0;
                this.querySelector('.button-text').textContent = '播放音频';
            }
        });

        // 音频播放结束时重置按钮文本
        audio.addEventListener('ended', function() {
            audioButton.querySelector('.button-text').textContent = '播放音频';
        });
    }

    // 在 script.js 中添加 addMessage 函数
    function addMessage(content, isUser = true) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        messageDiv.innerHTML = `
            <div class="message-content">${content}</div>
        `;
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // 添加在适当的位置
    function logToConsole(message, type = 'info') {
        const timestamp = new Date().toISOString();
        const logMessage = `[${timestamp}] ${message}`;
        
        switch(type) {
            case 'error':
                console.error(logMessage);
                break;
            case 'warn':
                console.warn(logMessage);
                break;
            default:
                console.log(logMessage);
        }
    }

    // 在发送聊天请求时
    async function sendMessage() {
        logToConsole('Preparing to send message');
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: userInput })
            });
            
            logToConsole(`Response status: ${response.status}`);
            const data = await response.json();
            
            if (data.request_id) {
                logToConsole(`Request ID: ${data.request_id}`);
            }
            if (data.process_time) {
                logToConsole(`Processing time: ${data.process_time}`);
            }
            
            if (data.success) {
                logToConsole('Message sent and received successfully');
            } else {
                logToConsole(`Error: ${data.error}`, 'error');
            }
            
        } catch (error) {
            logToConsole(`Failed to send message: ${error}`, 'error');
        }
    }
}); 