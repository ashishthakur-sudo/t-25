/**
 * CogniBot Client Application
 * Full-featured pair-programming AI with conversational learning,
 * persistent memory management, and bidirectional Voice (STT & TTS).
 */

// Application State
const state = {
  sessionId: 'default',
  autoSpeak: true,
  speechRate: 1.0,
  speechPitch: 1.0,
  selectedVoice: null,
  availableVoices: [],
  isListening: false,
  isSpeaking: false,
  recognition: null,
  currentUtterance: null,
  activeView: 'chat',
  categories: ['General'],
  currentEditId: null,
  pendingAttachment: null
};

// Brain Glowing Energy Icon SVG
const GLOWING_BRAIN_SVG = `
<svg class="glowing-brain-svg" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="msgBrainGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#00f5ff" stop-opacity="0.9" />
      <stop offset="60%" stop-color="#8b5cf6" stop-opacity="0.5" />
      <stop offset="100%" stop-color="#ec4899" stop-opacity="0" />
    </radialGradient>
    <linearGradient id="msgBrainGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#00f5ff" />
      <stop offset="50%" stop-color="#a855f7" />
      <stop offset="100%" stop-color="#ec4899" />
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="42" fill="url(#msgBrainGlow)" class="energy-pulse-core" />
  <g stroke="url(#msgBrainGrad)" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round" fill="none">
    <path d="M48 20 C35 19 22 28 21 42 C20 52 27 59 25 68 C23 76 31 82 46 82 C47 82 48 80 48 78 Z" />
    <path d="M52 20 C65 19 78 28 79 42 C80 52 73 59 75 68 C77 76 69 82 54 82 C53 82 52 80 52 78 Z" />
    <path d="M30 36 C36 34 42 38 46 36" />
    <path d="M26 48 C33 46 38 52 46 50" />
    <path d="M30 63 C36 61 41 68 46 66" />
    <path d="M70 36 C64 34 58 38 54 36" />
    <path d="M74 48 C67 46 62 52 54 50" />
    <path d="M70 63 C64 61 59 68 54 66" />
    <circle cx="34" cy="35" r="2.2" fill="#00f5ff" />
    <circle cx="66" cy="35" r="2.2" fill="#00f5ff" />
    <circle cx="28" cy="50" r="2.2" fill="#ffffff" />
    <circle cx="72" cy="50" r="2.2" fill="#ffffff" />
    <circle cx="40" cy="65" r="2.2" fill="#ec4899" />
    <circle cx="60" cy="65" r="2.2" fill="#ec4899" />
  </g>
</svg>
`;

// DOM Elements
const elements = {
  chatMessages: document.getElementById('chatMessages'),
  chatInput: document.getElementById('chatInput'),
  btnSend: document.getElementById('btnSend'),
  btnMic: document.getElementById('btnMic'),
  btnAttach: document.getElementById('btnAttach'),
  btnUrl: document.getElementById('btnUrl'),
  chatFileInput: document.getElementById('chatFileInput'),
  attachmentPreviewBar: document.getElementById('attachmentPreviewBar'),
  attachmentThumb: document.getElementById('attachmentThumb'),
  attachmentIcon: document.getElementById('attachmentIcon'),
  attachmentName: document.getElementById('attachmentName'),
  attachmentSize: document.getElementById('attachmentSize'),
  btnRemoveAttachment: document.getElementById('btnRemoveAttachment'),
  
  // URL Modal
  urlModal: document.getElementById('urlModal'),
  btnCloseUrlModal: document.getElementById('btnCloseUrlModal'),
  urlModalInput: document.getElementById('urlModalInput'),
  btnConfirmFetchUrl: document.getElementById('btnConfirmFetchUrl'),

  btnAutoSpeak: document.getElementById('btnAutoSpeak'),
  btnStopSpeech: document.getElementById('btnStopSpeech'),
  btnClearChat: document.getElementById('btnClearChat'),
  voiceWave: document.getElementById('voiceWave'),
  statMemories: document.getElementById('statMemories'),
  statCategories: document.getElementById('statCategories'),
  
  // Knowledge Base
  kbGrid: document.getElementById('kbGrid'),
  kbSearchInput: document.getElementById('kbSearchInput'),
  kbCategorySelect: document.getElementById('kbCategorySelect'),
  btnAddKnowledge: document.getElementById('btnAddKnowledge'),
  btnExportKb: document.getElementById('btnExportKb'),
  fileImportKb: document.getElementById('fileImportKb'),
  
  // Modal
  knowledgeModal: document.getElementById('knowledgeModal'),
  modalTitle: document.getElementById('modalTitle'),
  kbModalTitleInput: document.getElementById('kbModalTitleInput'),
  kbModalCategoryInput: document.getElementById('kbModalCategoryInput'),
  kbModalContentInput: document.getElementById('kbModalContentInput'),
  kbModalTagsInput: document.getElementById('kbModalTagsInput'),
  btnSaveModal: document.getElementById('btnSaveModal'),
  btnCloseModal: document.getElementById('btnCloseModal'),
  
  // Ingest
  dropZone: document.getElementById('dropZone'),
  docFileInput: document.getElementById('docFileInput'),
  uploadCategory: document.getElementById('uploadCategory'),
  ingestStatus: document.getElementById('ingestStatus'),
  
  // Settings
  voiceSelect: document.getElementById('voiceSelect'),
  speechRateSlider: document.getElementById('speechRateSlider'),
  speechPitchSlider: document.getElementById('speechPitchSlider'),
  rateValDisplay: document.getElementById('rateValDisplay'),
  pitchValDisplay: document.getElementById('pitchValDisplay'),
  autoSpeakCheckbox: document.getElementById('autoSpeakCheckbox'),
  btnTestVoice: document.getElementById('btnTestVoice'),
  providerSelect: document.getElementById('providerSelect'),
  ollamaUrlInput: document.getElementById('ollamaUrlInput'),
  ollamaModelInput: document.getElementById('ollamaModelInput'),
  geminiKeyInput: document.getElementById('geminiKeyInput'),
  geminiModelInput: document.getElementById('geminiModelInput'),
  openaiKeyInput: document.getElementById('openaiKeyInput'),
  openaiModelInput: document.getElementById('openaiModelInput'),
  btnSaveSettings: document.getElementById('btnSaveSettings'),
  
  toastContainer: document.getElementById('toastContainer')
};

// --- Initialization ---
document.addEventListener('DOMContentLoaded', () => {
  initVoiceEngine();
  initNavigation();
  initChat();
  initKnowledgeBase();
  initIngestion();
  initSettings();
  loadStats();
  loadChatHistory();
});

// --- Navigation Tabs ---
function initNavigation() {
  document.querySelectorAll('.nav-item').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetView = btn.getAttribute('data-view');
      switchView(targetView);
    });
  });
}

function switchView(viewName) {
  state.activeView = viewName;
  document.querySelectorAll('.nav-item').forEach(b => {
    b.classList.toggle('active', b.getAttribute('data-view') === viewName);
  });
  document.querySelectorAll('.view-panel').forEach(panel => {
    panel.classList.toggle('active', panel.id === `view-${viewName}`);
  });
  
  if (viewName === 'kb') {
    loadMemories();
  } else if (viewName === 'settings') {
    loadSettings();
  }
}

// --- Voice Engine (STT & TTS) ---
function initVoiceEngine() {
  // 1. Text-To-Speech (Speech Synthesis)
  if ('speechSynthesis' in window) {
    const updateVoices = () => {
      state.availableVoices = window.speechSynthesis.getVoices();
      populateVoiceList();
    };
    updateVoices();
    if (window.speechSynthesis.onvoiceschanged !== undefined) {
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  } else {
    showToast('⚠️ Speech Synthesis not supported in this browser.', 'warning');
  }

  // 2. Speech-To-Text (Speech Recognition)
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (SpeechRecognition) {
    state.recognition = new SpeechRecognition();
    state.recognition.continuous = false;
    state.recognition.interimResults = true;
    state.recognition.lang = 'en-US';

    state.recognition.onstart = () => {
      state.isListening = true;
      elements.btnMic.classList.add('listening');
      elements.voiceWave.classList.add('active');
    };

    state.recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; ++i) {
        if (event.results[i].isFinal) {
          finalTranscript += event.results[i][0].transcript;
        } else {
          interimTranscript += event.results[i][0].transcript;
        }
      }

      if (finalTranscript) {
        elements.chatInput.value = finalTranscript.trim();
        stopListening();
        sendMessage(); // automatically send on recognized voice query
      } else if (interimTranscript) {
        elements.chatInput.value = interimTranscript;
      }
    };

    state.recognition.onerror = (event) => {
      console.warn('Speech recognition error:', event.error);
      stopListening();
      if (event.error === 'not-allowed') {
        showToast('Microphone access was denied. Please allow microphone permissions.', 'danger');
      }
    };

    state.recognition.onend = () => {
      stopListening();
    };

    elements.btnMic.addEventListener('click', toggleListening);
  } else {
    elements.btnMic.title = 'Speech Recognition is not supported in this browser';
    elements.btnMic.style.opacity = '0.5';
    elements.btnMic.addEventListener('click', () => {
      showToast('Speech Recognition requires Chrome, Edge, or a WebSpeech-compatible browser.', 'warning');
    });
  }

  // Auto-speak toggle button in header
  elements.btnAutoSpeak.addEventListener('click', () => {
    state.autoSpeak = !state.autoSpeak;
    updateAutoSpeakButton();
    showToast(`Auto-Voice readout is now ${state.autoSpeak ? 'ENABLED' : 'MUTED'}.`);
  });

  // Stop speech button
  elements.btnStopSpeech.addEventListener('click', stopSpeaking);
}

function populateVoiceList() {
  if (!elements.voiceSelect) return;
  elements.voiceSelect.innerHTML = '';
  
  state.availableVoices.forEach((voice, index) => {
    const opt = document.createElement('option');
    opt.value = voice.name;
    opt.textContent = `${voice.name} (${voice.lang})${voice.default ? ' — Default' : ''}`;
    elements.voiceSelect.appendChild(opt);
  });

  // Pick preferred voice if available
  const savedVoiceName = localStorage.getItem('cognibot_voice_name');
  if (savedVoiceName) {
    const found = state.availableVoices.find(v => v.name === savedVoiceName);
    if (found) {
      elements.voiceSelect.value = savedVoiceName;
      state.selectedVoice = found;
      return;
    }
  }

  // Default to a high quality English voice if found
  const naturalVoice = state.availableVoices.find(v => (v.name.includes('Natural') || v.name.includes('Google') || v.name.includes('David') || v.name.includes('Zira') || v.name.includes('Samantha')) && v.lang.startsWith('en'));
  if (naturalVoice) {
    elements.voiceSelect.value = naturalVoice.name;
    state.selectedVoice = naturalVoice;
  } else if (state.availableVoices.length > 0) {
    state.selectedVoice = state.availableVoices[0];
  }
}

function toggleListening() {
  if (state.isListening) {
    stopListening();
  } else {
    startListening();
  }
}

function startListening() {
  if (!state.recognition) return;
  stopSpeaking(); // stop any current speech before listening
  try {
    state.recognition.start();
  } catch (e) {
    console.error('Failed to start speech recognition:', e);
  }
}

function stopListening() {
  state.isListening = false;
  elements.btnMic.classList.remove('listening');
  elements.voiceWave.classList.remove('active');
  if (state.recognition) {
    try { state.recognition.stop(); } catch (e) {}
  }
}

function speakText(text) {
  if (!('speechSynthesis' in window)) return;
  if (!text || !text.trim()) return;

  stopSpeaking();

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = state.speechRate || 1.0;
  utterance.pitch = state.speechPitch || 1.0;

  if (state.selectedVoice) {
    utterance.voice = state.selectedVoice;
  }

  utterance.onstart = () => {
    state.isSpeaking = true;
    elements.btnStopSpeech.style.display = 'flex';
  };

  utterance.onend = () => {
    state.isSpeaking = false;
    elements.btnStopSpeech.style.display = 'none';
  };

  utterance.onerror = () => {
    state.isSpeaking = false;
    elements.btnStopSpeech.style.display = 'none';
  };

  state.currentUtterance = utterance;
  window.speechSynthesis.speak(utterance);
}

function stopSpeaking() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  state.isSpeaking = false;
  elements.btnStopSpeech.style.display = 'none';
}

function updateAutoSpeakButton() {
  elements.btnAutoSpeak.classList.toggle('active', state.autoSpeak);
  elements.btnAutoSpeak.innerHTML = state.autoSpeak ? '🔊' : '🔇';
  elements.btnAutoSpeak.title = state.autoSpeak ? 'Voice readout is ON (click to mute)' : 'Voice readout is MUTED (click to enable)';
}

// --- Chat View ---
// --- Chat View ---
function initChat() {
  elements.btnSend.addEventListener('click', sendMessage);
  
  elements.chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  // Attach button & file input
  elements.btnAttach.addEventListener('click', () => {
    elements.chatFileInput.click();
  });

  elements.chatFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleAttachmentSelect(e.target.files[0]);
    }
  });

  elements.btnRemoveAttachment.addEventListener('click', clearAttachment);

  // URL modal triggers
  elements.btnUrl.addEventListener('click', openUrlModal);
  elements.btnCloseUrlModal.addEventListener('click', closeUrlModal);
  elements.btnConfirmFetchUrl.addEventListener('click', fetchUrlFromModal);
  elements.urlModalInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      fetchUrlFromModal();
    }
  });

  // Drag and drop onto chat
  elements.chatMessages.addEventListener('dragover', (e) => {
    e.preventDefault();
  });

  elements.chatMessages.addEventListener('drop', (e) => {
    e.preventDefault();
    if (e.dataTransfer.files.length > 0) {
      handleAttachmentSelect(e.dataTransfer.files[0]);
    }
  });

  elements.btnClearChat.addEventListener('click', async () => {
    if (confirm('Are you sure you want to clear the conversation history?')) {
      await fetch('/api/chat/clear', { method: 'POST' });
      elements.chatMessages.innerHTML = '';
      showWelcomeHero();
      showToast('Conversation cleared.');
    }
  });

  // Prompt chip click handlers
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      elements.chatInput.value = chip.getAttribute('data-prompt');
      sendMessage();
    });
  });

  updateAutoSpeakButton();
}

function handleAttachmentSelect(file) {
  const isImage = file.type.startsWith('image/');
  const isPdf = file.name.toLowerCase().endsWith('.pdf');
  
  state.pendingAttachment = {
    file: file,
    name: file.name,
    isImage: isImage,
    isPdf: isPdf
  };

  elements.attachmentName.textContent = file.name;
  elements.attachmentSize.textContent = `${(file.size / 1024).toFixed(1)} KB • ${isImage ? 'Image' : isPdf ? 'PDF Document' : 'Document'}`;
  
  if (isImage) {
    const reader = new FileReader();
    reader.onload = (e) => {
      elements.attachmentThumb.src = e.target.result;
      elements.attachmentThumb.style.display = 'block';
      elements.attachmentIcon.style.display = 'none';
    };
    reader.readAsDataURL(file);
  } else {
    elements.attachmentThumb.style.display = 'none';
    elements.attachmentIcon.style.display = 'inline';
    elements.attachmentIcon.textContent = isPdf ? '📄' : '📁';
  }

  elements.attachmentPreviewBar.classList.add('active');
  elements.chatInput.focus();
  showToast(`Attached ${file.name}`);
}

function clearAttachment() {
  state.pendingAttachment = null;
  elements.chatFileInput.value = '';
  elements.attachmentPreviewBar.classList.remove('active');
  elements.attachmentThumb.src = '';
}

function openUrlModal() {
  elements.urlModalInput.value = '';
  elements.urlModal.classList.add('active');
  setTimeout(() => elements.urlModalInput.focus(), 100);
}

function closeUrlModal() {
  elements.urlModal.classList.remove('active');
}

async function fetchUrlFromModal() {
  const url = elements.urlModalInput.value.trim();
  if (!url) {
    showToast('Please enter a website URL.', 'warning');
    return;
  }
  closeUrlModal();

  // Remove welcome hero if present
  const hero = document.querySelector('.welcome-hero');
  if (hero) hero.remove();

  appendMessageRow('user', `🔗 Fetch and learn from: ${url}`);
  const typingId = showTypingIndicator();

  try {
    const res = await fetch('/api/extract/url', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, session_id: state.sessionId })
    });

    removeTypingIndicator(typingId);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || 'Failed to extract URL');
    }

    appendMessageRow('assistant', data.display_message, {
      speechText: data.speech_text,
      sources: data.memories || [],
      learned: true
    });

    if (state.autoSpeak && data.speech_text) {
      speakText(data.speech_text);
    }
    loadStats();
    showToast('Website content extracted & learned!', 'success');
  } catch (err) {
    removeTypingIndicator(typingId);
    appendMessageRow('assistant', `⚠️ Failed to fetch website: ${err.message}`);
  }
}

async function sendMessage() {
  const message = elements.chatInput.value.trim();
  const attachment = state.pendingAttachment;

  if (!message && !attachment) return;

  // Clear input & attachment
  elements.chatInput.value = '';
  elements.chatInput.style.height = 'auto';

  // Remove welcome hero if present
  const hero = document.querySelector('.welcome-hero');
  if (hero) hero.remove();

  // 1. If sending with an attachment (PDF, Image, Doc)
  if (attachment) {
    clearAttachment();
    const promptText = message;
    
    appendMessageRow('user', `📎 **Attached:** \`${attachment.name}\`\n\n${message ? message : ''}`);
    const typingId = showTypingIndicator();

    const formData = new FormData();
    formData.append('file', attachment.file);
    formData.append('message', promptText);
    formData.append('session_id', state.sessionId);

    try {
      const response = await fetch('/api/chat/attachment', {
        method: 'POST',
        body: formData
      });

      removeTypingIndicator(typingId);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to process attachment');
      }

      appendMessageRow('assistant', data.text, {
        speechText: data.speech_text,
        sources: data.sources,
        learned: data.learned
      });

      if (state.autoSpeak && data.speech_text) {
        speakText(data.speech_text);
      }
      loadStats();
      if (data.document_id) {
        watchDocumentAnalysis(data.document_id, attachment.name);
      }
    } catch (err) {
      removeTypingIndicator(typingId);
      appendMessageRow('assistant', `⚠️ Failed to analyze file: ${err.message}`);
    }
    return;
  }

  // 2. Normal text message
  appendMessageRow('user', message);
  const typingId = showTypingIndicator();

  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: message, session_id: state.sessionId })
    });

    removeTypingIndicator(typingId);

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: Failed to get response`);
    }

    const data = await response.json();

    appendMessageRow('assistant', data.text, {
      speechText: data.speech_text,
      sources: data.sources,
      learned: data.learned
    });

    if (state.autoSpeak && data.speech_text) {
      speakText(data.speech_text);
    }

    if (data.learned) {
      loadStats();
    }

  } catch (err) {
    removeTypingIndicator(typingId);
    appendMessageRow('assistant', `⚠️ Sorry, an error occurred: ${err.message}`);
  }
}

function appendMessageRow(role, content, meta = {}) {
  const row = document.createElement('div');
  row.className = `message-row ${role}`;

  const avatar = document.createElement('div');
  avatar.className = 'message-avatar';
  if (role === 'assistant') {
    avatar.innerHTML = GLOWING_BRAIN_SVG;
  } else {
    avatar.textContent = '👤';
  }

  const bubble = document.createElement('div');
  bubble.className = 'message-bubble';

  const contentBox = document.createElement('div');
  contentBox.className = 'bubble-content';
  contentBox.innerHTML = formatMarkdown(content);

  bubble.appendChild(contentBox);

  // If new memory learned
  if (meta.learned) {
    const learnedBadge = document.createElement('div');
    learnedBadge.className = 'learned-badge';
    learnedBadge.innerHTML = '✨ Stored in Knowledge Base';
    bubble.appendChild(learnedBadge);
  }

  // If sources cited
  if (meta.sources && meta.sources.length > 0) {
    const sourcesList = document.createElement('div');
    sourcesList.className = 'sources-list';
    meta.sources.forEach(src => {
      const pill = document.createElement('span');
      pill.className = 'source-pill';
      pill.innerHTML = `📚 <b>${escapeHtml(src.title)}</b> (${escapeHtml(src.category)})`;
      sourcesList.appendChild(pill);
    });
    bubble.appendChild(sourcesList);
  }

  // Assistant actions (Speak text, Copy)
  if (role === 'assistant') {
    const actions = document.createElement('div');
    actions.className = 'message-actions';

    const btnSpeak = document.createElement('button');
    btnSpeak.className = 'btn-msg-action';
    btnSpeak.innerHTML = '🔊 Speak';
    btnSpeak.title = 'Listen to this response';
    btnSpeak.addEventListener('click', () => {
      speakText(meta.speechText || content);
    });

    const btnCopy = document.createElement('button');
    btnCopy.className = 'btn-msg-action';
    btnCopy.innerHTML = '📋 Copy';
    btnCopy.title = 'Copy to clipboard';
    btnCopy.addEventListener('click', () => {
      navigator.clipboard.writeText(content).then(() => {
        btnCopy.innerHTML = '✅ Copied';
        setTimeout(() => { btnCopy.innerHTML = '📋 Copy'; }, 2000);
      });
    });

    actions.appendChild(btnSpeak);
    actions.appendChild(btnCopy);
    bubble.appendChild(actions);
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  elements.chatMessages.appendChild(row);

  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
}

// Polls a background document analysis job and posts its report to the chat when done
function pollDocument(docId, onProgress) {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const res = await fetch(`/api/documents/${docId}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const doc = await res.json();
        if (doc.status === 'done' || doc.status === 'failed') {
          resolve(doc);
          return;
        }
        if (onProgress) onProgress(doc);
      } catch (err) {
        // Server may be briefly unavailable; keep trying
      }
      setTimeout(tick, 4000);
    };
    tick();
  });
}

async function watchDocumentAnalysis(docId, filename) {
  const typingId = showTypingIndicator();
  const doc = await pollDocument(docId);
  removeTypingIndicator(typingId);

  if (doc.status === 'done') {
    appendMessageRow('assistant', doc.result, { learned: true });
    showToast(`Analysis & research ready for ${filename}`, 'success');
    if (state.autoSpeak) {
      speakText(`My analysis and research on ${filename} is ready.`);
    }
  } else {
    appendMessageRow('assistant', `⚠️ I stored \`${filename}\`, but the analysis step failed: ${doc.error}`);
  }
  loadStats();
}

function showTypingIndicator() {
  const id = 'typing-' + Date.now();
  const row = document.createElement('div');
  row.id = id;
  row.className = 'message-row assistant';
  row.innerHTML = `
    <div class="message-avatar">${GLOWING_BRAIN_SVG}</div>
    <div class="message-bubble">
      <div class="bubble-content" style="display:flex; align-items:center; gap:8px;">
        <span style="font-size:0.85rem; color:var(--text-muted);">T25-chatbot is searching memory...</span>
        <div class="voice-wave active" style="height:14px;">
          <div class="wave-bar"></div><div class="wave-bar"></div><div class="wave-bar"></div>
        </div>
      </div>
    </div>
  `;
  elements.chatMessages.appendChild(row);
  elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

async function loadChatHistory() {
  try {
    const res = await fetch(`/api/chat/history?session_id=${state.sessionId}`);
    const data = await res.json();
    if (data.history && data.history.length > 0) {
      elements.chatMessages.innerHTML = '';
      data.history.forEach(item => {
        appendMessageRow(item.role, item.content);
      });
    } else {
      showWelcomeHero();
    }
  } catch (e) {
    showWelcomeHero();
  }
}

function showWelcomeHero() {
  elements.chatMessages.innerHTML = `
    <div class="welcome-hero">
      <div class="hero-avatar">${GLOWING_BRAIN_SVG}</div>
      <h2>T25-chatbot</h2>
      <p>I am <b>T25-chatbot</b>, your adaptive learning AI companion. Teach me facts, upload images/PDFs, paste links, and ask me anything anytime via chat or voice!</p>
      <div class="prompt-chips">
        <button class="chip" data-prompt="Remember that my pet dog is named Max and he loves tennis balls.">🐕 "Remember that my dog is Max..."</button>
        <button class="chip" data-prompt="What have you learned so far?">📚 "What have you learned so far?"</button>
        <button class="chip" data-prompt="Who are you and what can you do?">✨ "What can you do?"</button>
        <button class="chip" data-prompt="Note down: Project launch is scheduled for December 15.">🚀 "Note down: Project launch..."</button>
      </div>
    </div>
  `;
  // Re-bind click events
  document.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      elements.chatInput.value = chip.getAttribute('data-prompt');
      sendMessage();
    });
  });
}

// --- Knowledge Base View ---
function initKnowledgeBase() {
  elements.btnAddKnowledge.addEventListener('click', () => openKnowledgeModal());
  elements.btnCloseModal.addEventListener('click', closeKnowledgeModal);
  elements.btnSaveModal.addEventListener('click', saveKnowledgeModal);
  
  elements.kbSearchInput.addEventListener('input', debounce(() => loadMemories(), 300));
  elements.kbCategorySelect.addEventListener('change', () => loadMemories());

  elements.btnExportKb.addEventListener('click', () => {
    window.location.href = '/api/memories/export';
  });

  elements.fileImportKb.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    try {
      const text = await file.text();
      const items = JSON.parse(text);
      const res = await fetch('/api/memories/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(items)
      });
      const data = await res.json();
      showToast(`Imported ${data.imported_count} knowledge items!`, 'success');
      loadMemories();
      loadStats();
    } catch (err) {
      showToast(`Import error: ${err.message}`, 'danger');
    }
    e.target.value = '';
  });
}

async function loadMemories() {
  const search = elements.kbSearchInput.value.trim();
  const category = elements.kbCategorySelect.value;

  try {
    const res = await fetch(`/api/memories?search=${encodeURIComponent(search)}&category=${encodeURIComponent(category)}`);
    const data = await res.json();
    
    // Update categories dropdown
    state.categories = data.categories || ['General'];
    updateCategoryDropdowns();

    // Render cards
    renderKnowledgeCards(data.memories || []);
    loadStats();
  } catch (err) {
    elements.kbGrid.innerHTML = `<div style="color:var(--text-muted); padding:20px;">Failed to load knowledge base: ${err.message}</div>`;
  }
}

function renderKnowledgeCards(memories) {
  if (memories.length === 0) {
    elements.kbGrid.innerHTML = `
      <div style="grid-column: 1/-1; text-align:center; padding: 60px 20px; color:var(--text-muted);">
        <div style="font-size:40px; margin-bottom:12px;">📂</div>
        <h3>No knowledge items found</h3>
        <p style="font-size:0.9rem; margin-top:6px;">Add items manually or tell CogniBot <i>"Remember that..."</i> in the chat!</p>
      </div>
    `;
    return;
  }

  elements.kbGrid.innerHTML = '';
  memories.forEach(m => {
    const card = document.createElement('div');
    card.className = 'kb-card';
    card.innerHTML = `
      <div class="card-header">
        <h4 class="card-title">${escapeHtml(m.title)}</h4>
        <span class="card-tag">${escapeHtml(m.category)}</span>
      </div>
      <div class="card-content">${escapeHtml(m.content)}</div>
      <div class="card-footer">
        <span>${m.source || 'manual'} • ${formatDate(m.created_at)}</span>
        <div class="card-actions">
          <button class="btn-card-action edit" title="Edit">✏️</button>
          <button class="btn-card-action delete" title="Delete">🗑️</button>
        </div>
      </div>
    `;

    card.querySelector('.edit').addEventListener('click', () => openKnowledgeModal(m));
    card.querySelector('.delete').addEventListener('click', async () => {
      if (confirm(`Delete memory "${m.title}"?`)) {
        await fetch(`/api/memories/${m.id}`, { method: 'DELETE' });
        showToast('Memory item deleted');
        loadMemories();
        loadStats();
      }
    });

    elements.kbGrid.appendChild(card);
  });
}

function updateCategoryDropdowns() {
  const currentVal = elements.kbCategorySelect.value;
  elements.kbCategorySelect.innerHTML = '<option value="all">All Categories</option>';
  state.categories.forEach(cat => {
    const opt = document.createElement('option');
    opt.value = cat;
    opt.textContent = cat;
    elements.kbCategorySelect.appendChild(opt);
  });
  if (currentVal && state.categories.includes(currentVal)) {
    elements.kbCategorySelect.value = currentVal;
  }
}

function openKnowledgeModal(item = null) {
  state.currentEditId = item ? item.id : null;
  elements.modalTitle.textContent = item ? 'Edit Knowledge' : 'Add New Knowledge';
  elements.kbModalTitleInput.value = item ? item.title : '';
  elements.kbModalCategoryInput.value = item ? item.category : 'General';
  elements.kbModalContentInput.value = item ? item.content : '';
  elements.kbModalTagsInput.value = item ? (item.tags || '') : '';
  elements.knowledgeModal.classList.add('active');
}

function closeKnowledgeModal() {
  elements.knowledgeModal.classList.remove('active');
  state.currentEditId = null;
}

async function saveKnowledgeModal() {
  const title = elements.kbModalTitleInput.value.trim();
  const category = elements.kbModalCategoryInput.value.trim() || 'General';
  const content = elements.kbModalContentInput.value.trim();
  const tags = elements.kbModalTagsInput.value.trim();

  if (!title || !content) {
    showToast('Title and Content are required.', 'warning');
    return;
  }

  const payload = { title, category, content, tags };

  try {
    if (state.currentEditId) {
      await fetch(`/api/memories/${state.currentEditId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      showToast('Knowledge item updated!', 'success');
    } else {
      await fetch('/api/memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      showToast('New knowledge saved!', 'success');
    }

    closeKnowledgeModal();
    loadMemories();
    loadStats();
  } catch (err) {
    showToast(`Error: ${err.message}`, 'danger');
  }
}

// --- Document Ingestion View ---
function initIngestion() {
  elements.dropZone.addEventListener('click', () => elements.docFileInput.click());
  
  elements.dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.dropZone.classList.add('dragover');
  });

  elements.dropZone.addEventListener('dragleave', () => {
    elements.dropZone.classList.remove('dragover');
  });

  elements.dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.dropZone.classList.remove('dragover');
    if (e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });

  elements.docFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
      handleFileUpload(e.target.files[0]);
    }
  });
}

async function handleFileUpload(file) {
  const category = elements.uploadCategory.value.trim() || 'Document';
  const formData = new FormData();
  formData.append('file', file);
  formData.append('category', category);
  formData.append('session_id', state.sessionId);

  elements.ingestStatus.style.display = 'block';
  elements.ingestStatus.innerHTML = `⏳ Ingesting and learning from <b>${escapeHtml(file.name)}</b>...`;

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');

    elements.ingestStatus.innerHTML = `
      <div style="color:var(--success); font-weight:600;">✅ ${escapeHtml(data.message)}</div>
      <p style="font-size:0.85rem; color:var(--text-muted); margin-top:4px;">CogniBot has ingested ${data.chunks_stored} knowledge sections and can now answer questions about them.</p>
    `;
    showToast(`Learned from ${file.name}!`, 'success');
    loadStats();

    if (data.document_id) {
      const statusLine = document.createElement('p');
      statusLine.style.cssText = 'font-size:0.85rem; margin-top:6px;';
      elements.ingestStatus.appendChild(statusLine);
      const doc = await pollDocument(data.document_id, (d) => {
        statusLine.textContent = `⏳ ${d.stage}...`;
      });
      statusLine.textContent = doc.status === 'done'
        ? '🔎 Analysis & research complete. The full report has been posted in the Chat tab and saved to memory.'
        : `⚠️ ${doc.error}`;
      if (doc.status === 'done') {
        loadChatHistory();
      }
      loadStats();
    }
  } catch (err) {
    elements.ingestStatus.innerHTML = `<div style="color:var(--danger);">⚠️ ${escapeHtml(err.message)}</div>`;
  }
}

// --- Settings View ---
function initSettings() {
  elements.voiceSelect.addEventListener('change', (e) => {
    const found = state.availableVoices.find(v => v.name === e.target.value);
    if (found) {
      state.selectedVoice = found;
      localStorage.setItem('cognibot_voice_name', found.name);
    }
  });

  elements.speechRateSlider.addEventListener('input', (e) => {
    state.speechRate = parseFloat(e.target.value);
    elements.rateValDisplay.textContent = state.speechRate.toFixed(1) + 'x';
  });

  elements.speechPitchSlider.addEventListener('input', (e) => {
    state.speechPitch = parseFloat(e.target.value);
    elements.pitchValDisplay.textContent = state.speechPitch.toFixed(1);
  });

  elements.autoSpeakCheckbox.addEventListener('change', (e) => {
    state.autoSpeak = e.target.checked;
    updateAutoSpeakButton();
  });

  elements.btnTestVoice.addEventListener('click', () => {
    speakText("Hello! This is how I speak when answering your questions.");
  });

  elements.providerSelect.addEventListener('change', (e) => {
    const prov = e.target.value;
    document.getElementById('ollamaFields').style.display = prov === 'ollama' ? 'flex' : 'none';
    document.getElementById('geminiFields').style.display = prov === 'gemini' ? 'block' : 'none';
    document.getElementById('openaiFields').style.display = prov === 'openai' ? 'block' : 'none';
  });

  elements.btnSaveSettings.addEventListener('click', saveSettings);
}

async function loadSettings() {
  try {
    const res = await fetch('/api/settings');
    const data = await res.json();

    if (data.speech_rate) {
      state.speechRate = parseFloat(data.speech_rate);
      elements.speechRateSlider.value = state.speechRate;
      elements.rateValDisplay.textContent = state.speechRate.toFixed(1) + 'x';
    }
    if (data.speech_pitch) {
      state.speechPitch = parseFloat(data.speech_pitch);
      elements.speechPitchSlider.value = state.speechPitch;
      elements.pitchValDisplay.textContent = state.speechPitch.toFixed(1);
    }
    if (data.auto_speak !== undefined) {
      state.autoSpeak = data.auto_speak === 'true';
      elements.autoSpeakCheckbox.checked = state.autoSpeak;
      updateAutoSpeakButton();
    }

    elements.providerSelect.value = data.ai_provider || 'local';
    document.getElementById('ollamaFields').style.display = data.ai_provider === 'ollama' ? 'flex' : 'none';
    document.getElementById('geminiFields').style.display = data.ai_provider === 'gemini' ? 'block' : 'none';
    document.getElementById('openaiFields').style.display = data.ai_provider === 'openai' ? 'block' : 'none';

    if (data.gemini_api_key_masked) {
      elements.geminiKeyInput.placeholder = data.gemini_api_key_masked;
    }
    if (data.gemini_model) {
      elements.geminiModelInput.value = data.gemini_model;
    }
    if (data.openai_api_key_masked) {
      elements.openaiKeyInput.placeholder = data.openai_api_key_masked;
    }
    if (data.openai_model) {
      elements.openaiModelInput.value = data.openai_model;
    }
    elements.ollamaUrlInput.value = data.ollama_url || 'http://localhost:11434';
    elements.ollamaModelInput.value = data.ollama_model || 'llama3.1:8b';
  } catch (err) {
    console.error('Failed to load settings:', err);
  }
}

async function saveSettings() {
  const payload = {
    speech_rate: elements.speechRateSlider.value,
    speech_pitch: elements.speechPitchSlider.value,
    auto_speak: elements.autoSpeakCheckbox.checked ? 'true' : 'false',
    ai_provider: elements.providerSelect.value,
    ollama_url: elements.ollamaUrlInput.value.trim(),
    ollama_model: elements.ollamaModelInput.value.trim(),
    gemini_model: elements.geminiModelInput.value.trim(),
    openai_model: elements.openaiModelInput.value.trim()
  };

  if (elements.geminiKeyInput.value.trim()) {
    payload.gemini_api_key = elements.geminiKeyInput.value.trim();
  }
  if (elements.openaiKeyInput.value.trim()) {
    payload.openai_api_key = elements.openaiKeyInput.value.trim();
  }

  try {
    await fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    showToast('Settings saved successfully!', 'success');
  } catch (err) {
    showToast(`Failed to save settings: ${err.message}`, 'danger');
  }
}

// --- Stats Counter ---
async function loadStats() {
  try {
    const res = await fetch('/api/stats');
    const data = await res.json();
    if (elements.statMemories) elements.statMemories.textContent = data.total_memories || 0;
    if (elements.statCategories) elements.statCategories.textContent = data.total_categories || 0;
  } catch (e) {}
}

// --- Utilities ---
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  const icon = type === 'success' ? '✅' : type === 'warning' ? '⚠️' : type === 'danger' ? '❌' : 'ℹ️';
  toast.innerHTML = `<span>${icon}</span><span>${escapeHtml(message)}</span>`;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatDate(isoStr) {
  if (!isoStr) return '';
  try {
    const d = new Date(isoStr);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch (e) {
    return isoStr;
  }
}

function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

function formatMarkdown(text) {
  if (!text) return '';
  let html = escapeHtml(text);

  // Images: ![alt](url)
  html = html.replace(/!\[(.*?)\]\((.*?)\)/g, '<div class="msg-img-wrap"><img src="$2" alt="$1" class="msg-img" loading="lazy" /></div>');

  // Links: [text](url)
  html = html.replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="msg-link">$1 ↗</a>');

  // Headings
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h2>$1</h2>');

  // Bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  // Italics
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  // Blockquotes
  html = html.replace(/^&gt; (.*$)/gim, '<blockquote>$1</blockquote>');
  // Bullet lists
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/s, '<ul>$1</ul>');
  // Newlines
  html = html.replace(/\n\n/g, '<p></p>');
  html = html.replace(/\n/g, '<br>');

  return html;
}
