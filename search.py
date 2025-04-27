from flask import Flask, request, jsonify, stream_with_context, Response
from flask_cors import CORS
import subprocess
import threading
import os
import sys
import json
import traceback

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

            # Kill previous process if running
            with process_lock:
                if current_process:
                    try:
                        print("Killing previous process...")
                        current_process.kill()
                    except Exception as e:
                        print(f"Error killing previous process: {e}")
                    finally:
                        current_process = None

                current_process = subprocess.Popen(
                    [sys.executable, scraper_path, search_term, str(min_price), str(max_price), str(max_pages)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding='utf-8'
                )

            stdout, stderr = current_process.communicate()
            return_code = current_process.returncode

            print("Subprocess STDOUT:", stdout)
            print("Subprocess STDERR:", stderr)
            print("Subprocess Return Code:", return_code)

            with process_lock:
                current_process = None

            if return_code != 0:
                yield json.dumps({"error": f"Subprocess failed with code {return_code}: {stderr}"}, ensure_ascii=False) + "\n"
                return

            try:
                products = json.loads(stdout)
                yield json.dumps(products, ensure_ascii=False) + "\n"
            except json.JSONDecodeError as e:
                print(f"JSON Decode Error: {e}")
                print(f"Raw output: {stdout}")
                yield json.dumps({"error": "Invalid JSON returned from scraper"}, ensure_ascii=False) + "\n"
                return

        except Exception as e:
            print("Unhandled exception in generate():")
            traceback.print_exc()
            yield json.dumps({"error": str(e)}, ensure_ascii=False) + "\n"
            return

    return Response(generate(), mimetype='application/json')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
