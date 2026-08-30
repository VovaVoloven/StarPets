let currentPetId = null;

//OPEN SIDEBAR
async function openCommentSidebar(petId) {
    if (!petId) return;

    currentPetId = petId;

    const errorDiv = document.getElementById('commentError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }

    document.getElementById('commentSidebar').classList.add('active');
    document.getElementById('overlay').classList.add('active');
    document.getElementById('submitBtn').textContent = 'Post Comment';

    const commentsList = document.getElementById('commentsList');
    commentsList.innerHTML = '<p class="text-muted text-center">Loading comments....</p>';

    try{
        const response = await fetch(`${GET_COMMENTS_URL}${petId}/`);

        if (!response.ok) {
            throw new Error('Network response was not ok');
        }

        const data = await response.json();
        
        renderComments(data.comments);
        updateFormVisibility(data.user_has_commented, data.user_comment_text);
    } catch (error) {
        commentsList.innerHTML = '<p class="text-danger text-center"> Error loading comments.</p>';
        console.error("Failed to load comments:", error);
    }
}

//CLOSE SIDEBAR
function closeCommentSidebar() {
    document.getElementById('commentSidebar').classList.remove('active');
    document.getElementById('overlay').classList.remove('active');
    const errorDiv = document.getElementById('commentError');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        errorDiv.textContent = '';
    }
    currentPetId = null;
    cancelEdit(); //reset form state
}

function createCommentWrapper(comment) {
    const wrapper = document.createElement('div');
    wrapper.className = 'comment-item p-2 mb-2 border-bottom';

    const detailsNode = document.createElement('div');
    detailsNode.className = 'd-flex justify-content-between align-items-center';

    const usernameNode = document.createElement('span');
    usernameNode.className = 'fw-bold small';
    usernameNode.textContent = `@${comment.username}`;
    detailsNode.appendChild(usernameNode);

    const dateNode = document.createElement('span');
    dateNode.className = 'text-muted';
    dateNode.style.fontSize = '0.75rem';
    dateNode.textContent = comment.date;
    detailsNode.appendChild(dateNode);

    wrapper.appendChild(detailsNode);

    const commentNode = document.createElement('p');
    commentNode.className = 'mb-0 small';
    commentNode.style.whiteSpace = 'pre-wrap';
    commentNode.style.wordBreak = 'break-word';
    commentNode.textContent = comment.text;
    wrapper.appendChild(commentNode);
    return wrapper;
}

//DISPLAY COMMENTS
function renderComments(comments) {
    const commentsList = document.getElementById('commentsList');

    commentsList.replaceChildren();

    if (comments.length === 0) {
        const emptyListNode = document.createElement('p');
        emptyListNode.className = 'text-muted text-center';
        emptyListNode.textContent = "No comments yet, Be the first!";
        commentsList.appendChild(emptyListNode);
        return;
    }
    
    for (const comment of comments) {
        commentsList.appendChild(createCommentWrapper(comment));
    }
}

function updateFormVisibility(hasCommented, existingText){
    const formContainer = document.getElementById('commentFormContainer');
    const msgContainer = document.getElementById('alreadyCommentedMsg');
    const textArea = document.querySelector('#commentForm textarea');

    if (hasCommented) {
        formContainer.style.display = 'none';
        msgContainer.style.display = 'block';
        textArea.value = existingText;
        updateCharCount(existingText.length);
    } else {
        formContainer.style.display = 'block';
        msgContainer.style.display = 'none';
        textArea.value = '';
        updateCharCount(0);
    }
}

// POST & EDIT COMMENT
document.getElementById('commentForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const textArea = e.target.querySelector('textarea');
    const text = textArea.value.trim();
    const errorDiv = document.getElementById('commentError');

    if (errorDiv) errorDiv.style.display = 'none';

    if (!text || !currentPetId) {
        if (errorDiv && !text) {
            errorDiv.textContent = "Comment cannot be empty.";
            errorDiv.style.display = 'block';
        }
        return;
    }

    const formData = new FormData();
    formData.append('comment', text);
    formData.append('csrfmiddlewaretoken', CSRF_TOKEN);

    try {
        const response = await fetch(`${POST_COMMENT_URL}${currentPetId}/`, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        });

        if (response.ok) {
            openCommentSidebar(currentPetId);//refresh everything
        } else {
            const data = await response.json();
            if (errorDiv) {
                errorDiv.textContent = data.error || "An error occurred.";
                errorDiv.style.display = 'block';
            }
        }
    } catch (error) {
        if (errorDiv) {
            errorDiv.textContent = "A network or server error occurred. Please try again.";
            errorDiv.style.display = 'block';
        }
        console.error("Submission failed:", error);
    }
});

//DELETE COMMENT
async function deleteComment() {
    if (!currentPetId) return;

    if (!confirm("Are you sure you want to delete your comment?")) return;

    const errorDiv = document.getElementById('commentError');
    if (errorDiv) errorDiv.style.display = 'none';


    try {
        const response = await fetch(`${DELETE_COMMENT_URL}${currentPetId}/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': CSRF_TOKEN,
                'X-Requested-With': 'XMLHttpRequest'
            }
        });

        if (response.ok) {
            openCommentSidebar(currentPetId); //refresh to show empty form
        } else {
            const data = await response.json();
            if (errorDiv) {
                errorDiv.textContent = data.error || "Failed to delete comment.";
                errorDiv.style.display = 'block';
            }
        }
    } catch (error) {
        if (errorDiv) {
            errorDiv.textContent = "A network or server error occurred. Please try again.";
            errorDiv.style.display = 'block';
        }
        console.error("Deletion failed:", error);
    }
}

// UI HELPERS 
function enableCommentEdit() {
    document.getElementById('commentFormContainer').style.display = 'block';
    document.getElementById('alreadyCommentedMsg').style.display = 'none';
    document.getElementById('cancelEditBtn').style.display = 'block';
    document.getElementById('submitBtn').textContent = 'Update Comment';
}

function cancelEdit() {
    //user cancels edit - re fetch initial state (before they edited)
    if (currentPetId) openCommentSidebar(currentPetId);
    document.getElementById('cancelEditBtn').style.display = 'none';
    document.getElementById('submitBtn').textContent = 'Post Comment';
}

function updateCharCount(len) {
    document.getElementById('charCount').textContent = len;
}

//Listener for real time character counting

document.querySelector('#commentForm textarea').addEventListener('input', (e) => {
    updateCharCount(e.target.value.length);
});
