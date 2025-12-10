from flask import Flask, render_template, request, send_from_directory, jsonify
from werkzeug.utils import secure_filename
import os
from datetime import datetime

from utils.remove_bg import remove_background, remove_background_advanced

app = Flask(__name__)

# Static upload/output folders
UPLOAD_FOLDER = "static/uploads/input"
OUTPUT_FOLDER = "static/uploads/output"
MANUAL_FOLDER = "static/uploads/manual"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(MANUAL_FOLDER, exist_ok=True)
os.makedirs("static/css", exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER
app.config["MANUAL_FOLDER"] = MANUAL_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg', 'ico'}


def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/remove", methods=["POST"])
def remove_bg_route():
    """
    Handle image upload and removal request.
    """
    if "image" not in request.files:
        return "No file uploaded", 400

    file = request.files["image"]

    if file.filename == "":
        return "Invalid file name", 400

    # Check if file type is allowed
    if not allowed_file(file.filename):
        return f"File type not allowed. Supported formats: {', '.join(ALLOWED_EXTENSIONS).upper()}", 400

    # Get quality mode from form (default to 'best')
    mode = request.form.get('mode', 'best')

    filename = secure_filename(file.filename)
    base_name = filename.rsplit('.', 1)[0]
    
    input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    output_filename = base_name + ".png"
    output_path = os.path.join(app.config["OUTPUT_FOLDER"], output_filename)

    # Save uploaded image
    file.save(input_path)

    try:
        # Process background removal with selected mode
        if mode == 'advanced':
            remove_background_advanced(input_path, output_path)
        else:
            remove_background(input_path, output_path, mode=mode)
        
        # Use relative paths for templates (without 'static/' prefix in template)
        return render_template(
            "result.html",
            input_image=f"uploads/input/{filename}",
            output_image=f"uploads/output/{output_filename}"
        )
    except Exception as e:
        return f"Error processing image: {str(e)}", 500


@app.route("/manual_editor")
def manual_editor():
    """
    Render the manual editor page.
    """
    return render_template("manual_editor.html")


@app.route("/upload_for_manual", methods=["POST"])
def upload_for_manual():
    """
    Handle direct upload for manual editing.
    """
    if "image" not in request.files:
        return "No file uploaded", 400

    file = request.files["image"]

    if file.filename == "":
        return "Invalid file name", 400

    # Check if file type is allowed
    if not allowed_file(file.filename):
        return f"File type not allowed. Supported formats: {', '.join(ALLOWED_EXTENSIONS).upper()}", 400

    filename = secure_filename(file.filename)
    input_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    
    # Save uploaded image
    file.save(input_path)
    
    # Redirect to manual editor with the image
    image_url = f"/static/uploads/input/{filename}"
    return render_template("manual_editor.html", image_path=image_url)


@app.route("/save_manual_edit", methods=["POST"])
def save_manual_edit():
    """
    Save manually edited image.
    """
    if "image" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["image"]
    
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"manual_edit_{timestamp}.png"
    output_path = os.path.join(app.config["MANUAL_FOLDER"], filename)

    try:
        file.save(output_path)
        return jsonify({
            "success": True,
            "output_path": f"uploads/manual/{filename}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/result_manual")
def result_manual():
    """
    Show result page for manually edited image.
    """
    image_path = request.args.get('image', '')
    return render_template(
        "result_manual.html",
        output_image=image_path
    )


# Optional: Add a route to serve files directly (backup)
@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    return send_from_directory('static/uploads', filename)


if __name__ == "__main__":
    app.run(debug=True)