
let farmaci = [], confrontoData = [];

function log(msg, tipo) {
    const box = document.getElementById('logbox');
    if (!box) return;
    const ts = new Date().toLocaleTimeString('it-IT');
    const cls = tipo || 'info';
    const div = document.createElement('div');
    div.className = cls;
    div.textContent = '[' + ts + '] ' + msg;
    box.appendChild(div);
    box.scrollTop = box.scrollHeight;
    console.log('[' + cls + '] ' + msg);
}

async function apiFetch(path) {
    log('Fetch: ' + path);
    try {
        const r = await fetch(path);
        log('HTTP ' + r.status + ' ' + r.statusText, r.ok ? 'ok' : 'ko');
        if (!r.ok) throw new Error('HTTP ' + r.status);
        const data = await r.json();
        log('JSON ricevuto OK (' + JSON.stringify(data).length + ' bytes)', 'ok');
        return data;
    } catch(e) {
        log('ERRORE: ' + e.message, 'ko');
        throw e;
    }
}

function setMain(html) {
    document.getElementById('main').innerHTML = html;
}

function logBox() {
    return '<div id="logbox"></div>';
}

function spinner(msg) {
    setMain('<div class="spinner">&#9200; ' + msg + '</div>' + logBox());
}

function showError(msg) {
    setMain('<div class="error">&#10060; ' + msg +
        '<br><br><button class="btn" onclick="home()">&#8635; Riprova</button></div>' + logBox());
}

async function home() {
    spinner('Carico lista farmaci...');
    log('=== home() START ===');
    try {
        farmaci = await apiFetch('/api/farmaci');
        log('Farmaci ricevuti: ' + farmaci.length, 'ok');
        let h = '<button class="btn btn-green" onclick="confronto()">&#127942; Confronto totale farmacie</button>';
        h += '<p class="sec">Seleziona un farmaco:</p>';
        farmaci.forEach(function(f) {
            h += '<div class="card" onclick="mostraPrezzi(\'' + f.id + '\')"><h3>' + f.nome + '</h3><small>Qty: ' + f.qty + ' pz</small></div>';
        });
        h += '<p class="sec" onclick="toggleLog()" style="cursor:pointer">&#128196; Log diagnostico (tocca per vedere)</p>';
        h += '<div id="logbox" style="display:none"></div>';
        setMain(h);
        log('Home caricata OK', 'ok');
    } catch(e) {
        showError('Errore API farmaci: ' + e.message);
    }
}

function toggleLog() {
    const b = document.getElementById('logbox');
    if (b) b.style.display = (b.style.display === 'none' ? 'block' : 'none');
}

async function mostraPrezzi(id) {
    spinner('Scarico prezzi da Trovaprezzi...');
    log('=== prezzi(' + id + ') START ===');
    try {
        const d = await apiFetch('/api/prezzi/' + id);
        log('Offerte ricevute: ' + d.offerte.length, 'ok');
        let h = '<button class="back" onclick="home()">&#8249; Indietro</button>';
        h += '<div class="fhdr"><strong>' + d.farmaco + '</strong><br><small>Qty: ' + d.qty + ' pz</small></div>';
        h += '<p class="sec">' + d.offerte.length + ' offerte trovate</p>';
        d.offerte.forEach(function(o, i) {
            var best = (i === 0);
            var tq = (o.totale * d.qty).toFixed(2);
            h += '<div class="card' + (best ? ' best' : '') + '">';
            if (best) h += '<div class="best-badge">&#11088; MIGLIOR PREZZO</div>';
            h += '<div class="row"><strong>' + o.shop + '</strong><span class="price">' + o.prezzo.toFixed(2) + ' &#8364;</span></div>';
            h += '<div class="row"><span class="sub">Sped.: ' + (o.sped > 0 ? o.sped.toFixed(2) + '&#8364;' : 'Gratuita') + '</span>';
            h += '<span class="sub">Tot.: ' + o.totale.toFixed(2) + '&#8364;</span></div>';
            h += '<div class="row" style="margin-top:8px;padding-top:8px;border-top:1px solid #E2E8F0">';
            h += '<span class="sub">x' + d.qty + ' pz =</span>';
            h += '<span class="' + (best ? 'price-big' : 'price') + '">' + tq + ' &#8364;</span></div></div>';
        });
        if (!d.offerte.length) h += '<p class="empty">Nessuna offerta trovata</p>';
        setMain(h);
    } catch(e) {
        showError('Errore prezzi: ' + e.message);
    }
}

async function confronto() {
    spinner('Scarico tutti i prezzi... (1-2 minuti)');
    log('=== confronto() START ===');
    try {
        const data = await apiFetch('/api/confronto');
        confrontoData = data;
        log('Farmacie ricevute: ' + data.length, 'ok');
        let h = '<button class="back" onclick="home()">&#8249; Indietro</button>';
        h += '<p class="sec">&#127942; Classifica farmacie</p>';
        data.forEach(function(d, i) {
            var best = (i === 0);
            h += '<div class="card' + (best ? ' best' : '') + '" onclick="dettaglio(' + i + ')">';
            h += '<div class="row"><span class="rank">#' + (i+1) + '</span>';
            h += '<strong style="flex:1;margin:0 10px">' + d.shop + '</strong>';
            h += '<span class="' + (best ? 'price-big' : 'price') + '">' + d.totale.toFixed(2) + ' &#8364;</span></div>';
            h += '<div class="row"><span class="sub">Trovati: ' + d.trovati + '/' + farmaci.length + '</span>';
            h += '<span class="sub">Dettaglio &#8250;</span></div></div>';
        });
        setMain(h);
    } catch(e) {
        showError('Errore confronto: ' + e.message);
    }
}

function dettaglio(i) {
    var d = confrontoData[i];
    var h = '<h3 style="font-size:17px;margin-bottom:8px">' + d.shop + '</h3>';
    h += '<p style="color:var(--sub);margin-bottom:14px">Totale: <strong>' + d.totale.toFixed(2) + ' &#8364;</strong></p>';
    d.dettaglio.forEach(function(r) {
        h += '<div class="dr"><strong>' + r.farmaco + '</strong><br>';
        h += '<small style="color:var(--sub)">' + r.prezzo.toFixed(2) + '&#8364; + ' + r.sped.toFixed(2) + '&#8364; sped. x' + r.qty + ' = <strong>' + r.totale_qty.toFixed(2) + ' &#8364;</strong></small></div>';
    });
    h += '<button class="btn" style="margin-top:16px" onclick="chiudiModal()">Chiudi</button>';
    document.getElementById('mc').innerHTML = h;
    document.getElementById('modal').classList.add('open');
}

function chiudiModal() {
    document.getElementById('modal').classList.remove('open');
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM ready, avvio home()');
    home();
});
