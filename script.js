document.addEventListener('DOMContentLoaded', () => {
    const chatWindow = document.getElementById('chat-window');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const quickActionsContainer = document.getElementById('quick-actions-container');
    const loadingBar = document.getElementById('loading-bar');

    // --- API BASE URL CONFIGURATION ---
    // Automatically detects if running locally or in production
    const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
        ? 'http://127.0.0.1:5000' 
        : window.location.origin;

    console.log('🌐 API Base URL:', API_BASE_URL);

    let botState = 'LOADING';
    let chapterSections = [];
    let currentSectionIndex = 0;
    let firstChapterTitle = null;
    let firstChapterContent = null;
    let currentChapterContent = "";
    let tableOfContents = "";
    let allChapters = [];
    let currentChapterTitle = "";
    let completedChapters = [];
    let currentView = 'toc';
    let hasStartedAnyChapter = false; // Track if user has started any chapter
    
    // Separate chat storage for each chapter/section
    let chatHistory = {
        'toc': [],
    };

    const QUICK_ACTIONS = {
        START: ['Yes, start the course', 'How long will it take to complete this chapter?'],
        IN_PROGRESS: ['Move to next section'],
        END_OF_CHAPTER: ['Move to next Chapter', 'Restart the course']
    };

    // --- Loading Screen Functions ---
    function showFullScreenLoader() {
        const loader = document.getElementById('full-screen-loader');
        if (loader) {
            loader.style.display = 'flex';
            loader.style.opacity = '1';
        }
    }

    function hideFullScreenLoader() {
        const loader = document.getElementById('full-screen-loader');
        if (loader) {
            loader.style.opacity = '0';
            setTimeout(() => {
                loader.style.display = 'none';
            }, 500);
        }
    }

    function updateLoadingText(text) {
        const loadingText = document.getElementById('loading-text');
        if (loadingText) {
            loadingText.style.opacity = '0';
            setTimeout(() => {
                loadingText.textContent = text;
                loadingText.style.opacity = '1';
            }, 200);
        }
    }

    // --- Dynamic Banner Management ---
    function updateBanner(sectionType, sectionTitle = '') {
        const bannerSection = document.querySelector('.banner-section');
        if (bannerSection) {
            if (sectionType === 'toc') {
                bannerSection.textContent = 'Table of Contents';
            } else {
                bannerSection.textContent = sectionTitle;
            }
        }
    }

    // --- FIXED: Chat History Management for Each Chapter ---
    function saveChatToHistory(view) {
        if (chatHistory[view]) {
            chatHistory[view] = Array.from(chatMessages.children).map(row => ({
                html: row.outerHTML,
                sender: row.classList.contains('user-message-row') ? 'user' : 'bot',
                type: row.querySelector('.notion-content') ? 'notion' : 
                      row.querySelector('.ai-response') ? 'ai' : 'default'
            }));
            console.log(`💾 Saved chat for ${view}:`, chatHistory[view].length, 'messages');
        }
    }

    function loadChatFromHistory(view) {
        chatMessages.innerHTML = '';
        if (chatHistory[view] && chatHistory[view].length > 0) {
            console.log(`📖 Loading chat for ${view}:`, chatHistory[view].length, 'messages');
            chatHistory[view].forEach(message => {
                chatMessages.innerHTML += message.html;
            });
            chatWindow.scrollTop = chatWindow.scrollHeight;
        } else {
            console.log(`📖 No chat history found for ${view}`);
        }
    }

    function switchToView(newView, sectionTitle = '') {
        console.log(`🔄 Switching from ${currentView} to ${newView}`);
        
        // Save current chat only if we have messages
        if (chatMessages.children.length > 0) {
            saveChatToHistory(currentView);
        }
        
        // Switch to new view
        const previousView = currentView;
        currentView = newView;
        
        // Initialize chat history for new view if it doesn't exist
        if (!chatHistory[newView]) {
            chatHistory[newView] = [];
            console.log(`🆕 Created new chat history for ${newView}`);
        }
        
        // Only load chat if we're switching to a different view
        if (previousView !== newView) {
            loadChatFromHistory(newView);
        }
        
        // Update banner
        updateBanner(newView === 'toc' ? 'toc' : 'chapter', sectionTitle);
        
        // Update current chapter title in header
        document.getElementById('current-chapter-title').textContent = 
            newView === 'toc' ? "Hylee's Intro to Multifamily" : sectionTitle;
        
        // Set appropriate bot state and quick actions for TOC
        if (newView === 'toc') {
            if (hasStartedAnyChapter) {
                // User has started course before - allow direct chapter access
                botState = 'TOC_NAVIGATION';
                renderQuickActions(['Continue where I left off', 'Restart from beginning']);
            } else {
                // First time - show start course actions
                botState = 'AWAITING_COURSE_START';
                renderQuickActions(QUICK_ACTIONS.START);
            }
        }
    }

    // --- Sidebar Management ---
    function initializeSidebar() {
        const menuBtn = document.getElementById('menu-btn');
        const sidebarToggle = document.getElementById('sidebar-toggle');
        const sidebar = document.getElementById('sidebar');

        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('hidden');
        });

        sidebarToggle.addEventListener('click', () => {
            sidebar.classList.add('hidden');
        });
    }

    // --- Calculate Chapter Progress ---
    function calculateChapterProgress(chapterTitle) {
        if (completedChapters.includes(chapterTitle)) {
            return 100;
        }
        if (chapterTitle === currentChapterTitle && chapterSections.length > 0) {
            return Math.round((currentSectionIndex / chapterSections.length) * 100);
        }
        return 0;
    }

    function renderChaptersList() {
        const chaptersList = document.getElementById('chapters-list');
        chaptersList.innerHTML = '';

        // Add Table of Contents item
        const tocItem = document.createElement('div');
        tocItem.classList.add('chapter-item');
        if (currentView === 'toc') {
            tocItem.classList.add('current');
        } else {
            tocItem.classList.add('unlocked');
        }

        const tocIcon = document.createElement('div');
        tocIcon.classList.add('chapter-icon', 'unlocked');
        tocIcon.textContent = '📋';

        const tocContent = document.createElement('div');
        tocContent.classList.add('chapter-content');
        const tocTitle = document.createElement('div');
        tocTitle.classList.add('chapter-title');
        tocTitle.textContent = 'Table of Contents';
        tocContent.appendChild(tocTitle);

        tocItem.appendChild(tocIcon);
        tocItem.appendChild(tocContent);
        
        if (currentView !== 'toc') {
            tocItem.addEventListener('click', () => {
                switchToView('toc');
            });
        }

        chaptersList.appendChild(tocItem);

        // Add chapters
        allChapters.forEach((chapter, index) => {
            const chapterItem = document.createElement('div');
            chapterItem.classList.add('chapter-item');
            
            const isCompleted = completedChapters.includes(chapter.title);
            const isCurrent = chapter.title === currentChapterTitle && currentView === chapter.title;
            const isUnlocked = !chapter.locked || isCompleted;
            const progress = calculateChapterProgress(chapter.title);

            // If chapter is completed, hide the action buttons
            if (isCompleted) {
                chapterItem.classList.add('completed');
                return; // Skip rendering action buttons for completed chapters
            }

            if (isCurrent) {
                chapterItem.classList.add('current');
            } else if (isUnlocked) {
                chapterItem.classList.add('unlocked');
            } else {
                chapterItem.classList.add('locked');
            }

            const icon = document.createElement('div');
            icon.classList.add('chapter-icon');
            if (isCompleted) {
                icon.classList.add('completed');
                icon.textContent = '✓';
            } else if (isUnlocked) {
                icon.classList.add('unlocked');
                icon.textContent = chapter.number;
            } else {
                icon.classList.add('locked');
                icon.innerHTML = '●';
            }

            const chapterContent = document.createElement('div');
            chapterContent.classList.add('chapter-content');

            const title = document.createElement('div');
            title.classList.add('chapter-title');
            title.textContent = chapter.title;

            // Add progress bar for unlocked chapters
            if (isUnlocked) {
                const progressBar = document.createElement('div');
                progressBar.classList.add('chapter-progress');
                
                const progressFill = document.createElement('div');
                progressFill.classList.add('progress-fill');
                progressFill.style.width = `${progress}%`;
                
                progressBar.appendChild(progressFill);
                
                const progressText = document.createElement('div');
                progressText.classList.add('progress-text');
                progressText.textContent = `${progress}% complete`;
                
                chapterContent.appendChild(title);
                chapterContent.appendChild(progressBar);
                chapterContent.appendChild(progressText);
            } else {
                chapterContent.appendChild(title);
            }

            chapterItem.appendChild(icon);
            chapterItem.appendChild(chapterContent);

            // Add click handler for unlocked chapters
            if (isUnlocked && !isCurrent) {
                chapterItem.addEventListener('click', () => {
                    startChapter(chapter.title);
                });
            }

            chaptersList.appendChild(chapterItem);
        });
    }

    function updateCurrentChapterTitle(title) {
        currentChapterTitle = title;
        renderChaptersList();
    }

    // --- UPDATED: Better loading bar management ---
    function showLoadingBar() { 
        loadingBar.style.opacity = '1'; 
        loadingBar.style.width = '70%'; 
    }
    
    function hideLoadingBar() {
        loadingBar.style.width = '100%';
        setTimeout(() => { 
            loadingBar.style.opacity = '0'; 
            loadingBar.style.width = '0'; 
        }, 300);
    }
    
    // Force hide loading bar immediately (for debugging)
    function forceHideLoadingBar() {
        loadingBar.style.opacity = '0';
        loadingBar.style.width = '0';
        loadingBar.style.transition = 'none';
        setTimeout(() => {
            loadingBar.style.transition = 'width 0.2s ease-in-out, opacity 0.2s';
        }, 100);
    }
    
    function disableQuickActions() { quickActionsContainer.classList.add('disabled'); }
    function enableQuickActions() { quickActionsContainer.classList.remove('disabled'); }

    function createMessageElement(sender, messageType = 'default') {
        const row = document.createElement('div');
        row.classList.add('message-row', `${sender}-message-row`);

        const avatar = document.createElement('img');
        avatar.classList.add('avatar');
        avatar.src = sender === 'bot' ? 'bot-avatar.png' : 'https://placehold.co/40x40/e0f7ff/333333?text=DI';

        const messageBubble = document.createElement('div');
        messageBubble.classList.add('message', `${sender}-message`);
        
        if (sender === 'bot') {
            if (messageType === 'notion') {
                messageBubble.classList.add('notion-content');
            } else if (messageType === 'ai') {
                messageBubble.classList.add('ai-response');
                const aiIcon = document.createElement('div');
                aiIcon.classList.add('ai-icon');
                messageBubble.appendChild(aiIcon);
            }
        }

        row.appendChild(avatar);
        row.appendChild(messageBubble);
        chatMessages.appendChild(row);
        chatWindow.scrollTop = chatWindow.scrollHeight;
        
        return messageBubble;
    }

    // --- UPDATED: Faster typing for Notion content ---
    function typewriterDisplay(messageBubble, markdownContent, onCompleteCallback, isNotionContent = false) {
        const lines = markdownContent.split('\n');
        let i = 0;
        
        // Faster typing for Notion content (20ms vs 50ms)
        const typingSpeed = isNotionContent ? 20 : 50;
        
        const intervalId = setInterval(() => {
            if (i < lines.length) {
                if (lines[i].trim() !== "") messageBubble.innerHTML += marked.parse(lines[i]);
                i++;
                chatWindow.scrollTop = chatWindow.scrollHeight;
            } else {
                clearInterval(intervalId);
                if (onCompleteCallback) onCompleteCallback();
            }
        }, typingSpeed);
    }

    // --- NEW: Streaming typewriter for AI responses ---
    function streamingTypewriter(messageBubble, text, onCompleteCallback) {
        let i = 0;
        const typingSpeed = 30; // Character by character typing
        
        const intervalId = setInterval(() => {
            if (i < text.length) {
                messageBubble.innerHTML = marked.parse(text.substring(0, i + 1));
                i++;
                chatWindow.scrollTop = chatWindow.scrollHeight;
            } else {
                clearInterval(intervalId);
                if (onCompleteCallback) onCompleteCallback();
            }
        }, typingSpeed);
    }

    function renderQuickActions(actionSet) {
        quickActionsContainer.innerHTML = '';
        if (!actionSet || actionSet.length === 0) return;
        actionSet.forEach(actionText => {
            const button = document.createElement('button');
            button.classList.add('quick-action-btn');
            button.textContent = actionText;
            button.addEventListener('click', () => handleUserInput(actionText));
            quickActionsContainer.appendChild(button);
        });
        enableQuickActions();
    }

    // --- UPDATED: Generate content-specific quick actions ---
    async function generateContextualActions(sectionContent) {
        try {
            const response = await fetch(`${API_BASE_URL}/generate-quick-actions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ section_content: sectionContent })
            });
            
            if (!response.ok) throw new Error("Quick actions generation failed");
            const data = await response.json();
            console.log('🎯 Generated actions from server:', data.actions);
            return data.actions;
        } catch (error) {
            console.error('Quick actions generation error:', error);
            return ['What does this mean?', 'Give me examples', 'How is this used?'];
        }
    }

    async function renderDynamicQuickActions(sectionContent) {
        const currentChapter = allChapters.find(ch => ch.title === currentChapterTitle);
        const nextChapter = allChapters.find(ch => !ch.locked && !completedChapters.includes(ch.title) && ch.title !== currentChapterTitle);

        // If chapter is completed, hide quick actions
        if (completedChapters.includes(currentChapterTitle)) {
            renderQuickActions([]); // No actions
        } else {
            const dynamicActions = await generateContextualActions(sectionContent);
            const allActions = ['Move to next section', ...dynamicActions];
            renderQuickActions(allActions);
        }
    }

    function checkContinueKeywords(text) {
        const continueKeywords = [
            'next', 'continue', 'proceed', 'move on', 'go ahead', 'keep going',
            'yes', 'ok', 'sure', 'got it', 'understood', 'clear', 'makes sense',
            'let\'s go', 'lets go', 'let\'s continue', 'lets continue', 'move to next',
            'next section', 'go on', 'carry on', 'move forward', 'progress',
            'alright', 'right', 'good', 'fine', 'yep', 'yeah', 'perfect'
        ];
        
        const lowerText = text.toLowerCase().trim();
        return continueKeywords.some(keyword => {
            return lowerText === keyword || 
                   lowerText.includes(' ' + keyword + ' ') ||
                   lowerText.startsWith(keyword + ' ') ||
                   lowerText.endsWith(' ' + keyword);
        });
    }

    function checkQuestionKeywords(text) {
        const questionKeywords = [
            'what', 'how', 'why', 'when', 'where', 'who', 'which',
            'explain', 'clarify', 'elaborate', 'more details', 'more info',
            'don\'t understand', 'dont understand', 'confused', 'unclear',
            'can you', 'could you', 'would you', 'help me', 'tell me',
            'example', 'meaning', 'definition', 'what does', 'how does'
        ];
        
        const lowerText = text.toLowerCase().trim();
        return questionKeywords.some(keyword => lowerText.includes(keyword)) ||
               text.includes('?');
    }

    async function classifyUserIntent(userInput, currentSection, nextSection) {
        try {
            showLoadingBar();
            const response = await fetch(`${API_BASE_URL}/classify-intent`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    user_input: userInput,
                    current_section_title: currentSection,
                    next_section_title: nextSection
                })
            });
            hideLoadingBar();
            
            if (!response.ok) throw new Error("Intent classification failed");
            const data = await response.json();
            return data.intent;
        } catch (error) {
            hideLoadingBar();
            console.error('Intent classification error:', error);
            return 'QUESTION';
        }
    }

    async function classifyUserIntentHybrid(userInput, currentSection, nextSection) {
        if (checkContinueKeywords(userInput)) {
            console.log('🚀 Fast keyword match: CONTINUE');
            return 'CONTINUE';
        }
        
        if (checkQuestionKeywords(userInput)) {
            console.log('🚀 Fast keyword match: QUESTION');
            return 'QUESTION';
        }
        
        console.log('🤖 Using AI fallback for:', userInput);
        return await classifyUserIntent(userInput, currentSection, nextSection);
    }

    // --- FIXED: Streaming AI responses with proper loading bar management ---
    async function askAI(question) {
        showLoadingBar();
        try {
            const context = (botState === 'AWAITING_COURSE_START' || botState === 'TOC_NAVIGATION') ? tableOfContents : currentChapterContent;
            const response = await fetch(`${API_BASE_URL}/ask-question-stream`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    question, 
                    context,
                    current_chapter_title: currentChapterTitle
                })
            });
            
            if (!response.ok) {
                hideLoadingBar();
                throw new Error("AI server error");
            }
            
            // Create AI response message bubble
            const botMessageBubble = createMessageElement('bot', 'ai');
            
            // Read the streaming response
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let fullResponse = '';
            let hasStartedStreaming = false;
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const chunk = decoder.decode(value, { stream: true });
                const lines = chunk.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            // Ensure loading bar is completely hidden
                            forceHideLoadingBar();
                            
                            // Streaming complete - render quick actions
                            if (botState === 'AWAITING_COURSE_START') {
                                renderQuickActions(QUICK_ACTIONS.START);
                            } else if (botState === 'TOC_NAVIGATION') {
                                renderQuickActions(['Continue where I left off', 'Restart from beginning']);
                            } else if (botState === 'AWAITING_NEXT_SECTION') {
                                const currentSection = chapterSections[currentSectionIndex];
                                if (currentSection) {
                                    renderDynamicQuickActions(currentSection.content);
                                } else {
                                    renderQuickActions(['Move to next section', 'What does this mean?']);
                                }
                            }
                            return;
                        }
                        
                        try {
                            const parsed = JSON.parse(data);
                            if (parsed.content) {
                                // Hide loading bar on first content chunk
                                if (!hasStartedStreaming) {
                                    hideLoadingBar();
                                    hasStartedStreaming = true;
                                }
                                
                                fullResponse += parsed.content;
                                // Update the message bubble with streaming content
                                botMessageBubble.innerHTML = marked.parse(fullResponse);
                                chatWindow.scrollTop = chatWindow.scrollHeight;
                            }
                        } catch (e) {
                            // Ignore parsing errors for incomplete chunks
                        }
                    }
                }
            }
        } catch (error) {
            forceHideLoadingBar(); // Force hide on any error
            createMessageElement('bot', 'ai').innerHTML = "Sorry, I had trouble thinking of an answer.";
            enableQuickActions();
        }
    }

    function proceedToNextStep() {
        const nextSection = chapterSections[currentSectionIndex + 1];
        if (nextSection) {
            if (nextSection.title.trim().toLowerCase().startsWith('factoid')) {
                currentSectionIndex++;
                renderChaptersList();
                displayCurrentSection();
            } else {
                botState = 'AWAITING_NEXT_SECTION';
                const currentSection = chapterSections[currentSectionIndex];
                const cleanCurrentTitle = currentSection.title.replace(/^\d+(\.\d+)*\s*/, '');
                const cleanNextTitle = nextSection.title.replace(/^\d+(\.\d+)*\s*/, '');
                const polishedPrompt = `Hope you understood **${cleanCurrentTitle}**. Let me know if you have any questions, otherwise, we can move on to the next section: **${cleanNextTitle}**`;
                
                const promptBubble = createMessageElement('bot', 'notion');
                typewriterDisplay(promptBubble, polishedPrompt, () => {
                    renderDynamicQuickActions(currentSection.content);
                }, true); // Mark as Notion content for faster typing
            }
        } else {
            completeCurrentChapter();
        }
    }

    async function completeCurrentChapter() {
        botState = 'CHAPTER_COMPLETED';
        
        try {
            const response = await fetch(`${API_BASE_URL}/complete-chapter`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chapter_title: currentChapterTitle })
            });
            
            if (response.ok) {
                const data = await response.json();
                allChapters = data.unlockedChapters;
                completedChapters.push(currentChapterTitle);
                renderChaptersList();
                
                const congratsBubble = createMessageElement('bot', 'notion');
                let congratsMessage = `🎉 Congratulations! You've completed **${currentChapterTitle}**!`;
                
                if (data.nextChapter) {
                    congratsMessage += `\n\nGreat news! **${data.nextChapter.title}** is now unlocked and ready for you.`;
                    botState = 'AWAITING_NEXT_CHAPTER';
                    typewriterDisplay(congratsBubble, congratsMessage, () => {
                        renderQuickActions([`Start ${data.nextChapter.title}`, 'Review this chapter', 'View all chapters']);
                    }, true); // Notion content - faster typing
                } else {
                    congratsMessage += `\n\n🎓 Amazing! You've completed the entire course! You're now ready to apply your multifamily knowledge in the real world.`;
                    typewriterDisplay(congratsBubble, congratsMessage, () => {
                        renderQuickActions(['Restart course', 'View certificate', 'Course summary']);
                    }, true); // Notion content - faster typing
                }
            }
        } catch (error) {
            console.error('Chapter completion error:', error);
            const congratsBubble = createMessageElement('bot', 'notion');
            typewriterDisplay(congratsBubble, "Congratulations, you've completed this chapter!", () => {
                renderQuickActions(['Continue learning', 'Review chapter']);
            }, true);
        }
    }

    function displayCurrentSection() {
        if (currentSectionIndex < chapterSections.length) {
            const section = chapterSections[currentSectionIndex];
            const sectionBubble = createMessageElement('bot', 'notion');
            if (section.content.includes('| ---')) {
                sectionBubble.innerHTML = marked.parse(section.content);
                proceedToNextStep();
            } else {
                // Mark as Notion content for faster typing
                typewriterDisplay(sectionBubble, section.content, proceedToNextStep, true);
            }
        }
    }

    function parseContentIntoSections(markdown) {
        const sections = [];
        let currentSection = null;
        markdown.split('\n').forEach(line => {
            if (line.trim().startsWith('#')) {
                if (currentSection) sections.push(currentSection);
                currentSection = { title: line.replace(/#/g, '').trim(), content: line };
            } else if (currentSection) {
                currentSection.content += '\n' + line;
            }
        });
        if (currentSection) sections.push(currentSection);
        return sections;
    }

    async function startChapter(title) {
        console.log(`🚀 Starting chapter: ${title}`);
        
        // Mark that user has started a chapter
        hasStartedAnyChapter = true;
        
        // Switch to chapter view (this will save current chat automatically)
        switchToView(title, title);
        updateCurrentChapterTitle(title);
        
        // If this is a fresh chapter start (no chat history), load content
        if (!chatHistory[title] || chatHistory[title].length === 0) {
            console.log(`📖 Fresh chapter start for ${title} - loading content`);
            
            if (title === firstChapterTitle && firstChapterContent) {
                console.log('🚀 Using preloaded first chapter content - instant load!');
                currentChapterContent = firstChapterContent;
                chapterSections = parseContentIntoSections(firstChapterContent);
                currentSectionIndex = 0;
                renderChaptersList();
                displayCurrentSection();
                return;
            }
            
            console.log('📡 Loading chapter content from server...');
            showLoadingBar();
            renderQuickActions([]);
            try {
                const response = await fetch(`${API_BASE_URL}/get-chapter-content`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title }),
                });
                hideLoadingBar();
                if (!response.ok) throw new Error('Server error');
                const data = await response.json();
                currentChapterContent = data.content;
                chapterSections = parseContentIntoSections(data.content);
                currentSectionIndex = 0;
                renderChaptersList();
                displayCurrentSection();
            } catch (error) {
                hideLoadingBar();
                createMessageElement('bot').innerHTML = 'Sorry, there was a problem loading the chapter.';
            }
        } else {
            // Restore chapter state from chat history - content should already be loaded
            console.log(`📖 Resuming chapter ${title} from chat history`);
            renderChaptersList();
            
            // If we don't have the chapter content in memory, reload it
            if (!currentChapterContent || chapterSections.length === 0) {
                console.log('📡 Reloading chapter content for resumed session...');
                try {
                    const response = await fetch(`${API_BASE_URL}/get-chapter-content`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title }),
                    });
                    if (response.ok) {
                        const data = await response.json();
                        currentChapterContent = data.content;
                        chapterSections = parseContentIntoSections(data.content);
                    }
                } catch (error) {
                    console.error('Error reloading chapter content:', error);
                }
            }
        }
    }
    
    async function handleUserInput(textFromButton = null) {
        const userText = textFromButton || userInput.value.trim();
        if (!userText || botState === 'LOADING') return;
        
        createMessageElement('user').textContent = userText;
        userInput.value = '';
        disableQuickActions();

        const lowerCaseText = userText.toLowerCase();
        
        if (botState === 'AWAITING_COURSE_START') {
            const startKeywords = ['yes', 'start', 'begin', 'continue', 'proceed', 'ok', 'sure'];
            if (startKeywords.some(keyword => lowerCaseText.includes(keyword))) {
                startChapter(firstChapterTitle);
                return;
            } else {
                askAI(userText);
                return;
            }
        }
        
        if (botState === 'TOC_NAVIGATION') {
            if (lowerCaseText.includes('continue') && lowerCaseText.includes('left off')) {
                // Find the most recently started chapter
                if (currentChapterTitle && chatHistory[currentChapterTitle] && chatHistory[currentChapterTitle].length > 0) {
                    startChapter(currentChapterTitle);
                } else {
                    startChapter(firstChapterTitle);
                }
                return;
            } else if (lowerCaseText.includes('restart') && lowerCaseText.includes('beginning')) {
                hasStartedAnyChapter = false;
                currentChapterTitle = "";
                completedChapters = [];
                startChapter(firstChapterTitle);
                return;
            } else {
                askAI(userText);
                return;
            }
        }
        
        if (botState === 'AWAITING_NEXT_CHAPTER') {
            if (lowerCaseText.includes('start') && lowerCaseText.includes('chapter')) {
                const nextChapter = allChapters.find(ch => !ch.locked && !completedChapters.includes(ch.title) && ch.title !== currentChapterTitle);
                if (nextChapter) {
                    startChapter(nextChapter.title);
                    return;
                }
            } else if (lowerCaseText.includes('view') && lowerCaseText.includes('chapters')) {
                const sidebar = document.getElementById('sidebar');
                sidebar.classList.remove('hidden');
                return;
            } else {
                askAI(userText);
                return;
            }
        }
        
        if (botState === 'AWAITING_END_OF_CHAPTER') {
            if (lowerCaseText.includes('next chapter')) {
                const bubble = createMessageElement('bot');
                typewriterDisplay(bubble, "Moving to the next chapter is not implemented yet!", () => {
                    renderQuickActions(QUICK_ACTIONS.END_OF_CHAPTER);
                });
                return;
            } else if (lowerCaseText.includes('restart')) {
                location.reload();
                return;
            } else {
                askAI(userText);
                return;
            }
        }

        if (botState === 'AWAITING_NEXT_SECTION') {
            const currentSection = chapterSections[currentSectionIndex];
            const nextSection = chapterSections[currentSectionIndex + 1];
            
            const currentTitle = currentSection ? currentSection.title : "Current Section";
            const nextTitle = nextSection ? nextSection.title : "Next Section";
            
            const intent = await classifyUserIntentHybrid(userText, currentTitle, nextTitle);
            
            if (intent === 'CONTINUE') {
                currentSectionIndex++;
                renderChaptersList();
                displayCurrentSection();
            } else {
                askAI(userText);
            }
            return;
        }

        askAI(userText);
    }

    async function loadInitialContent() {
        showFullScreenLoader();
        updateLoadingText('Connecting to your course...');
        
        try {
            updateLoadingText('Loading course content...');
            const response = await fetch(`${API_BASE_URL}/get-course-content`);
            if (!response.ok) throw new Error('Server error');
            
            updateLoadingText('Preparing your learning experience...');
            const data = await response.json();
            
            firstChapterTitle = data.firstChapterTitle;
            firstChapterContent = data.firstChapterContent;
            tableOfContents = data.content;
            allChapters = data.allChapters || [];
            
            // Initialize chat history for all chapters
            allChapters.forEach(chapter => {
                chatHistory[chapter.title] = [];
            });
            
            initializeSidebar();
            renderChaptersList();
            
            if (firstChapterContent) {
                console.log('✅ First chapter preloaded successfully!');
                updateLoadingText('Almost ready...');
            } else {
                console.log('⚠️ First chapter preload failed, will load on demand');
            }
            
            await new Promise(resolve => setTimeout(resolve, 800));
            
            hideFullScreenLoader();
            
            // Start in table of contents view
            updateBanner('toc');
            
            const tocBubble = createMessageElement('bot', 'notion');
            // Faster typing for table of contents (Notion content)
            typewriterDisplay(tocBubble, data.content, () => {
                if (firstChapterTitle) {
                    const questionText = `Are you ready to start with **${firstChapterTitle}**?`;
                    const questionBubble = createMessageElement('bot', 'notion');
                    typewriterDisplay(questionBubble, questionText, () => {
                        botState = 'AWAITING_COURSE_START';
                        renderQuickActions(QUICK_ACTIONS.START);
                    }, true); // Notion content - faster typing
                }
            }, true); // Notion content - faster typing
        } catch (error) {
            hideFullScreenLoader();
            createMessageElement('bot').innerHTML = 'Sorry, there was a problem loading the course.';
        }
    }
    
    userInput.addEventListener('keydown', (e) => e.key === 'Enter' && (e.preventDefault(), handleUserInput()));
    
    loadInitialContent();
});
