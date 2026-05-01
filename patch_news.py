"""
Patch index.html to add the floating news panel.
Run: python patch_news.py
"""
import re

with open('index.html', 'r', encoding='utf-8') as f:
    html = f.read()

# ── 1. CSS ────────────────────────────────────────────────────────────────────
NEWS_CSS = """
/* ── News Panel ─────────────────────────────────── */
#news-panel {
  position: fixed; right: 20px; bottom: 320px;
  width: 380px; height: 480px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; box-shadow: 0 16px 48px rgba(0,0,0,0.5);
  z-index: 200; display: none; flex-direction: column;
  overflow: hidden; resize: both; min-width: 300px; min-height: 200px;
}
#news-panel.visible { display: flex; }
#news-panel.minimized { height: 44px !important; resize: none; overflow: hidden; }
#news-header {
  display: flex; align-items: center; gap: 8px; padding: 10px 14px;
  background: var(--surface2); border-bottom: 1px solid var(--border);
  cursor: move; flex-shrink: 0; user-select: none;
}
#news-header .news-title { font-size: 13px; font-weight: 600; flex: 1; }
#news-header .news-ctrl {
  background: none; border: none; color: var(--text-muted);
  cursor: pointer; font-size: 14px; padding: 2px 6px; border-radius: 4px;
  font-family: inherit; transition: color 0.15s, background 0.15s;
}
#news-header .news-ctrl:hover { color: var(--text); background: var(--surface3); }
#news-toolbar {
  padding: 8px 12px; border-bottom: 1px solid var(--border);
  display: flex; gap: 6px; flex-shrink: 0; flex-wrap: wrap;
}
#news-search {
  flex: 1; min-width: 120px; background: var(--surface3);
  border: 1px solid var(--border); border-radius: 4px; padding: 5px 8px;
  color: var(--text); font-size: 11px; font-family: inherit; outline: none;
}
#news-search:focus { border-color: var(--accent); }
#news-company-filter {
  background: var(--surface3); border: 1px solid var(--border);
  border-radius: 4px; padding: 5px 8px; color: var(--text);
  font-size: 11px; font-family: inherit; cursor: pointer; outline: none;
}
#news-list {
  flex: 1; overflow-y: auto; padding: 8px 10px;
  display: flex; flex-direction: column; gap: 6px;
}
#news-list::-webkit-scrollbar { width: 4px; }
#news-list::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
.news-item {
  background: var(--surface2); border: 1px solid var(--border);
  border-radius: 6px; padding: 10px 12px; cursor: pointer; transition: border-color 0.15s;
}
.news-item:hover { border-color: var(--accent); }
.news-item-title { font-size: 12px; font-weight: 500; margin-bottom: 4px; line-height: 1.4; }
.news-item-meta { font-size: 10px; color: var(--text-muted); margin-bottom: 6px; }
.news-item-tags { display: flex; flex-wrap: wrap; gap: 3px; }
.news-tag {
  font-size: 9px; padding: 1px 5px; border-radius: 3px;
  background: var(--surface3); border: 1px solid var(--border);
  color: var(--text-muted); cursor: pointer; transition: all 0.15s;
}
.news-tag:hover { background: var(--accent-dim); border-color: var(--accent); color: var(--accent); }
.news-tag.company { background: rgba(59,158,255,0.1); border-color: rgba(59,158,255,0.3); color: var(--accent); }
.news-tag.state-tag { background: rgba(46,204,113,0.1); border-color: rgba(46,204,113,0.3); color: var(--green); }
.news-tag.medicilon { background: var(--gold-dim); border-color: var(--gold-border); color: var(--gold); }
.news-item-summary {
  display: none; font-size: 11px; color: var(--text-muted);
  margin-top: 8px; padding-top: 8px; border-top: 1px solid var(--border); line-height: 1.5;
}
.news-item.expanded .news-item-summary { display: block; }
#news-footer {
  padding: 8px 12px; border-top: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between; flex-shrink: 0;
}
#news-footer .news-count { font-size: 10px; color: var(--text-dim); }
.btn-news-refresh {
  background: var(--surface2); border: 1px solid var(--border); border-radius: 4px;
  padding: 4px 10px; color: var(--text-muted); font-size: 11px; cursor: pointer;
  font-family: inherit; transition: all 0.15s;
}
.btn-news-refresh:hover { color: var(--accent); border-color: var(--accent); }
#news-open-btn {
  background: var(--surface2); border: 1px solid var(--border); border-radius: 6px;
  padding: 6px 14px; color: var(--text); font-size: 12px; cursor: pointer;
  font-family: inherit; font-weight: 500; transition: all 0.15s;
  display: flex; align-items: center; gap: 6px;
}
#news-open-btn:hover { border-color: var(--accent); color: var(--accent); }
"""

html = html.replace('</style>', NEWS_CSS + '\n</style>', 1)

# ── 2. Button in topbar ───────────────────────────────────────────────────────
NEWS_BTN = '<button id="news-open-btn">📰 News</button>\n'
html = html.replace('<div class="topbar-spacer"></div>', '<div class="topbar-spacer"></div>\n' + NEWS_BTN, 1)

# ── 3. Panel HTML before </body> ──────────────────────────────────────────────
NEWS_PANEL_HTML = """
<!-- News Panel -->
<div id="news-panel">
  <div id="news-header">
    <span>📰</span>
    <span class="news-title">CRO News Intelligence</span>
    <button class="news-ctrl" id="news-minimize">−</button>
    <button class="news-ctrl" id="news-close">✕</button>
  </div>
  <div id="news-toolbar">
    <input id="news-search" type="text" placeholder="Search news...">
    <select id="news-company-filter">
      <option value="">All Companies</option>
    </select>
  </div>
  <div id="news-list"></div>
  <div id="news-footer">
    <span class="news-count" id="news-count-label">— items</span>
    <button class="btn-news-refresh" id="news-refresh-btn">↺ Refresh</button>
  </div>
</div>
"""
html = html.replace('</body>', NEWS_PANEL_HTML + '\n</body>', 1)

# ── 4. JS — news data + functions, appended before </script> ─────────────────
NEWS_JS = r"""
// ─── News Data ────────────────────────────────────────────────────────────────
const NEWS_DATA = [
  { id:1,  title:'Charles River Laboratories Expands Toxicology Campus in Raleigh, NC', source:'BioPharma Dive', date:'2d ago', tags:['Charles River','Toxicology','NC'], summary:'Charles River announced a $45M expansion of its Raleigh safety assessment campus, adding 12 new study director positions and increasing GLP toxicology capacity by 30%.' },
  { id:2,  title:'WuXi AppTec Strengthens DMPK Capabilities at NJ Site', source:'Fierce Biotech', date:'5d ago', tags:['WuXi AppTec','DMPK','NJ'], summary:'WuXi AppTec installed four new LC-MS/MS systems at its Plainsboro, NJ facility to support growing demand for metabolite ID and PK studies from US biotech clients.' },
  { id:3,  title:'Covance Acquires Bioanalysis Specialist to Expand LBA Services', source:'Drug Discovery News', date:'1w ago', tags:['Covance / Labcorp','Bioanalysis'], summary:'Labcorp Drug Development completed acquisition of a boutique LBA specialist, adding immunogenicity and PK assay capabilities across four US sites.' },
  { id:4,  title:'Crown Bioscience Opens New PDX Model Repository in San Diego', source:'GEN News', date:'1w ago', tags:['Crown Bioscience','In Vivo / Mouse Services','CA'], summary:'Crown Bioscience unveiled a 500+ PDX model library at its San Diego campus, targeting immuno-oncology drug developers seeking predictive preclinical efficacy data.' },
  { id:5,  title:'Pharmaron Announces IND-Enabling Tox Package for Novel ADC in Kentucky', source:'PRNewswire', date:'2w ago', tags:['Pharmaron','Toxicology','KY'], summary:'Pharmaron completed a full IND-enabling toxicology program for a US biotech ADC, leveraging its Lexington GLP facility.' },
  { id:6,  title:'Medicilon Partners with US Biotech for Integrated Preclinical Package', source:'Medicilon Press', date:'3d ago', tags:['Medicilon','DMPK','ADME','Bioanalysis'], summary:'Medicilon announced a multi-year collaboration with a Boston-based biotech to provide integrated DMPK, ADME, and bioanalytical services, marking expanded US client engagement.' },
  { id:7,  title:'Eurofins Opens New CLIA-Certified Biomarker Lab in Research Triangle Park', source:'Lab Manager', date:'4d ago', tags:['Eurofins','Biomarker / Genomics','NC'], summary:'Eurofins expanded its RTP facility with a new CLIA-certified biomarker laboratory offering NGS, flow cytometry, and multiplex immunoassay services.' },
  { id:8,  title:'Syneos Health Wins $200M Clinical Trial Contract with Top-10 Pharma', source:'CRO News', date:'6d ago', tags:['Syneos Health','Clinical Trials','NC'], summary:'Syneos Health secured a major Phase III oncology trial management contract, expanding its Morrisville NC operations center and adding 150 clinical staff.' },
  { id:9,  title:'BioAgilytix Expands Cell-Based Assay Services at Durham Campus', source:'Bioanalysis Zone', date:'1w ago', tags:['BioAgilytix','Bioanalysis','NC'], summary:'BioAgilytix doubled its cell-based assay lab space in Durham, NC, adding PBMC isolation, ELISPOT, and cytokine multiplex capabilities.' },
  { id:10, title:'Altasciences Launches Phase I Unit in Seattle Area', source:'Fierce Biotech', date:'2w ago', tags:['Altasciences','Clinical Trials','WA'], summary:'Altasciences opened a 24-bed Phase I clinical unit in Everett, WA, complementing its existing PK/PD bioanalytical capabilities.' },
  { id:11, title:'ICON plc Integrates PRA Health Sciences Bioanalytical Network', source:'CRO News', date:'3w ago', tags:['ICON plc','Bioanalysis','PA'], summary:'ICON completed the full integration of PRA Health Sciences bioanalytical labs, creating one of the largest CRO bioanalytical networks with 12 sites across North America.' },
  { id:12, title:'Charles River Reports Record Q1 2026 Revenue Driven by In Vivo Demand', source:'FierceCRO', date:'1w ago', tags:['Charles River','In Vivo / Mouse Services'], summary:'Charles River posted Q1 2026 revenues of $1.1B, with its RMS segment growing 18% YoY driven by surge in demand for specialty mouse models.' },
  { id:13, title:'Celerion Adds Dermal PK Capability at Arizona Phase I Facility', source:'PRNewswire', date:'2w ago', tags:['Celerion','DMPK','AZ'], summary:'Celerion expanded its Tempe, AZ Phase I unit with specialist dermal PK and PD capabilities, targeting specialty pharma and topical drug developers.' },
  { id:14, title:'Medicilon Receives US FDA Acceptance of IND Application for Client Program', source:'Medicilon Press', date:'1w ago', tags:['Medicilon','Regulatory Affairs','Toxicology'], summary:'An IND application supported entirely by Medicilon preclinical data was accepted by FDA, validating the quality of its US-regulatory-standard toxicology packages.' },
  { id:15, title:'WuXi AppTec Expands CMC Services at Philadelphia Site', source:'Drug Discovery Today', date:'3w ago', tags:['WuXi AppTec','CMC','PA'], summary:'WuXi AppTec invested $30M in additional process chemistry and formulation development capabilities at its Philadelphia campus.' },
  { id:16, title:'Eurofins ADME Bioanalysis Achieves EMA and FDA Dual Validation for Novel Biomarkers', source:'Analytical Scientist', date:'2w ago', tags:['Eurofins','ADME','Bioanalysis'], summary:'Eurofins Discovery announced a dual FDA/EMA validated biomarker assay panel for metabolic disease programs.' },
  { id:17, title:'Midwest Biotech Cluster Eyes CRO Expansion: Nebraska and Kansas Gap Identified', source:'BioPharma Reporter', date:'4d ago', tags:['In Vivo / Mouse Services','DMPK','NE','KS'], summary:'An industry report highlights a service gap in the Midwest — Nebraska and Kansas lack sufficient in vivo pharmacology and DMPK CRO capacity, presenting an opportunity for new entrants.' },
  { id:18, title:'Pharmaron Protein Sciences Unit Wins ADC Bioanalysis Contract', source:'CRO News', date:'1w ago', tags:['Pharmaron','Protein Sciences / Biologics','Bioanalysis','MD'], summary:'Pharmaron Biologics secured a multi-year ADC bioanalysis contract from a mid-size US oncology biotech, utilizing its Baltimore PK/ADA/NAb platform.' },
  { id:19, title:'Crown Bioscience Expands Syngeneic Tumor Model Portfolio to 80+ Models', source:'GEN News', date:'5d ago', tags:['Crown Bioscience','In Vivo / Mouse Services','CA'], summary:'Crown Bioscience added 20 new syngeneic mouse tumor models, strengthening support for IO combination therapy programs.' },
  { id:20, title:'Medicilon Targets US East Coast Hub: Strategic Partnership Discussions Underway', source:'CRO Strategy Weekly', date:'2d ago', tags:['Medicilon','In Vivo / Mouse Services','DMPK','MA','NJ'], summary:'Medicilon is reportedly in discussions with US biotech hubs in Boston and New Jersey for a potential US operational foothold, marking a key step in its international expansion strategy.' }
];

let newsFilter = { search: '', company: '', tags: [] };

function initNewsPanel() {
  const panel = document.getElementById('news-panel');
  const header = document.getElementById('news-header');
  const openBtn = document.getElementById('news-open-btn');
  const closeBtn = document.getElementById('news-close');
  const minimizeBtn = document.getElementById('news-minimize');
  const searchInput = document.getElementById('news-search');
  const companyFilter = document.getElementById('news-company-filter');
  const refreshBtn = document.getElementById('news-refresh-btn');

  // Populate company dropdown
  const companies = [...new Set(NEWS_DATA.flatMap(n => n.tags.filter(t =>
    croData && croData.cros.some(c => c.short_name === t || c.name === t)
  )))].sort();
  companies.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c; opt.textContent = c;
    companyFilter.appendChild(opt);
  });

  openBtn.addEventListener('click', () => {
    panel.classList.toggle('visible');
    if (panel.classList.contains('visible')) { panel.classList.remove('minimized'); renderNewsList(); }
  });
  closeBtn.addEventListener('click', () => panel.classList.remove('visible'));
  minimizeBtn.addEventListener('click', () => {
    panel.classList.toggle('minimized');
    minimizeBtn.textContent = panel.classList.contains('minimized') ? '+' : '−';
  });
  searchInput.addEventListener('input', () => { newsFilter.search = searchInput.value.toLowerCase(); renderNewsList(); });
  companyFilter.addEventListener('change', () => { newsFilter.company = companyFilter.value; renderNewsList(); });
  if (refreshBtn) refreshBtn.addEventListener('click', renderNewsList);

  // Drag support
  let dragging = false, ox = 0, oy = 0;
  header.addEventListener('mousedown', e => {
    if (e.target.classList.contains('news-ctrl')) return;
    dragging = true;
    ox = e.clientX - panel.offsetLeft;
    oy = e.clientY - panel.offsetTop;
    e.preventDefault();
  });
  document.addEventListener('mousemove', e => {
    if (!dragging) return;
    panel.style.left = (e.clientX - ox) + 'px';
    panel.style.top = (e.clientY - oy) + 'px';
    panel.style.right = 'auto';
    panel.style.bottom = 'auto';
  });
  document.addEventListener('mouseup', () => { dragging = false; });
}

function renderNewsList() {
  const list = document.getElementById('news-list');
  const countLabel = document.getElementById('news-count-label');
  if (!list) return;

  const items = NEWS_DATA.filter(item => {
    if (newsFilter.search && !item.title.toLowerCase().includes(newsFilter.search) &&
        !item.summary.toLowerCase().includes(newsFilter.search)) return false;
    if (newsFilter.company && !item.tags.includes(newsFilter.company)) return false;
    if (newsFilter.tags.length > 0 && !newsFilter.tags.some(t => item.tags.includes(t))) return false;
    return true;
  });

  if (countLabel) countLabel.textContent = items.length + ' items';
  list.innerHTML = '';

  if (items.length === 0) {
    list.innerHTML = '<div style="color:var(--text-dim);font-size:12px;padding:20px;text-align:center">No news matching current filters</div>';
    return;
  }

  items.forEach(item => {
    const div = document.createElement('div');
    div.className = 'news-item';
    const tagHtml = item.tags.map(t => {
      const isMed = t === 'Medicilon';
      const isCo = !isMed && croData && croData.cros.some(c => c.short_name === t || c.name === t);
      const isState = !isCo && !isMed && t.length === 2 && /^[A-Z]{2}$/.test(t);
      const cls = isMed ? 'medicilon' : isCo ? 'company' : isState ? 'state-tag' : '';
      return '<span class="news-tag ' + cls + '" data-tag="' + t + '">' + t + '</span>';
    }).join('');
    div.innerHTML =
      '<div class="news-item-title">' + item.title + '</div>' +
      '<div class="news-item-meta">' + item.source + ' · ' + item.date + '</div>' +
      '<div class="news-item-tags">' + tagHtml + '</div>' +
      '<div class="news-item-summary">' + item.summary + '</div>';

    div.addEventListener('click', function(e) {
      if (e.target.classList.contains('news-tag')) {
        const tag = e.target.dataset.tag;
        const isCo = croData && croData.cros.some(c => c.short_name === tag || c.name === tag);
        if (isCo) {
          document.getElementById('news-company-filter').value = tag;
          newsFilter.company = tag;
          newsFilter.tags = [];
        } else {
          const idx = newsFilter.tags.indexOf(tag);
          if (idx >= 0) newsFilter.tags.splice(idx, 1);
          else newsFilter.tags.push(tag);
        }
        renderNewsList();
        return;
      }
      div.classList.toggle('expanded');
    });
    list.appendChild(div);
  });
}

function openNewsForState(stateAbbr) {
  const panel = document.getElementById('news-panel');
  newsFilter.tags = [stateAbbr];
  newsFilter.company = '';
  newsFilter.search = '';
  const si = document.getElementById('news-search');
  const cf = document.getElementById('news-company-filter');
  if (si) si.value = '';
  if (cf) cf.value = '';
  panel.classList.add('visible');
  panel.classList.remove('minimized');
  const mb = document.getElementById('news-minimize');
  if (mb) mb.textContent = '−';
  renderNewsList();
}

function openNewsForCompany(companyName) {
  const panel = document.getElementById('news-panel');
  newsFilter.company = companyName;
  newsFilter.tags = [];
  newsFilter.search = '';
  const si = document.getElementById('news-search');
  const cf = document.getElementById('news-company-filter');
  if (si) si.value = '';
  if (cf) { cf.value = companyName; }
  panel.classList.add('visible');
  panel.classList.remove('minimized');
  const mb = document.getElementById('news-minimize');
  if (mb) mb.textContent = '−';
  renderNewsList();
}
"""

# Insert JS before last </script>
last_script = html.rfind('</script>')
html = html[:last_script] + NEWS_JS + '\n' + html[last_script:]

# ── 5. Call initNewsPanel() in init() ─────────────────────────────────────────
old_loading_hide = "document.getElementById('loading').style.display = 'none';"
new_loading_hide = old_loading_hide + "\n    initNewsPanel();"
html = html.replace(old_loading_hide, new_loading_hide, 1)

# ── 6. Add 'View News' button to detail panel CRO cards ───────────────────────
# Find the openDetailPanel function and patch the card building
# Look for where detail-services div is appended, add news link after
old_card_close = "card.querySelector('.detail-services').innerHTML = svcHtml;"
new_card_close = """card.querySelector('.detail-services').innerHTML = svcHtml;
      const newsLinkDiv = document.createElement('div');
      newsLinkDiv.style.marginTop = '6px';
      newsLinkDiv.innerHTML = '<button onclick=\"openNewsForCompany(\\'' + cro.short_name + '\\')\" style=\"background:none;border:none;color:var(--accent);font-size:10px;cursor:pointer;font-family:inherit;padding:0\">📰 View News \u2192</button>';
      card.appendChild(newsLinkDiv);"""
if old_card_close in html:
    html = html.replace(old_card_close, new_card_close, 1)
    print("Patched: View News button in detail cards")
else:
    print("WARNING: Could not find detail card injection point — skipping View News button")

# ── 7. Write output ───────────────────────────────────────────────────────────
with open('index.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f"Done. File size: {len(html)} bytes")
print(f"Has news-panel: {'news-panel' in html}")
print(f"Has initNewsPanel: {'initNewsPanel' in html}")
print(f"Has NEWS_DATA: {'NEWS_DATA' in html}")
