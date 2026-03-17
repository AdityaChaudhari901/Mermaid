"""
Flask app wrapper for the Mermaid converter serverless function
Use for local testing or deployment to platforms that need a WSGI app
"""

from flask import Flask, request, jsonify
from serverless_handler import handler
import json

app = Flask(__name__)


@app.route("/mermaid/convert", methods=["POST", "OPTIONS"])
def mermaid_convert():
    """
    Handle Mermaid conversion requests.
    
    POST /mermaid/convert
    {
        "mermaid_code": "graph TD; A-->B;",
        "theme": "dark",
        "background_color": "FFFFFF",
        "width": 800,
        "height": 600
    }
    
    Returns:
    {
        "png": "data:image/png;base64,...",
        "svg": "data:image/svg+xml;base64,...",
        "link": "https://mermaid.ink/img/...",
        "mermaid_code": "graph TD; A-->B;",
        "theme": "dark"
    }
    """
    if request.method == "OPTIONS":
        return "", 204
    
    try:
        # Get request data
        data = request.get_json() or {}
        
        # Create event for handler
        event = {
            "body": json.dumps(data) if isinstance(data, dict) else data
        }
        
        # Call handler
        response = handler(event)
        
        # Parse response body
        body = json.loads(response["body"])
        status_code = response.get("statusCode", 200)
        
        return jsonify(body), status_code
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok"}), 200


@app.route("/", methods=["GET"])
def index():
    """Root endpoint with API documentation"""
    return jsonify({
        "service": "Mermaid Converter Serverless",
        "version": "1.0.0",
        "endpoints": {
            "POST /mermaid/convert": "Convert Mermaid code to PNG, SVG, and link",
            "GET /health": "Health check",
            "GET /": "API documentation"
        },
        "request_format": {
            "mermaid_code": "string (required) - Mermaid diagram syntax",
            "theme": "string (optional) - default, dark, neutral, forest",
            "background_color": "string (optional) - hex color or !named_color",
            "width": "integer (optional) - image width in pixels",
            "height": "integer (optional) - image height in pixels"
        },
        "response_format": {
            "png": "string - PNG image as data URI",
            "svg": "string - SVG image as data URI",
            "link": "string - Direct mermaid.ink URL",
            "mermaid_code": "string - Original Mermaid code",
            "theme": "string - Applied theme"
        }
    }), 200


# CORS error handler
@app.after_request
def after_request(response):
    """Add CORS headers to all responses"""
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add("Access-Control-Allow-Methods", "POST, GET, OPTIONS, PUT, DELETE")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type, Authorization")
    return response


if __name__ == "__main__":
    # For local testing
    print("Starting Mermaid Converter Server...")
    print("API available at http://localhost:5000")
    print("Docs at http://localhost:5000/")
    app.run(debug=True, host="0.0.0.0", port=5000)
