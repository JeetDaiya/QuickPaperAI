import requests
import time

BASE_URL = "http://127.0.0.1:8000"

def test_flow():
    # 1. Fetch available textbook chapters
    print("⚡ [STEP 1] Testing GET /api/db/get-chapters...")
    try:
        res = requests.get(f"{BASE_URL}/api/db/get-chapters")
        print("✅ Chapters found:", len(res.json().get("chapters", [])), "records")
    except Exception as e:
        print("❌ Server is not running or unreachable:", e)
        return

    # 2. Trigger question paper generation
    payload = {
        "institution_name": "Antigravity Test School",
        "subject": "science",
        "standard": "10",
        "difficulty": "Balanced",
        "chapters": ["1"],
        "objective_count": 3,
        "subjective_count": 2
    }
    
    print("\n⚡ [STEP 2] Launching generation via POST /api/generate...")
    res = requests.post(f"{BASE_URL}/api/generate", json=payload)
    data = res.json()
    print("👉 Generate response:", data)
    thread_id = data.get("thread_id")
    
    if not thread_id:
        print("❌ Generation failed to yield a thread ID")
        return
        
    # 3. Poll status in a loop until complete
    print(f"\n⚡ [STEP 3] Polling progress for thread: {thread_id}")
    while True:
        status_res = requests.get(f"{BASE_URL}/api/status/{thread_id}").json()
        status = status_res.get("status")
        print(f"   [POLL] Status: {status}")
        
        # Scenario A: Generation complete
        if status == "completed":
            print("\n🎉 SUCCESS! Question paper generation fully completed!")
            print("📁 Final compilation downloads:")
            for name, url in status_res.get("files", {}).items():
                print(f"   * {name}: {BASE_URL}{url}")
            break
            
        # Scenario B: Suspended at review stage (HITL Interrupt)
        elif status == "awaiting_review":
            questions = status_res.get("questions", [])
            print(f"\n🙋 INTERRUPT: Paused for review! Generated {len(questions)} candidates.")
            
            # Print the candidates to terminal
            for i, q in enumerate(questions):
                print(f"   [{i}] ({q['question_type']}) {q['question_text'][:80]}...")
            
            # Automatically approve all candidates
            approved_indices = list(range(len(questions)))
            print(f"\n⚡ [STEP 4] Posting approvals for indices: {approved_indices}...")
            
            resume_res = requests.post(
                f"{BASE_URL}/api/resume/{thread_id}", 
                json={"selected_indices": approved_indices}
            ).json()
            print("👉 Resume response:", resume_res)
            
        elif status == "failed":
            print("\n❌ Generation pipeline failed.")
            break
            
        time.sleep(3)

if __name__ == "__main__":
    test_flow()
