// 공통 함수: 삭제 버튼 토글
function toggleDeleteButton(button) {
    const deleteButton = button.nextElementSibling;
    deleteButton.classList.toggle('d-none');
}

// 공통 함수: 채팅 기록 삭제
async function deleteChatHistory(threadId) {
    try {
        // 현재 URL을 기반으로 챗봇 타입 결정 (텍스트 또는 이미지)
        const currentPath = window.location.pathname;
        let chatbotType = '';
        if (currentPath.includes('/chatbot')) {
            chatbotType = 'chatbot';
        } else if (currentPath.includes('/imagebot')) {
            chatbotType = 'imagebot';
        }

        // threadId가 유효한지 확인
        if (!threadId) {
            console.error('threadId가 제공되지 않았습니다.');
            return;
        }

        const deleteUrl = `/${chatbotType}/delete_chat/${threadId}`;
        console.log(`삭제 요청 보냄: ${deleteUrl}`); // 삭제 요청 로그 추가

        const response = await axios.delete(deleteUrl);
        if (response.status === 200) {
            console.log('채팅 기록 삭제 완료:', threadId);
            // 사이드바를 업데이트하여 삭제된 항목 반영
            await updateSidebar(`/${chatbotType}/get_history`, (historyId) => loadChatHistory(historyId, `/${chatbotType}`));
        } else {
            console.error('채팅 기록 삭제 실패:', response.data);
        }
    } catch (error) {
        console.error('채팅 기록 삭제 오류:', error);
    }
}


// 공통 함수: 사이드바 업데이트
async function updateSidebar(getHistoryUrl, loadChatCallback) {
    try {
        const response = await axios.get(getHistoryUrl);
        const sidebar = document.getElementById('chatHistoryList');
        sidebar.innerHTML = ''; // 기존 내용 지우기

        if (response.data.chat_histories.length === 0) {
            sidebar.innerHTML = '<li class="nav-item"><span>기록이 없습니다.</span></li>';
            return;
        }

        response.data.chat_histories.forEach(history => {
            const existingItem = document.querySelector(`.nav-link[data-id='${history.thread_id}']`);
            if (existingItem) {
                return; // 이미 존재하는 항목이면 추가하지 않음
            }

            const li = document.createElement('li');
            li.className = 'nav-item d-flex justify-content-between align-items-center';

            const link = document.createElement('a');
            link.className = 'nav-link chat-history-link';
            link.href = `${window.location.pathname}?thread_id=${history.thread_id}`;
            link.textContent = history.user_question.slice(0, 20) + '...';
            link.dataset.id = history.thread_id;

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-danger btn-sm delete-button';
            deleteBtn.dataset.id = history.thread_id;
            deleteBtn.textContent = '삭제';
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                deleteChatHistory(history.thread_id);
            });

            li.appendChild(link);
            li.appendChild(deleteBtn);
            sidebar.appendChild(li);
        });
    } catch (error) {
        console.error('사이드바 업데이트 오류:', error);
    }
}


// 공통 함수: 채팅 기록 불러오기
async function loadChatHistory(threadId, baseUrl) {
    try {
        const getUrl = `${baseUrl}/get_chat/${threadId}`;
        console.log(`채팅 기록 불러오기를 위해 GET 요청을 보냄: ${getUrl}`); // URL 디버깅 로그 추가
        const response = await axios.get(getUrl);
        if (response.status === 200) {
            const chatContentDiv = document.getElementById('chatContainer');
            chatContentDiv.innerHTML = ''; // 기존 내용을 지우고 새로 불러온 기록으로 대체

            // thread_id를 숨겨진 필드에 설정합니다.
            const threadIdInput = document.getElementById('threadId');
            threadIdInput.value = response.data.thread_id;

            // 기록된 메시지를 채팅창에 추가
            response.data.chat_history.forEach(history => {
                if (history.user_question) {
                    const userMessageDiv = document.createElement('div');
                    userMessageDiv.className = 'message user-message';
                    userMessageDiv.textContent = history.user_question;
                    chatContentDiv.appendChild(userMessageDiv);
                }

                if (history.maked_text) {
                    const botMessageDiv = document.createElement('div');
                    botMessageDiv.className = 'message bot-message';
                    botMessageDiv.textContent = history.maked_text;
                    chatContentDiv.appendChild(botMessageDiv);
                }

                if (history.maked_image_url) {
                    const botImageDiv = document.createElement('div');
                    botImageDiv.className = 'message bot-message';
                    const imageElement = document.createElement('img');
                    imageElement.src = history.maked_image_url;
                    imageElement.alt = 'Generated Image';
                    imageElement.style.width = '50%';
                    imageElement.style.height = 'auto';
                    imageElement.className = 'chatbot-image';
                    botImageDiv.appendChild(imageElement);
                    chatContentDiv.appendChild(botImageDiv);
                }
            });

            document.getElementById('chatContainer').scrollTop = chatContentDiv.scrollHeight;
        } else {
            console.error('기록을 찾을 수 없습니다:', response.data);
        }
    } catch (error) {
        console.error('채팅 기록 불러오기 오류:', error);
        const chatContentDiv = document.getElementById('chatContainer');
        chatContentDiv.innerHTML = `<p>기록을 불러오는데 오류가 발생했습니다.</p>`;
    }
}

// NEW CHAT 버튼 기능 수정
document.addEventListener("DOMContentLoaded", function() {
    const newChatButton = document.getElementById('newChatButton');
    if (newChatButton) {
        newChatButton.addEventListener('click', function() {
            const chatContainer = document.getElementById('chatContainer');
            if (chatContainer) {
                chatContainer.innerHTML = ''; // 채팅창 초기화
            }
            const threadIdInput = document.getElementById('threadId');
            threadIdInput.value = ''; // 새로운 채팅 스레드를 시작하므로 thread_id를 초기화합니다.

            // 현재 페이지의 chatbot type을 확인하고 새로운 대화 시작
            const currentPath = window.location.pathname;
            if (currentPath.includes('/chatbot')) {
                window.location.href = '/chatbot/chat';
            } else if (currentPath.includes('/imagebot')) {
                window.location.href = '/imagebot/image';
            }
        });
    }

    // 페이지 로드 시 적절한 URL에 따라 사이드바 업데이트
    const currentPath = window.location.pathname;
    if (currentPath.includes('/chatbot')) {
        updateSidebar('/chatbot/get_history', (threadId) => loadChatHistory(threadId, '/chatbot'));
    } else if (currentPath.includes('/imagebot')) {
        updateSidebar('/imagebot/get_history', (threadId) => loadChatHistory(threadId, '/imagebot'));
    }
});
