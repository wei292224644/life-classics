#!/usr/bin/env python3
"""
从 PDF 文件中提取图片资源

支持两种模式：
1. 将 PDF 页面转换为图片（适合扫描版 PDF，所有内容都是图片）
2. 提取 PDF 中嵌入的图片对象（适合包含图片的 PDF）

使用方法：
    # 将 PDF 页面转换为图片
    python test/extract_pdf_images.py files/GB-31613.2-2021.pdf --mode page-to-image
    
    # 提取嵌入的图片对象
    python test/extract_pdf_images.py files/example.pdf --mode extract-images
    
    # 批量处理目录下所有 PDF
    python test/extract_pdf_images.py files/ --batch
"""
import argparse
import sys
from pathlib import Path
from typing import List, Optional

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    print("警告: pdf2image 未安装，无法使用页面转图片功能")

try:
    from pypdf import PdfReader
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("警告: pypdf 未安装，无法使用提取嵌入图片功能")

try:
    from PIL import Image
    import numpy as np
    PIL_AVAILABLE = True
    NUMPY_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    NUMPY_AVAILABLE = False
    print("警告: Pillow 未安装，无法处理图片")
    try:
        import numpy as np
        NUMPY_AVAILABLE = True
    except ImportError:
        NUMPY_AVAILABLE = False
        print("警告: numpy 未安装，无法检测空白图片")


def is_blank_image(image: Image.Image, threshold: float = 0.95, variance_threshold: float = 500.0) -> bool:
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
        if image.mode != 'L':
            gray = image.convert('L')
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
            colors = gray.getcolors(maxcolors=256*256)
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
            variance = sum(count * (color - mean_brightness) ** 2 for count, color in colors) / total_pixels
            
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
        print(f"    警告: 检测空白图片时出错: {e}")
        return False


def extract_embedded_images(
    pdf_path: str, 
    output_dir: Path,
    skip_blank: bool = True,
    blank_threshold: float = 0.95,
    blank_variance_threshold: float = 500.0
) -> int:
    """
    提取 PDF 中嵌入的图片对象
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        skip_blank: 是否跳过空白图片（默认: True）
        blank_threshold: 空白检测的平均亮度阈值（0-1，默认: 0.95）
        blank_variance_threshold: 空白检测的方差阈值（默认: 500.0）
        
    Returns:
        提取的图片数量
    """
    if not PYPDF_AVAILABLE:
        raise ImportError("pypdf 未安装，无法提取嵌入图片")
    
    if not PIL_AVAILABLE:
        raise ImportError("Pillow 未安装，无法处理图片")
    
    reader = PdfReader(pdf_path)
    image_count = 0
    saved_count = 0
    skipped_count = 0
    
    print(f"  处理 PDF: {pdf_path}")
    print(f"  总页数: {len(reader.pages)}")
    print(f"  跳过空白: {skip_blank}")
    
    for page_num, page in enumerate(reader.pages, start=1):
        if '/XObject' in page['/Resources']:
            xObject = page['/Resources']['/XObject'].get_object()
            
            for obj_num, obj in xObject.items():
                if obj['/Subtype'] == '/Image':
                    image_count += 1
                    
                    # 获取图片数据
                    size = (obj['/Width'], obj['/Height'])
                    data = obj.get_data()
                    
                    # 确定图片格式
                    if obj['/Filter'] == '/DCTDecode':
                        ext = '.jpg'
                    elif obj['/Filter'] == '/FlateDecode':
                        ext = '.png'
                    elif obj['/Filter'] == '/CCITTFaxDecode':
                        ext = '.tiff'
                    else:
                        ext = '.png'
                    
                    # 检测是否为空白图片
                    if skip_blank:
                        try:
                            # 从字节数据创建 PIL Image
                            from io import BytesIO
                            img = Image.open(BytesIO(data))
                            
                            if is_blank_image(img, blank_threshold, blank_variance_threshold):
                                print(f"    页面 {page_num} 图片 {image_count}: 跳过空白图片")
                                skipped_count += 1
                                continue
                        except Exception as e:
                            # 如果检测失败，继续保存图片
                            print(f"    警告: 检测图片 {image_count} 时出错: {e}，继续保存")
                    
                    # 保存图片
                    image_filename = f"page_{page_num:03d}_img_{image_count:03d}{ext}"
                    image_path = output_dir / image_filename
                    
                    with open(image_path, 'wb') as img_file:
                        img_file.write(data)
                    
                    print(f"    提取图片: {image_filename} ({size[0]}x{size[1]})")
                    saved_count += 1
    
    if skip_blank and skipped_count > 0:
        print(f"  跳过 {skipped_count} 张空白图片")
    
    return saved_count


def convert_pages_to_images(
    pdf_path: str, 
    output_dir: Path, 
    dpi: int = 300,
    fmt: str = 'PNG',
    auto_rotate: bool = True,
    skip_blank: bool = True,
    blank_threshold: float = 0.95,
    blank_variance_threshold: float = 500.0
) -> int:
    """
    将 PDF 页面转换为图片（适合扫描版 PDF）
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录
        dpi: 图片分辨率（默认 300）
        fmt: 图片格式（PNG 或 JPEG）
        auto_rotate: 是否自动根据 PDF 页面旋转信息修正图片方向（默认: True）
        skip_blank: 是否跳过空白图片（默认: True）
        blank_threshold: 空白检测的平均亮度阈值（0-1，默认 0.98）
        blank_variance_threshold: 空白检测的方差阈值（默认 100.0）
        
    Returns:
        转换的图片数量
    """
    if not PDF2IMAGE_AVAILABLE:
        raise ImportError("pdf2image 未安装，无法将页面转换为图片")
    
    if not PIL_AVAILABLE:
        raise ImportError("Pillow 未安装，无法处理图片")
    
    print(f"  处理 PDF: {pdf_path}")
    print(f"  DPI: {dpi}, 格式: {fmt}")
    print(f"  自动旋转: {auto_rotate}")
    print(f"  跳过空白: {skip_blank}")
    
    # 读取 PDF 页面的旋转信息（如果需要自动旋转）
    page_rotations = []
    if auto_rotate and PYPDF_AVAILABLE:
        try:
            reader = PdfReader(pdf_path)
            for page in reader.pages:
                # 获取页面旋转角度（0, 90, 180, 270）
                rotation = page.get('/Rotate', 0)
                if rotation is None:
                    rotation = 0
                page_rotations.append(rotation)
        except Exception as e:
            print(f"  警告: 无法读取页面旋转信息: {e}，将不进行自动旋转")
            page_rotations = []
    
    # 将 PDF 页面转换为图片
    try:
        # 使用 strict=False 参数，让 pdf2image 更好地处理有问题的 PDF
        images = convert_from_path(pdf_path, dpi=dpi, strict=False)
    except Exception as e:
        print(f"  错误: 无法转换 PDF 页面: {e}")
        print(f"  提示: 可能需要安装 poppler")
        print(f"  macOS: brew install poppler")
        print(f"  Ubuntu: sudo apt-get install poppler-utils")
        raise
    
    image_count = len(images)
    print(f"  总页数: {image_count}")
    
    # 保存图片
    pdf_name = Path(pdf_path).stem
    saved_count = 0
    skipped_count = 0
    
    for i, image in enumerate(images, start=1):
        # 如果需要自动旋转，根据 PDF 页面的旋转信息旋转图片
        if auto_rotate and page_rotations and i <= len(page_rotations):
            rotation = page_rotations[i - 1]
            if rotation != 0:
                # PDF 的旋转是顺时针的，PIL 的 rotate 是逆时针的，所以需要取反
                # 0 -> 0, 90 -> -90, 180 -> -180, 270 -> -270
                pil_rotation = -rotation
                image = image.rotate(pil_rotation, expand=True)
                print(f"    页面 {i}: 应用旋转 {rotation}°")
        
        # 检测是否为空白图片
        if skip_blank and is_blank_image(image, blank_threshold, blank_variance_threshold):
            print(f"    页面 {i}: 跳过空白图片")
            skipped_count += 1
            continue
        
        if fmt.upper() == 'PNG':
            ext = '.png'
        elif fmt.upper() == 'JPEG' or fmt.upper() == 'JPG':
            ext = '.jpg'
        else:
            ext = '.png'
        
        image_filename = f"{pdf_name}_page_{i:03d}{ext}"
        image_path = output_dir / image_filename
        
        # 保存图片
        if fmt.upper() == 'JPEG' or fmt.upper() == 'JPG':
            image.save(image_path, 'JPEG', quality=95)
        else:
            image.save(image_path, 'PNG')
        
        print(f"    保存图片: {image_filename} ({image.size[0]}x{image.size[1]})")
        saved_count += 1
    
    if skip_blank and skipped_count > 0:
        print(f"  跳过 {skipped_count} 张空白图片")
    
    return saved_count


def extract_images_from_pdf(
    pdf_path: str,
    output_dir: Optional[Path] = None,
    mode: str = 'page-to-image',
    dpi: int = 300,
    fmt: str = 'PNG',
    auto_rotate: bool = True,
    skip_blank: bool = True,
    blank_threshold: float = 0.95,
    blank_variance_threshold: float = 500.0
) -> int:
    """
    从 PDF 中提取图片
    
    Args:
        pdf_path: PDF 文件路径
        output_dir: 输出目录（如果为 None，则在 PDF 同目录下创建 images 子目录）
        mode: 提取模式 ('page-to-image' 或 'extract-images')
        dpi: 图片分辨率（仅对 page-to-image 模式有效）
        fmt: 图片格式（仅对 page-to-image 模式有效）
        
    Returns:
        提取的图片数量
    """
    pdf_path_obj = Path(pdf_path)
    
    if not pdf_path_obj.exists():
        raise FileNotFoundError(f"PDF 文件不存在: {pdf_path}")
    
    if not pdf_path_obj.suffix.lower() == '.pdf':
        raise ValueError(f"不是 PDF 文件: {pdf_path}")
    
    # 确定输出目录
    if output_dir is None:
        output_dir =  Path('test/pdf_images/images') / pdf_path_obj.stem
    else:
        output_dir = Path(output_dir)
    
    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"输出目录: {output_dir}")
    
    # 根据模式提取图片
    if mode == 'page-to-image':
        image_count = convert_pages_to_images(
            pdf_path=str(pdf_path_obj),
            output_dir=output_dir,
            dpi=dpi,
            fmt=fmt,
            auto_rotate=auto_rotate,
            skip_blank=skip_blank,
            blank_threshold=blank_threshold,
            blank_variance_threshold=blank_variance_threshold
        )
    elif mode == 'extract-images':
        image_count = extract_embedded_images(
            pdf_path=str(pdf_path_obj),
            output_dir=output_dir,
            skip_blank=skip_blank,
            blank_threshold=blank_threshold,
            blank_variance_threshold=blank_variance_threshold
        )
    else:
        raise ValueError(f"不支持的模式: {mode}，支持的模式: 'page-to-image', 'extract-images'")
    
    print(f"\n✓ 成功提取 {image_count} 张图片到: {output_dir}")
    return image_count


def batch_extract_images(
    directory: str,
    output_base_dir: Optional[str] = None,
    mode: str = 'page-to-image',
    dpi: int = 300,
    fmt: str = 'PNG',
    auto_rotate: bool = True,
    skip_blank: bool = True,
    blank_threshold: float = 0.95,
    blank_variance_threshold: float = 500.0
) -> None:
    """
    批量处理目录下所有 PDF 文件
    
    Args:
        directory: PDF 文件目录
        output_base_dir: 输出基础目录（如果为 None，则在每个 PDF 同目录下创建 images 子目录）
        mode: 提取模式
        dpi: 图片分辨率
        fmt: 图片格式
    """
    dir_path = Path(directory)
    
    if not dir_path.exists():
        raise FileNotFoundError(f"目录不存在: {directory}")
    
    if not dir_path.is_dir():
        raise ValueError(f"不是目录: {directory}")
    
    # 查找所有 PDF 文件
    pdf_files = list(dir_path.glob("*.pdf"))
    
    if not pdf_files:
        print(f"在 {directory} 目录中未找到 PDF 文件")
        return
    
    pdf_files.sort(key=lambda x: x.name)
    total_files = len(pdf_files)
    
    print(f"找到 {total_files} 个 PDF 文件")
    print(f"提取模式: {mode}")
    print("=" * 60)
    
    total_images = 0
    success_count = 0
    error_count = 0
    
    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{total_files}] 处理: {pdf_file.name}")
        
        try:
            if output_base_dir:
                output_dir = Path(output_base_dir) / pdf_file.stem
            else:
                output_dir = None
            
            image_count = extract_images_from_pdf(
                pdf_path=str(pdf_file),
                output_dir=output_dir,
                mode=mode,
                dpi=dpi,
                fmt=fmt,
                auto_rotate=auto_rotate,
                skip_blank=skip_blank,
                blank_threshold=blank_threshold,
                blank_variance_threshold=blank_variance_threshold
            )
            total_images += image_count
            success_count += 1
        except Exception as e:
            print(f"  ✗ 处理失败: {e}")
            import traceback
            traceback.print_exc()
            error_count += 1
            continue
    
    print("\n" + "=" * 60)
    print("批量处理完成")
    print("=" * 60)
    print(f"成功: {success_count} 个文件")
    print(f"失败: {error_count} 个文件")
    print(f"总图片数: {total_images} 张")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="从 PDF 文件中提取图片资源",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 将 PDF 页面转换为图片（适合扫描版 PDF）
  python test/extract_pdf_images.py files/GB-31613.2-2021.pdf --mode page-to-image
  
  # 提取嵌入的图片对象
  python test/extract_pdf_images.py files/example.pdf --mode extract-images
  
  # 指定输出目录
  python test/extract_pdf_images.py files/GB-31613.2-2021.pdf --output output/images
  
  # 批量处理目录下所有 PDF
  python test/extract_pdf_images.py files/ --batch
  
  # 使用自定义 DPI 和格式
  python test/extract_pdf_images.py files/GB-31613.2-2021.pdf --mode page-to-image --dpi 600 --format JPEG
  
  # 禁用自动旋转（如果图片方向不正确）
  python test/extract_pdf_images.py files/GB-31613.2-2021.pdf --no-auto-rotate
  
  # 不跳过空白图片（默认会跳过）
  python test/extract_pdf_images.py files/GB-31613.2-2021.pdf --no-skip-blank
  
  # 自定义空白检测阈值
  python test/extract_pdf_images.py files/GB-31613.2-2021.pdf --blank-threshold 0.95 --blank-variance-threshold 50.0
        """,
    )
    
    parser.add_argument(
        "input",
        help="PDF 文件路径或包含 PDF 文件的目录（使用 --batch 模式）",
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="page-to-image",
        choices=["page-to-image", "extract-images"],
        help="提取模式: 'page-to-image' 将页面转换为图片（适合扫描版 PDF），'extract-images' 提取嵌入的图片对象（默认: page-to-image）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出目录（默认: PDF 同目录下的 images/文件名 子目录）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式：处理目录下所有 PDF 文件",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="图片分辨率，仅对 page-to-image 模式有效（默认: 300）",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="PNG",
        choices=["PNG", "JPEG", "JPG"],
        help="图片格式，仅对 page-to-image 模式有效（默认: PNG）",
    )
    parser.add_argument(
        "--no-auto-rotate",
        action="store_true",
        help="禁用自动旋转（默认会自动根据 PDF 页面旋转信息修正图片方向）",
    )
    parser.add_argument(
        "--no-skip-blank",
        action="store_true",
        help="不跳过空白图片（默认会跳过空白图片）",
    )
    parser.add_argument(
        "--blank-threshold",
        type=float,
        default=0.95,
        help="空白检测的平均亮度阈值（0-1，默认: 0.95，即 95%% 白色）",
    )
    parser.add_argument(
        "--blank-variance-threshold",
        type=float,
        default=500.0,
        help="空白检测的方差阈值（默认: 500.0，方差越小说明内容越单一）",
    )
    
    args = parser.parse_args()
    
    # 检查依赖
    if args.mode == 'page-to-image' and not PDF2IMAGE_AVAILABLE:
        print("错误: pdf2image 未安装，无法使用页面转图片功能")
        print("请安装: pip install pdf2image")
        print("注意: 还需要安装 poppler")
        print("  macOS: brew install poppler")
        print("  Ubuntu: sudo apt-get install poppler-utils")
        sys.exit(1)
    
    if args.mode == 'extract-images' and not PYPDF_AVAILABLE:
        print("错误: pypdf 未安装，无法提取嵌入图片")
        print("请安装: pip install pypdf")
        sys.exit(1)
    
    if not PIL_AVAILABLE:
        print("错误: Pillow 未安装，无法处理图片")
        print("请安装: pip install Pillow")
        sys.exit(1)
    
    # 执行提取
    try:
        auto_rotate = not args.no_auto_rotate
        skip_blank = not args.no_skip_blank
        
        if args.batch:
            batch_extract_images(
                directory=args.input,
                output_base_dir=args.output,
                mode=args.mode,
                dpi=args.dpi,
                fmt=args.format,
                auto_rotate=auto_rotate,
                skip_blank=skip_blank,
                blank_threshold=args.blank_threshold,
                blank_variance_threshold=args.blank_variance_threshold
            )
        else:
            extract_images_from_pdf(
                pdf_path=args.input,
                output_dir=Path(args.output) if args.output else None,
                mode=args.mode,
                dpi=args.dpi,
                fmt=args.format,
                auto_rotate=auto_rotate,
                skip_blank=skip_blank,
                blank_threshold=args.blank_threshold,
                blank_variance_threshold=args.blank_variance_threshold
            )
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

