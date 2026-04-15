(() => {
    const page = document.querySelector(".intern-dashboard-page");
    if (!page) {
        return;
    }

    const payload = JSON.parse(page.dataset.kpi || "{}");
    const css = getComputedStyle(document.documentElement);
    const colors = {
        navy: css.getPropertyValue("--color-navy-500").trim() || "#1f3a5f",
        navyDark: css.getPropertyValue("--color-navy-700").trim() || "#162b47",
        navyLight: css.getPropertyValue("--color-navy-100").trim() || "#dbe7f3",
        gold: css.getPropertyValue("--color-gold-500").trim() || "#c99a2e",
        goldDark: css.getPropertyValue("--color-gold-700").trim() || "#9f7420",
        gray: css.getPropertyValue("--color-gray-500").trim() || "#6b7280",
        grid: css.getPropertyValue("--color-gray-300").trim() || "#d1d5db",
    };

    if (window.Chart) {
        Chart.defaults.font.family = getComputedStyle(page).fontFamily;
        Chart.defaults.color = colors.gray;
        Chart.defaults.maintainAspectRatio = false;
    }

    function emptyState(element) {
        const parent = element && element.parentElement ? element.parentElement : element;
        if (parent && !parent.querySelector(".dashboard-empty-state")) {
            const message = document.createElement("div");
            message.className = "dashboard-empty-state";
            message.textContent = "No KPI data available yet.";
            parent.appendChild(message);
        }
    }

    function renderAverageScoreChart() {
        const container = document.getElementById("averageScoreProgress");
        const rows = payload.average_scores || [];
        if (!container || !rows.length) {
            if (container) {
                emptyState(container);
            }
            return;
        }

        const row = rows[0];
        const averageScore = Number(row.average_score || 0);
        const maxScore = 5;
        const progress = Math.min((averageScore / maxScore) * 100, 100);

        container.innerHTML = `
            <div class="dashboard-score-progress__header">
                <div>
                    <div class="dashboard-score-progress__value">${averageScore.toFixed(2)} / ${maxScore.toFixed(2)}</div>
                </div>
                <div class="dashboard-score-progress__percent">${progress.toFixed(0)}%</div>
            </div>
            <div class="dashboard-score-progress__track" role="progressbar" aria-valuenow="${progress.toFixed(2)}" aria-valuemin="0" aria-valuemax="100" aria-label="Average score progress">
                <div class="dashboard-score-progress__fill" style="width: ${progress}%;"></div>
            </div>
            <div class="dashboard-score-progress__meta">
                <span>Current Score: ${averageScore.toFixed(2)} pts</span>
                <span>Target Score: ${maxScore.toFixed(2)} pts</span>
            </div>
        `;
    }

    function renderHoursChart() {
        const container = document.getElementById("hoursProgressChart");
        const rows = payload.hours || [];
        if (!container || !rows.length) {
            if (container) {
                emptyState(container);
            }
            return;
        }

        const row = rows[0];
        const renderedHours = Number(row.rendered_hours || 0);
        const contractHours = Number(row.contract_hours || 0);
        const renderedDays = Number(row.rendered_days || 0);
        const contractDays = Number(row.contract_days || 0);
        const progress = contractHours ? Math.min((renderedHours / contractHours) * 100, 100) : 0;

        container.innerHTML = `
            <div class="dashboard-hours-progress__header">
                <div>
                    <div class="dashboard-hours-progress__value">${renderedHours.toFixed(2)} / ${contractHours.toFixed(2)} hrs</div>
                </div>
                <div class="dashboard-hours-progress__percent">${progress.toFixed(0)}%</div>
            </div>
            <div class="dashboard-hours-progress__track" role="progressbar" aria-valuenow="${progress.toFixed(2)}" aria-valuemin="0" aria-valuemax="100" aria-label="Rendered hours progress">
                <div class="dashboard-hours-progress__fill" style="width: ${progress}%;"></div>
            </div>
            <div class="dashboard-hours-progress__meta">
                <span>Rendered: ${renderedHours.toFixed(2)} hrs (${renderedDays.toFixed(2)} days)</span>
                <span>Contract: ${contractHours.toFixed(2)} hrs (${contractDays.toFixed(2)} days)</span>
            </div>
        `;
    }

    function renderTimelinessResponsivenessChart() {
        const canvas = document.getElementById("timelinessResponsivenessChart");
        const rows = payload.timeliness_responsiveness_trend || [];
        if (!canvas || !rows.length) {
            if (canvas) {
                emptyState(canvas);
            }
            return;
        }

        if (!window.Chart) {
            return;
        }

        new Chart(canvas, {
            type: "line",
            data: {
                labels: rows.map((row, index) => `Week ${index + 1}`),
                datasets: [
                    {
                        label: "Timeliness",
                        data: rows.map((row) => row.timeliness),
                        backgroundColor: colors.gold,
                        borderColor: colors.goldDark,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        tension: 0,
                        yAxisID: "y",
                    },
                    {
                        label: "Responsiveness",
                        data: rows.map((row) => row.responsiveness),
                        backgroundColor: colors.navy,
                        borderColor: colors.navyDark,
                        pointRadius: 5,
                        pointHoverRadius: 7,
                        tension: 0,
                        yAxisID: "y1",
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const row = rows[context.dataIndex] || {};
                                const value = Number(context.raw || 0).toFixed(2);
                                const datePart = row.evaluation_date ? ` (${row.evaluation_date})` : "";
                                return `${context.dataset.label}: ${value}${datePart}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        title: { display: true, text: "Week" },
                        grid: { color: colors.grid },
                    },
                    y: {
                        min: 0,
                        max: 5,
                        grid: { color: colors.grid },
                    },
                    y1: {
                        min: 0,
                        max: 5,
                        position: "right",
                        grid: { drawOnChartArea: false },
                    },
                },
            },
        });
    }

    renderHoursChart();
    renderAverageScoreChart();

    if (window.Chart) {
        renderTimelinessResponsivenessChart();
    }
})();
