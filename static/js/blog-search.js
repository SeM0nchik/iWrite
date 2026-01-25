// static/js/blog-search.js

class BlogSearch {
    constructor(searchInputSelector, resultsContainerSelector, searchUrl) {
        this.searchInput = document.querySelector(searchInputSelector);
        this.resultsContainer = document.querySelector(resultsContainerSelector);
        this.searchUrl = searchUrl;
        this.isLoading = false;
        this.debounceTimer = null;

        this.init();
    }

    init() {
        // Обработчик ввода с debounce
        this.searchInput.addEventListener('input', () => {
            this.debounce(this.handleSearch.bind(this), 250)();
        });

        // Скрытие результатов при клике вне
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) &&
                !this.resultsContainer.contains(e.target)) {
                this.hideResults();
            }
        });

        // Предотвращаем отправку формы при Enter
        const form = this.searchInput.closest('form');
        if (form) {
            form.addEventListener('submit', (e) => {
                // Позволяем обычный поиск по Enter
                return true;
            });
        }
    }

    debounce(func, wait) {
        return () => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => func.call(this), wait);
        };
    }

    async handleSearch() {
        const query = this.searchInput.value.trim();

        if (query.length < 2) {
            this.hideResults();
            return;
        }

        if (this.isLoading) return;

        this.isLoading = true;
        this.showLoading();

        try {
            const response = await fetch(`${this.searchUrl}?query=${encodeURIComponent(query)}`, {
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });

            if (!response.ok) {
                throw new Error('Network error');
            }

            const data = await response.json();
            this.displayResults(data.results);

        } catch (error) {
            console.error('Search error:', error);
            this.showError();
        } finally {
            this.isLoading = false;
        }
    }

    displayResults(results) {
        if (results.length === 0) {
            this.resultsContainer.innerHTML = `
                <div class="search-result-item empty-result">
                    <i class="bi bi-search"></i>
                    <span>Ничего не найдено по запросу "${this.searchInput.value}"</span>
                </div>
            `;
        } else {
            this.resultsContainer.innerHTML = results.map(result => `
                <a href="${result.url}" class="search-result-item" data-result-id="${result.id}">
                    <div class="result-header">
                        <h5 class="result-title">${this.escapeHtml(result.title)}</h5>
                        <span class="relevance-score">${(result.rank * 100).toFixed(1)}%</span>
                    </div>
                    <p class="result-preview">${this.escapeHtml(result.headline)}</p>
                </a>
            `).join('');
        }

        this.showResults();
    }

    showLoading() {
        this.resultsContainer.innerHTML = `
            <div class="search-loading">
                <div class="spinner-border spinner-border-sm" role="status">
                    <span class="visually-hidden">Загрузка...</span>
                </div>
                <span>Поиск...</span>
            </div>
        `;
        this.showResults();
    }

    showError() {
        this.resultsContainer.innerHTML = `
            <div class="search-result-item error">
                <i class="bi bi-exclamation-triangle"></i>
                <span>Ошибка поиска. Попробуйте позже.</span>
            </div>
        `;
        this.showResults();
    }

    showResults() {
        this.resultsContainer.classList.add('show');
        document.body.classList.add('search-open');
    }

    hideResults() {
        this.resultsContainer.classList.remove('show');
        document.body.classList.remove('search-open');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// Инициализация при загрузке DOM
document.addEventListener('DOMContentLoaded', function() {
    // Подключаем к вашей поисковой форме
    new BlogSearch(
        'input[name="query"]',           // селектор input
        '#searchDropdownResults',       // селектор контейнера результатов
        "{% url 'search' %}"            // URL вашего search view
    );
});
