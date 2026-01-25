console.log('🎯 Ratings script loading...');

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM ready, initializing ratings...');

    injectFixedStyles();

    const ratingContainers = document.querySelectorAll('.rating-buttons');
    console.log(`📊 Found ${ratingContainers.length} rating container(s)`);

    if (ratingContainers.length === 0) {
        console.warn('⚠️ No rating containers found');
        return;
    }

    ratingContainers.forEach((container, index) => {
        initRatingContainer(container, index);
    });

    console.log('✅ Ratings initialized successfully');
});

function injectFixedStyles() {
    const styleId = 'rating-fixed-styles';

    const oldStyle = document.getElementById(styleId);
    if (oldStyle) oldStyle.remove();

    const style = document.createElement('style');
    style.id = styleId;
    style.textContent = `
        .rating-buttons {
            margin-bottom: 20px !important;
        }

        .rating-buttons .like-btn,
        .rating-buttons .dislike-btn {
            margin-right: 8px !important;
        }

        .rating-buttons .like-btn.active {
            background-color: #0d6efd !important;
            border-color: #0a58ca !important;
            color: white !important;
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(13, 110, 253, 0.3);
        }

        .rating-buttons .dislike-btn.active {
            background-color: #dc3545 !important;
            border-color: #b02a37 !important;
            color: white !important;
            transform: scale(1.05);
            box-shadow: 0 4px 12px rgba(220, 53, 69, 0.3);
        }

        .rating-buttons .rating-btn.active .positive-count,
        .rating-buttons .rating-btn.active .negative-count {
            font-size: 1.1rem !important;
            font-weight: 700 !important;
        }

        .rating-buttons .rating-btn.active img {
            filter: brightness(0) invert(1) !important;
        }

        .rating-buttons .rating-btn:not(.active) img {
            filter: brightness(0.5) !important;
        }

        .rating-sum.updated {
            animation: pulse 0.5s ease;
        }

        .count-updated {
            animation: bounce 0.3s ease;
        }

        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.1); }
            100% { transform: scale(1); }
        }

        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-3px); }
        }

        .card-footer .d-flex.flex-wrap.gap-1 {
            margin-top: 10px !important;
            clear: both !important;
        }
    `;

    document.head.appendChild(style);
    console.log('🎨 Fixed styles injected');
}

function initRatingContainer(container, index) {
    const likeBtn = container.querySelector('.like-btn');
    const dislikeBtn = container.querySelector('.dislike-btn');

    if (!likeBtn || !dislikeBtn) {
        console.warn(`⚠️ Container ${index}: missing like/dislike buttons`);
        return;
    }

    const postId = likeBtn.dataset.post || dislikeBtn.dataset.post;
    console.log(`📝 Container ${index}: post ID = ${postId}`);

    restoreButtonState(likeBtn, dislikeBtn, postId);

    likeBtn.addEventListener('click', function(event) {
        event.stopPropagation();
        handleRatingClick(event, container, postId, true);
    });

    dislikeBtn.addEventListener('click', function(event) {
        event.stopPropagation();
        handleRatingClick(event, container, postId, false);
    });

    console.log(`✅ Container ${index} initialized`);
}

function restoreButtonState(likeBtn, dislikeBtn, postId) {
    const savedState = localStorage.getItem(`rating_${postId}`);

    if (savedState) {
        try {
            const state = JSON.parse(savedState);

            const weekInMs = 7 * 24 * 60 * 60 * 1000;
            if (Date.now() - state.timestamp < weekInMs) {
                if (state.value === 1) {
                    likeBtn.classList.add('active');
                } else if (state.value === -1) {
                    dislikeBtn.classList.add('active');
                }
                console.log(`♻️ Restored rating for post ${postId}: ${state.value}`);
            } else {
                localStorage.removeItem(`rating_${postId}`);
            }
        } catch (e) {
            console.error('❌ Error parsing saved state:', e);
        }
    }
}

function handleRatingClick(event, container, postId, isLike) {
    if (container.classList.contains('processing')) return;
    container.classList.add('processing');

    const likeBtn = container.querySelector('.like-btn');
    const dislikeBtn = container.querySelector('.dislike-btn');

    const clickedBtn = isLike ? likeBtn : dislikeBtn;
    const otherBtn = isLike ? dislikeBtn : likeBtn;

    const value = isLike ? 1 : -1;
    const wasActive = clickedBtn.classList.contains('active');
    const otherWasActive = otherBtn.classList.contains('active');


    if (wasActive) {
        clickedBtn.classList.remove('active');
        console.log(`🔄 Toggling OFF ${isLike ? 'like' : 'dislike'} for post ${postId}`);

        updateCounters(container, clickedBtn, isLike, false, otherWasActive);

        saveRatingToStorage(postId, null);

        sendRatingToServer(postId, 0)
            .then(response => updateFromServer(container, response))
            .catch(error => handleError(container, clickedBtn, isLike, true, otherWasActive))
            .finally(() => container.classList.remove('processing'));

    } else {
        clickedBtn.classList.add('active');
        if (otherWasActive) {
            otherBtn.classList.remove('active');
        }
        console.log(`🔄 Toggling ON ${isLike ? 'like' : 'dislike'} for post ${postId}`);

        updateCounters(container, clickedBtn, isLike, true, otherWasActive);

        saveRatingToStorage(postId, value);

        sendRatingToServer(postId, value)
            .then(response => updateFromServer(container, response))
            .catch(error => handleError(container, clickedBtn, isLike, false, otherWasActive))
            .finally(() => container.classList.remove('processing'));
    }
}

function updateCounters(container, clickedBtn, isLike, isAdding, otherWasActive) {
    const likeBtn = container.querySelector('.like-btn');
    const dislikeBtn = container.querySelector('.dislike-btn');

    const likeCountEl = likeBtn.querySelector('.positive-count');
    const dislikeCountEl = dislikeBtn.querySelector('.negative-count');

    let likeCount = parseInt(likeCountEl.textContent) || 0;
    let dislikeCount = parseInt(dislikeCountEl.textContent) || 0;

    if (isAdding) {
        if (isLike) {
            likeCount += 1;
            if (otherWasActive) {
                dislikeCount = Math.max(0, dislikeCount - 1);
            }
        } else {
            dislikeCount += 1;
            if (otherWasActive) {
                likeCount = Math.max(0, likeCount - 1);
            }
        }
    } else {
        if (isLike) {
            likeCount = Math.max(0, likeCount - 1);
        } else {
            dislikeCount = Math.max(0, dislikeCount - 1);
        }
    }

    likeCountEl.textContent = likeCount;
    dislikeCountEl.textContent = dislikeCount;

    const updatedEl = isLike ? likeCountEl : dislikeCountEl;
    updatedEl.classList.add('count-updated');
    setTimeout(() => updatedEl.classList.remove('count-updated'), 300);


}

function handleError(container, clickedBtn, isLike, wasActive, otherWasActive) {
    console.error('❌ Error saving rating');

    const likeBtn = container.querySelector('.like-btn');
    const dislikeBtn = container.querySelector('.dislike-btn');

    if (wasActive) {
        clickedBtn.classList.add('active');
        if (otherWasActive && isLike) {
            dislikeBtn.classList.remove('active');
        } else if (otherWasActive && !isLike) {
            likeBtn.classList.remove('active');
        }
    } else {
        clickedBtn.classList.remove('active');
        if (otherWasActive && isLike) {
            dislikeBtn.classList.add('active');
        } else if (otherWasActive && !isLike) {
            likeBtn.classList.add('active');
        }
    }

    setTimeout(() => {
        alert('Ошибка при сохранении оценки. Страница будет перезагружена.');
        location.reload();
    }, 500);
}

function updateFromServer(container, data) {
    const positiveCount = container.querySelector('.positive-count');
    const negativeCount = container.querySelector('.negative-count');

    if (positiveCount) positiveCount.textContent = data['positive-count'] || 0;
    if (negativeCount) negativeCount.textContent = data['negative-count'] || 0;

    console.log('📤 Rating saved to server:', data);
}

function saveRatingToStorage(postId, value) {
    if (value === null) {
        localStorage.removeItem(`rating_${postId}`);
        console.log(`🗑️ Removed rating for post ${postId} from localStorage`);
    } else {
        const state = {
            value: value,
            timestamp: Date.now()
        };
        localStorage.setItem(`rating_${postId}`, JSON.stringify(state));
        console.log(`💾 Saved rating ${value} for post ${postId} to localStorage`);
    }
}

function sendRatingToServer(postId, value) {
    const csrfToken = getCSRFToken();

    const formData = new FormData();
    formData.append('post_id', postId);
    formData.append('value', value);

    console.log(`📤 Sending rating to server: post=${postId}, value=${value}`);

    return fetch('/rating/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': csrfToken,
            'X-Requested-With': 'XMLHttpRequest',
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.json();
    });
}

function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;

    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }

    return cookieValue;
}

window.RatingSystem = {
    debug: () => {
        console.log('🔍 Rating System Debug Info:');
        console.log('- Containers:', document.querySelectorAll('.rating-buttons').length);

        const ratings = Object.keys(localStorage).filter(k => k.startsWith('rating_'));
        console.log('- LocalStorage ratings:', ratings.length);
        ratings.forEach(key => {
            try {
                const data = JSON.parse(localStorage.getItem(key));
                console.log(`  ${key}:`, data);
            } catch (e) {}
        });

        document.querySelectorAll('.rating-buttons').forEach((container, i) => {
            const likeBtn = container.querySelector('.like-btn');
            const dislikeBtn = container.querySelector('.dislike-btn');
            console.log(`\nContainer ${i}:`);
            console.log('  Post ID:', likeBtn?.dataset.post);
            console.log('  Like active:', likeBtn?.classList.contains('active'));
            console.log('  Dislike active:', dislikeBtn?.classList.contains('active'));
        });
    },

    reset: (postId) => {
        if (postId) {
            localStorage.removeItem(`rating_${postId}`);
            console.log(`🗑️ Rating for post ${postId} reset`);
        } else {
            Object.keys(localStorage)
                .filter(k => k.startsWith('rating_'))
                .forEach(k => localStorage.removeItem(k));
            console.log('🗑️ All ratings reset');
        }
        location.reload();
    },

    testToggle: (postId) => {
        const container = document.querySelector(`.like-btn[data-post="${postId}"]`)?.closest('.rating-buttons');
        if (container) {
            const likeBtn = container.querySelector('.like-btn');
            likeBtn.click();
            console.log('Test toggle executed');
        }
    }
};

console.log('✅ Ratings script loaded successfully');