// Reference Transcripts for instant testing
const PRESETS = {
  ex1: `Agent: We provide an online business management service.
Customer: Achha, ye kaise work karta hai?
Agent: It helps you manage...
Customer: Iska price kya hai?`,

  ex2: `Agent: Would you like to know more?
Customer: Nahi, mujhe iski zarurat nahi hai.`,

  ex3: `Agent: We can provide the service at a monthly price.
Customer: Hmm, thoda expensive lag raha hai.
Agent: We also have another plan.
Customer: Achha, woh plan kitne ka hai?`,

  ex4: `Agent: Can I explain the service?
Customer: Haan, batao.
Agent: We help automate client outreach...
Customer: WhatsApp pe details bhej sakte ho?`,

  ex5: `Agent: Would you like us to contact you later?
Customer: Nahi. Please don't call me again.`,

  ex6: `Agent: Would you like to try the service?
Customer: Abhi sure nahi hoon.
Agent: I can explain how it works.
Customer: Haan, explain karo.`,

  ex7: `Agent: Can I tell you about our service?
Customer: No.
Agent: We also provide integrated GST filing...
Customer: Oh, actually I need something like that. How much does it cost?`,

  ex8: `Agent: Can I explain our service?
Customer: Hello?
Agent: Yes sir, can you hear me?
Customer: Hello?
[call disconnected]`,

  hinglish_angry: `Agent: Sir hum cloud backup and security solutions provide karte hain.
Customer: Aap faltu baat band karo aur pehle price batao, phir main decide karunga!`,

  marathi_interest: `Agent: Namaskar, aamhi business digital billing solution det aahot.
Customer: Ho sanga na, kasa work karto? Aani kiti rupaye padel?`,

  marathi_dnc: `Agent: Namaskar sir, credit card offer ahe.
Customer: Punha phone karu naka, number kadhun taka aani tras deu naka.`,

  dnc_override: `Agent: We have a comprehensive health checkup package.
Customer: Oh that sounds interesting, what tests are included?
Agent: Blood count, lipid profile, and doctor consultation.
Customer: Actually don't call me again, please remove my number from your database.`,

  wrong_person: `Agent: Hi, is this Dr. Sharma from Apollo Clinic?
Customer: No, wrong number. You have the wrong person, I'm not a doctor.`,

  noisy_stt: `Agent: Calling regarding business financial planning.
Customer: accha watsp pe detils snd krna dekhta hu ... thoda price kitna padega?`
};

document.addEventListener('DOMContentLoaded', () => {
  const transcriptInput = document.getElementById('transcriptInput');
  const presetSelect = document.getElementById('presetSelect');
  const classifyBtn = document.getElementById('classifyBtn');
  const clearBtn = document.getElementById('clearBtn');
  const noiseBtn = document.getElementById('noiseBtn');
  const copyJsonBtn = document.getElementById('copyJsonBtn');

  // Result Elements
  const resultPlaceholder = document.getElementById('resultPlaceholder');
  const resultContent = document.getElementById('resultContent');
  const decisionBadge = document.getElementById('decisionBadge');
  const confidenceValue = document.getElementById('confidenceValue');
  const confidenceFill = document.getElementById('confidenceFill');
  const priorityTier = document.getElementById('priorityTier');
  const languagesDetected = document.getElementById('languagesDetected');
  const customerTurnsCount = document.getElementById('customerTurnsCount');
  const leadRuleApplied = document.getElementById('leadRuleApplied');
  const decisionReason = document.getElementById('decisionReason');
  const signalTags = document.getElementById('signalTags');
  const turnsContainer = document.getElementById('turnsContainer');
  const rawJsonDisplay = document.getElementById('rawJsonDisplay');

  // Load default preset on startup
  presetSelect.value = 'ex1';
  transcriptInput.value = PRESETS['ex1'];

  // Preset Selection
  presetSelect.addEventListener('change', (e) => {
    const val = e.target.value;
    if (val && PRESETS[val]) {
      transcriptInput.value = PRESETS[val];
      classifyTranscript();
    }
  });

  // Clear Button
  clearBtn.addEventListener('click', () => {
    transcriptInput.value = '';
    presetSelect.value = '';
    resultPlaceholder.classList.remove('hidden');
    resultContent.classList.add('hidden');
  });

  // Noise Simulator
  noiseBtn.addEventListener('click', () => {
    let text = transcriptInput.value;
    if (!text.trim()) return;

    // Simulate typical ASR errors
    text = text.replace(/whatsapp/gi, 'watsp')
               .replace(/details/gi, 'detils')
               .replace(/price/gi, 'praic')
               .replace(/interested/gi, 'intrested')
               .replace(/\?/g, ' ..')
               .replace(/kaise/gi, 'kaisey');

    transcriptInput.value = text;
  });

  // Classify Button
  classifyBtn.addEventListener('click', () => {
    classifyTranscript();
  });

  // Copy JSON
  copyJsonBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(rawJsonDisplay.textContent);
    copyJsonBtn.textContent = 'Copied!';
    setTimeout(() => { copyJsonBtn.textContent = 'Copy JSON'; }, 1500);
  });

  // Tab switching
  const tabBtns = document.querySelectorAll('.tab-btn');
  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      tabBtns.forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetTab = document.getElementById(btn.dataset.tab);
      if (targetTab) targetTab.classList.add('active');
    });
  });

  async function classifyTranscript() {
    const transcript = transcriptInput.value.trim();
    if (!transcript) {
      alert('Please enter or select a call transcript first.');
      return;
    }

    classifyBtn.disabled = true;
    classifyBtn.innerHTML = '<span>Analyzing...</span>';

    try {
      const response = await fetch('/classify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ transcript, explain: true })
      });

      if (!response.ok) {
        throw new Error(`API error: ${response.statusText}`);
      }

      const data = await response.json();
      displayResults(data);

    } catch (err) {
      console.error(err);
      alert('Classification request failed. Ensure the server is running.');
    } finally {
      classifyBtn.disabled = false;
      classifyBtn.innerHTML = `<span>Classify Intent</span>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>`;
    }
  }

  function displayResults(data) {
    resultPlaceholder.classList.add('hidden');
    resultContent.classList.remove('hidden');

    const isInterested = data.classification === 'INTERESTED';
    decisionBadge.textContent = data.classification;
    decisionBadge.className = 'badge-large ' + (isInterested ? 'badge-interested' : 'badge-not-interested');

    const confidencePct = Math.round(data.confidence * 100);
    confidenceValue.textContent = `${confidencePct}%`;
    confidenceFill.style.width = `${confidencePct}%`;
    confidenceFill.style.background = isInterested 
      ? 'linear-gradient(90deg, #6366f1, #10b981)' 
      : 'linear-gradient(90deg, #6366f1, #f43f5e)';

    priorityTier.textContent = `Priority ${data.priority_level}`;
    languagesDetected.textContent = data.languages_detected.join(', ') || 'English';
    customerTurnsCount.textContent = `${data.customer_turns_count} turns (${data.total_turns_count} total)`;
    
    leadRuleApplied.textContent = data.rule_applied;
    leadRuleApplied.className = 'm-value ' + (isInterested ? 'text-emerald' : 'text-ruby');

    decisionReason.textContent = data.reason;

    // Render signals
    signalTags.innerHTML = '';
    if (data.signals_detected && data.signals_detected.length > 0) {
      data.signals_detected.forEach(sig => {
        const tag = document.createElement('span');
        const isPos = ['STRONG_INTEREST', 'QUESTION_INQUIRY', 'CONDITIONAL_FUTURE', 'SKEPTICISM'].includes(sig);
        tag.className = `signal-tag ${isPos ? 'positive' : 'negative'}`;
        tag.textContent = sig;
        signalTags.appendChild(tag);
      });
    } else {
      const tag = document.createElement('span');
      tag.className = 'signal-tag';
      tag.textContent = 'NO_EXPLICIT_KEYWORD_SIGNAL';
      signalTags.appendChild(tag);
    }

    // Render turns
    turnsContainer.innerHTML = '';
    if (data.turns && data.turns.length > 0) {
      data.turns.forEach(t => {
        const turnCard = document.createElement('div');
        turnCard.className = `turn-card ${t.role}`;
        
        const header = document.createElement('div');
        header.className = 'turn-header';
        
        const pill = document.createElement('span');
        pill.className = `speaker-pill speaker-${t.role}`;
        pill.textContent = `${t.role} (Turn #${t.turn_index + 1})`;
        header.appendChild(pill);

        if (t.signals && t.signals.length > 0) {
          const sigSpan = document.createElement('span');
          sigSpan.className = 'signal-tag positive';
          sigSpan.style.fontSize = '0.7rem';
          sigSpan.textContent = t.signals.join(', ');
          header.appendChild(sigSpan);
        }

        const body = document.createElement('div');
        body.className = 'turn-text';
        body.textContent = t.text;

        turnCard.appendChild(header);
        turnCard.appendChild(body);
        turnsContainer.appendChild(turnCard);
      });
    }

    // Render strict Section 20 JSON
    const strictJson = {
      "classification": data.classification
    };
    rawJsonDisplay.textContent = JSON.stringify(strictJson, null, 2);
  }

  // Initial trigger
  classifyTranscript();
});
