// VPN Bot Panel - JavaScript функционал

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация тултипов
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Автообновление статистики
    if (document.getElementById('statsChart')) {
        setInterval(updateStats, 30000); // Обновлять каждые 30 секунд
    }

    // Обработка форм
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const submitBtn = this.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Загрузка...';
            }
        });
    });

    // Динамическое обновление контента
    initDynamicContent();
});

// Обновление статистики
async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const stats = await response.json();
        
        // Обновляем карточки статистики
        updateStatCard('total-users', stats.total_users);
        updateStatCard('active-servers', stats.active_servers);
        updateStatCard('active-subscriptions', stats.active_subscriptions);
        updateStatCard('total-revenue', stats.total_revenue.toFixed(2) + ' ₽');
        
        console.log('Статистика обновлена');
    } catch (error) {
        console.error('Ошибка обновления статистики:', error);
    }
}

// Обновление карточки статистики
function updateStatCard(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        // Анимация изменения значения
        const oldValue = parseInt(element.textContent) || 0;
        const newValue = parseInt(value) || value;
        
        if (!isNaN(oldValue) && !isNaN(newValue)) {
            animateValue(element, oldValue, newValue, 1000);
        } else {
            element.textContent = value;
        }
    }
}

// Анимация чисел
function animateValue(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        const value = Math.floor(progress * (end - start) + start);
        element.textContent = value.toLocaleString();
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

// Инициализация динамического контента
function initDynamicContent() {
    // Ленивая загрузка изображений
    const lazyImages = [].slice.call(document.querySelectorAll('img.lazy'));
    
    if ('IntersectionObserver' in window) {
        let lazyImageObserver = new IntersectionObserver(function(entries, observer) {
            entries.forEach(function(entry) {
                if (entry.isIntersecting) {
                    let lazyImage = entry.target;
                    lazyImage.src = lazyImage.dataset.src;
                    lazyImage.classList.remove('lazy');
                    lazyImageObserver.unobserve(lazyImage);
                }
            });
        });

        lazyImages.forEach(function(lazyImage) {
            lazyImageObserver.observe(lazyImage);
        });
    }

    // Обработка AJAX запросов
    document.addEventListener('click', function(e) {
        if (e.target.matches('[data-ajax]')) {
            e.preventDefault();
            handleAjaxRequest(e.target);
        }
    });
}

// Обработка AJAX запросов
async function handleAjaxRequest(element) {
    const url = element.dataset.url;
    const method = element.dataset.method || 'GET';
    
    try {
        showLoading();
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const data = await response.json();
        
        if (data.success) {
            showNotification('Успешно!', 'success');
            if (element.dataset.reload) {
                setTimeout(() => location.reload(), 1000);
            }
        } else {
            showNotification(data.error || 'Произошла ошибка', 'error');
        }
    } catch (error) {
        showNotification('Ошибка сети', 'error');
        console.error('AJAX ошибка:', error);
    } finally {
        hideLoading();
    }
}

// Показать уведомление
function showNotification(message, type = 'info') {
    const alertClass = {
        'success': 'alert-success',
        'error': 'alert-danger',
        'warning': 'alert-warning',
        'info': 'alert-info'
    }[type] || 'alert-info';

    const alertDiv = document.createElement('div');
    alertDiv.className = `alert ${alertClass} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.querySelector('.container').insertBefore(alertDiv, document.querySelector('.container').firstChild);
    
    // Автоматическое скрытие
    setTimeout(() => {
        if (alertDiv.parentElement) {
            alertDiv.remove();
        }
    }, 5000);
}

// Показать загрузку
function showLoading() {
    let loadingDiv = document.getElementById('global-loading');
    if (!loadingDiv) {
        loadingDiv = document.createElement('div');
        loadingDiv.id = 'global-loading';
        loadingDiv.className = 'position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center';
        loadingDiv.style.backgroundColor = 'rgba(0,0,0,0.5)';
        loadingDiv.style.zIndex = '9999';
        loadingDiv.innerHTML = '<div class="spinner-border text-primary" style="width: 3rem; height: 3rem;"></div>';
        document.body.appendChild(loadingDiv);
    }
}

// Скрыть загрузку
function hideLoading() {
    const loadingDiv = document.getElementById('global-loading');
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// Утилиты для работы с API
const API = {
    async get(url) {
        const response = await fetch(url);
        return response.json();
    },
    
    async post(url, data) {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });
        return response.json();
    },
    
    async delete(url) {
        const response = await fetch(url, {
            method: 'DELETE'
        });
        return response.json();
    }
};

// Экспорт для глобального использования
window.API = API;
window.showNotification = showNotification;