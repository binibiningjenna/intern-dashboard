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

    const formatHours = (value) => Number(value || 0).toFixed(0);
    const formatDays = (value) => Number(value || 0).toFixed(2);

    function emptyState(element, messageText = "No data available yet.") {
        const parent = element && element.parentElement ? element.parentElement : element;
        if (parent && !parent.querySelector(".dashboard-empty-state")) {
            const message = document.createElement("div");
            message.className = "dashboard-empty-state";
            message.textContent = messageText;
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
                    <div class="dashboard-hours-progress__value">${formatHours(renderedHours)} / ${formatHours(contractHours)} hrs</div>
                </div>
                <div class="dashboard-hours-progress__percent">${progress.toFixed(0)}%</div>
            </div>
            <div class="dashboard-hours-progress__track" role="progressbar" aria-valuenow="${progress.toFixed(2)}" aria-valuemin="0" aria-valuemax="100" aria-label="Rendered hours progress">
                <div class="dashboard-hours-progress__fill" style="width: ${progress}%;"></div>
            </div>
            <div class="dashboard-hours-progress__meta">
                <span>Rendered: ${formatHours(renderedHours)} hrs (${formatDays(renderedDays)} days)</span>
                <span>Contract: ${formatHours(contractHours)} hrs (${formatDays(contractDays)} days)</span>
            </div>
        `;
    }

    function renderTimelinessResponsivenessChart() {
        const canvas = document.getElementById("timelinessResponsivenessChart");
        const emptyStateElement = document.getElementById("timelinessResponsivenessEmptyState");
        const rows = payload.timeliness_responsiveness_trend || [];
        if (!canvas || !rows.length) {
            if (canvas) {
                canvas.style.display = "none";
            }
            if (emptyStateElement) {
                emptyStateElement.setAttribute("style", "display: flex !important;");
            }
            return;
        }

        if (!window.Chart) {
            return;
        }

        if (emptyStateElement) {
            emptyStateElement.setAttribute("style", "display: none !important;");
        }
        canvas.style.display = "block";

        function formatWeekAxisLabel(rawLabel, fallbackIndex) {
            const labelWithoutDateRange = (rawLabel || `Week ${fallbackIndex + 1}`)
                .replace(/\s*\([^)]*\)\s*/g, "")
                .trim();
            const numberedWeekMatch = labelWithoutDateRange.match(/^Week\s+(\d+)$/i);
            return numberedWeekMatch ? numberedWeekMatch[1] : labelWithoutDateRange;
        }

        function buildTrendDataset({ label, values, baseColor, baseBorderColor, axisId }) {
            return {
                label,
                data: values,
                backgroundColor: baseColor,
                borderColor: baseBorderColor,
                pointRadius: 5,
                pointHoverRadius: 7,
                pointBorderWidth: 2,
                pointBorderColor: baseBorderColor,
                pointBackgroundColor: baseColor,
                segment: {
                    borderColor: baseBorderColor,
                    borderDash: (context) => {
                        const fromValue = Number(context.p0.parsed.y || 0);
                        const toValue = Number(context.p1.parsed.y || 0);
                        return toValue < fromValue ? [6, 4] : undefined;
                    },
                },
                clip: false,
                tension: 0,
                yAxisID: axisId,
            };
        }

        new Chart(canvas, {
            type: "line",
            data: {
                labels: rows.map((row, index) => {
                    const rawLabel = row.week_display_label || row.week_label;
                    return formatWeekAxisLabel(rawLabel, index);
                }),
                datasets: [
                    buildTrendDataset({
                        label: "Timeliness",
                        values: rows.map((row) => row.timeliness),
                        baseColor: colors.gold,
                        baseBorderColor: colors.goldDark,
                        axisId: "y",
                    }),
                    buildTrendDataset({
                        label: "Responsiveness",
                        values: rows.map((row) => row.responsiveness),
                        baseColor: colors.navy,
                        baseBorderColor: colors.navyDark,
                        axisId: "y1",
                    }),
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: true },
                    tooltip: {
                        callbacks: {
                            title: (tooltipItems) => {
                                const row = rows[tooltipItems[0]?.dataIndex] || {};
                                if (row.week_display_label) {
                                    return row.week_display_label;
                                }
                                return tooltipItems[0]?.label || "";
                            },
                            label: (context) => {
                                const value = Number(context.raw || 0).toFixed(2);
                                const currentValue = Number(context.raw || 0);
                                const datasetValues = context.dataset.data || [];
                                const previousValue = context.dataIndex > 0
                                    ? Number(datasetValues[context.dataIndex - 1] || 0)
                                    : null;
                                const flags = [];
                                if (previousValue !== null && currentValue < previousValue) {
                                    flags.push("Declining");
                                }
                                return `${context.dataset.label}: ${value}${flags.length ? ` (${flags.join(", ")})` : ""}`;
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
                layout: {
                    padding: {
                        top: 10,
                        bottom: 6,
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

// Animation
document.addEventListener("DOMContentLoaded", function () {
    AOS.init({
        duration: 400,
        once: true,
        easing: 'ease-out-quad'
    });
});
