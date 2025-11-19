async function loadSummary() {
    const resp = await fetch("/api/bugs/summary");
    return resp.json();
}

async function loadFiles() {
    const resp = await fetch("/api/files");
    return resp.json();
}

let charts = {};

function plotBugsOverTime(data) {
    const ctx = document.getElementById("bugsOverTime");
    if (charts.bugsOverTime) charts.bugsOverTime.destroy();

    charts.bugsOverTime = new Chart(ctx, {
        type: "line",
        data: {
            labels: data.map(i => i.period),
            datasets: [{
                label: "Bugs Created",
                data: data.map(i => i.count),
                borderWidth: 2,
                borderColor: "rgba(75, 192, 192, 1)",
                backgroundColor: "rgba(75, 192, 192, 0.2)"
            }]
        },
        options: { responsive: true }
    });
}

function plotTimeToFix(data) {
    const ctx = document.getElementById("timeToFix");
    if (charts.timeToFix) charts.timeToFix.destroy();

    charts.timeToFix = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.map((_, i) => i),
            datasets: [{
                label: "Days to Fix",
                data: data,
                borderWidth: 1,
                backgroundColor: "rgba(255, 159, 64, 0.7)"
            }]
        },
        options: { responsive: true }
    });
}

function plotTopDevs(data) {
    const ctx = document.getElementById("topDevs");
    if (charts.topDevs) charts.topDevs.destroy();

    charts.topDevs = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.map(i => i.developer),
            datasets: [{
                label: "Bugs Closed",
                data: data.map(i => i.count),
                borderWidth: 1,
                backgroundColor: "rgba(153, 102, 255, 0.7)"
            }]
        },
        options: { responsive: true }
    });
}

function plotFiles(data) {
    const ctx = document.getElementById("topFiles");
    if (charts.topFiles) charts.topFiles.destroy();

    charts.topFiles = new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.map(i => i.file_name),
            datasets: [{
                label: "Times Modified",
                data: data.map(i => i.changes),
                borderWidth: 1,
                backgroundColor: "rgba(54, 162, 235, 0.7)"
            }]
        },
        options: {
            responsive: true,
            indexAxis: 'y', // horizontal bar chart
        }
    });
}

async function updateCharts() {
    try {
        const summary = await loadSummary();
        const files = await loadFiles();

        plotBugsOverTime(summary.bugs_over_time);
        plotTimeToFix(summary.time_to_fix);
        plotTopDevs(summary.top_developers);
        plotFiles(files);
    } catch (err) {
        console.error("Error updating charts:", err);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // Initial load
    updateCharts();
    // Auto-refresh every 5 minutes (300000 ms)
    setInterval(updateCharts, 300000);
});
