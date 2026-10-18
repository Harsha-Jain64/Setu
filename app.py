# app.py
import os
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from tinyfish import TinyFish, RunStatus
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

client = TinyFish() if os.getenv("TINYFISH_API_KEY") else None
MOCK_MODE = False 

CAREGIVER_LOGS = []
SPEECH_PRACTICE_HISTORY = []

# NEW: Speech Therapist Target Phrases
SPEECH_PRACTICE_PHRASES = [
    {
        "id": "p1",
        "target": "I want to pay my electricity bill",
        "critical_words": ["pay", "bill", "electricity"],
        "hint": "Start with 'I want to...'",
        "category": "Bills"
    },
    {
        "id": "p2",
        "target": "I need to order my medicine",
        "critical_words": ["order", "medicine"],
        "hint": "Think of 'medicine' - it starts with 'med'",
        "category": "Health"
    },
    {
        "id": "p3",
        "target": "Please book a doctor appointment",
        "critical_words": ["book", "doctor", "appointment"],
        "hint": "You need a 'doctor' and an 'appointment'",
        "category": "Health"
    },
    {
        "id": "p4",
        "target": "Can you help me check my bill",
        "critical_words": ["help", "check", "bill"],
        "hint": "Ask for 'help' with your 'bill'",
        "category": "Bills"
    }
]

TODAY_BOARD = [
    {
        "id": "elec_bill",
        "title": "Electricity Bill",
        "description": "₹1,840 due Friday",
        "icon": "ri-flashlight-fill",
        "color": "bg-amber-100 text-amber-700",
        "amount": 1840,
        "details": """
            <div class='text-left space-y-2'>
                <div class='flex justify-between border-b pb-2'><span class='text-slate-500'>Provider:</span><span class='font-semibold'>MSEB (Maharashtra)</span></div>
                <div class='flex justify-between border-b pb-2'><span class='text-slate-500'>Consumer No:</span><span class='font-semibold'>4592-881-002</span></div>
                <div class='flex justify-between border-b pb-2'><span class='text-slate-500'>Units Used:</span><span class='font-semibold'>150 kWh</span></div>
                <div class='flex justify-between pt-1 text-lg'><span class='font-bold text-slate-800'>Total Due:</span><span class='font-bold text-red-600'>₹1,840.00</span></div>
                <div class='text-sm text-amber-600 bg-amber-50 p-2 rounded mt-2'><i class='ri-alarm-warning-line'></i> Due Friday. Late fee ₹50 after.</div>
            </div>
        """,
        "task_goal": "Read the main heading of this page and tell me what it says.",
        "url": "https://example.com"
    },
    {
        "id": "med_order",
        "title": "Medicine Order",
        "description": "Amlodipine & Metformin",
        "icon": "ri-capsule-fill",
        "color": "bg-emerald-100 text-emerald-700",
        "amount": 450,
        "details": """
            <div class='text-left space-y-2'>
                <div class='flex justify-between border-b pb-2'><span class='text-slate-500'>Pharmacy:</span><span class='font-semibold'>Apollo Pharmacy</span></div>
                <div class='flex justify-between border-b pb-2'><span class='text-slate-500'>Prescription ID:</span><span class='font-semibold'>RX-99281</span></div>
                <div class='border-b pb-2'><span class='text-slate-500 block mb-1'>Items:</span><ul class='list-disc list-inside text-sm'><li>Amlodipine 5mg (30 tabs)</li><li>Metformin 500mg (60 tabs)</li></ul></div>
                <div class='flex justify-between pt-1 text-lg'><span class='font-bold text-slate-800'>Total:</span><span class='font-bold text-emerald-700'>₹450.00</span></div>
                <div class='text-sm text-emerald-700 bg-emerald-50 p-2 rounded mt-2'><i class='ri-truck-line'></i> Delivery by Saturday.</div>
            </div>
        """,
        "task_goal": "Find the title and price of the first book listed on this page.",
        "url": "https://books.toscrape.com/"
    },
    {
        "id": "dr_appt",
        "title": "Doctor Appointment",
        "description": "Dr. Sharma (Cardiologist)",
        "icon": "ri-calendar-check-fill",
        "color": "bg-blue-100 text-blue-700",
        "amount": 0,
        "details": """
            <div class='text-left space-y-2'>
                <div class='flex justify-between border-b pb-2'><span class='text-slate-500'>Doctor:</span><span class='font-semibold'>Dr. A. Sharma</span></div>
                <div class='flex justify-between border-b pb-2'><span class='text-slate-500'>Specialty:</span><span class='font-semibold'>Cardiologist</span></div>
                <div class='flex justify-between border-b pb-2'><span class='text-slate-500'>Location:</span><span class='font-semibold'>HeartCare Clinic, Room 4</span></div>
                <div class='border-b pb-2 pt-1'><span class='text-slate-500 block mb-1'>Schedule:</span><div class='bg-blue-50 text-blue-800 p-2 rounded text-sm font-medium'><i class='ri-time-line'></i> Next Available: Tue, 28th Oct at 10:30 AM</div></div>
            </div>
        """,
        "task_goal": "Read the first paragraph of this page and summarize it in one sentence.",
        "url": "https://en.wikipedia.org/wiki/Aphasia"
    }
]

@app.route('/')
def index():
    return render_template('index.html', board_data=TODAY_BOARD, practice_phrases=SPEECH_PRACTICE_PHRASES)

@app.route('/logs')
def get_logs():
    return jsonify(CAREGIVER_LOGS)

@app.route('/speech_history')
def get_speech_history():
    return jsonify(SPEECH_PRACTICE_HISTORY)

# NEW: AI Speech Therapist Endpoint
@app.route('/speech_practice', methods=['POST'])
def speech_practice():
    data = request.json
    target = data.get('target', '').lower()
    transcript = data.get('transcript', '').lower()
    critical_words = data.get('critical_words', [])
    
    if not transcript:
        return jsonify({"success": False, "error": "No speech detected."})

    # Normalize words (remove punctuation)
    import re
    def clean_words(text):
        return re.findall(r'\b\w+\b', text.lower())
    
    target_words = clean_words(target)
    spoken_words = clean_words(transcript)
    
    # 1. Intent Score (did they get the meaning across?)
    critical_found = [w for w in critical_words if w in spoken_words]
    intent_score = (len(critical_found) / len(critical_words)) * 100 if critical_words else 0
    
    # 2. Word Overlap Score
    target_set = set(target_words)
    spoken_set = set(spoken_words)
    common = target_set & spoken_set
    word_score = (len(common) / len(target_set)) * 100 if target_set else 0
    
    # 3. Missing Words (only content words)
    filler_words = {'i', 'to', 'my', 'a', 'an', 'the', 'can', 'you', 'me', 'please'}
    missing = [w for w in target_words if w not in spoken_set and w not in filler_words]
    
    # 4. Overall Score (Intent weighted higher - aphasia-friendly)
    overall = round(intent_score * 0.7 + word_score * 0.3)
    
    # 5. Feedback Generation
    if overall >= 80:
        feedback = "Excellent work! Your meaning was perfectly clear."
        mood = "great"
    elif overall >= 50:
        feedback = "Good job! You got the main idea across. Keep going!"
        mood = "good"
    else:
        feedback = "Nice try! Let's focus on the key words together."
        mood = "try"
    
    if critical_found:
        feedback += f" You correctly said: {', '.join(critical_found)}."
    if missing:
        feedback += f" Try these words next: {', '.join(missing[:3])}."

    # Log the attempt
    entry = {
        "target": target,
        "transcript": transcript,
        "score": overall,
        "intent_score": round(intent_score),
        "word_score": round(word_score),
        "missing": missing,
        "time": datetime.now().strftime("%I:%M %p")
    }
    SPEECH_PRACTICE_HISTORY.insert(0, entry)
    
    return jsonify({
        "success": True,
        "score": overall,
        "intent_score": round(intent_score),
        "word_score": round(word_score),
        "critical_found": critical_found,
        "missing": missing,
        "feedback": feedback,
        "mood": mood
    })

@app.route('/search_task', methods=['POST'])
def search_task():
    query = request.json.get('query', '')
    if not query:
        return jsonify({"success": False, "error": "No query provided."})
    if MOCK_MODE or not client:
        time.sleep(2)
        return jsonify({"success": True, "result": f"I found a way to help with: '{query}'."})
    try:
        response = client.agent.run(url="https://duckduckgo.com/", goal=f"Search for '{query}' and summarize the top result.")
        if response.status == RunStatus.COMPLETED:
            return jsonify({"success": True, "result": str(response.result)})
        return jsonify({"success": False, "error": "Search failed."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/execute', methods=['POST'])
def execute_task():
    data = request.json
    task_id = data.get('task_id')
    task = next((t for t in TODAY_BOARD if t["id"] == task_id), None)
    if not task:
        return jsonify({"success": False, "error": "Task not found."}), 404

    is_anomaly = task["amount"] > 5000
    alert_message = f"Unusually high amount: ₹{task['amount']}" if is_anomaly else ""

    log_entry = {
        "time": datetime.now().strftime("%I:%M %p"),
        "date": datetime.now().strftime("%b %d, %Y"),
        "task": task["title"],
        "amount": f"₹{task['amount']}" if task["amount"] > 0 else "N/A",
        "status": "Completed",
        "is_anomaly": is_anomaly,
        "alert": alert_message
    }

    if MOCK_MODE or not client:
        time.sleep(2)
        CAREGIVER_LOGS.insert(0, log_entry)
        return jsonify({"success": True, "result": f"[Mock] Completed: {task['title']}.", "is_anomaly": is_anomaly})

    try:
        response = client.agent.run(url=task["url"], goal=task["task_goal"])
        if response.status == RunStatus.COMPLETED:
            CAREGIVER_LOGS.insert(0, log_entry)
            return jsonify({"success": True, "result": str(response.result), "is_anomaly": is_anomaly})
        error_msg = response.error.message if response.error else "Agent failed."
        return jsonify({"success": False, "error": error_msg})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    app.run(debug=True, port=5000)