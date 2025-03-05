// voice-output.js - Text-to-speech for interview questions and feedback

document.addEventListener('DOMContentLoaded', () => {
    // Elements
    const speechToggle = document.getElementById('use_speech');
    const speechStatusElement = document.getElementById('speechStatus');
    
    // Get stored speech preference or default to true
    const useSpeech = localStorage.getItem('useSpeech') !== 'false';
    
    // Initialize speech synthesis
    const synth = window.speechSynthesis;
    let speaking = false;
    
    // Setup speech toggle if it exists on the page
    if (speechToggle) {
        speechToggle.checked = useSpeech;
        
        speechToggle.addEventListener('change', (e) => {
            const useSpeech = e.target.checked;
            localStorage.setItem('useSpeech', useSpeech);
            updateSpeechStatus();
        });
    }
    
    // Update speech status display
    function updateSpeechStatus() {
        if (speechStatusElement) {
            const useSpeech = localStorage.getItem('useSpeech') !== 'false';
            speechStatusElement.textContent = useSpeech ? 'Voice enabled' : 'Voice disabled';
            speechStatusElement.classList.toggle('text-success', useSpeech);
            speechStatusElement.classList.toggle('text-secondary', !useSpeech);
        }
    }
    
    // Call once on page load
    updateSpeechStatus();
    
    // Function to speak text
    function speakText(text, callback) {
        const useSpeech = localStorage.getItem('useSpeech') !== 'false';
        
        if (!useSpeech || !text || speaking) {
            if (callback) callback();
            return;
        }
        
        // Cancel any ongoing speech
        synth.cancel();
        
        // Split text into manageable chunks to avoid cutoffs
        const chunks = splitTextIntoChunks(text, 200);
        let currentChunk = 0;
        
        function speakNextChunk() {
            if (currentChunk >= chunks.length) {
                speaking = false;
                if (callback) callback();
                return;
            }
            
            const utterance = new SpeechSynthesisUtterance(chunks[currentChunk]);
            
            // Set voice properties
            utterance.rate = 1.0;
            utterance.pitch = 1.0;
            utterance.volume = 1.0;
            
            // Get voices and try to use a female voice if available
            const voices = synth.getVoices();
            if (voices.length > 0) {
                // Try to find a female voice
                const femaleVoice = voices.find(voice => 
                    voice.name.includes('female') || 
                    voice.name.includes('Female') ||
                    voice.name.includes('Samantha') ||
                    voice.name.includes('Victoria') ||
                    voice.name.includes('Google US English female'));
                
                utterance.voice = femaleVoice || voices[0];
            }
            
            speaking = true;
            
            utterance.onend = () => {
                currentChunk++;
                speakNextChunk();
            };
            
            utterance.onerror = (event) => {
                console.error('Speech synthesis error', event);
                speaking = false;
                currentChunk++;
                speakNextChunk();
            };
            
            synth.speak(utterance);
        }
        
        speakNextChunk();
    }
    
    // Helper function to split text into manageable chunks
    function splitTextIntoChunks(text, maxLength) {
        const chunks = [];
        
        // Split by sentences or paragraphs
        const sentences = text.match(/[^.!?]+[.!?]+/g) || [];
        
        let currentChunk = '';
        
        sentences.forEach(sentence => {
            if ((currentChunk + sentence).length <= maxLength) {
                currentChunk += sentence;
            } else {
                if (currentChunk) {
                    chunks.push(currentChunk.trim());
                }
                
                if (sentence.length <= maxLength) {
                    currentChunk = sentence;
                } else {
                    // If sentence is too long, split by chunks of maxLength
                    let remainingSentence = sentence;
                    while (remainingSentence.length > 0) {
                        // Try to split at word boundaries
                        let chunkEnd = maxLength;
                        if (remainingSentence.length > maxLength) {
                            chunkEnd = remainingSentence.lastIndexOf(' ', maxLength);
                            if (chunkEnd === -1) chunkEnd = maxLength; // If no space found, just split at maxLength
                        }
                        
                        chunks.push(remainingSentence.substring(0, chunkEnd).trim());
                        remainingSentence = remainingSentence.substring(chunkEnd);
                    }
                    currentChunk = '';
                }
            }
        });
        
        if (currentChunk) {
            chunks.push(currentChunk.trim());
        }
        
        return chunks.length > 0 ? chunks : [text];
    }
    
    // Function to speak question
    function speakQuestion() {
        const questionElement = document.querySelector('.interview-question h5');
        if (questionElement) {
            speakText("Here's your interview question: " + questionElement.textContent);
        }
    }
    
    // Function to speak feedback
    function speakFeedback() {
        const feedbackElement = document.querySelector('.feedback-content');
        if (feedbackElement) {
            speakText("Here's your feedback: " + feedbackElement.textContent.replace(/\s+/g, ' '));
        }
    }
    
    // Auto-speak content when page loads, if enabled
    // Slight delay to ensure the page is fully loaded
    setTimeout(() => {
        if (document.querySelector('.interview-question')) {
            speakQuestion();
        } else if (document.querySelector('.feedback-content')) {
            speakFeedback();
        }
    }, 500);
    
    // Expose functions globally
    window.speechUtils = {
        speak: speakText,
        speakQuestion: speakQuestion,
        speakFeedback: speakFeedback,
        cancel: () => synth.cancel()
    };
});
