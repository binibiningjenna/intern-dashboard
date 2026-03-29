/** @odoo-module **/

import { Component, onWillStart, onMounted, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";

class TimelinessResponsivenessScatter extends Component {
    static template = "famtech_intern_dashboard.TimelinessResponsivenessScatter";

    setup() {
        this.orm = useService("orm");
        this.canvasRef = useRef("canvas");
        this.state = useState({
            points: [],
            loaded: false,
        });
        this.chart = null;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            this.state.points = await this.orm.call(
                "intern.evaluation",
                "get_timeliness_responsiveness_scatter_data",
                []
            );
            this.state.loaded = true;
        });

        onMounted(() => this.renderChart());
        onWillUnmount(() => {
            if (this.chart) {
                this.chart.destroy();
            }
        });
    }

    renderChart() {
        if (!this.canvasRef.el || !this.state.points.length) {
            return;
        }
        if (this.chart) {
            this.chart.destroy();
        }

        const points = this.state.points.map((point) => ({
            x: point.timeliness,
            y: point.responsiveness,
            employeeName: point.employee_name,
            evaluationDate: point.evaluation_date,
        }));

        this.chart = new Chart(this.canvasRef.el, {
            type: "scatter",
            data: {
                datasets: [
                    {
                        label: "Intern Results",
                        data: points,
                        backgroundColor: "#2563eb",
                        borderColor: "#1d4ed8",
                        pointRadius: 6,
                        pointHoverRadius: 8,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false,
                    },
                    tooltip: {
                        callbacks: {
                            label: (context) => {
                                const raw = context.raw;
                                const datePart = raw.evaluationDate ? `, Eval Date: ${raw.evaluationDate}` : "";
                                return `${raw.employeeName}: Timeliness ${raw.x}%, Responsiveness ${raw.y}${datePart}`;
                            },
                        },
                    },
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: "Timeliness (%)",
                        },
                        min: 0,
                        max: 100,
                    },
                    y: {
                        title: {
                            display: true,
                            text: "Responsiveness Score",
                        },
                        min: 0,
                        max: 5,
                    },
                },
            },
            plugins: [
                {
                    id: "pointLabels",
                    afterDatasetsDraw: (chart) => {
                        const { ctx } = chart;
                        ctx.save();
                        ctx.font = "12px sans-serif";
                        ctx.fillStyle = "#334155";

                        chart.data.datasets.forEach((dataset, datasetIndex) => {
                            const meta = chart.getDatasetMeta(datasetIndex);
                            meta.data.forEach((element, index) => {
                                const point = dataset.data[index];
                                ctx.fillText(point.employeeName, element.x + 8, element.y - 8);
                            });
                        });

                        ctx.restore();
                    },
                },
            ],
        });
    }
}

registry.category("actions").add(
    "famtech_intern_dashboard.timeliness_responsiveness_scatter",
    TimelinessResponsivenessScatter
);
