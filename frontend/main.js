// --- 1. REALISTIC INTRO SEQUENCE ---
window.addEventListener('DOMContentLoaded', () => {
    const door = document.getElementById('main-door');
    const character = document.getElementById('intro-character');
    const greeting = document.getElementById('greeting');
    const introLayer = document.getElementById('intro-layer');
    const mainContent = document.getElementById('main-content');
    const glow = document.getElementById('portal-glow');

    // Jumping Text Preparation
    const text = "HELLO BUDDY!!!";
    greeting.innerHTML = text.split("").map((char, i) =>
        `<span style="animation-delay: ${i * 0.07}s">${char === " " ? "&nbsp;" : char}</span>`
    ).join("");

    // Start Sequence: 0.8s Wait
    setTimeout(() => {
        door.classList.add('open');
        glow.style.opacity = '1';

        setTimeout(() => {
            character.classList.add('step-forward');
            setTimeout(() => {
                greeting.classList.add('show');
                greeting.querySelectorAll('span').forEach(span => span.classList.add('jump'));
            }, 400);
        }, 600);
    }, 800);

    // MOVE TO HOME PAGE (Reduced to 5.5 Seconds)
    setTimeout(() => {
        introLayer.style.opacity = '0';
        setTimeout(() => {
            introLayer.classList.add('hidden');
            mainContent.classList.remove('hidden');
        }, 600);
    }, 5500);
});

// --- 2. NAVIGATION ---
function switchView(viewName) {
    const views = ['home-view', 'search-view', 'pdf-view'];
    views.forEach(v => {
        const el = document.getElementById(v);
        if (el) el.classList.add('hidden');
    });
    const target = document.getElementById(`${viewName}-view`);
    if (target) target.classList.remove('hidden');
}

// --- 3. AGENT LOGIC ---
function typeWriter(text, elementId, speed = 15) {
    let i = 0;
    const element = document.getElementById(elementId);
    if (!element) return;
    element.textContent = "";
    function type() {
        if (i < text.length) {
            element.textContent += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    type();
}

async function callAgent(query, resultAreaId, agentDisplayId, outputTextId, loaderElement) {
    const resultArea = document.getElementById(resultAreaId);
    const outputText = document.getElementById(outputTextId);
    const agentDisplay = agentDisplayId ? document.getElementById(agentDisplayId) : null;
    if (!query || query.trim() === "") return;
    if (loaderElement) loaderElement.style.animationDuration = '0.5s';
    outputText.textContent = 'Querying the Nexus...';
    resultArea.classList.remove('hidden');
    try {
        const response = await fetch('/ask', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query.trim() })
        });
        const data = await response.json();
        if (agentDisplay) agentDisplay.textContent = `AGENT: ${data.agent}`;
        typeWriter(data.result, outputTextId);
    } catch (e) {
        outputText.textContent = 'Communication failure.';
    } finally {
        if (loaderElement) loaderElement.style.animationDuration = '3s';
    }
}

async function askQuery() {
    const q = document.getElementById('queryInput').value;
    const fireball = document.getElementById('fireball');
    await callAgent(q, 'search-results', 'agent-display', 'search-output-text', fireball);
}

async function queryPdf() {
    const q = document.getElementById('pdfQueryInput').value;
    await callAgent(q, 'pdf-output', null, 'pdf-output-text', null);
}

async function uploadPdf() {
    const fileInput = document.getElementById('pdfFile');
    const status = document.getElementById('uploadStatus');
    if (fileInput.files.length === 0) return;
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    status.textContent = 'Ingesting document...';
    try {
        const response = await fetch('/pdf-upload', { method: 'POST', body: formData });
        const data = await response.json();
        status.textContent = data.message;
    } catch (e) {
        status.textContent = 'Upload failed.';
    }
}