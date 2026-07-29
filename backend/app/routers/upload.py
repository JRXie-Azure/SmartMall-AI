"""
File upload router — 本地存储 + S3对象存储双模式
支持: 阿里云OSS / 腾讯云COS / MinIO / AWS S3 (S3兼容协议)
增强: Pillow 图片压缩 + 缩略图 + 商品图片上传 + 文件删除
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pathlib import Path
import uuid

import logging
from app.config import get_settings
from app.auth import get_current_user, get_current_admin
from app.models import User as UserModel

settings = get_settings()
router = APIRouter(prefix="/api/upload", tags=["File Upload"])
logger = logging.getLogger(__name__)

ALLOWED_IMAGE_TYPES = {"png", "jpg", "jpeg", "gif", "webp"}
MAX_FILE_SIZE = settings.MAX_UPLOAD_SIZE

# ====== 图片处理参数 (Pillow) ======
MAX_IMAGE_WIDTH = 1200       # 原图最大宽度 (px)
IMAGE_QUALITY = 85           # JPEG 压缩质量
THUMBNAIL_SIZE = 300         # 缩略图边长 (正方形 px)
# 上传文件可能存放的子目录 (删除时依次查找)
UPLOAD_SUBDIRS = ["images", "products", "products/thumbnails"]

# ====== S3 客户端懒加载 ======
_s3_client = None

def _get_s3_client():
    global _s3_client
    if _s3_client is None and settings.storage_is_s3:
        import boto3
        from botocore.config import Config
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
            config=Config(s3={"addressing_style": "virtual"}),
        )
    return _s3_client


def _get_ext(filename: str) -> str:
    return Path(filename).suffix.lower().lstrip(".") or "jpg"


def _get_image_type(content: bytes) -> str:
    """通过文件头 Magic Bytes 检测图片类型 (替代 Python 3.13 移除的 imghdr)"""
    if content.startswith(b'\xff\xd8'):
        return 'jpeg'
    if content.startswith(b'\x89PNG\r\n\x1a\n'):
        return 'png'
    if content.startswith(b'GIF89a') or content.startswith(b'GIF87a'):
        return 'gif'
    if content.startswith(b'RIFF') and content[8:12] == b'WEBP':
        return 'webp'
    return ''

def _validate_image(file: UploadFile, content: bytes) -> str:
    ext = _get_ext(file.filename)
    if ext not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式: {ext}, 允许: {', '.join(ALLOWED_IMAGE_TYPES)}"
        )
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件过大, 最大: {MAX_FILE_SIZE / 1024 / 1024:.0f}MB"
        )
    real_type = _get_image_type(content)
    if real_type and real_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="图片内容无效")
    return ext


# ====== 图片压缩与缩略图 (Pillow) ======
def _compress_image(
    content: bytes,
    max_width: int = MAX_IMAGE_WIDTH,
    quality: int = IMAGE_QUALITY,
) -> tuple[bytes, str]:
    """
    用 Pillow 压缩图片:
    - 宽度超过 max_width 时等比缩小
    - 以 quality 质量输出 JPEG
    - GIF 保持原样以保留动画
    返回: (压缩后字节, 输出扩展名)
    """
    from io import BytesIO
    try:
        from PIL import Image
    except ImportError:
        logger.warning("未安装 Pillow, 跳过图片压缩")
        return content, _get_image_type(content) or "jpg"

    try:
        img = Image.open(BytesIO(content))
    except Exception as e:
        logger.warning(f"Pillow 无法解析图片, 跳过压缩: {e}")
        return content, _get_image_type(content) or "jpg"

    # GIF 保留动图原样, 不做有损压缩
    if (img.format or "").upper() == "GIF":
        return content, "gif"

    # 等比缩放 (仅当宽度超出限制)
    if img.width > max_width:
        new_height = int(img.height * max_width / img.width)
        img = img.resize((max_width, new_height), Image.LANCZOS)

    # JPEG 不支持透明通道, 统一转 RGB (透明区域填白底)
    if img.mode in ("RGBA", "LA"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue(), "jpg"


def _make_thumbnail(content: bytes, size: int = THUMBNAIL_SIZE) -> tuple[bytes, str]:
    """
    生成居中裁剪的正方形缩略图 (默认 300x300), 输出 JPEG
    返回: (缩略图字节, 扩展名)
    """
    from io import BytesIO
    try:
        from PIL import Image
    except ImportError:
        logger.warning("未安装 Pillow, 跳过缩略图生成")
        return content, "jpg"

    try:
        img = Image.open(BytesIO(content))
    except Exception as e:
        logger.warning(f"无法生成缩略图: {e}")
        return content, "jpg"

    img = img.convert("RGB")
    width, height = img.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    img = img.crop((left, top, left + side, top + side))
    img = img.resize((size, size), Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue(), "jpg"


def _save_local(content: bytes, ext: str, subdir: str = "images") -> str:
    upload_dir = Path(settings.UPLOAD_DIR) / subdir
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.{ext}"
    filepath = upload_dir / filename
    with open(filepath, "wb") as f:
        f.write(content)
    return f"/uploads/{subdir}/{filename}"


def _save_s3(content: bytes, ext: str, subdir: str = "images") -> str:
    """上传到 S3 兼容对象存储，返回可访问的公网URL"""
    client = _get_s3_client()
    filename = f"{subdir}/{uuid.uuid4().hex}.{ext}"
    content_type = f"image/{ext.replace('jpg', 'jpeg')}"
    try:
        client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=filename,
            Body=content,
            ContentType=content_type,
            ACL="public-read",
        )
        # 返回公网访问URL
        if settings.S3_PUBLIC_URL:
            return f"{settings.S3_PUBLIC_URL.rstrip('/')}/{filename}"
        # 从 endpoint 构造 URL (虚拟主机风格)
        endpoint = settings.S3_ENDPOINT.rstrip("/")
        return f"{endpoint}/{settings.S3_BUCKET}/{filename}"
    except Exception as e:
        logger.error(f"S3 upload failed: {e}")
        raise HTTPException(status_code=500, detail=f"对象存储上传失败: {e}")


def _save_upload(content: bytes, ext: str, subdir: str = "images") -> str:
    """统一上传入口: 根据配置自动选择本地或S3"""
    if settings.storage_is_s3:
        return _save_s3(content, ext, subdir)
    return _save_local(content, ext, subdir)


# ====== 文件删除 (本地 / S3) ======
def _delete_local(filename: str) -> bool:
    """从本地存储删除文件, 在已知子目录中查找。返回是否删除成功。"""
    name = Path(filename).name  # 仅取文件名, 防止路径穿越
    for subdir in UPLOAD_SUBDIRS:
        filepath = Path(settings.UPLOAD_DIR) / subdir / name
        if filepath.exists():
            try:
                filepath.unlink()
                return True
            except OSError as e:
                logger.error(f"删除本地文件失败 {filepath}: {e}")
                return False
    return False


def _delete_s3(filename: str) -> bool:
    """从 S3 删除文件, 在已知子目录前缀中尝试。"""
    client = _get_s3_client()
    if client is None:
        return False
    name = Path(filename).name
    for subdir in UPLOAD_SUBDIRS:
        key = f"{subdir}/{name}"
        try:
            client.head_object(Bucket=settings.S3_BUCKET, Key=key)
        except Exception:
            continue  # 该前缀下不存在, 继续尝试下一个
        try:
            client.delete_object(Bucket=settings.S3_BUCKET, Key=key)
            return True
        except Exception as e:
            logger.error(f"S3 删除失败 {key}: {e}")
            return False
    return False


def _delete_upload(filename: str) -> bool:
    """统一删除入口: 根据配置自动选择本地或S3"""
    if settings.storage_is_s3:
        return _delete_s3(filename)
    return _delete_local(filename)


@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
):
    content = await file.read()
    ext = _validate_image(file, content)
    # 上传前用 Pillow 自动压缩图片
    content, ext = _compress_image(content)
    url = _save_upload(content, ext, subdir="images")
    return {"url": url, "filename": Path(url).name}


@router.post("/images")
async def upload_multiple_images(
    files: list[UploadFile] = File(...),
    current_user: UserModel = Depends(get_current_user),
):
    urls = []
    for file in files:
        content = await file.read()
        ext = _validate_image(file, content)
        # 上传前用 Pillow 自动压缩图片
        content, ext = _compress_image(content)
        url = _save_upload(content, ext, subdir="images")
        urls.append(url)
    return {"urls": urls}


@router.post("/product-image")
async def upload_product_image(
    file: UploadFile = File(...),
    current_user: UserModel = Depends(get_current_user),
):
    """
    商品图片上传:
    - 自动压缩原图 (最大宽度 1200px, 质量 85%)
    - 生成 300x300 缩略图用于商品列表
    - 同时上传两者, 返回 {original_url, thumbnail_url}
    """
    content = await file.read()
    _validate_image(file, content)
    # 压缩原图
    original_content, original_ext = _compress_image(content)
    # 生成缩略图 (基于原始内容, 清晰度更高)
    thumb_content, thumb_ext = _make_thumbnail(content)
    original_url = _save_upload(original_content, original_ext, subdir="products")
    thumbnail_url = _save_upload(thumb_content, thumb_ext, subdir="products/thumbnails")
    return {"original_url": original_url, "thumbnail_url": thumbnail_url}


@router.get("/config")
async def get_upload_config(current_user: UserModel = Depends(get_current_user)):
    """返回当前上传配置 (前端用于判断支持哪些功能)"""
    return {
        "storage_type": "s3" if settings.storage_is_s3 else "local",
        "max_size": MAX_FILE_SIZE,
        "allowed_types": list(ALLOWED_IMAGE_TYPES),
    }


@router.delete("/{filename}")
async def delete_upload(
    filename: str,
    current_user: UserModel = Depends(get_current_admin),
):
    """
    删除已上传的文件 (仅管理员可操作)
    支持本地存储与 S3 对象存储, 在已知子目录中查找并删除。
    """
    deleted = _delete_upload(filename)
    if not deleted:
        raise HTTPException(status_code=404, detail="文件不存在或已被删除")
    return {"message": "删除成功", "filename": Path(filename).name}
