"""
Serverless handler for Mermaid converter
Works with AWS Lambda, Google Cloud Functions, Azure Functions, and Boltic Serverless
"""

import base64
import json
import logging
from typing import Any
from urllib.parse import urlencode

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict[str, Any], context: Any = None) -> dict[str, Any]:
    """
    Serverless handler that converts Mermaid code to PNG, SVG, and link.
    
    Compatible with:
    - AWS Lambda
    - Google Cloud Functions
    - Azure Functions
    - Boltic Serverless
    
    Args:
        event: HTTP request event
        context: Lambda/Cloud context (optional)
        
    Returns:
        HTTP response with PNG, SVG, and link data
    """
    try:
        # Parse request body based on source
        if isinstance(event, dict) and "body" in event:
            # AWS Lambda / Boltic format
            body_str = event.get("body", "{}")
            if isinstance(body_str, str):
                request_data = json.loads(body_str)
            else:
                request_data = body_str
        elif isinstance(event, dict) and "data" in event:
            # Google Cloud Functions format
            request_data = event.get("data", {})
        else:
            request_data = event or {}
        
        # Extract Mermaid code
        mermaid_code = request_data.get("mermaid_code", "").strip()
        
        # Strip markdown code block fences
        mermaid_code = mermaid_code.replace("```mermaid", "").replace("```", "").strip()
        
        if not mermaid_code:
            return _error_response(400, "Mermaid code is required and cannot be empty")
        
        # Extract parameters with defaults
        theme = request_data.get("theme", "default")
        background_color = request_data.get("background_color", "")
        width = request_data.get("width")
        height = request_data.get("height")
        
        logger.info("Converting Mermaid diagram to PNG, SVG and link formats")
        
        # Base64 encode the mermaid code
        try:
            encoded_diagram = base64.urlsafe_b64encode(mermaid_code.encode('utf-8')).decode('ascii')
        except Exception as e:
            return _error_response(400, f"Failed to encode diagram: {str(e)}")
        
        # Get PNG, SVG and direct link
        png_data = _get_format(encoded_diagram, "png", theme, background_color, width, height)
        svg_data = _get_format(encoded_diagram, "svg", theme, background_color, width, height)
        link = _build_link(encoded_diagram, theme, background_color, width, height)
        
        if not png_data:
            return _error_response(500, "Failed to convert diagram to PNG")
        
        if not svg_data:
            return _error_response(500, "Failed to convert diagram to SVG")
        
        # Convert binary data to base64 for JSON response
        png_base64 = base64.b64encode(png_data).decode('utf-8')
        svg_base64 = base64.b64encode(svg_data).decode('utf-8')
        
        response_data = {
            "png": f"data:image/png;base64,{png_base64}",
            "svg": f"data:image/svg+xml;base64,{svg_base64}",
            "link": link,
            "mermaid_code": mermaid_code,
            "theme": theme
        }
        
        logger.info("Successfully converted diagram to all formats")
        
        return _success_response(response_data)
        
    except json.JSONDecodeError:
        return _error_response(400, "Invalid JSON in request body")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return _error_response(500, f"Server error: {str(e)}")


def _get_format(encoded_diagram: str, output_format: str, theme: str, 
               background_color: str, width: int = None, height: int = None) -> bytes | None:
    """
    Fetch diagram in specific format from mermaid.ink API.
    
    Args:
        encoded_diagram: Base64 encoded mermaid code
        output_format: Format to fetch (png, svg)
        theme: Visual theme
        background_color: Background color
        width: Image width
        height: Image height
        
    Returns:
        Binary data of the diagram or None on failure
    """
    try:
        url = _build_api_url(encoded_diagram, output_format, theme, background_color, width, height)
        
        response = requests.get(url, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            logger.error(f"Failed to fetch {output_format}: HTTP {response.status_code}")
            return None
                
    except Exception as e:
        logger.error(f"Error fetching {output_format}: {str(e)}")
        return None


def _build_api_url(encoded_diagram: str, output_format: str, theme: str, 
                  background_color: str, width: int = None, height: int = None) -> str:
    """
    Build the mermaid.ink API URL with proper parameters.
    
    Args:
        encoded_diagram: Base64 encoded mermaid code
        output_format: Target format (png/svg)
        theme: Visual theme
        background_color: Background color
        width: Image width
        height: Image height
        
    Returns:
        Complete API URL with parameters
    """
    if output_format == "svg":
        base_url = f"https://mermaid.ink/svg/{encoded_diagram}"
    else:  # png
        base_url = f"https://mermaid.ink/img/{encoded_diagram}"
    
    # Build query parameters
    params = {}
    
    # Format-specific parameters
    if output_format == "png":
        params["type"] = "png"
        
    # Theme parameter
    if theme and theme != "default" and output_format == "png":
        params["theme"] = theme
    
    # Background color parameter
    if background_color:
        if background_color.startswith("!"):
            params["bgColor"] = background_color
        else:
            color = background_color.lstrip("#")
            if len(color) == 6 and all(c in "0123456789ABCDEFabcdef" for c in color):
                params["bgColor"] = color
    
    # Size parameters
    if width:
        params["width"] = str(width)
    if height:
        params["height"] = str(height)
    
    # Combine URL with parameters
    if params:
        return f"{base_url}?{urlencode(params)}"
    else:
        return base_url


def _build_link(encoded_diagram: str, theme: str, 
               background_color: str, width: int = None, height: int = None) -> str:
    """
    Build direct mermaid.ink link to the diagram.
    
    Args:
        encoded_diagram: Base64 encoded mermaid code
        theme: Visual theme
        background_color: Background color
        width: Image width
        height: Image height
        
    Returns:
        Direct link to view/download diagram
    """
    base_url = f"https://mermaid.ink/img/{encoded_diagram}"
    
    params = {"type": "png"}
    
    if theme and theme != "default":
        params["theme"] = theme
    
    if background_color:
        if background_color.startswith("!"):
            params["bgColor"] = background_color
        else:
            color = background_color.lstrip("#")
            if len(color) == 6 and all(c in "0123456789ABCDEFabcdef" for c in color):
                params["bgColor"] = color
    
    if width:
        params["width"] = str(width)
    if height:
        params["height"] = str(height)
    
    if params:
        return f"{base_url}?{urlencode(params)}"
    else:
        return base_url


def _success_response(data: dict[str, Any]) -> dict[str, Any]:
    """
    Format successful response for serverless.
    
    Compatible with:
    - AWS Lambda (returns body as string)
    - Google Cloud Functions (returns dict)
    - Boltic Serverless (returns dict or body)
    """
    response_body = json.dumps(data)
    
    return {
        "statusCode": 200,
        "status": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": response_body
    }


def _error_response(status_code: int, error_message: str) -> dict[str, Any]:
    """
    Format error response for serverless.
    
    Compatible with:
    - AWS Lambda (returns body as string)
    - Google Cloud Functions (returns dict)
    - Boltic Serverless (returns dict or body)
    """
    response_body = json.dumps({"error": error_message})
    
    return {
        "statusCode": status_code,
        "status": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        },
        "body": response_body
    }


# For local testing / Flask development
if __name__ == "__main__":
    from flask import Flask, request, jsonify
    
    app = Flask(__name__)
    
    @app.route("/mermaid/convert", methods=["POST", "OPTIONS"])
    def mermaid_convert():
        if request.method == "OPTIONS":
            return "", 204
        
        event = {
            "body": request.get_json() or {}
        }
        
        response = handler(event)
        body = json.loads(response["body"])
        
        return jsonify(body), response["statusCode"]
    
    @app.route("/", methods=["GET"])
    def health():
        return jsonify({"status": "ok"}), 200
    
    app.run(debug=True, port=5000)
