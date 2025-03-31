from flask import Flask, request, jsonify
from flask_cors import CORS
import subprocess
import json
import sys
import os
import traceback

app = Flask(__name__)
CORS(app)

@app.route('/search', methods=['GET'])
def search_products():
    search_term = request.args.get('searchTerm', '')
    min_price = request.args.get('minPrice', 0)
    max_price = request.args.get('maxPrice', 10000)
    max_pages = request.args.get('maxPages', 1) 


    print(f"Received search request: Term={search_term}, Min Price={min_price}, Max Price={max_price}")

    try:
        # Get the directory of the current script
        script_dir = os.path.dirname(os.path.abspath(__file__))
        scraper_path = os.path.join(script_dir, '..', 'project.py')  # Adjust path as needed

        print(f"Attempting to run scraper: {scraper_path}")

        # Run the Python scraping script with corrected subprocess parameters
        result = subprocess.run(
            [sys.executable, scraper_path, search_term, str(min_price), str(max_price), str(max_pages)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Enhanced error logging
        print("Subprocess STDOUT:", result.stdout)
        print("Subprocess STDERR:", result.stderr)
        print("Subprocess Return Code:", result.returncode)

        # Check for any errors in subprocess
        if result.returncode != 0:
            print("Subprocess error details:")
            print(result.stderr)
            return jsonify({"error": result.stderr}), 500

        # Try to parse the output
        try:
            products = json.loads(result.stdout)
            return jsonify(products)
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Raw output: {result.stdout}")
            return jsonify({"error": "Invalid JSON response from scraper"}), 500
    
    except Exception as e:
        # Log the full traceback
        print("Full error traceback:")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)