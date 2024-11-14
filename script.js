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
            // 如果切换到 ComfyUI 页面，刷新 iframe
            if (sectionId === '#comfyui') {
                const iframe = document.getElementById('comfyuiFrame');
                iframe.src = iframe.src;
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
            loadingDiv.innerHTML = '<div class="message-content loading">正在思考</div>';
            chatMessages.appendChild(loadingDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;

            try {
                console.log('Sending request to:', `${API_BASE_URL}/chat`);  // 添加调试日志
                const response = await fetch(`${API_BASE_URL}/chat`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ message: message })
                });
                
                console.log('Chat response status:', response.status);
                const data = await response.json();
                console.log('Chat response data:', data);
                
                // 移除加载状态
                chatMessages.removeChild(loadingDiv);
                
                if (data.success) {
                    addMessage(data.response, false);
                } else {
                    addMessage('错误: ' + (data.error || '未知错误'), false);
                }
            } catch (error) {
                console.error('Chat error:', error);
                // 移除加载状态
                chatMessages.removeChild(loadingDiv);
                addMessage('发送消息时出错，请重试', false);
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

    // 前端日志
    console.log("This will show in browser console only")

    // 在 DOMContentLoaded 事件监听器中添加
    function initAIGallery() {
        console.log('Current API_BASE_URL:', API_BASE_URL);
        const imageUpload = document.getElementById('imageUpload');
        const uploadButton = document.getElementById('uploadButton');
        const imageGrid = document.querySelector('.ai-image-grid');
        const refreshButton = document.getElementById('refreshButton');
        const cleanupButton = document.getElementById('cleanupButton');

        // 加载已有图片
        async function loadExistingImages() {
            try {
                const response = await fetch(`${API_BASE_URL}/get-images`);
                const data = await response.json();
                
                if (data.success) {
                    imageGrid.innerHTML = ''; // 清空现有内容
                    data.images.forEach(imageData => {
                        addImageToGrid(imageData);
                    });
                } else {
                    console.error('Failed to load images:', data.error);
                }
            } catch (error) {
                console.error('Error loading images:', error);
            }
        }

        // 添加图片到网格
        function addImageToGrid(imageData) {
            const imageContainer = document.createElement('div');
            imageContainer.className = 'image-container';
            
            const img = document.createElement('img');
            img.src = imageData.path;
            img.alt = imageData.original_filename || imageData.filename;
            
            // 添加错误处理
            img.onerror = function() {
                console.error('Failed to load image:', imageData.path);
                this.src = 'static/images/error-image.png';  // 可以添加一个默认的错误图片
            };
            
            // 添加图片信息
            const infoDiv = document.createElement('div');
            infoDiv.className = 'image-info';
            infoDiv.innerHTML = `
                <div class="image-title">${imageData.original_filename || '未命名图片'}</div>
                <div class="image-meta">
                    <span>上传时间: ${new Date(imageData.upload_date).toLocaleString()}</span>
                    <span>大小: ${(imageData.file_size / 1024).toFixed(2)} KB</span>
                </div>
            `;
            
            // 添加点击事件
            img.addEventListener('click', () => {
                openModal(imageData.path, imageData.original_filename || imageData.filename);
            });
            
            imageContainer.appendChild(img);
            imageContainer.appendChild(infoDiv);
            imageGrid.appendChild(imageContainer);
        }

        // 上传片
        uploadButton.addEventListener('click', async () => {
            const files = imageUpload.files;
            if (files.length === 0) {
                alert('请先选择图片');
                return;
            }

            for (const file of files) {
                const formData = new FormData();
                formData.append('image', file);

                try {
                    const response = await fetch(`${API_BASE_URL}/upload-image`, {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();
                    
                    if (data.success) {
                        addImageToGrid(data);
                    } else {
                        alert('上传失败: ' + data.error);
                    }
                } catch (error) {
                    console.error('Upload error:', error);
                    alert('上传出错，请重试');
                }
            }

            // 清空文件选择
            imageUpload.value = '';
        });

        // 初始加载图片
        loadExistingImages();

        // 添加模态框相关功能
        const modal = document.getElementById('imageModal');
        const modalImg = document.getElementById('modalImage');
        const modalCaption = document.getElementById('modalCaption');
        const closeBtn = document.querySelector('.modal-close');

        function openModal(src, alt) {
            modal.style.display = "block";
            modalImg.src = src;
            modalCaption.textContent = alt;
        }

        // 关闭按钮事件
        closeBtn.addEventListener('click', () => {
            modal.style.display = "none";
        });

        // 点击模态框外部关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.style.display = "none";
            }
        });

        // ESC键关闭模态框
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.style.display === "block") {
                modal.style.display = "none";
            }
        });

        // 添加刷新功能
        async function refreshImages() {
            try {
                refreshButton.classList.add('loading');
                refreshButton.textContent = '刷新中...';
                
                const response = await fetch(`${API_BASE_URL}/refresh-images`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // 重新加载图片
                    await loadExistingImages();
                    alert('图片刷新成功！');
                } else {
                    alert('刷新失败: ' + data.error);
                }
            } catch (error) {
                console.error('Refresh error:', error);
                alert('刷新出错，请重试');
            } finally {
                refreshButton.classList.remove('loading');
                refreshButton.textContent = '刷新图片';
            }
        }

        // 添加刷新按钮事件监听
        refreshButton.addEventListener('click', refreshImages);

        // 添加清理功能
        async function cleanupImages() {
            try {
                cleanupButton.classList.add('loading');
                cleanupButton.textContent = '清理中...';
                
                const response = await fetch(`${API_BASE_URL}/cleanup-images`, {
                    method: 'POST'
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // 重新加载图片
                    await loadExistingImages();
                    alert(data.message);
                } else {
                    alert('清理失败: ' + data.error);
                }
            } catch (error) {
                console.error('Cleanup error:', error);
                alert('清理出错，请重试');
            } finally {
                cleanupButton.classList.remove('loading');
                cleanupButton.textContent = '清理无效图片';
            }
        }

        // 添加清理按钮事件监听
        cleanupButton.addEventListener('click', cleanupImages);
    }

    // 在现有的 DOMContentLoaded 事件监听器中调用
    initAIGallery();
}); 