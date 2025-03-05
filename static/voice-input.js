// voice-input.js - Speech recognition for interview answers

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const startButton = document.getElementById('startRecording');
    const stopButton = document.getElementById('stopRecording');
    const statusElement = document.getElementById('recordingStatus');
    const answerTextarea = document.getElementById('answer');
    
    // Check if browser supports SpeechRecognition
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
        statusElement.textContent = 'Speech recognition not supported in this browser';
        startButton.disabled = true;
        return;
    }
    
    // Setup speech recognition
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';
    
    let finalTranscript = '';
    
    // Events
    startButton.addEventListener('click', () => {
        finalTranscript = answerTextarea.value;
        recognition.start();
        startButton.disabled = true;
        stopButton.disabled = false;
        statusElement.textContent = 'Recording...';
        statusElement.classList.add('text-danger');
    });
    
    stopButton.addEventListener('click', () => {
        recognition.stop();
        startButton.disabled = false;
        stopButton.disabled = true;
        statusElement.textContent = 'Stopped';
        statusElement.classList.remove('text-danger');
    });
    
    recognition.onresult = (event) => {
        let interimTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; i++) {
            const transcript = event.results[i][0].transcript;
            
            if (event.results[i].isFinal) {
                finalTranscript += ' ' + transcript;
            } else {
                interimTranscript += transcript;
            }
        }
        
        answerTextarea.value = finalTranscript + interimTranscript;
    };
    
    recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        statusElement.textContent = `Error: ${event.error}`;
        startButton.disabled = false;
        stopButton.disabled = true;
    };
    
    recognition.onend = () => {
        startButton.disabled = false;
        stopButton.disabled = true;
        statusElement.textContent = 'Ready';
        statusElement.classList.remove('text-danger');
    };
});
