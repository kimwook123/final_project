// 공통 함수: 삭제 버튼 토글
function toggleDeleteButton(button) {
  const deleteButton = button.nextElementSibling;
  deleteButton.classList.toggle('d-none');
}

// 공통 함수: 채팅 기록 삭제
async function deleteChatHistory(historyId, url) {
  try {
      const response = await axios.delete(`${url}/delete_chat/${historyId}`);
      if (response.status === 200) {
          console.log('채팅 기록 삭제 완료:', historyId);
          await updateSidebar(url); 
      } else {
          console.error('채팅 기록 삭제 실패:', response.data);
      }
  } catch (error) {
      console.error('채팅 기록 삭제 오류:', error);
  }
}

// 공통 함수: 사이드바 업데이트
async function updateSidebar(url, loadChatHistoryCallback) {
  try {
      const response = await axios.get(url);
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
          link.addEventListener('click', () => loadChatHistoryCallback(history.id));

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
          deleteBtn.addEventListener('click', (e) => {
              e.stopPropagation();
              deleteChatHistory(history.id, url);
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
