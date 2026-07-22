/**
 * HITECH Reminder System - Main App Logic
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initToasts();
});

function initTheme() {
    const themeToggleBtn = document.getElementById('theme-toggle');
    if (!themeToggleBtn) return;

    themeToggleBtn.addEventListener('click', () => {
        let currentTheme = document.documentElement.getAttribute('data-theme');
        let newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        // Add a class to body to enable transition only on user toggle, preventing load flash
        document.body.classList.add('theme-transitioning');
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Remove class after transition
        setTimeout(() => {
            document.body.classList.remove('theme-transitioning');
            // Re-render charts with new theme colors if they exist
            if (typeof initCharts === 'function') {
                initCharts();
            }
        }, 300);
    });
}

function initSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    const closeBtn = document.getElementById('sidebar-close');
    const overlay = document.getElementById('sidebar-overlay');
    
    if (!sidebar || !toggleBtn) return;

    function openSidebar() {
        sidebar.classList.add('open');
        if (overlay) overlay.classList.add('show');
    }

    function closeSidebar() {
        sidebar.classList.remove('open');
        if (overlay) overlay.classList.remove('show');
    }

    toggleBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (overlay) overlay.addEventListener('click', closeSidebar);
}

function initToasts() {
    // Automatically fade out success/notice alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.error)');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade-out');
            setTimeout(() => alert.remove(), 300); // Wait for transition
        }, 5000);
    });
}

/* ==========================================================================
   Dashboard Widgets
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initToasts();
    
    // Dashboard Logic
    initCounters();
    initSchedulerMonitor();
    initMockLogs();
    
    if (typeof Chart !== 'undefined') {
        initCharts();
    }

    // Users Logic
    initUsersTable();

    // Activities Logic
    initActivitiesTable();
});

function initCounters() {
    const counters = document.querySelectorAll('.counter');
    if (!counters.length) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const el = entry.target;
                const target = parseInt(el.getAttribute('data-target'), 10) || 0;
                animateValue(el, 0, target, 1500);
                observer.unobserve(el);
            }
        });
    }, { threshold: 0.1 });

    counters.forEach(counter => observer.observe(counter));
}

function animateValue(obj, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        // easeOutQuart
        const ease = 1 - Math.pow(1 - progress, 4);
        obj.innerHTML = Math.floor(ease * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        } else {
            obj.innerHTML = end;
        }
    };
    window.requestAnimationFrame(step);
}

function initSchedulerMonitor() {
    const widget = document.querySelector('.scheduler-widget');
    if (!widget) return;
    
    const targetStr = widget.getAttribute('data-next-run');
    if (!targetStr) return;
    
    const targetDate = new Date(targetStr).getTime();
    const countdownEl = document.getElementById('scheduler-countdown');
    
    function updateCountdown() {
        const now = new Date().getTime();
        const distance = targetDate - now;
        
        if (distance < 0) {
            countdownEl.innerHTML = "00:00:00";
            return;
        }
        
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        
        countdownEl.innerHTML = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
    }
    
    updateCountdown();
    setInterval(updateCountdown, 1000); // Tick every second for real-time feel
}

function initMockLogs() {
    const feed = document.getElementById('email-log-feed');
    const skeleton = document.getElementById('log-skeleton');
    if (!feed || !skeleton) return;
    
    // Simulate real-time network fetch
    setTimeout(() => {
        skeleton.style.display = 'none';
        feed.style.display = 'flex';
        
        const now = new Date();
        const mocks = [
            { offset: 12, email: 'sneha.manager@example.com', success: true, activity: 'Monthly Review Reminder' },
            { offset: 45, email: 'system.admin@example.com', success: true, activity: 'Database Backup Alert' },
            { offset: 120, email: 'legacy.test@example.com', success: false, activity: 'Tax Filing Reminder', reason: 'SMTP Connection Timeout' }
        ];
        
        mocks.forEach(m => {
            const logTime = new Date(now.getTime() - m.offset * 60000);
            const hh = String(logTime.getHours()).padStart(2, '0');
            const mm = String(logTime.getMinutes()).padStart(2, '0');
            const ss = String(logTime.getSeconds()).padStart(2, '0');
            
            const card = document.createElement('div');
            card.className = `log-card ${m.success ? 'success' : 'error'} mock-data`;
            
            let html = `
              <div class="log-header">
                <span class="status-badge ${m.success ? 'success' : 'error'}">${m.success ? 'Success' : 'Failed'}</span>
                <span class="log-time">${hh}:${mm}:${ss}</span>
              </div>
              <div class="log-body">
                Sent to <strong>${m.email}</strong> for <em>${m.activity}</em>
              </div>
            `;
            
            if (!m.success && m.reason) {
                html += `<div class="log-reason">${m.reason}</div>`;
            }
            
            card.innerHTML = html;
            feed.appendChild(card);
        });
    }, 800); // 800ms loading skeleton phase
}

window.chartInstances = window.chartInstances || [];

function initCharts() {
    // Destroy existing instances if re-rendering
    window.chartInstances.forEach(chart => chart.destroy());
    window.chartInstances = [];

    const style = getComputedStyle(document.body);
    const primary = style.getPropertyValue('--primary').trim();
    const primaryLight = style.getPropertyValue('--primary-light').trim() || 'rgba(15, 124, 112, 0.2)';
    const success = style.getPropertyValue('--success').trim();
    const danger = style.getPropertyValue('--danger').trim();
    const textMain = style.getPropertyValue('--text-main').trim();
    const border = style.getPropertyValue('--border-color').trim();

    Chart.defaults.color = textMain;
    Chart.defaults.font.family = 'Inter, sans-serif';

    // Emails Per Month Chart (Mock Data)
    const ctxMonth = document.getElementById('chart-emails-month');
    if (ctxMonth) {
        window.chartInstances.push(new Chart(ctxMonth, {
            type: 'line',
            data: {
                labels: ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul'],
                datasets: [{
                    label: 'Emails Sent',
                    data: [150, 230, 180, 320, 290, 410],
                    borderColor: primary,
                    backgroundColor: primaryLight,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: border }
                    },
                    x: {
                        grid: { display: false }
                    }
                }
            }
        }));
    }

    // Success vs Failure Chart (Mock Data)
    const ctxSuccess = document.getElementById('chart-success-rate');
    if (ctxSuccess) {
        window.chartInstances.push(new Chart(ctxSuccess, {
            type: 'doughnut',
            data: {
                labels: ['Delivered', 'Failed'],
                datasets: [{
                    data: [98.5, 1.5],
                    backgroundColor: [success, danger],
                    borderWidth: 0,
                    hoverOffset: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '75%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { padding: 20 }
                    }
                }
            }
        }));
    }
}

/* ==========================================================================
   Users Management
   ========================================================================== */

function initUsersTable() {
    const searchInput = document.getElementById('user-search');
    const roleFilter = document.getElementById('user-role-filter');
    const table = document.getElementById('users-table');
    const emptyState = document.getElementById('users-empty-state');
    const clearBtn = document.getElementById('clear-filters-btn');

    if (!table || !searchInput || !roleFilter) return;

    const rows = Array.from(table.querySelectorAll('tbody .user-row'));

    function filterRows() {
        const query = searchInput.value.toLowerCase().trim();
        const role = roleFilter.value;
        let visibleCount = 0;

        rows.forEach(row => {
            const rowSearch = row.getAttribute('data-search') || '';
            const rowRole = row.getAttribute('data-role') || '';
            
            const matchesSearch = query === '' || rowSearch.includes(query);
            const matchesRole = role === 'all' || rowRole === role;
            
            if (matchesSearch && matchesRole) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        // Toggle empty state
        if (visibleCount === 0) {
            table.style.display = 'none';
            if (emptyState) emptyState.style.display = 'flex';
        } else {
            table.style.display = '';
            if (emptyState) emptyState.style.display = 'none';
        }
    }

    searchInput.addEventListener('keyup', filterRows);
    roleFilter.addEventListener('change', filterRows);
    
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            roleFilter.value = 'all';
            filterRows();
        });
    }
}

/* ==========================================================================
   Activities Management
   ========================================================================== */

function initActivitiesTable() {
    const searchInput = document.getElementById('activity-search');
    const freqFilter = document.getElementById('activity-freq-filter');
    const table = document.getElementById('activities-table');
    const emptyState = document.getElementById('activities-empty-state');
    const clearBtn = document.getElementById('clear-act-filters-btn');

    if (!table || !searchInput || !freqFilter) return;

    const rows = Array.from(table.querySelectorAll('tbody .activity-row'));

    function filterRows() {
        const query = searchInput.value.toLowerCase().trim();
        const freq = freqFilter.value;
        let visibleCount = 0;

        rows.forEach(row => {
            const rowSearch = row.getAttribute('data-search') || '';
            const rowFreq = row.getAttribute('data-freq') || '';
            
            const matchesSearch = query === '' || rowSearch.includes(query);
            const matchesFreq = freq === 'all' || rowFreq === freq;
            
            if (matchesSearch && matchesFreq) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        if (visibleCount === 0) {
            table.style.display = 'none';
            if (emptyState) emptyState.style.display = 'flex';
        } else {
            table.style.display = '';
            if (emptyState) emptyState.style.display = 'none';
        }
    }

    searchInput.addEventListener('keyup', filterRows);
    freqFilter.addEventListener('change', filterRows);
    
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            freqFilter.value = 'all';
            filterRows();
        });
    }
}
