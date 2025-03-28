import os
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
import pyttsx3  
import speech_recognition as sr

question_template = """
You are an AI interview assistant named "InterviewMate". You are an expert interviewer for all professional fields.

The user wants to practice for an interview in the field of: {job_topic}

Generate a challenging and realistic interview question about {job_topic}. This should be question #{question_number} in the practice session.

Make sure the question is:
- Technical and specific to the job topic
- Similar to what might be asked in a real interview
- Challenging but answerable
- Clear and concise

Previous questions asked in this session:
{previous_questions}

IMPORTANT: Do NOT repeat any of the previous questions. Generate a completely new and different question.

Return ONLY the interview question without any introductory text or explanations.
"""

feedback_template = """
You are an AI interview assistant named "InterviewMate". You are an expert interviewer for all professional fields.

You are evaluating a candidate's answer to an interview question about {job_topic}.

Question: {question}
Candidate's Answer: {answer}

Provide detailed feedback on the candidate's answer. Include:
1. Whether the answer is technically correct or incorrect
2. Strengths of the answer
3. Areas for improvement
4. A model answer that would be considered excellent
5. Any key points that were missed

Be specific, constructive, and helpful. Your goal is to help the candidate improve their interview skills.
"""

class VoiceEnabledInterviewMate:
    def __init__(self, api_key=None):
        # Initialize text-to-speech engine
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150)
        self.engine.setProperty('volume', 0.9)
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)  # Female voice

        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        # Initialize LLM with provided API key
        self.setup_llm(api_key)

    def setup_llm(self, api_key):
        """Set up the LLM with the provided API key"""
        if not api_key:
            raise ValueError("API key is required")
        
        self.llm = ChatOpenAI(
            #base_url="https://models.inference.ai.azure.com",
            api_key=api_key,
            model="gpt-4o-mini",
            temperature=0.1,
        )

        # Setup chains
        self.question_chain = (
            {"job_topic": RunnablePassthrough(), "question_number": RunnablePassthrough(), "previous_questions": RunnablePassthrough()}
            | PromptTemplate(input_variables=["job_topic", "question_number", "previous_questions"], template=question_template)
            | self.llm
            | StrOutputParser()
        )

        self.feedback_chain = (
            {"job_topic": RunnablePassthrough(), "question": RunnablePassthrough(), "answer": RunnablePassthrough()}
            | PromptTemplate(input_variables=["job_topic", "question", "answer"], template=feedback_template)
            | self.llm
            | StrOutputParser()
        )

    def speak(self, text):
        """Convert text to speech"""
        print(text)
        self.engine.say(text)
        self.engine.runAndWait()

    def listen(self):
        """Listen to user input via microphone"""
        with self.microphone as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1.5)
            audio = self.recognizer.listen(source)
            
            try:
                print("Recognizing...")
                text = self.recognizer.recognize_google(audio)
                print(f"You said: {text}")
                return text
            except sr.UnknownValueError:
                print("Sorry, I didn't understand that.")
                return None
            except sr.RequestError:
                print("Sorry, I'm having trouble accessing the speech recognition service.")
                return None

    def get_user_answer(self, use_voice=True):
        """Get the user's answer through voice or text"""
        if use_voice:
            self.speak("Please provide your answer. When you're finished, remain silent for a moment.")
            answer_parts = []
            silence_count = 0
            max_silence = 3  # Number of consecutive silences to detect end of answer
            
            while silence_count < max_silence:
                user_input = self.listen()
                if user_input:
                    answer_parts.append(user_input)
                    silence_count = 0
                else:
                    silence_count += 1
                    if silence_count == 1:
                        self.speak("Are you finished with your answer? If so, wait. If not, continue speaking.")
            
            return " ".join(answer_parts) if answer_parts else "No answer provided."
        else:
            # Get text input
            print("Type your answer below (press Enter twice when finished):")
            answer_lines = []
            while True:
                line = input()
                if line.strip() == "":
                    if not answer_lines:
                        continue
                    break
                answer_lines.append(line)
            
            return "\n".join(answer_lines)

    def generate_question(self, job_topic, question_number, previous_questions):
        """Generate an interview question"""
        prev_questions_formatted = "\n".join([f"- {q}" for q in previous_questions]) if previous_questions else "None yet."
        
        return self.question_chain.invoke({
            "job_topic": job_topic, 
            "question_number": question_number,
            "previous_questions": prev_questions_formatted
        })
    
    def generate_feedback(self, job_topic, question, answer):
        """Generate feedback for an answer"""
        return self.feedback_chain.invoke({
            "job_topic": job_topic,
            "question": question, 
            "answer": answer
        })

    def run_interview_session(self):
        """Run the interview practice session"""
        self.speak("Welcome to InterviewMate Practice System!")
        
        # Get API key first
        api_key = input("Enter your OpenAI API key: ")
        try:
            self.setup_llm(api_key)
        except Exception as e:
            print(f"Error setting up LLM: {e}")
            return
        
        # Get job topic
        self.speak("Enter the job topic you want to practice for. For example, Software Engineering, Marketing, or Data Science.")
        job_topic = input("Enter job topic: ")
        
        # Ask for input mode preference
        self.speak("Would you like to use voice input for your answers? Say yes or no.")
        voice_preference = input("Use voice input for answers? (yes/no): ").lower()
        use_voice = voice_preference in ["yes", "y"]
        
        # Get number of questions
        self.speak("How many questions would you like to practice per round?")
        while True:
            try:
                questions_per_round = int(input("How many questions per round? "))
                if questions_per_round > 0:
                    break
                else:
                    self.speak("Please enter a positive number.")
            except ValueError:
                self.speak("Please enter a valid number.")
        
        question_number = 1
        continue_practice = True
        previous_questions = []
        
        while continue_practice:
            for i in range(questions_per_round):
                print("\n" + "="*60)
                
                # Generate interview question
                interview_question = self.generate_question(job_topic, question_number, previous_questions)
                previous_questions.append(interview_question)
                
                # Speak the question
                self.speak(f"Question {question_number}:")
                self.speak(interview_question)
                
                # Get user's answer
                user_answer = self.get_user_answer(use_voice)
                
                # Generate and speak feedback
                self.speak("Analyzing your answer...")
                feedback = self.generate_feedback(job_topic, interview_question, user_answer)
                
                self.speak("Here's your feedback:")
                self.speak(feedback)
                
                question_number += 1
            
            # Ask if user wants to continue
            self.speak("Would you like to continue with another round of questions? Say yes or no.")
            continue_input = input("\nContinue with another round? (yes/no): ")
            continue_practice = continue_input.lower() in ["yes", "y"]
        
        self.speak("Thank you for using InterviewMate Practice System. Good luck with your interviews!")

def main():
    interview_mate = VoiceEnabledInterviewMate()
    interview_mate.run_interview_session()

if __name__ == '__main__':
    main()