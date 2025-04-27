from flask import Flask, request, jsonify, stream_with_context, Response
from flask_cors import CORS 
import subprocess
import threading
import os
import sys
import json
import traceback
import time

app = Flask(__name__)
CORS(app)

current_process = None
process_lock = threading.Lock()

@app.route('/search', methods=['GET'])
def search_products():
    global current_process

    search_term = request.args.get('searchTerm', '')
    min_price = request.args.get('minPrice', 0)
    max_price = request.args.get('maxPrice', 10000)
    max_pages = request.args.get('maxPages', 1)

    print(f"Received search request: Term={search_term}, Min Price={min_price}, Max Price={max_price}")

    @stream_with_context
    def generate():
        global current_process
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            scraper_path = os.path.join(script_dir, 'project.py')

            with process_lock:
                if current_process:
                    try:
                        print("Killing previous process...")
                        current_process.kill()
                    except Exception as e:
                        print(f"Error killing previous process: {e}")
                current_process = subprocess.Popen(
                    [sys.executable, scraper_path, search_term, str(min_price), str(max_price), str(max_pages)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )

            stdout, stderr = current_process.communicate()
            return_code = current_process.returncode  # 🔥 αποθηκεύουμε πρώτα
            
            if return_code != 0:
                print(f"Subprocess error (code {return_code}):", stderr)
                yield json.dumps({"error": "Υπήρξε πρόβλημα κατά την εκτέλεση του scraper."}) + "\n"
                return

            with process_lock:
                current_process = None

            print("Subprocess STDOUT:", stdout)
            print("Subprocess STDERR:", stderr)
            print("Subprocess Return Code:", return_code)
            
            if return_code != 0:
                yield json.dumps({"error": stderr})
                return

            try:
                products = json.loads(stdout)
                yield json.dumps(products, ensure_ascii=False)
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                print(f"Raw output: {stdout}")
                yield json.dumps({"error": "Invalid JSON response from scraper"})
                return

        except Exception as e:
            print("Full error traceback:")
            traceback.print_exc()
            yield json.dumps({"error": str(e)})
            return

    return Response(generate(), mimetype='application/json')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
