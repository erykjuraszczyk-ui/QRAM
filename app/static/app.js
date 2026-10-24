const $ = (id) => document.getElementById(id);
async function api(url, options = {}) {
  const headers = {"Content-Type":"application/json", ...(options.headers || {})};
  const apiKey = sessionStorage.getItem("qramApiKey");
  if (apiKey) headers["X-API-Key"] = apiKey;
  const response = await fetch(url, {...options, headers});
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
  return body;
}
function showError(target, error) { $(target).textContent = `Błąd: ${error.message}`; }
async function refreshMemory() {
  const data = await api("/api/memory");
  $("capacity").textContent = data.stats.capacity; $("used").textContent = data.stats.used; $("free").textContent = data.stats.free;
  const tbody = $("cells"); tbody.replaceChildren();
  if (!data.cells.length) { const row=tbody.insertRow(); const cell=row.insertCell(); cell.colSpan=4; cell.textContent="Pamięć jest pusta."; return; }
  for (const item of data.cells) {
    const row=tbody.insertRow();
    for (const value of [item.address,item.value,item.revision,item.updated_at]) row.insertCell().textContent=value;
  }
}
async function checkHealth() {
  try { const h=await api("/api/health"); $("health").textContent=`● ONLINE · v${h.version} · SQLite`; }
  catch { $("health").textContent="● API OFFLINE"; }
}
$("write-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try { const r=await api("/api/memory/write",{method:"POST",body:JSON.stringify({address:Number($("write-address").value),value:$("write-value").value})}); $("write-result").textContent=`Zapisano adres ${r.address}, rewizja ${r.revision}: ${r.value}`; $("history-address").value=r.address; await refreshMemory(); }
  catch(error){showError("write-result",error);}
});
$("read-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try { const r=await api(`/api/memory/read/${encodeURIComponent($("read-address").value)}`); $("read-result").textContent=`Adres ${r.address} → ${r.value} · rewizja ${r.revision} · ${r.updated_at}`; }
  catch(error){showError("read-result",error);}
});
$("history-button").addEventListener("click", async () => {
  try { const r=await api(`/api/memory/history/${encodeURIComponent($("history-address").value)}`); $("history-result").textContent=JSON.stringify(r.history,null,2); }
  catch(error){showError("history-result",error);}
});
$("refresh").addEventListener("click", async () => { try{await refreshMemory();}catch(error){alert(error.message);} });
$("reset").addEventListener("click", async () => {
  if(!confirm("Usunąć wszystkie aktywne komórki? Historia rewizji pozostanie.")) return;
  try{const r=await api("/api/memory",{method:"DELETE"});await refreshMemory();alert(`Usunięto aktywne komórki: ${r.removed_cells}`);}
  catch(error){alert(error.message);}
});
$("quantum-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try{const r=await api("/api/quantum/demo",{method:"POST",body:JSON.stringify({qubits:Number($("qubits").value),operation:"hadamard_all"})});$("quantum-result").textContent=JSON.stringify(r,null,2);}
  catch(error){showError("quantum-result",error);}
});
checkHealth(); refreshMemory().catch((error)=>{$("cells").textContent=error.message;});


async function loadBackendStatus() {
  try {
    const status = await api("/api/quantum/backend");
    $("backend-status").textContent = status.available
      ? `Backend dostępny: ${status.backend} · ${status.mode}`
      : `${status.note} Instalacja: pip install -r requirements-quantum.txt`;
  } catch (error) { showError("backend-status", error); }
}
$("circuit-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const qubits = Number($("circuit-qubits").value);
    const shots = Number($("circuit-shots").value);
    const result = await api(`/api/quantum/circuit-demo?shots=${encodeURIComponent(shots)}`, {
      method: "POST",
      body: JSON.stringify({qubits, operation: "hadamard_all"})
    });
    $("circuit-result").textContent = JSON.stringify(result, null, 2);
  } catch (error) { showError("circuit-result", error); }
});
loadBackendStatus();


async function loadIntegrationCapabilities() {
  try {
    const data = await api("/api/integrations/capabilities");
    $("integration-status").textContent = JSON.stringify(data.integrations, null, 2);
  } catch (error) { showError("integration-status", error); }
}
async function refreshExperiments() {
  try {
    const data = await api("/api/experiments");
    $("experiment-list").textContent = JSON.stringify(data.experiments, null, 2);
  } catch (error) { showError("experiment-list", error); }
}
$("experiment-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const created = await api("/api/experiments", {
      method: "POST",
      body: JSON.stringify({
        qubits: Number($("experiment-qubits").value),
        shots: Number($("experiment-shots").value),
        label: "hadamard_all"
      })
    });
    $("experiment-result").textContent = JSON.stringify(created, null, 2);
    if (created.status === "queued") {
      try {
        const result = await api(`/api/experiments/${created.experiment_id}/run`, {method: "POST"});
        $("experiment-result").textContent = JSON.stringify(result, null, 2);
      } catch (error) { $("experiment-result").textContent = `Eksperyment utworzony, ale uruchomienie nie powiodło się: ${error.message}`; }
    }
    await refreshExperiments();
  } catch (error) { showError("experiment-result", error); }
});
$("refresh-experiments").addEventListener("click", refreshExperiments);
loadIntegrationCapabilities();
refreshExperiments();


const apiKeyInput = document.getElementById("api-key-input");
const apiKeyResult = document.getElementById("api-key-result");
if (apiKeyInput) apiKeyInput.value = sessionStorage.getItem("qramApiKey") || "";
const saveApiKeyButton = document.getElementById("save-api-key");
if (saveApiKeyButton) saveApiKeyButton.addEventListener("click", async () => {
  const value = apiKeyInput.value.trim();
  if (value) sessionStorage.setItem("qramApiKey", value);
  else sessionStorage.removeItem("qramApiKey");
  apiKeyResult.textContent = "Klucz ustawiony dla bieżącej sesji. Sprawdzam dostęp…";
  try { await refreshMemory(); await loadIntegrationCapabilities(); await refreshExperiments(); apiKeyResult.textContent = "Dostęp potwierdzony."; }
  catch (error) { apiKeyResult.textContent = `Nie udało się potwierdzić dostępu: ${error.message}`; }
});
const clearApiKeyButton = document.getElementById("clear-api-key");
if (clearApiKeyButton) clearApiKeyButton.addEventListener("click", () => {
  sessionStorage.removeItem("qramApiKey"); apiKeyInput.value = ""; apiKeyResult.textContent = "Klucz usunięty z bieżącej sesji.";
});
async function loadAuthMode() {
  try { const h = await api("/api/health"); const v = await api("/api/version");
    const el = document.getElementById("auth-mode");
    if (el) el.textContent = v.api_key_required ? "Ochrona kluczem aktywna" : "Tryb lokalny bez klucza";
  } catch (error) { const el = document.getElementById("auth-mode"); if (el) el.textContent = error.message; }
}
loadAuthMode();
