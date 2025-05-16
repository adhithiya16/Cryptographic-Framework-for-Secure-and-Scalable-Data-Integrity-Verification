from flask import Flask, request, jsonify
from flask_cors import CORS
from merkle import MerkleTree
import hashlib
from pymongo import MongoClient
import os
from werkzeug.utils import secure_filename
import logging
import base64

# Set up logging to display only warnings or errors
logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc'}  # still allow binary files
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# MongoDB Atlas connection string
mongo_uri = "mongodb+srv://user:1234@cluster0.mc5qp.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_uri)
db = client.document_timestamping_db
collection = db.documents

# Store the Merkle tree and root
merkle_tree = None
merkle_root = None

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/timestamp', methods=['POST'])
def timestamp_document():
    global merkle_tree, merkle_root

    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(file_path)
        except Exception as e:
            app.logger.error(f"Error saving file: {e}")
            return jsonify({'error': f'Error saving file: {str(e)}'}), 500

        # Read the file in binary mode
        try:
            with open(file_path, 'rb') as f:
                document_bytes = f.read()
        except Exception as e:
            app.logger.error(f"Error reading file: {e}")
            return jsonify({'error': f'Error reading file: {str(e)}'}), 500

        # Initialize or update the Merkle tree with the binary data
        try:
            if merkle_tree is None:
                merkle_tree = MerkleTree([document_bytes])
            else:
                merkle_tree.data.append(document_bytes)
                merkle_tree = MerkleTree(merkle_tree.data)
            merkle_root = merkle_tree.get_root()
        except Exception as e:
            app.logger.error(f"Error building Merkle tree: {e}")
            return jsonify({'error': f'Error building Merkle tree: {str(e)}'}), 500

        # Compute the document hash on the binary content
        document_hash = hashlib.sha256(document_bytes).hexdigest()
        # Optionally, store the document as a Base64 string so it can be saved in MongoDB as text.
        encoded_document = base64.b64encode(document_bytes).decode('utf-8')

        try:
            collection.insert_one({
                "document": encoded_document,
                "document_hash": document_hash,
                "merkle_root": merkle_root
            })
        except Exception as e:
            app.logger.error(f"MongoDB error: {e}")
            return jsonify({'error': f'MongoDB error: {str(e)}'}), 500

        return jsonify({
            'document_hash': document_hash,
            'merkle_root': merkle_root
        }), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400

@app.route('/verify', methods=['POST'])
def verify_document():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        try:
            file.save(file_path)
        except Exception as e:
            app.logger.error(f"Error saving file: {e}")
            return jsonify({'error': f'Error saving file: {str(e)}'}), 500

        try:
            with open(file_path, 'rb') as f:
                document_bytes = f.read()
        except Exception as e:
            app.logger.error(f"Error reading file: {e}")
            return jsonify({'error': f'Error reading file: {str(e)}'}), 500

        document_hash = hashlib.sha256(document_bytes).hexdigest()

        try:
            stored_document = collection.find_one({"document_hash": document_hash})
        except Exception as e:
            app.logger.error(f"MongoDB error: {e}")
            return jsonify({'error': f'MongoDB error: {str(e)}'}), 500

        is_valid = stored_document is not None
        return jsonify({'is_valid': is_valid}), 200
    else:
        return jsonify({'error': 'Invalid file type'}), 400

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
