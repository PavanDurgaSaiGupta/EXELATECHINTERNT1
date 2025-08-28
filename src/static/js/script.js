document.addEventListener('DOMContentLoaded', () => {
    const timeframeButtons = document.querySelectorAll('.timeframe-selector button');
    const exportCsvBtn = document.getElementById('export-csv-btn');
    const mockDataSwitch = document.getElementById('mock-data-switch');
    const realDataSubtitle = document.getElementById('real-data-subtitle');
    const toast = document.getElementById('toast');
    let spendingTrendChart, resourceDistributionChart;

    // --- Chart Configuration ---
    const chartConfigs = {
        spendingTrend: {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Daily Spending',
                    data: [],
                    borderColor: '#00aaff',
                    backgroundColor: 'rgba(0, 170, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        },
        resourceDistribution: {
            type: 'doughnut',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: ['#3b82f6', '#f97316', '#a855f7']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    }
                }
            }
        }
    };

    // --- Fetch and Update Dashboard ---
    async function updateDashboard(timeframe, useMockData) {
        // Show/hide subtitle based on the toggle state
        realDataSubtitle.style.display = useMockData ? 'none' : 'block';

        try {
            const response = await fetch(`/api/cost-data?timeframe=${timeframe}&use_mock_data=${useMockData}`);
            const data = await response.json();

            if (response.ok) {
                updateUI(data, timeframe);
            } else {
                // If real data fails (e.g., missing credentials), show a toast and zero out the dashboard.
                if (!useMockData) {
                    showToast(data.error || '⚠️ Real data unavailable. Check credentials.');
                    clearDashboard(); // Zero out metrics and charts
                    realDataSubtitle.style.display = 'none'; // Hide subtitle as we have no real data
                } else {
                    // This case handles errors in mock data generation itself.
                    showToast('Error fetching mock data.');
                    clearDashboard();
                }
            }
        } catch (error) {
            console.error('Error fetching dashboard data:', error);
            showToast('An unexpected error occurred.');
            clearDashboard();
        }
    }

    function updateUI(data, timeframe) {
        // Update metrics
        document.getElementById('total-cost').textContent = `$${data.total_cost.toFixed(2)}`;
        document.getElementById('avg-daily-cost').textContent = `$${data.average_daily_cost.toFixed(2)}`;
        document.getElementById('forecasted-cost').textContent = `$${data.forecasted_monthly_cost.toFixed(2)}`;

        // Update charts
        document.getElementById('spending-trend-title').textContent = data.spending_trend.title;
        updateSpendingTrendChart(data.spending_trend.labels, data.spending_trend.data, timeframe);

        document.getElementById('resource-distribution-title').textContent = data.resource_distribution.title;
        updateResourceDistributionChart(data.resource_distribution.labels, data.resource_distribution.data);

        // Update export link
        exportCsvBtn.href = `/export-csv?timeframe=${timeframe}`;
    }

    function showToast(message) {
        toast.textContent = message;
        toast.className = "show";
        setTimeout(() => { toast.className = toast.className.replace("show", ""); }, 3000);
    }

    function clearDashboard() {
        document.getElementById('total-cost').textContent = '$0.00';
        document.getElementById('avg-daily-cost').textContent = '$0.00';
        document.getElementById('forecasted-cost').textContent = '$0.00';
        document.getElementById('spending-trend-title').textContent = "Spending Trend";
        updateSpendingTrendChart([], [], 'daily');
        document.getElementById('resource-distribution-title').textContent = "Cost Distribution";
        updateResourceDistributionChart([], []);
    }

    // --- Chart Update Functions ---
    function updateSpendingTrendChart(labels, data, timeframe) {
        if (!spendingTrendChart) {
            const ctx = document.getElementById('spending-trend-chart').getContext('2d');
            spendingTrendChart = new Chart(ctx, chartConfigs.spendingTrend);
        }
        spendingTrendChart.data.labels = labels;
        spendingTrendChart.data.datasets[0].data = data;
        spendingTrendChart.data.datasets[0].label = `${timeframe.charAt(0).toUpperCase() + timeframe.slice(1)} Spending`;
        spendingTrendChart.update();
    }

    function updateResourceDistributionChart(labels, data) {
        if (!resourceDistributionChart) {
            const ctx = document.getElementById('resource-distribution-chart').getContext('2d');
            resourceDistributionChart = new Chart(ctx, chartConfigs.resourceDistribution);
        }
        resourceDistributionChart.data.labels = labels;
        resourceDistributionChart.data.datasets[0].data = data;
        resourceDistributionChart.update();
    }

    // --- Event Listeners ---
    timeframeButtons.forEach(button => {
        button.addEventListener('click', () => {
            timeframeButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            const timeframe = button.id.replace('-btn', '');
            const useMockData = mockDataSwitch.checked;
            updateDashboard(timeframe, useMockData);
        });
    });

    mockDataSwitch.addEventListener('change', () => {
        const useMockData = mockDataSwitch.checked;
        localStorage.setItem('useMockData', useMockData);
        const timeframe = document.querySelector('.timeframe-selector button.active').id.replace('-btn', '');
        updateDashboard(timeframe, useMockData);
    });

    // --- Initial Load ---
    const savedMockData = localStorage.getItem('useMockData');
    if (savedMockData !== null) {
        mockDataSwitch.checked = savedMockData === 'true';
    }

    const initialTimeframe = 'daily';
    const initialUseMockData = mockDataSwitch.checked;
    updateDashboard(initialTimeframe, initialUseMockData); // Load data on page load
});