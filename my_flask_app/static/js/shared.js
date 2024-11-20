// 공통 함수: 삭제 버튼 토글
function toggleDeleteButton(button) {
    const deleteButton = button.nextElementSibling;
    deleteButton.classList.toggle('d-none');
}

// 공통 함수: 채팅 기록 삭제
async function deleteChatHistory(historyId) {
    try {
        // 삭제 요청 URL 구성
        const deleteUrl = `${baseUrl}/delete_chat/${historyId}`;
        console.log(`삭제 요청 보냄: ${deleteUrl}`); // 삭제 요청 로그 추가

        const response = await axios.delete(deleteUrl);
        if (response.status === 200) {
            console.log('채팅 기록 삭제 완료:', historyId);
            // 사이드바를 업데이트하여 삭제된 항목 반영
            await updateSidebar(); 
        } else {
            console.error('채팅 기록 삭제 실패:', response.data);
        }
    } catch (error) {
        console.error('채팅 기록 삭제 오류:', error);
    }
}

// 공통 함수: 사이드바 업데이트
async function updateSidebar() {
    try {
        const getUrl = `${baseUrl}/get_history`;
        console.log(`사이드바 업데이트를 위해 GET 요청을 보냄: ${getUrl}`); // URL 디버깅 로그 추가
        const response = await axios.get(getUrl);
        const sidebar = document.getElementById('chatHistoryList');
        sidebar.innerHTML = '';

        response.data.chat_histories.forEach(history => {
            const li = document.createElement('li');
            li.className = 'nav-item d-flex justify-content-between align-items-center';

            const link = document.createElement('a');
            link.className = 'nav-link chat-history-link';
            link.href = '#';
            link.textContent = history.user_question.slice(0, 20) + '...';
            link.dataset.id = history.id;

            // 각 링크 클릭 시 올바른 baseUrl을 전달하여 loadChatHistory 호출
            link.addEventListener('click', () => loadChatHistory(history.id, baseUrl));

            const optionsBtn = document.createElement('button');
            optionsBtn.className = 'btn btn-secondary btn-sm options-button';
            optionsBtn.dataset.id = history.id;
            optionsBtn.textContent = '...';
            optionsBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                toggleDeleteButton(optionsBtn);
            });

            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'btn btn-danger btn-sm delete-button d-none';
            deleteBtn.dataset.id = history.id;
            deleteBtn.textContent = '삭제';
            deleteBtn.addEventListener('click', async (e) => {
                e.stopPropagation();
                await deleteChatHistory(history.id);
            });

            li.appendChild(link);
            li.appendChild(optionsBtn);
            li.appendChild(deleteBtn);
            sidebar.appendChild(li);
        });
    } catch (error) {
        console.error('사이드바 업데이트 오류:', error);
    }
}

// NEW CHAT 버튼 기능 추가
document.addEventListener("DOMContentLoaded", function() {
    const newChatButton = document.getElementById('newChatButton');
    if (newChatButton) {
        newChatButton.addEventListener('click', function() {
            const chatContainer = document.getElementById('chatContainer');
            if (chatContainer) {
                chatContainer.innerHTML = ''; // 채팅창 초기화
            }
            // 사이드바도 다시 업데이트하여 새 대화 시작
            updateSidebar();
        });
    }
});

// 공통 함수: 채팅 기록 불러오기
async function loadChatHistory(historyId, baseUrl) {
    try {
        const getUrl = `${baseUrl}/get_chat/${historyId}`;
        console.log(`채팅 기록 불러오기를 위해 GET 요청을 보냄: ${getUrl}`); // URL 디버깅 로그 추가
        const response = await axios.get(getUrl);
        if (response.status === 200) {
            const chatContentDiv = document.getElementById('chatContainer');
            chatContentDiv.innerHTML = ''; // 기존 내용을 지우고 새로 불러온 기록으로 대체

            const userMessageDiv = document.createElement('div');
            userMessageDiv.className = 'message user-message';
            userMessageDiv.textContent = response.data.user_question;
            chatContentDiv.appendChild(userMessageDiv);

            if (response.data.maked_text) {
                const botMessageDiv = document.createElement('div');
                botMessageDiv.className = 'message bot-message';
                botMessageDiv.textContent = response.data.maked_text;
                chatContentDiv.appendChild(botMessageDiv);
            }

            if (response.data.maked_image_url) {
                const botImageDiv = document.createElement('div');
                botImageDiv.className = 'message bot-message';
                const imageElement = document.createElement('img');
                imageElement.src = response.data.maked_image_url;
                imageElement.alt = 'Generated Image';
                imageElement.style.width = '50%';
                imageElement.style.height = 'auto';
                botImageDiv.appendChild(imageElement);
                chatContentDiv.appendChild(botImageDiv);
            }

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