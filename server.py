#Here is the version of 20241107 lidong
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import logging
import time
from datetime import datetime
from werkzeug.utils import secure_filename
import base64
from flask_sqlalchemy import SQLAlchemy

# 创建logs目录（如果不存在）
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 生成带时间戳的日志文件名
log_file = os.path.join(log_dir, f'server_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')

# 修改日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 禁用 werkzeug 默认日志
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__, static_url_path='')
CORS(app)

OLLAMA_API_URL = "http://localhost:11434/api/generate"

# 配置上传文件的存储位置
UPLOAD_FOLDER = 'static/ai_pictures'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 数据库配置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///images.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 定义图片模型
class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    original_filename = db.Column(db.String(200))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)  # 文件大小（字节）
    mime_type = db.Column(db.String(100))  # 文件类型

# 在应用启动时创建数据库表
with app.app_context():
    db.create_all()

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

@app.route('/script.js')
def serve_script():
    return send_from_directory('.', 'script.js')

@app.route('/styles.css')
def serve_styles():
    return send_from_directory('.', 'styles.css')

@app.route('/chat', methods=['POST'])
def chat():
    try:
        request_id = f"req_{int(time.time()*1000)}"
        client_ip = request.remote_addr
        
        logger.info(f"[{request_id}] New chat request received from {client_ip}")
        logger.info(f"[{request_id}] Headers: {dict(request.headers)}")
        
        data = request.json
        message = data.get('message')
        logger.info(f"[{request_id}] User message: {message}")
        
        logger.info(f"[{request_id}] Calling Ollama API at {OLLAMA_API_URL}")
        
        start_time = time.time()
        try:
            response = requests.post(OLLAMA_API_URL, json={
                "model": "qwen2.5:7b",
                "prompt": message,
                "stream": False
            })
            process_time = time.time() - start_time
            
            logger.info(f"[{request_id}] Ollama response time: {process_time:.2f}s")
            logger.info(f"[{request_id}] Ollama status code: {response.status_code}")
            
            if response.status_code == 200:
                ai_response = response.json().get('response', '')
                logger.info(f"[{request_id}] AI response length: {len(ai_response)} chars")
                return jsonify({
                    "success": True,
                    "response": ai_response,
                    "request_id": request_id,
                    "process_time": f"{process_time:.2f}s"
                })
            else:
                error_msg = f"Failed to get response from Ollama: {response.text}"
                logger.error(f"[{request_id}] {error_msg}")
                return jsonify({
                    "success": False,
                    "error": error_msg,
                    "request_id": request_id
                }), 500
                
        except requests.exceptions.ConnectionError as e:
            error_msg = "Cannot connect to Ollama service"
            logger.error(f"[{request_id}] Connection error: {str(e)}")
            return jsonify({
                "success": False,
                "error": error_msg,
                "request_id": request_id
            }), 500
            
    except Exception as e:
        logger.error(f"[{request_id}] Unexpected error: {str(e)}")
        import traceback
        logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": str(e),
            "request_id": request_id
        }), 500

# 修改上传图片的路由
@app.route('/upload-image', methods=['POST'])
def upload_image():
    try:
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename):
            # 生成文件名和保存文件
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
            filename = timestamp + secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 获取文件信息
            file_size = os.path.getsize(filepath)
            mime_type = file.content_type
            
            # 保存到数据库
            new_image = Image(
                filename=filename,
                path=f'/static/ai_pictures/{filename}',
                original_filename=file.filename,
                file_size=file_size,
                mime_type=mime_type
            )
            db.session.add(new_image)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'filename': filename,
                'path': f'/static/ai_pictures/{filename}',
                'upload_date': new_image.upload_date.isoformat(),
                'file_size': file_size,
                'mime_type': mime_type
            })
            
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Upload error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 修改获取图片列表的路由
@app.route('/get-images', methods=['GET'])
def get_images():
    try:
        # 从数据库获取所有图片信息
        images = Image.query.order_by(Image.upload_date.desc()).all()
        return jsonify({
            'success': True,
            'images': [{
                'filename': img.filename,
                'path': img.path,
                'original_filename': img.original_filename,
                'upload_date': img.upload_date.isoformat(),
                'file_size': img.file_size,
                'mime_type': img.mime_type
            } for img in images]
        })
    except Exception as e:
        logger.error(f"Error getting images: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    logger.info(f"Server starting on http://0.0.0.0:8000")
    app.run(host='0.0.0.0', port=8000)

# 服务器端日志
import logging

# Vercel 环境下的日志会被收集
logging.info("This will be captured in Vercel logs")
print("This will also be captured")
