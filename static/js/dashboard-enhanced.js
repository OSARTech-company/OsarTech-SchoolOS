/**
 * Enhanced Dashboard - Visual Enhancements & Charts
 * Includes Chart.js integration and interactive elements
 **/

// Load Chart.js library
const chartScriptId = 'chart-js-library';
if (!document.getElementById(chartScriptId)) {
    const script = document.createElement('script');
    script.id = chartScriptId;
    script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.js';
    document.head.appendChild(script);
}

// Chart color schemes
const chartColors = {
    primary: 'rgba(15, 76, 129, 0.8)',
    primaryLight: 'rgba(15, 76, 129, 0.2)',
    secondary: 'rgba(31, 122, 140, 0.8)',
    secondaryLight: 'rgba(31, 122, 140, 0.2)',
    success: 'rgba(16, 185, 129, 0.8)',
    successLight: 'rgba(16, 185, 129, 0.2)',
    warning: 'rgba(245, 158, 11, 0.8)',
    warningLight: 'rgba(245, 158, 11, 0.2)',
    danger: 'rgba(239, 68, 68, 0.8)',
    dangerLight: 'rgba(239, 68, 68, 0.2)',
};

/**
 * Create a line chart for trends
 **/
function createTrendChart(canvasId, labels, data, label = 'Trend') {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return null;

    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: label,
                data: data,
                borderColor: chartColors.primary,
                backgroundColor: chartColors.primaryLight,
                borderWidth: 2,
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: chartColors.primary,
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointHoverRadius: 6,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: { usePointStyle: true, font: { size: 12 } }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

/**
 * Create a bar chart for comparisons
 **/
function createBarChart(canvasId, labels, datasets, chartLabel = 'Comparison') {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return null;

    const colors = [chartColors.primary, chartColors.secondary, chartColors.success];
    const formattedDatasets = datasets.map((dataset, idx) => ({
        label: dataset.label,
        data: dataset.data,
        backgroundColor: colors[idx % colors.length],
    }));

    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: formattedDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'x',
            plugins: {
                legend: {
                    display: true,
                    labels: { usePointStyle: true, font: { size: 12 } }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' }
                },
                x: {
                    grid: { display: false }
                }
            }
        }
    });
}

/**
 * Create a pie/doughnut chart for distribution
 **/
function createDistributionChart(canvasId, labels, data, chartType = 'doughnut') {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return null;

    const colors = [
        chartColors.primary,
        chartColors.secondary,
        chartColors.success,
        chartColors.warning,
        chartColors.danger,
    ];

    return new Chart(ctx, {
        type: chartType,
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, data.length),
                borderColor: '#fff',
                borderWidth: 2,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { usePointStyle: true, font: { size: 12 }, padding: 15 }
                }
            }
        }
    });
}

/**
 * Create a radial/radar chart for multiple metrics
 **/
function createRadarChart(canvasId, labels, datasets) {
    const ctx = document.getElementById(canvasId);
    if (!ctx || !window.Chart) return null;

    const colors = [chartColors.primary, chartColors.secondary, chartColors.success];
    const formattedDatasets = datasets.map((dataset, idx) => ({
        label: dataset.label,
        data: dataset.data,
        borderColor: colors[idx % colors.length],
        backgroundColor: colors[idx % colors.length],
        borderWidth: 2,
        fill: true,
        tension: 0.4,
    }));

    return new Chart(ctx, {
        type: 'radar',
        data: {
            labels: labels,
            datasets: formattedDatasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    labels: { usePointStyle: true, font: { size: 11 } }
                }
            },
            scales: {
                r: {
                    beginAtZero: true,
                    grid: { color: 'rgba(0,0,0,0.05)' }
                }
            }
        }
    });
}

/**
 * Animate progress bars
 **/
function animateProgressBars() {
    const progressFills = document.querySelectorAll('.progress-fill');
    progressFills.forEach(fill => {
        const targetWidth = fill.getAttribute('data-width') || fill.style.width;
        fill.style.width = '0%';
        setTimeout(() => {
            fill.style.transition = 'width 1s ease';
            fill.style.width = targetWidth;
        }, 100);
    });
}

/**
 * Animate counters
 **/
function animateCounters() {
    const counters = document.querySelectorAll('[data-count]');
    counters.forEach(counter => {
        const target = parseInt(counter.getAttribute('data-count'));
        const duration = 1000;
        const startTime = Date.now();
        
        function updateCount() {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const current = Math.floor(target * progress);
            counter.textContent = current.toLocaleString();
            
            if (progress < 1) {
                requestAnimationFrame(updateCount);
            }
        }
        
        updateCount();
    });
}

/**
 * Initialize all enhancements
 **/
function initDashboardEnhancements() {
    // Animate progress bars when page loads
    window.addEventListener('load', () => {
        animateProgressBars();
        animateCounters();
    });

    // Add hover effects to stat cards
    document.querySelectorAll('.stat-card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transition = 'transform 0.3s ease';
        });
    });

    // Toggle functionality
    document.querySelectorAll('.toggle-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.toggle-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

/**
 * Export dashboard data as CSV
 **/
function exportDashboardDataAsCSV(filename = 'dashboard-data.csv') {
    const table = document.querySelector('.enhanced-table');
    if (!table) {
        alert('No table found to export');
        return;
    }

    let csv = [];
    table.querySelectorAll('tr').forEach(row => {
        const cols = row.querySelectorAll('td, th');
        const rowData = Array.from(cols).map(col => `"${col.innerText.trim()}"`).join(',');
        csv.push(rowData);
    });

    const csvContent = 'data:text/csv;charset=utf-8,' + csv.join('\n');
    const link = document.createElement('a');
    link.href = encodeURI(csvContent);
    link.download = filename;
    link.click();
}

/**
 * Print dashboard section
 **/
function printDashboardSection(sectionId) {
    const section = document.getElementById(sectionId);
    if (!section) {
        alert('Section not found');
        return;
    }

    const printWindow = window.open('', '', 'width=800,height=600');
    printWindow.document.write('<html><head><title>Dashboard Report</title>');
    printWindow.document.write('<link rel="stylesheet" href="/static/css/dashboard-enhanced.css">');
    printWindow.document.write('<style>body { font-family: Arial; margin: 20px; }</style>');
    printWindow.document.write('</head><body>');
    printWindow.document.write(section.outerHTML);
    printWindow.document.write('</body></html>');
    printWindow.document.close();
    printWindow.print();
}

/**
 * Create a metric card dynamically
 **/
function createMetricCard(title, value, icon = 'fa-chart-line', color = 'primary') {
    const card = document.createElement('div');
    card.className = `stat-card ${color}`;
    card.innerHTML = `
        <div class="stat-icon"><i class="fas ${icon}"></i></div>
        <h3 data-count="${value}">${value}</h3>
        <p>${title}</p>
    `;
    return card;
}

/**
 * Refresh dashboard data (auto-update)
 **/
function autoRefreshDashboard(interval = 300000) {
    setInterval(() => {
        // This can be connected to an API endpoint for live updates
        console.log('Dashboard auto-refresh triggered');
        // location.reload(); // Uncomment to auto-reload page
    }, interval);
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', initDashboardEnhancements);

// Export functions for global access
window.Dashboard = {
    createTrendChart,
    createBarChart,
    createDistributionChart,
    createRadarChart,
    animateProgressBars,
    animateCounters,
    exportDashboardDataAsCSV,
    printDashboardSection,
    createMetricCard,
    autoRefreshDashboard
};
