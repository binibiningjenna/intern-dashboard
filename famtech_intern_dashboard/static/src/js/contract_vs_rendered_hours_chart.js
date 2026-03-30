/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { loadBundle } from "@web/core/assets";
import { useService } from "@web/core/utils/hooks";

class ContractVsRenderedHoursChart extends Component {
    static template = "famtech_intern_dashboard.ContractVsRenderedHoursChart";

    setup() {
        this.orm = useService("orm");
        this.canvasRef = useRef("canvas");
        this.state = useState({
            rows: [],
            loaded: false,
        });
        this.chart = null;

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
            this.state.rows = await this.orm.call(
                "hr.employee",
                "get_contract_vs_rendered_hours_chart_data",
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
        if (!this.canvasRef.el || !this.state.rows.length) {
            return;
        }
        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(this.canvasRef.el, {
            type: "bar",
            data: {
                labels: this.state.rows.map((row) => row.employee_name),
                datasets: [
                    {
                        label: "Contract Hours",
                        data: this.state.rows.map((row) => row.contract_hours),
                        backgroundColor: "#94a3b8",
                        borderColor: "#64748b",
                        borderWidth: 1,
                    },
                    {
                        label: "Rendered Hours",
                        data: this.state.rows.map((row) => row.rendered_hours),
                        backgroundColor: "#2563eb",
                        borderColor: "#1d4ed8",
                        borderWidth: 1,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: "top",
                    },
                },
                scales: {
                    x: {
                        ticks: {
                            autoSkip: false,
                        },
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: "Hours",
                        },
                    },
                },
            },
        });
    }
}

registry.category("actions").add(
    "famtech_intern_dashboard.contract_vs_rendered_hours_chart",
    ContractVsRenderedHoursChart
);
