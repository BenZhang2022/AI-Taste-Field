#Here is the version of 20241107 lidong
from flask import Flask, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import requests
import os
import logging
import time
from datetime import datetime
from werkzeug.utils import secure_filename
import base64
from flask_sqlalchemy import SQLAlchemy
import glob
import os.path

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

app = Flask(__name__, static_url_path='/static', static_folder='static')
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# 确认这个地址是否正确
OLLAMA_API_URL = "http://127.0.0.1:11434/api/generate"

# 配置上传文件的存储位置
UPLOAD_FOLDER = 'static/ai_pictures'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 在文件开头的配置部分添加（在 UPLOAD_FOLDER 定义之后）
BACKUP_FOLDER = 'static/ai_pictures_backup'
# 确保备份目录存在
if not os.path.exists(BACKUP_FOLDER):
    os.makedirs(BACKUP_FOLDER)

app.config['BACKUP_FOLDER'] = BACKUP_FOLDER  # 可选，如果需在其他地方通过 app.config 访问

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
    content = db.Column(db.LargeBinary)  # 添加这个字段来存储图片内容

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
    try:
        return send_from_directory('static', path)
    except Exception as e:
        logger.error(f"Error serving static file {path}: {str(e)}")
        return jsonify({'error': 'File not found'}), 404

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
        logger.info(f"[{request_id}] Raw data: {request.get_data()}")
        
        data = request.json
        message = data.get('message')
        logger.info(f"[{request_id}] User message: {message}")
        
        # 测试 Ollama 连接
        try:
            logger.info(f"[{request_id}] Testing Ollama connection...")
            test_response = requests.get("http://localhost:11434/api/tags")
            logger.info(f"[{request_id}] Ollama test response: {test_response.status_code}")
        except Exception as e:
            logger.error(f"[{request_id}] Ollama connection test failed: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Cannot connect to Ollama service",
                "details": str(e)
            }), 500

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
        logger.info("开始处理图片上传请求")
        if 'image' not in request.files:
            logger.error("没有找到上传的文件")
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['image']
        logger.info(f"接收到文件: {file.filename}")
        
        if file.filename == '':
            logger.error("文件名为空")
            return jsonify({'success': False, 'error': 'No selected file'}), 400
            
        if file and allowed_file(file.filename):
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
            filename = timestamp + secure_filename(file.filename)
            
            # 确保两个目录都存在
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            os.makedirs(BACKUP_FOLDER, exist_ok=True)
            
            # 保存到主目录
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            logger.info(f"文件已保存到主目录: {filepath}")
            
            # 时保存到备份目录
            backup_path = os.path.join(BACKUP_FOLDER, filename)
            with open(filepath, 'rb') as src:
                with open(backup_path, 'wb') as dst:
                    dst.write(src.read())
            logger.info(f"文件已保存到备份目录: {backup_path}")
            
            # 获取文件信息
            file_size = os.path.getsize(filepath)
            mime_type = file.content_type
            
            # 保存图片内容
            with open(filepath, 'rb') as f:
                file_content = f.read()
                new_image = Image(
                    filename=filename,
                    path=f'/static/ai_pictures/{filename}',
                    original_filename=file.filename,
                    file_size=file_size,
                    mime_type=mime_type,
                    content=file_content  # 保存图片内容
                )
            db.session.add(new_image)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'filename': filename,
                'path': f'/static/ai_pictures/{filename}',
                'original_filename': file.filename,
                'upload_date': new_image.upload_date.isoformat(),
                'file_size': file_size,
                'mime_type': mime_type
            })
            
        return jsonify({'success': False, 'error': 'File type not allowed'}), 400
        
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 修改获取图片列表的路由
@app.route('/get-images', methods=['GET'])
def get_images():
    try:
        images = Image.query.order_by(Image.upload_date.desc()).limit(10).all()
        base_url = request.url_root.rstrip('/')
        
        image_list = []
        for img in images:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
            if os.path.exists(file_path):
                image_list.append({
                    'filename': img.filename,
                    'path': f'{base_url}/static/ai_pictures/{img.filename}',
                    'original_filename': img.original_filename,
                    'upload_date': img.upload_date.isoformat(),
                    'file_size': img.file_size,
                    'mime_type': img.mime_type
                })
        
        return jsonify({
            'success': True,
            'images': image_list
        })
    except Exception as e:
        logger.error(f"Error getting images: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 修改刷新图片的路由
@app.route('/refresh-images', methods=['POST'])
def refresh_images():
    try:
        logger.info("开始刷新图片")
        
        # 1. 确保目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        os.makedirs(BACKUP_FOLDER, exist_ok=True)
        
        # 2. 检查当前目录中的图片数量
        current_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) 
                        if os.path.isfile(os.path.join(app.config['UPLOAD_FOLDER'], f))]
        logger.info(f"当前目录中有 {len(current_files)} 张图片")
        
        # 3. 从数据库获取最新的10张图片记录
        images = Image.query.order_by(Image.upload_date.desc()).limit(10).all()
        logger.info(f"从数据库获取了 {len(images)} 张图片记录")
        
        success_count = 0
        for img in images:
            try:
                backup_path = os.path.join(BACKUP_FOLDER, img.filename)
                target_path = os.path.join(app.config['UPLOAD_FOLDER'], img.filename)
                
                # 如果备份文件不存在，尝试从数据库获取并保存
                if not os.path.exists(backup_path):
                    # 这里需要实现从数据库获取图片内容的逻辑
                    # 假设图片内容存储在数据库的 content 字段
                    if hasattr(img, 'content') and img.content:
                        with open(backup_path, 'wb') as backup_file:
                            backup_file.write(img.content)
                        logger.info(f"从数据库下载图片到备份目录: {img.filename}")
                
                # 如果备份文件存在，复制到主目录
                if os.path.exists(backup_path):
                    if not os.path.exists(target_path):
                        with open(backup_path, 'rb') as src:
                            with open(target_path, 'wb') as dst:
                                dst.write(src.read())
                        success_count += 1
                        logger.info(f"已复制文件到主目录: {img.filename}")
                else:
                    logger.warning(f"无法获取图片文件: {img.filename}")
                    
            except Exception as e:
                logger.error(f"处理文件 {img.filename} 时出错: {str(e)}")
                continue
        
        logger.info(f"成功补充了 {success_count} 张图片")
        return jsonify({
            'success': True,
            'message': f'Successfully refreshed {success_count} images'
        })
        
    except Exception as e:
        logger.error(f"Error refreshing images: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 添加清理数据库记录的路由
@app.route('/cleanup-images', methods=['POST'])
def cleanup_images():
    try:
        logger.info("开始清理数据库中的无效图片记录")
        
        # 获取所有图片记录
        all_images = Image.query.all()
        removed_count = 0
        
        for img in all_images:
            # 检查备份文件是否存在
            backup_path = os.path.join(BACKUP_FOLDER, img.filename)
            
            # 如果备份文件不存在，但数据库中有内容，尝试恢复
            if not os.path.exists(backup_path) and img.content:
                try:
                    # 从数据库恢复到备份目录
                    with open(backup_path, 'wb') as backup_file:
                        backup_file.write(img.content)
                    logger.info(f"从数据库恢复文件到备份目录: {img.filename}")
                    continue  # 恢复成功，跳过删除
                except Exception as e:
                    logger.error(f"恢复文件失败: {str(e)}")
            
            # 如果备份文件不存在且无法从数据库恢复，删除记录
            if not os.path.exists(backup_path):
                logger.info(f"删除无效记录: {img.filename}")
                db.session.delete(img)
                removed_count += 1
        
        # 提交更改
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'已清理 {removed_count} 条无效记录'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"清理记录时出错: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 修改 ComfyUI 代理路由
@app.route('/comfui/<path:path>', methods=['GET', 'POST', 'OPTIONS', 'WS', 'WSS'])
def proxy_comfyui(path):
    try:
        target_url = f'http://localhost:8188/{path}'
        
        # 转发所有请求头，但修改 Host 和 Origin
        headers = {key: value for (key, value) in request.headers if key.lower() not in ['host', 'origin']}
        headers['Host'] = 'localhost:8188'
        headers['Origin'] = 'http://localhost:8188'
        
        # 处理 WebSocket 升级请求
        if request.headers.get('Upgrade') == 'websocket':
            return Response(
                status=101,
                headers={
                    'Upgrade': 'websocket',
                    'Connection': 'Upgrade',
                    'Sec-WebSocket-Accept': request.headers.get('Sec-WebSocket-Key', '')
                }
            )
        
        # 常规请求处理
        if request.method == 'GET':
            params = request.args.to_dict()
            response = requests.get(target_url, headers=headers, params=params, stream=True)
        elif request.method == 'POST':
            data = request.get_data()
            response = requests.post(target_url, headers=headers, data=data, stream=True)
        else:
            return '', 204
            
        # 转发响应，但修改 CORS 头
        resp_headers = dict(response.headers)
        resp_headers['Access-Control-Allow-Origin'] = '*'
        resp_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp_headers['Access-Control-Allow-Headers'] = '*'
        
        return Response(
            response.raw.read(),
            status=response.status_code,
            headers=resp_headers
        )
        
    except Exception as e:
        logger.error(f"Error proxying ComfyUI request: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 修改 ComfyUI 根路径代理
@app.route('/comfui/', methods=['GET', 'POST', 'OPTIONS'])
def proxy_comfyui_root():
    try:
        headers = {
            'Host': 'localhost:8188',
            'Origin': 'http://localhost:8188'
        }
        
        try:
            params = request.args.to_dict()
            response = requests.get('http://localhost:8188/', headers=headers, params=params, timeout=2)
            resp_headers = dict(response.headers)
            resp_headers['Access-Control-Allow-Origin'] = '*'
            resp_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            resp_headers['Access-Control-Allow-Headers'] = '*'
            
            return response.content, response.status_code, resp_headers.items()
        except requests.exceptions.ConnectionError:
            return jsonify({'error': 'ComfyUI service is not running'}), 503
            
    except Exception as e:
        logger.error(f"Error proxying ComfyUI root: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 修改 OmniGen 代理路由
@app.route('/omnigen/<path:path>', methods=['GET', 'POST', 'OPTIONS', 'WS', 'WSS'])
def proxy_omnigen(path):
    try:
        target_url = f'http://localhost:7860/{path}'
        
        # 转发所有请求头，但修改 Host 和 Origin
        headers = {key: value for (key, value) in request.headers if key.lower() not in ['host', 'origin']}
        headers['Host'] = 'localhost:7860'
        headers['Origin'] = 'http://localhost:7860'
        
        # 处理 WebSocket 升级请求
        if request.headers.get('Upgrade') == 'websocket':
            return Response(
                status=101,
                headers={
                    'Upgrade': 'websocket',
                    'Connection': 'Upgrade',
                    'Sec-WebSocket-Accept': request.headers.get('Sec-WebSocket-Key', '')
                }
            )
        
        # 常规请求处理
        if request.method == 'GET':
            params = request.args.to_dict()
            response = requests.get(target_url, headers=headers, params=params, stream=True)
        elif request.method == 'POST':
            data = request.get_data()
            response = requests.post(target_url, headers=headers, data=data, stream=True)
        else:
            return '', 204
            
        # 转发响应，但修改 CORS 头
        resp_headers = dict(response.headers)
        resp_headers['Access-Control-Allow-Origin'] = '*'
        resp_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp_headers['Access-Control-Allow-Headers'] = '*'
        
        return Response(
            response.raw.read(),
            status=response.status_code,
            headers=resp_headers
        )
        
    except Exception as e:
        logger.error(f"Error proxying OmniGen request: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 修改 OmniGen 根路径代理
@app.route('/omnigen/', methods=['GET', 'POST', 'OPTIONS'])
def proxy_omnigen_root():
    try:
        headers = {
            'Host': 'localhost:7860',
            'Origin': 'http://localhost:7860'
        }
        
        try:
            params = request.args.to_dict()
            response = requests.get('http://localhost:7860/', headers=headers, params=params, timeout=2)
            resp_headers = dict(response.headers)
            resp_headers['Access-Control-Allow-Origin'] = '*'
            resp_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            resp_headers['Access-Control-Allow-Headers'] = '*'
            
            return response.content, response.status_code, resp_headers.items()
        except requests.exceptions.ConnectionError:
            return jsonify({'error': 'OmniGen service is not running'}), 503
            
    except Exception as e:
        logger.error(f"Error proxying OmniGen root: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/static/comfyui.html')
def serve_comfyui_page():
    return send_from_directory('static', 'comfyui.html')

@app.route('/static/omnigen.html')
def serve_omnigen_page():
    return send_from_directory('static', 'omnigen.html')

@app.route('/upload-latest-comfyui', methods=['POST'])
def upload_latest_comfyui():
    try:
        # ComfyUI 输出目录
        output_dir = '/Users/jianbinzhang/ComfyUI/output'
        
        # 获取目录中最新的图片
        files = glob.glob(os.path.join(output_dir, '*.*'))
        if not files:
            return jsonify({'success': False, 'error': 'No images found in output directory'}), 404
            
        latest_file = max(files, key=os.path.getctime)
        filename = os.path.basename(latest_file)
        
        # 确保文件是图片
        if not allowed_file(filename):
            return jsonify({'success': False, 'error': 'Latest file is not an image'}), 400
            
        # 生成新文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_")
        new_filename = timestamp + secure_filename(filename)
        
        # 保存到主目录和备份目录
        with open(latest_file, 'rb') as f:
            file_content = f.read()
            
            # 保存到主目录
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], new_filename)
            with open(filepath, 'wb') as dst:
                dst.write(file_content)
                
            # 保存到备份目录
            backup_path = os.path.join(BACKUP_FOLDER, new_filename)
            with open(backup_path, 'wb') as dst:
                dst.write(file_content)
        
        # 获取文件信息
        file_size = os.path.getsize(filepath)
        mime_type = 'image/' + filename.rsplit('.', 1)[1].lower()
        
        # 保存到数据库
        new_image = Image(
            filename=new_filename,
            path=f'/static/ai_pictures/{new_filename}',
            original_filename=filename,
            file_size=file_size,
            mime_type=mime_type,
            content=file_content
        )
        db.session.add(new_image)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'filename': new_filename,
            'path': f'/static/ai_pictures/{new_filename}'
        })
        
    except Exception as e:
        logger.error(f"Error uploading latest ComfyUI image: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# 添加 OpenWebUI 代理路由
@app.route('/webui/<path:path>', methods=['GET', 'POST', 'OPTIONS', 'WS', 'WSS'])
def proxy_webui(path):
    try:
        container_ip = "10.88.0.2"  # podman 容器的 IP
        target_url = f'http://{container_ip}:3000/{path}'
        
        # 转发所有请求头，但修改 Host 和 Origin
        headers = {key: value for (key, value) in request.headers if key.lower() not in ['host', 'origin']}
        headers['Host'] = f'{container_ip}:3000'
        headers['Origin'] = f'http://{container_ip}:3000'
        
        # 处理 WebSocket 升级请求
        if request.headers.get('Upgrade') == 'websocket':
            return Response(
                status=101,
                headers={
                    'Upgrade': 'websocket',
                    'Connection': 'Upgrade',
                    'Sec-WebSocket-Accept': request.headers.get('Sec-WebSocket-Key', '')
                }
            )
        
        # 常规请求处理
        if request.method == 'GET':
            params = request.args.to_dict()
            response = requests.get(target_url, headers=headers, params=params, stream=True)
        elif request.method == 'POST':
            data = request.get_data()
            response = requests.post(target_url, headers=headers, data=data, stream=True)
        else:
            return '', 204
            
        # 转发响应，但修改 CORS 头
        resp_headers = dict(response.headers)
        resp_headers['Access-Control-Allow-Origin'] = '*'
        resp_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp_headers['Access-Control-Allow-Headers'] = '*'
        
        return Response(
            response.raw.read(),
            status=response.status_code,
            headers=resp_headers
        )
        
    except Exception as e:
        logger.error(f"Error proxying WebUI request: {str(e)}")
        return jsonify({'error': str(e)}), 500

# 添加 WebUI 根路径代理
@app.route('/webui/', methods=['GET', 'POST', 'OPTIONS'])
def proxy_webui_root():
    try:
        # 使用容器的实际 IP 地址
        container_ip = "10.88.0.2"  # podman 容器的 IP
        headers = {
            'Host': f'{container_ip}:3000',
            'Origin': f'http://{container_ip}:3000'
        }
        
        try:
            params = request.args.to_dict()
            response = requests.get(f'http://{container_ip}:3000/', headers=headers, params=params, timeout=2)
            resp_headers = dict(response.headers)
            resp_headers['Access-Control-Allow-Origin'] = '*'
            resp_headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            resp_headers['Access-Control-Allow-Headers'] = '*'
            
            return response.content, response.status_code, resp_headers.items()
        except requests.exceptions.ConnectionError:
            return jsonify({'error': 'WebUI service is not running'}), 503
            
    except Exception as e:
        logger.error(f"Error proxying WebUI root: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/static/webui.html')
def serve_webui_page():
    return send_from_directory('static', 'webui.html')

if __name__ == '__main__':
    logger.info(f"Server starting on http://0.0.0.0:8000")
    app.run(host='0.0.0.0', port=8000)

# 服务器端日志
import logging

# Vercel 环境下的日志会被收集
logging.info("This will be captured in Vercel logs")
print("This will also be captured")
