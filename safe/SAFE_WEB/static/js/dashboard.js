// Dashboard Live Update Script with Advanced Features
(function() {
    'use strict';
    
    // Global data storage
    let allData = [];
    let filteredData = [];
    let tempChart = null;
    let recentStatusPie = null;
    let currentPage = 1;
    const itemsPerPage = 10;
    
    // Filter state
    let currentFilter = 'all'; // 'all', 'normal', 'anomaly'
    let currentSort = 'newest'; // 'newest', 'oldest', 'temp_high', 'temp_low'
    let searchQuery = '';
    let chartDataLimit = 30; // Default 30 data untuk line chart
    
    // Initialize charts on page load
    function initCharts() {
        // Read initial data from server
        const getJsonData = (id) => {
            const elem = document.getElementById(id);
            if (!elem) return null;
            try {
                return JSON.parse(elem.textContent || '[]');
            } catch(e) {
                console.error('Parse error for', id, e);
                return [];
            }
        };
        
        const labels = getJsonData('chart_labels_json') || [];
        const temps = getJsonData('chart_temps_json') || [];
        const humids = getJsonData('chart_humids_json') || [];
        
        // Temperature & Humidity Line Chart
        const ctx = document.getElementById('tempHumidityChart');
        if (ctx) {
            tempChart = new Chart(ctx.getContext('2d'), {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [
                        { 
                            label: 'Suhu (°C)', 
                            data: temps, 
                            borderColor: '#f72585', 
                            backgroundColor: 'rgba(247,37,133,0.08)', 
                            tension: 0.25 
                        },
                        { 
                            label: 'Kelembaban (%)', 
                            data: humids, 
                            borderColor: '#4895ef', 
                            backgroundColor: 'rgba(72,149,239,0.08)', 
                            tension: 0.25 
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: { y: { beginAtZero: true } }
                }
            });
        }
        
        // Pie Chart for Status Distribution
        const ctxPie = document.getElementById('recentStatusPie');
        if (ctxPie) {
            const anomalyCount = getJsonData('anomaly_count_json') || 0;
            const normalCount = getJsonData('normal_count_json') || 0;
            
            recentStatusPie = new Chart(ctxPie.getContext('2d'), {
                type: 'doughnut',
                data: { 
                    labels: ['Normal','Anomali'], 
                    datasets: [{ 
                        data: [normalCount, anomalyCount], 
                        backgroundColor: ['#38b000','#f72585'] 
                    }] 
                },
                options: { 
                    responsive: true, 
                    maintainAspectRatio: false 
                }
            });
        }
    }
    
    // Apply filters and sorting
    function applyFiltersAndSort() {
        // Start with all data
        let data = allData.slice();
        
        // Apply filter
        if (currentFilter === 'normal') {
            data = data.filter(r => !r.is_anomaly);
        } else if (currentFilter === 'anomaly') {
            data = data.filter(r => r.is_anomaly);
        }
        
        // Apply search
        if (searchQuery) {
            const query = searchQuery.toLowerCase();
            data = data.filter(r => {
                return (r.device_id && r.device_id.toLowerCase().includes(query)) ||
                       (r.temperature && r.temperature.toString().includes(query)) ||
                       (r.humidity && r.humidity.toString().includes(query));
            });
        }
        
        // Apply sorting
        if (currentSort === 'newest') {
            data.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        } else if (currentSort === 'oldest') {
            data.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp));
        } else if (currentSort === 'temp_high') {
            data.sort((a, b) => parseFloat(b.temperature) - parseFloat(a.temperature));
        } else if (currentSort === 'temp_low') {
            data.sort((a, b) => parseFloat(a.temperature) - parseFloat(b.temperature));
        }
        
        filteredData = data;
        currentPage = 1; // Reset to first page
        renderTable();
        renderPagination();
    }
    
    // Render table with pagination
    function renderTable() {
        const tbody = document.getElementById('sensor-rows');
        if (!tbody) return;
        
        if (filteredData.length === 0) {
            tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;padding:40px;color:#999;">Tidak ada data yang sesuai dengan filter</td></tr>';
            return;
        }
        
        // Calculate pagination
        const startIdx = (currentPage - 1) * itemsPerPage;
        const endIdx = startIdx + itemsPerPage;
        const pageData = filteredData.slice(startIdx, endIdx);
        
        const locationName = document.querySelector('.header-content h1');
        const locName = locationName ? locationName.textContent.replace('Dashboard Sensor - ', '').trim() : '';
        
        tbody.innerHTML = pageData.map((r, idx) => {
            const isAnomaly = r.is_anomaly || false;
            const rowClass = isAnomaly ? 'anomaly-row' : '';
            const statusHtml = isAnomaly 
                ? '<span class="status-anomaly">⚠️ ANOMALI</span>' 
                : '<span class="status-normal">✅ NORMAL</span>';
            
            const dt = new Date(r.timestamp);
            const dateStr = dt.toLocaleDateString('id-ID') + ' ' + dt.toLocaleTimeString('id-ID');
            const globalIdx = startIdx + idx + 1;
            
            return '<tr class="' + rowClass + '">' +
                '<td>' + globalIdx + '</td>' +
                '<td>' + dateStr + '</td>' +
                '<td>' + (r.device_id || '-') + '</td>' +
                '<td>' + r.temperature + '</td>' +
                '<td>' + r.humidity + '</td>' +
                '<td>' + locName + '</td>' +
                '<td>' + statusHtml + '</td>' +
                '</tr>';
        }).join('');
    }
    
    // Render pagination controls
    function renderPagination() {
        const totalPages = Math.ceil(filteredData.length / itemsPerPage);
        const paginationDiv = document.getElementById('pagination-controls');
        
        if (!paginationDiv || totalPages <= 1) {
            if (paginationDiv) paginationDiv.innerHTML = '';
            return;
        }
        
        let html = '<div style="display:flex;justify-content:center;align-items:center;gap:10px;margin-top:20px;">';
        html += '<span style="color:#666;font-size:14px;">Halaman ' + currentPage + ' dari ' + totalPages + '</span>';
        
        // Previous button
        if (currentPage > 1) {
            html += '<button class="pagination-btn" data-page="' + (currentPage - 1) + '" style="padding:8px 16px;border:1px solid #4361ee;background:#fff;color:#4361ee;border-radius:6px;cursor:pointer;">← Sebelumnya</button>';
        }
        
        // Page numbers (show max 5)
        const startPage = Math.max(1, currentPage - 2);
        const endPage = Math.min(totalPages, startPage + 4);
        
        for (let i = startPage; i <= endPage; i++) {
            const activeStyle = i === currentPage ? 'background:#4361ee;color:#fff;' : 'background:#fff;color:#4361ee;';
            html += '<button class="pagination-btn" data-page="' + i + '" style="padding:8px 12px;border:1px solid #4361ee;' + activeStyle + 'border-radius:6px;cursor:pointer;min-width:40px;">' + i + '</button>';
        }
        
        // Next button
        if (currentPage < totalPages) {
            html += '<button class="pagination-btn" data-page="' + (currentPage + 1) + '" style="padding:8px 16px;border:1px solid #4361ee;background:#fff;color:#4361ee;border-radius:6px;cursor:pointer;">Berikutnya →</button>';
        }
        
        html += '</div>';
        paginationDiv.innerHTML = html;
        
        // Add click handlers
        document.querySelectorAll('.pagination-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                currentPage = parseInt(this.dataset.page);
                renderTable();
                renderPagination();
            });
        });
    }
    
    // Update table with new data
    function updateTable(rows, locationName) {
        if (!rows || rows.length === 0) return;
        allData = rows;
        applyFiltersAndSort();
    }
    
    // Update charts with new data
    function updateCharts(rows, totalNormal, totalAnomalies) {
        if (!rows || rows.length === 0) {
            rows = allData;
        }
        if (rows.length === 0) return;
        
        // PERBAIKAN: Gunakan chartDataLimit (dinamis sesuai dropdown)
        const lastN_newest = rows.slice(0, chartDataLimit);
        
        // Untuk chart line (perlu dibalik agar kronologis dari kiri ke kanan)
        const lastN_chrono = lastN_newest.slice().reverse();
        
        const chartLabels = lastN_chrono.map(r => new Date(r.timestamp).toLocaleTimeString('id-ID'));
        const chartTemps = lastN_chrono.map(r => parseFloat(r.temperature) || 0);
        const chartHums = lastN_chrono.map(r => parseFloat(r.humidity) || 0);
        
        // Update line chart
        if (tempChart) {
            tempChart.data.labels = chartLabels;
            tempChart.data.datasets[0].data = chartTemps;
            tempChart.data.datasets[1].data = chartHums;
            tempChart.update('none'); // No animation for live updates
        }
        
        // PERBAIKAN: Gunakan total dari API (SEMUA data, bukan hanya 50)
        // Jika tidak ada parameter, hitung dari rows
        const anomalies = totalAnomalies !== undefined ? totalAnomalies : rows.filter(r => r.is_anomaly).length;
        const normal = totalNormal !== undefined ? totalNormal : rows.filter(r => !r.is_anomaly).length;
        
        // Update pie chart dengan SEMUA data
        if (recentStatusPie) {
            recentStatusPie.data.datasets[0].data = [normal, anomalies];
            recentStatusPie.update('none');
        }
        
        // Update stat cards dengan SEMUA data (bukan 50)
        const totalCard = document.querySelector('.stat-card.total .stat-value');
        const normalCard = document.querySelector('.stat-card.normal .stat-value');
        const anomalyCard = document.querySelector('.stat-card.anomaly .stat-value');
        
        if (totalCard) totalCard.textContent = normal + anomalies;
        if (normalCard) normalCard.textContent = normal;
        if (anomalyCard) anomalyCard.textContent = anomalies;
    }
    
    // Fetch data from server
    async function fetchData(locationId, locationName) {
        try {
            const url = '/location/' + locationId + '/data.json';
            const response = await fetch(url);
            
            if (!response.ok) {
                console.warn('Fetch failed:', response.status);
                return;
            }
            
            const payload = await response.json();
            const rows = payload.data || [];
            
            if (rows.length > 0) {
                updateTable(rows, locationName);
                // Pass total counts dari API (menghitung SEMUA data di database)
                updateCharts(rows, payload.total_normal_count, payload.total_anomaly_count);
            }
            
        } catch (error) {
            console.error('Fetch error:', error);
        }
    }
    
    // Export to CSV function
    function exportToCSV() {
        if (filteredData.length === 0) {
            alert('Tidak ada data untuk diekspor!');
            return;
        }
        
        const locationName = document.querySelector('.header-content h1');
        const locName = locationName ? locationName.textContent.replace('Dashboard Sensor - ', '').trim() : 'Unknown';
        
        let csvContent = 'No,Waktu,Device ID,Suhu (°C),Kelembaban (%),Lokasi,Status\n';
        
        filteredData.forEach((r, idx) => {
            const dt = new Date(r.timestamp);
            const dateStr = dt.toLocaleDateString('id-ID') + ' ' + dt.toLocaleTimeString('id-ID');
            const status = r.is_anomaly ? 'ANOMALI' : 'NORMAL';
            
            csvContent += (idx + 1) + ',"' + dateStr + '","' + (r.device_id || '-') + '",' + 
                          r.temperature + ',' + r.humidity + ',"' + locName + '","' + status + '"\n';
        });
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const link = document.createElement('a');
        const fileName = 'sensor_data_' + locName + '_' + new Date().toISOString().split('T')[0] + '.csv';
        
        link.setAttribute('href', url);
        link.setAttribute('download', fileName);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        setTimeout(() => URL.revokeObjectURL(url), 100);
        console.log('CSV exported:', fileName);
    }
    
    // Initialize everything when page loads
    window.addEventListener('DOMContentLoaded', function() {
        console.log('Dashboard initializing...');
        
        // Get location info from page
        const getJsonValue = (id) => {
            const elem = document.getElementById(id);
            if (!elem) return null;
            try {
                return JSON.parse(elem.textContent || 'null');
            } catch(e) {
                return null;
            }
        };
        
        const locationId = getJsonValue('current_location_id_json');
        const locationNameElem = document.querySelector('.header-content h1');
        const locationName = locationNameElem ? locationNameElem.textContent.replace('Dashboard Sensor - ', '').trim() : 'Unknown';
        
        if (!locationId) {
            console.error('Location ID not found');
            return;
        }
        
        // Initialize charts
        initCharts();
        
        // Setup filter buttons
        const filterButtons = document.querySelectorAll('.filter-section .filter-btn');
        filterButtons.forEach(btn => {
            btn.addEventListener('click', function() {
                if (this.tagName === 'BUTTON') {
                    const text = this.textContent.trim();
                    
                    // Remove active from all buttons
                    filterButtons.forEach(b => {
                        if (b.tagName === 'BUTTON') b.classList.remove('active');
                    });
                    
                    // Add active to clicked button
                    this.classList.add('active');
                    
                    // Set filter
                    if (text === 'Semua Data') {
                        currentFilter = 'all';
                    } else if (text === 'Normal') {
                        currentFilter = 'normal';
                    } else if (text === 'Anomali') {
                        currentFilter = 'anomaly';
                    }
                    
                    applyFiltersAndSort();
                }
            });
        });
        
        // Setup sort dropdown
        const sortSelect = document.getElementById('deviceSelect');
        if (sortSelect) {
            sortSelect.addEventListener('change', function() {
                const value = this.value;
                if (value === 'Urutkan Terbaru') currentSort = 'newest';
                else if (value === 'Urutkan Terlama') currentSort = 'oldest';
                else if (value === 'Suhu Tertinggi') currentSort = 'temp_high';
                else if (value === 'Suhu Terendah') currentSort = 'temp_low';
                
                applyFiltersAndSort();
            });
        }
        
        // Setup search
        const searchBox = document.querySelector('.search-box');
        const searchBtn = document.querySelector('.search-section .filter-btn');
        
        if (searchBox && searchBtn) {
            searchBtn.addEventListener('click', function() {
                searchQuery = searchBox.value.trim();
                applyFiltersAndSort();
            });
            
            searchBox.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    searchQuery = this.value.trim();
                    applyFiltersAndSort();
                }
            });
        }
        
        // Setup export CSV button
        const exportBtn = document.getElementById('exportCsvBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', exportToCSV);
        }
        
        // Setup chart data limit dropdown
        const chartLimitSelect = document.getElementById('chartDataLimit');
        if (chartLimitSelect) {
            chartLimitSelect.addEventListener('change', function() {
                chartDataLimit = parseInt(this.value);
                console.log('Chart limit changed to:', chartDataLimit);
                // Re-render chart dengan data limit baru
                updateCharts(allData);
            });
        }
        
        // Start polling after 3 seconds
        setTimeout(function() {
            console.log('Starting live updates for location', locationId);
            
            // First fetch
            fetchData(locationId, locationName);
            
            // Then poll every 5 seconds
            setInterval(function() {
                fetchData(locationId, locationName);
            }, 5000);
        }, 3000);
    });
})();
