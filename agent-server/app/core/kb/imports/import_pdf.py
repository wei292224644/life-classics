"""
PDF 文件导入模块
支持文本提取和图片型PDF的OCR识别（使用视觉模型）
"""

import json
import os
import tempfile
from io import BytesIO
from typing import List, Optional
from pathlib import Path

import pymupdf.layout  # 必须先导入这个来激活布局功能
import pymupdf  # PyMuPDF
from app.core.document_chunk import DocumentChunk, ContentType
from app.core.config import settings
from app.core.llm import get_multimodal

# 导入图片提取和解析功能
try:
    import dashscope

    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False

try:
    from PIL import Image
    import numpy as np

    PIL_AVAILABLE = True
    NUMPY_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    try:
        import numpy as np

        NUMPY_AVAILABLE = True
    except ImportError:
        NUMPY_AVAILABLE = False

try:
    from pypdf import PdfReader

    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False


def extract_pdf_text(pdf_path: str) -> str:
    """
    从PDF中提取所有文本（基于 pdfplumber）

    Args:
        pdf_path: PDF文件路径

    Returns:
        提取的文本内容
    """
    text_parts = []

    try:
        with pymupdf.open(pdf_path) as pdf:
            print(f"PDF总页数: {len(pdf)}")

            for page_num, page in enumerate(pdf, start=1):
                list = page.get_text_blocks() or ""
                text = json.dumps(list, ensure_ascii=False)
                if text:
                    text_parts.append(f"=== 第 {page_num} 页 ===\n{text}\n")
                    print(f"  第 {page_num} 页: 提取了 {len(text)} 个字符")

            full_text = "\n".join(text_parts)
            print(f"\n总共提取了 {len(full_text)} 个字符")
            return full_text

    except Exception as e:
        print(f"PDF解析失败: {e}")
        import traceback

        traceback.print_exc()
        return ""


def is_blank_image(
    image: Image.Image, threshold: float = 0.95, variance_threshold: float = 500.0
) -> bool:
    """
    检测图片是否为空白（主要是白色）

    Args:
        image: PIL Image 对象
        threshold: 平均亮度阈值，超过此值认为是空白（0-1，默认 0.95，即 95% 白色）
        variance_threshold: 方差阈值，低于此值认为内容单一，可能是空白（默认 500.0）

    Returns:
        是否为空白图片
    """
    if not PIL_AVAILABLE:
        return False

    try:
        # 转换为灰度图
        if image.mode != "L":
            gray = image.convert("L")
        else:
            gray = image

        if NUMPY_AVAILABLE:
            # 使用 numpy 进行精确计算
            img_array = np.array(gray)

            # 计算平均亮度（0-255，255为白色）
            mean_brightness = np.mean(img_array)
            mean_ratio = mean_brightness / 255.0

            # 计算方差（衡量图片内容的多样性）
            variance = np.var(img_array)

            # 计算接近白色的像素比例（亮度 >= 240 的像素）
            white_pixels = np.sum(img_array >= 240)
            total_pixels = img_array.size
            white_ratio = white_pixels / total_pixels if total_pixels > 0 else 0

            # 计算非白色像素比例（亮度 < 240 的像素）
            non_white_pixels = total_pixels - white_pixels
            non_white_ratio = non_white_pixels / total_pixels if total_pixels > 0 else 0

            # 计算深色像素比例（亮度 < 200 的像素，可能是文字或内容）
            dark_pixels = np.sum(img_array < 200)
            dark_ratio = dark_pixels / total_pixels if total_pixels > 0 else 0

            # 改进的检测逻辑：只有同时满足以下条件才认为是空白：
            # 1. 平均亮度很高（>= threshold）
            # 2. 方差很小（<= variance_threshold，说明内容单一）
            # 3. 非白色像素很少（< 2%，确保几乎没有内容）
            # 4. 深色像素很少（< 0.5%，确保几乎没有文字或深色内容）
            is_blank = (
                mean_ratio >= threshold
                and variance <= variance_threshold
                and non_white_ratio < 0.02  # 非白色像素少于2%
                and dark_ratio < 0.005  # 深色像素少于0.5%
            )

            return is_blank
        else:
            # 如果没有 numpy，使用 getcolors 方法
            colors = gray.getcolors(maxcolors=256 * 256)
            if not colors:
                return False

            # 计算加权平均亮度
            total_pixels = sum(count for count, _ in colors)
            if total_pixels == 0:
                return False

            weighted_sum = sum(count * color for count, color in colors)
            mean_brightness = weighted_sum / total_pixels
            mean_ratio = mean_brightness / 255.0

            # 计算接近白色的像素比例（亮度 >= 240）
            white_pixels = sum(count for count, color in colors if color >= 240)
            white_ratio = white_pixels / total_pixels if total_pixels > 0 else 0

            # 计算非白色像素比例（亮度 < 240）
            non_white_pixels = total_pixels - white_pixels
            non_white_ratio = non_white_pixels / total_pixels if total_pixels > 0 else 0

            # 计算深色像素比例（亮度 < 200）
            dark_pixels = sum(count for count, color in colors if color < 200)
            dark_ratio = dark_pixels / total_pixels if total_pixels > 0 else 0

            # 计算方差
            variance = (
                sum(count * (color - mean_brightness) ** 2 for count, color in colors)
                / total_pixels
            )

            # 改进的检测逻辑：只有同时满足以下条件才认为是空白：
            # 1. 平均亮度很高（>= threshold）
            # 2. 方差很小（<= variance_threshold，说明内容单一）
            # 3. 非白色像素很少（< 2%，确保几乎没有内容）
            # 4. 深色像素很少（< 0.5%，确保几乎没有文字或深色内容）
            is_blank = (
                mean_ratio >= threshold
                and variance <= variance_threshold
                and non_white_ratio < 0.02  # 非白色像素少于2%
                and dark_ratio < 0.005  # 深色像素少于0.5%
            )

            return is_blank
    except Exception as e:
        # 如果检测失败，不跳过图片
        print(f"  警告: 检测空白图片时出错: {e}")
        return False


def extract_pdf_images(
    pdf_path: str,
    output_dir: Path,
    skip_blank: bool = True,
    blank_threshold: float = 0.95,
    blank_variance_threshold: float = 500.0,
) -> List[Path]:
    """
    从PDF中提取嵌入的图片对象（extract-images模式）

    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录
        skip_blank: 是否跳过空白图片（默认: True）
        blank_threshold: 空白检测的平均亮度阈值（0-1，默认: 0.95）
        blank_variance_threshold: 空白检测的方差阈值（默认: 500.0）

    Returns:
        提取的图片文件路径列表
    """
    if not PYPDF_AVAILABLE:
        raise ImportError("pypdf 未安装，无法提取嵌入图片")

    if not PIL_AVAILABLE:
        raise ImportError("Pillow 未安装，无法处理图片")

    reader = PdfReader(pdf_path)
    image_count = 0
    image_files = []
    skipped_count = 0

    print(f"  处理 PDF: {pdf_path}")
    print(f"  总页数: {len(reader.pages)}")
    print(f"  跳过空白: {skip_blank}")

    for page_num, page in enumerate(reader.pages, start=1):
        try:
            # 获取页面的 Resources，需要先获取对象
            resources = page.get("/Resources")
            if resources is None:
                continue

            # 如果是间接引用，需要获取实际对象
            if hasattr(resources, "get_object"):
                resources = resources.get_object()

            if not isinstance(resources, dict) or "/XObject" not in resources:
                continue

            # 获取 XObject 字典
            xObject = resources["/XObject"]
            if hasattr(xObject, "get_object"):
                xObject = xObject.get_object()

            if not isinstance(xObject, dict):
                continue

            for obj_num, obj in xObject.items():
                # 如果是间接引用，需要获取实际对象
                if hasattr(obj, "get_object"):
                    obj = obj.get_object()

                if not isinstance(obj, dict):
                    continue

                if obj.get("/Subtype") != "/Image":
                    continue

                image_count += 1

                # 获取图片数据
                try:
                    size = (obj.get("/Width", 0), obj.get("/Height", 0))
                    data = obj.get_data()
                except Exception as e:
                    print(f"    警告: 无法获取图片 {image_count} 的数据: {e}")
                    continue

                # 确定图片格式
                filter_type = obj.get("/Filter", "")
                if isinstance(filter_type, list):
                    filter_type = filter_type[0] if filter_type else ""

                if filter_type == "/DCTDecode":
                    ext = ".jpg"
                elif filter_type == "/FlateDecode":
                    ext = ".png"
                elif filter_type == "/CCITTFaxDecode":
                    ext = ".tiff"
                else:
                    ext = ".png"

                # 检测是否为空白图片
                if skip_blank:
                    try:
                        # 从字节数据创建 PIL Image
                        img = Image.open(BytesIO(data))

                        if is_blank_image(
                            img, blank_threshold, blank_variance_threshold
                        ):
                            print(
                                f"    页面 {page_num} 图片 {image_count}: 跳过空白图片"
                            )
                            skipped_count += 1
                            continue
                    except Exception as e:
                        # 如果检测失败，继续保存图片
                        print(f"    警告: 检测图片 {image_count} 时出错: {e}，继续保存")

                # 保存图片
                image_filename = f"page_{page_num:03d}_img_{image_count:03d}{ext}"
                image_path = output_dir / image_filename

                try:
                    with open(image_path, "wb") as img_file:
                        img_file.write(data)
                    image_files.append(image_path)
                    print(f"    提取图片: {image_filename} ({size[0]}x{size[1]})")
                except Exception as e:
                    print(f"    警告: 保存图片 {image_filename} 失败: {e}")
        except Exception as e:
            print(f"    警告: 处理页面 {page_num} 时出错: {e}")
            continue

    if skip_blank and skipped_count > 0:
        print(f"  跳过 {skipped_count} 张空白图片")

    print(f"  成功提取 {len(image_files)} 张图片")
    return image_files


def parse_images_with_llm(
    image_paths: List[Path], prompt: str, model: str = "qwen3-vl-plus-2025-12-19"
) -> str:
    """
    使用视觉模型解析图片内容

    Args:
        image_paths: 图片文件路径列表
        prompt: 提示词
        model: 模型名称

    Returns:
        解析后的文本内容
    """
    # 使用封装的 get_multimodal 获取多模态对话实例
    multimodal = get_multimodal(
        "dashscope",
        {"model": model, "temperature": 0.5, "enable_thinking": False, "top_p": 0.5},
    )

    # 构建消息内容：先添加所有图片，然后添加文本
    content = []
    for image_path in image_paths:
        content.append({"image": f"file://{os.path.abspath(str(image_path))}"})
    content.append({"text": prompt})

    # 构建消息
    messages = [
        {
            "role": "user",
            "content": content,
        }
    ]

    # 调用多模态对话模型
    response = multimodal.invoke(messages)

    return response.content[0]["text"]


def detect_image_pdf(file_path: str, text_content: str) -> bool:
    """
    检测是否为图片型PDF

    Args:
        file_path: PDF文件路径
        text_content: 提取的文本内容

    Returns:
        是否为图片型PDF
    """
    # 方法1: 检查提取的文本长度
    # 如果文本很少或为空，可能是图片型PDF
    if not text_content or len(text_content.strip()) < 100:
        print(
            f"检测到图片型PDF（文本长度: {len(text_content.strip()) if text_content else 0}）"
        )
        return True

    # 方法2: 检查PDF中的图片对象数量
    # 如果图片对象数量远大于文本内容，可能是图片型PDF
    if PYPDF_AVAILABLE:
        try:
            reader = PdfReader(file_path)
            total_images = 0
            total_pages = len(reader.pages)

            for page in reader.pages:
                if "/XObject" in page.get("/Resources", {}):
                    xObject = page["/Resources"]["/XObject"]
                    if hasattr(xObject, "get_object"):
                        xObject = xObject.get_object()
                    if isinstance(xObject, dict):
                        for obj_num, obj in xObject.items():
                            if (
                                isinstance(obj, dict)
                                and obj.get("/Subtype") == "/Image"
                            ):
                                total_images += 1

            # 如果平均每页有图片，且文本密度很低，可能是图片型PDF
            # 文本密度 = 文本长度 / 页数
            text_density = (
                len(text_content.strip()) / total_pages if total_pages > 0 else 0
            )

            # 判断条件：
            # 1. 有图片对象
            # 2. 文本密度很低（每页少于200字符）
            # 3. 或者图片数量明显多于文本内容
            if total_images > 0 and (
                text_density < 200 or total_images > len(text_content.strip()) / 10
            ):
                print(
                    f"检测到图片型PDF（图片数: {total_images}, 文本密度: {text_density:.1f} 字符/页）"
                )
                return True
        except Exception as e:
            # 如果检测失败，使用文本长度作为判断依据
            print(f"图片检测失败，使用文本长度判断: {e}")

    return False


def process_pdf_with_ocr(pdf_path: str) -> str:
    """
    使用OCR（视觉模型）处理图片型PDF

    Args:
        pdf_path: PDF文件路径

    Returns:
        解析后的文本内容
    """
    print(f"\n开始OCR处理: {Path(pdf_path).name}")
    print(f"PDF路径: {pdf_path}")

    if not PYPDF_AVAILABLE:
        raise ImportError("pypdf 未安装，无法提取PDF图片")

    # 构建提示词
    prompt = """【任务目标】
逐字逐行转写图片中所有以独立印刷体文本行形式存在的内容（包括标题、说明、编号条目、图注、标签等），并对图谱/曲线图/色谱图等图像类内容仅添加且仅添加一句客观描述句。

【必须遵守的规则】

仅转写真实存在的独立文本行：

仅当某行文字在图片中以完整、独立的印刷体文本行形式呈现（如标题、段落、列表项、图注等），才可原样转写；
坐标轴刻度值（如"0""20""100"）、峰顶数值（如"4.34""3.82"）、网格线标记、图形内部数字标签等视觉元素，一律不得拆解为分行文本输出；
图形中的文字标签（如"t/min""相对丰度，%""1""2"）若以独立文本行形式存在（如坐标轴标题），则按原文转写；若嵌入图形内部（如色谱图右端序号），则仅在图谱描述句中提及。
图谱/曲线图/色谱图等图像类内容的处理：

禁止任何形式的坐标轴还原、峰形描述或数值分行转写；
必须且仅能用一段连贯陈述句描述该图像的整体构成，该句需：
严格基于图中明确可见的文字与符号（如坐标轴标签、峰时间值、图序号）；
包含图像类型（如"特征离子质量色谱图"）、标号范围（如"标号1至4"）、坐标轴定义（如"横坐标为保留时间t/min（0–10 min）"）、关键可见特征（如"可见两组峰位于约4.34 min处"）；
不得虚构、补充或解释任何未在图中直接显示的信息（如不添加"图中显示""结果表明"等推断性表述）；
必须作为单句存在，不使用分号、项目符号或换行。
排版与内容边界：

严格保持原文换行、缩进及层级结构；
仅当图片中存在图谱类内容时，才在所有真实文本行之后、图注之前或之后（依原图逻辑顺序） 插入图谱描述句；
若图中无任何文字标签（如纯图形无标注），则不输出任何描述句。
绝对禁止行为：

添加区域标题（如"图谱部分"）、说明性语句（如"以下为图谱内容"）；
对内容分类、归纳、总结或补充背景知识；
修改原文符号（如将"—"替换为"-"）、统一数字格式或添加标点。
【输出要求】

仅输出转写结果本身，无前言、结论或标注；
顺序为：真实文本行 → （图谱描述句，若存在） → 其余真实文本行；
图谱描述句格式示例（需根据图片动态适配）：
"图中包含四组特征离子质量色谱图，标号1至4，横坐标为保留时间t/min（0–10 min），纵坐标为相对丰度（%），可见两组峰位于约4.34 min处、两组峰位于约3.82 min处，各图右侧标注对应序号。"

【页面级忽略规则】

如果图片内容整体符合以下任一情况，则该图片视为【出版物附属尾页】，不属于原文转写范围，应直接忽略并不输出任何内容：

1. 页面主要由以下类型文字构成：
   - 出版单位、印刷单位、发行单位
   - 地址、邮政编码、网址
   - 开本、印张、字数
   - 版次、印次、印刷时间
   - 书号、定价
   - "版权专有""侵权必究""举报电话"等版权声明

2. 页面未包含：
   - 标准正文条款
   - 技术要求
   - 检测方法
   - 表格、公式、图谱或其编号

3. 页面内容在版式上呈现为：
   - 连续说明性段落
   - 或列表式出版信息
   - 且不与正文章节连续

当整页被判定为【出版物附属尾页】时：
- 不输出任何文字
- 不输出占位符
- 不输出说明性语句
- 不输出"已忽略"等提示
"""

    try:
        # 创建临时目录存储提取的图片
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # 步骤1: 从PDF中提取嵌入的图片
            print("步骤1: 提取PDF嵌入图片...")
            image_files = extract_pdf_images(
                pdf_path,
                temp_path,
                skip_blank=True,
                blank_threshold=0.8,
                blank_variance_threshold=10,
            )
            print(f"  提取了 {len(image_files)} 张图片")

            if not image_files:
                print("  警告: 未能提取到图片")
                return ""

            # 步骤2: 使用视觉模型解析图片
            print("步骤2: 使用视觉模型解析图片...")
            parsed_text = parse_images_with_llm(
                image_paths=image_files, prompt=prompt, model=settings.QWEN_VL_MODEL
            )

            print(f"  解析完成，获得 {len(parsed_text)} 个字符")
            print("✓ OCR处理完成")
            return parsed_text

    except Exception as e:
        print(f"✗ OCR处理失败: {e}")
        import traceback

        traceback.print_exc()
        return ""


def import_pdf(file_path: str, original_filename: str = None) -> List[DocumentChunk]:
    """
    导入 PDF 文件，支持文本提取和图片型PDF的OCR识别

    Args:
        file_path: PDF 文件路径
        original_filename: 原始文件名（如果提供，将使用此文件名作为 doc_id 和 doc_title）

    Returns:
        知识库通用数据结构列表
    """
    file_path_obj = Path(file_path)

    # 使用原始文件名或文件路径中的文件名
    if original_filename:
        file_name = original_filename
        doc_id = Path(original_filename).stem
        doc_title = Path(original_filename).stem
    else:
        file_name = os.path.basename(file_path)
        doc_id = file_path_obj.stem
        doc_title = file_path_obj.stem

    # 步骤1: 尝试提取文本
    print(f"\n处理PDF文件: {file_name}")
    text_content = extract_pdf_text(file_path)

    # 步骤2: 检测是否为图片型PDF
    is_image_pdf = False
    if settings.ENABLE_OCR:
        is_image_pdf = detect_image_pdf(file_path, text_content)
    else:
        print("OCR功能已禁用，跳过图片型PDF检测")

    # 步骤3: 如果是图片型PDF且文本很少，使用OCR处理
    final_content = text_content

    if is_image_pdf and settings.ENABLE_OCR:
        # 如果文本很少或为空，使用OCR处理
        if not text_content or len(text_content.strip()) < 100:
            print(
                f"文本内容过少（{len(text_content.strip()) if text_content else 0}字符），使用OCR处理..."
            )
            ocr_text = process_pdf_with_ocr(file_path)
            if ocr_text:
                final_content = ocr_text
                print(f"OCR处理完成，获得 {len(ocr_text)} 个字符")
            else:
                print("OCR处理失败，使用原始文本内容")
                final_content = text_content
        else:
            # 有文本但检测到是图片型PDF，保留文本内容
            print("检测到图片型PDF，但已有文本内容，保留文本内容")

    # 步骤4: 创建 DocumentChunk
    if not final_content or not final_content.strip():
        print(f"警告: 未能从PDF中提取到内容: {file_name}")
        return []

    return [
        DocumentChunk(
            doc_id=doc_id,
            doc_title=doc_title,
            section_path=[],
            content_type=ContentType.NOTE,
            content=final_content,
            meta={
                "file_name": file_name,
                "file_path": file_path,
                "source_format": "pdf",
            },
        )
    ]
