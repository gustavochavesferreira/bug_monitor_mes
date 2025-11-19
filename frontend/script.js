let charts = {};

async function loadSummary() {
  const resp = await fetch("/api/bugs/summary");
  return resp.json();
}

async function loadFiles() {
  const resp = await fetch("/api/files");
  return resp.json();
}

function plotLineChart(id, labels, data, label, color) {
  const ctx = document.getElementById(id);
  if (charts[id]) charts[id].destroy();

  charts[id] = new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [{
        label,
        data,
        borderColor: color,
        backgroundColor: color.replace('1)', '0.1)'),
        tension: 0.3,
        fill: true,
        pointRadius: 4,
        borderWidth: 3
      }]
    },
    options: { 
      responsive: true,
      plugins: {
        legend: { display: true },
        tooltip: { mode: 'index', intersect: false }
      },
      interaction: { mode: 'nearest', axis: 'x', intersect: false },
      scales: {
        y: { beginAtZero: true, ticks: { precision: 0 } }
      }
    }
  });
}

function plotBarChart(id, labels, data, label, color, horizontal = false) {
  const ctx = document.getElementById(id);
  if (charts[id]) charts[id].destroy();

  charts[id] = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label,
        data,
        backgroundColor: color,
        borderRadius: 6
      }]
    },
    options: { 
      responsive: true,
      indexAxis: horizontal ? 'y' : 'x',
      plugins: { legend: { display: true }, tooltip: { mode: 'nearest' } },
      scales: { 
        x: { beginAtZero: true, ticks: { precision: 0 } },
        y: { beginAtZero: true, ticks: { precision: 0 } }
      }
    }
  });
}

async function updateCharts() {
  try {
    const summary = await loadSummary();
    const files = await loadFiles();

    plotLineChart(
      "bugsOverTime",
      summary.bugs_over_time.map(i => i.period),
      summary.bugs_over_time.map(i => i.count),
      "Bugs Criados",
      "rgba(52, 152, 219, 1)"
    );

    plotBarChart(
      "timeToFix",
      summary.time_to_fix.map((_, i) => i + 1),
      summary.time_to_fix,
      "Dias para Corrigir",
      "rgba(241, 196, 15, 0.8)"
    );

    plotBarChart(
      "topDevs",
      summary.top_developers.map(i => i.developer),
      summary.top_developers.map(i => i.count),
      "Bugs Corrigidos",
      "rgba(155, 89, 182, 0.8)"
    );

    plotBarChart(
      "topFiles",
      files.map(i => i.file_name),
      files.map(i => i.changes),
      "Vezes Modificado",
      "rgba(46, 204, 113, 0.8)",
      true
    );

  } catch (err) {
    console.error("Erro ao atualizar gráficos:", err);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  updateCharts();
  setInterval(updateCharts, 300000); // Atualiza a cada 5 minutos
});
