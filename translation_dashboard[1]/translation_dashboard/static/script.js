document.addEventListener("DOMContentLoaded", function () {
    // Get DOM elements
    const translateForm = document.getElementById("translateForm");
    const inputText = document.getElementById("inputText");
    const resultText = document.getElementById("translatedText");
    const sourceLang = document.getElementById("source");
    const targetLang = document.getElementById("target");
    const swapBtn = document.getElementById("swapBtn"); 
    const playAudioBtn = document.getElementById("playAudioBtn");
    const audioPlayer = document.getElementById("audioPlayer");
    const recordBtn = document.getElementById("recordBtn");
    const detectedLangText = document.getElementById("detected_lang");
    const copyBtn = document.getElementById("copyBtn");
    
    let recognition;

    // Check for browser support of Speech Recognition API
    if (window.SpeechRecognition || window.webkitSpeechRecognition) {
        recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.continuous = false; // Stop recognition after a single phrase
        recognition.interimResults = false; // Only return final results
    } else {
        alert("Speech Recognition not supported. Use Chrome!");
    }

    swapBtn.addEventListener("click", () => {
        const temp = sourceLang.value;
        sourceLang.value = targetLang.value;
        targetLang.value = temp;
    
        if (inputText.value.trim()) {
            sendTranslation(inputText.value.trim());
        }
    });
    

    copyBtn.addEventListener("click", function () {
        const translatedText = resultText.innerText;
        navigator.clipboard.writeText(translatedText).then(() => {
            copyBtn.textContent = "✅ Copied!";
            setTimeout(() => {
                copyBtn.textContent = "📋 Copy";
            }, 1500);
        });
    });
    

    // 🎤 Handle speech recording
    recordBtn.addEventListener("click", function () {
        if (recordBtn.dataset.listening === "true") {
            recognition.stop();
            recordBtn.dataset.listening = "false";
            recordBtn.textContent = "🎙";
        } else {
            recognition.lang = "auto";
            recognition.start();
            recordBtn.dataset.listening = "true";
            recordBtn.textContent = "🎤 Listening...";
        }
    });

    // 🎙 When speech is recognized, update input and send translation request
    recognition.onresult = async function (event) {
        const spokenText = event.results[event.results.length - 1][0].transcript;
        inputText.value = spokenText;
        await sendTranslation(spokenText);
        recordBtn.textContent="🎙";
    };
    recognition.onerror = function () {
        recordBtn.textContent = "🎙";
        recordBtn.dataset.listening = "false";
    };

    // 📤 Handle form submission for text translation
    inputText.addEventListener("input", async function () {
        const text = inputText.value.trim();
        if (text) await sendTranslation(text);
    });
    
    document.getElementById("source").addEventListener("change", async function () {
        const text = inputText.value.trim();
        if (text) await sendTranslation(text);
    });
    
    document.getElementById("target").addEventListener("change", async function () {
        const text = inputText.value.trim();
        if (text) await sendTranslation(text);
    });
    

    // 🚀 Send translation request to backend
    async function sendTranslation(text) {
        const source = document.getElementById("source").value || "auto"; // Auto-detect language if none is set
        const target = document.getElementById("target").value;

        try {
            const res = await fetch("/translate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text, source, target }),
            });

            const data = await res.json();
            if (data.error) {
                alert("Translation Error: " + data.error);
                return;
            }
            if (data.translated) {
                // Show corrected text if available and different from original
                if (data.corrected && data.corrected.toLowerCase() !== data.original.toLowerCase()) {
                    resultText.innerHTML = `<strong>💬 Translated:</strong> ${data.translated}`;
                } else {
                    resultText.innerText = data.translated;
                }
                if (data.corrected && data.corrected.toLowerCase() !== data.original.toLowerCase()) {
                    document.getElementById("correctedText").innerText = `Did you mean: ${data.corrected}`;
                } else {
                    document.getElementById("correctedText").innerText = "";
                }
                
            
                copyBtn.style.display = "inline-block";
            
                if (data.source){
                    detectedLangText.innerText = `Detected Language: ${data.source.toUpperCase()}`;
                }
            
                if (data.audio_url) {
                    audioPlayer.src = data.audio_url;
                    audioPlayer.style.display = "block";
                    playAudioBtn.style.display = "block";
                }
            
                loadHistory();
            }
            
            else {
                resultText.innerText = "Error: " + data.error;
            }
        } catch (error) {
            alert("Failed to fetch translation. Please try again.");
        }
    }

    // 🎵 Play translated speech manually
    playAudioBtn.addEventListener("click", function () {
        audioPlayer.play();
    });

    // 📜 Load translation history from backend
    async function loadHistory() {
        try {
            const res = await fetch("/history");
            const data = await res.json();
            const list = document.getElementById("historyList");
            list.innerHTML = "";
            data.slice(-10).reverse().forEach(item => {
                list.innerHTML += `<li><b>${item.original}</b> → ${item.translated}</li>`;
            });
        } catch (error) {
            console.error("Failed to load history", error);
        }
    }

    // Initial Load: Fetch and display history
    loadHistory();
});

document.getElementById("listenInputBtn").addEventListener("click", async () => {
    const text = document.getElementById("inputText").value;
    const source = document.getElementById("source").value;

    const res = await fetch("/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, source, target: source })
    });

    const data = await res.json();
    if (data.audio_url) {
        const audio = document.getElementById("audioPlayer");
        audio.src = data.audio_url;
        audio.play();
    }
});



