async function loadSummary() {
    const resp = await fetch("/api/bugs/summary");
    return resp.json();
}

function plotBugsOverTime(data) {
    const ctx = document.getElementById("bugsOverTime");

    new Chart(ctx, {
        type: "line",
        data: {
            labels: data.map(i => i.period),
            datasets: [{
                label: "Bugs Created",
                data: data.map(i => i.count),
                borderWidth: 2
            }]
        }
    });
}

function plotTimeToFix(data) {
    const ctx = document.getElementById("timeToFix");

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.map((_, i) => i),
            datasets: [{
                label: "Days to Fix",
                data: data,
                borderWidth: 1
            }]
        }
    });
}

function plotTopDevs(data) {
    const ctx = document.getElementById("topDevs");

    new Chart(ctx, {
        type: "bar",
        data: {
            labels: data.map(i => i.developer),
            datasets: [{
                label: "Bugs Closed",
                data: data.map(i => i.count),
                borderWidth: 1
            }]
        }
    });
}

async function main() {
    const summary = await loadSummary();

    plotBugsOverTime(summary.bugs_over_time);
    plotTimeToFix(summary.time_to_fix);
    plotTopDevs(summary.top_developers);
}

main();
