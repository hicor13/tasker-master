from flask import Flask, render_template, request, jsonify, make_response
import json, os, uuid, csv, io, difflib

app = Flask(__name__)
DATA_FILE = 'tasks.json'

# Moved to the top so it's always accessible
SEC_CAT_MAP = {
    "FOHVENC2": "CORE 21", "IBK01": "CORE 1", "IBK07": "CORE 1", "IBKT1A": "CORE 1","IBKHT6": "CORE 1",
    "MAFT2T3": "CORE 1", "PRYT0A": "CORE 1", "SANT1": "CORE 1","SANT1_DED": "CORE 1", "SANT2": "CORE 1",
    "SANT2_DED": "CORE 1", "BFBT3A": "CORE 11", "BFBT0A": "CORE 11", "BFBT1A": "CORE 11", "FOHCASTI": "CORE 11",
    "IBK03": "CORE 11", "IBK04": "CORE 11", "MAFCAST": "CORE 11", "MAFJNR1": "CORE 11", "BFBT2A": "CORE 21",
    "BFBT6A": "CORE 21", "CNCCAST1": "CORE 21", "IBKVTS": "CORE 21", "IBKCIMA": "CORE 21",
    "FOHT1A": "CORE 21", "IBK08": "CORE 21", "IBKPREV1": "CORE 21",
}

def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f: return json.load(f)
    return []

def save_tasks(tasks):
    with open(DATA_FILE, 'w') as f: json.dump(tasks, f, indent=4)

@app.route('/')
def index(): return render_template('index.html')

@app.route('/tasks', methods=['GET'])
def get_tasks(): return jsonify(load_tasks())

@app.route('/tasks', methods=['POST'])
def add_task():
    data = request.json
    tasks = load_tasks()
    data['id'] = str(uuid.uuid4())
    # Ensure sec_category is assigned based on the type
    data['sec_category'] = SEC_CAT_MAP.get(data['type'], "General")
    tasks.append(data)
    save_tasks(tasks)
    return jsonify({"success": True})

@app.route('/tasks/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    tasks = load_tasks()
    for t in tasks:
        if t['id'] == task_id: t.update(data)
    save_tasks(tasks)
    return jsonify({"success": True})

@app.route('/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    tasks = load_tasks()
    # Create a new list excluding the ID to be deleted
    updated_tasks = [t for t in tasks if t['id'] != task_id]
    
    if len(updated_tasks) == len(tasks):
        return jsonify({"success": False, "error": "Task not found"}), 404
        
    save_tasks(updated_tasks)
    return jsonify({"success": True})

@app.route('/tasks/hide_visible', methods=['POST'])
def hide_visible():
    ids = request.json.get('ids', [])
    tasks = load_tasks()
    for t in tasks:
        if t['id'] in ids: t['hidden'] = True
    save_tasks(tasks)
    return jsonify({"success": True})

@app.route('/export/<tab_type>')
def export_csv(tab_type):
    tasks = [t for t in load_tasks() if t.get('tab') == tab_type]
    if not tasks: return "No data", 400
    si = io.StringIO()
    # Comprehensive fieldnames to avoid ValueErrors
    fieldnames = ['type', 'sec_category', 'date', 'time', 'state', 'total', 'current', 'id', 'tab', 'hidden']
    writer = csv.DictWriter(si, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(tasks)
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={tab_type}_export.csv"
    output.headers["Content-type"] = "text/csv"
    return output

@app.route('/match_filename', methods=['POST'])
def match_filename():
    filename = request.json.get('filename', '')
    types_list = list(SEC_CAT_MAP.keys())
    
    # Extract filename without extension
    name_without_ext = os.path.splitext(filename)[0].upper()
    
    # Try exact match first
    if name_without_ext in types_list:
        return jsonify({"match": name_without_ext, "confidence": 1.0})
    
    # Try fuzzy matching with cutoff
    matches = difflib.get_close_matches(name_without_ext, types_list, n=1, cutoff=0.6)
    
    if matches:
        matched = matches[0]
        # Calculate similarity score
        ratio = difflib.SequenceMatcher(None, name_without_ext, matched).ratio()
        return jsonify({"match": matched, "confidence": round(ratio, 2)})
    
    # No match found, return empty
    return jsonify({"match": None, "confidence": 0})

if __name__ == '__main__':
    app.run(port=5069, debug=True)