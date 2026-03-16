import requests
import json
import time

base = 'http://localhost:8080'

print('\n=== 2. Ingest PDFs ===')
def ingest(file_path):
    with open(file_path, 'rb') as f:
        r = requests.post(f'{base}/ingest', files={'file': f})
        print(f'{file_path}:', r.status_code, r.json())

ingest('data/peblo_pdf_grade1_math_numbers.pdf')
ingest('data/peblo_pdf_grade3_science_plants_animals.pdf')

print('\n=== 4. Generate Quiz ===')
r1 = requests.post(f'{base}/generate-quiz', json={'source_id': 'SRC_001', 'max_questions_per_chunk': 3})
print(r1.status_code, r1.text)

r2 = requests.post(f'{base}/generate-quiz', json={'source_id': 'SRC_002', 'max_questions_per_chunk': 2})
print(r2.status_code, r2.text)

print('\n=== 5. Get Quiz Questions ===')
r = requests.get(f'{base}/quiz')
quiz_data = r.json()
print(f'Total questions generated: {quiz_data.get("total", 0)}')

if quiz_data.get('questions'):
    q = quiz_data['questions'][0]
    print('\nSample Question:')
    print(json.dumps(q, indent=2))
    
    print('\n=== 6. Submit Answer ===')
    ans_req = {
        'student_id': 'S_TEST',
        'question_id': q['question_id'],
        'selected_answer': q['answer']
    }
    r_ans = requests.post(f'{base}/submit-answer', json=ans_req)
    print(r_ans.status_code, json.dumps(r_ans.json(), indent=2))

    print('\n=== 7. Get Performance ===')
    r_perf = requests.get(f'{base}/student-performance/S_TEST')
    print(r_perf.status_code, json.dumps(r_perf.json(), indent=2))
