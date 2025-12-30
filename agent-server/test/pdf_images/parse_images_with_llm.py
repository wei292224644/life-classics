#!/usr/bin/env python3
"""
使用 Qwen3-VL-Plus 模型解析图片内容

支持：
- 单张图片解析
- 批量处理目录下所有图片
- 自定义提示词
- 输出解析结果到文件

使用方法：
    # 解析单张图片
    python test/pdf_images/parse_images_with_llm.py test/pdf_images/images/GB-31613.2-2021/page_001_img_001.jpg

    # 批量处理目录下所有图片
    python test/pdf_images/parse_images_with_llm.py test/pdf_images/images/GB-31613.2-2021/ --batch

    # 使用自定义提示词
    python test/pdf_images/parse_images_with_llm.py images/GB-31613.2-2021/page_001_img_001.jpg --prompt "请提取这张图片中的所有文字和表格内容"
"""
import argparse
import sys
import os
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import dashscope
    from dashscope import MultiModalConversation

    DASHSCOPE_AVAILABLE = True
except ImportError:
    DASHSCOPE_AVAILABLE = False
    print("警告: dashscope 未安装，无法使用视觉模型")
    print("请安装: pip install dashscope")

# 尝试使用 OpenAI 兼容 API
try:
    from openai import OpenAI

    OPENAI_COMPATIBLE_AVAILABLE = True
except ImportError:
    OPENAI_COMPATIBLE_AVAILABLE = False

try:
    from PIL import Image

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("警告: Pillow 未安装，无法处理图片")

# 导入项目配置
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from app.core.config import settings


def load_image_as_base64(image_path: str) -> str:
    """
    将图片转换为 base64 编码

    Args:
        image_path: 图片文件路径

    Returns:
        base64 编码的图片数据
    """
    import base64

    with open(image_path, "rb") as image_file:
        image_data = image_file.read()
        base64_data = base64.b64encode(image_data).decode("utf-8")
        return base64_data


def parse_image_with_llm(
    image_paths: List[str],
    prompt: str,
    api_key: Optional[str] = None,
    model: str = "qwen3-vl-plus-2025-12-19",
) -> Dict[str, Any]:
    """
    使用 Qwen3-VL-Plus-2025-12-19 模型解析图片

    Args:
        image_path: 图片文件路径
        prompt: 提示词
        api_key: DashScope API Key（如果为 None，则使用配置中的）
        model: 模型名称（默认: qwen3-vl-plus-2025-12-19）

    Returns:
        解析结果字典，包含：
        - success: 是否成功
        - content: 解析内容
        - error: 错误信息（如果有）
    """
    if not PIL_AVAILABLE:
        return {"success": False, "content": None, "error": "Pillow 未安装"}

    # 获取 API Key
    if api_key:
        api_key_value = api_key
    else:
        api_key_value = settings.DASHSCOPE_API_KEY

    if not api_key_value:
        return {"success": False, "content": None, "error": "DASHSCOPE_API_KEY 未设置"}

    # 读取图片文件
    if not all(os.path.exists(image_path) for image_path in image_paths):
        return {
            "success": False,
            "content": None,
            "error": f"图片文件不存在: {image_paths}",
        }

    try:

        # 方法2: 使用 DashScope 原生 API
        if DASHSCOPE_AVAILABLE:
            dashscope.api_key = api_key_value

            # 构建消息内容：先添加所有图片，然后添加文本
            content = []
            for image_path in image_paths:
                content.append({"image": f"file://{os.path.abspath(image_path)}"})
            content.append({"text": prompt})

            # 使用 MultiModalConversation 调用视觉模型
            messages = [
                {
                    "role": "user",
                    "content": content,
                }
            ]

            response = MultiModalConversation.call(
                model=model, messages=messages, enable_thinking=False, top_p=0.5
            )

            if response.status_code == 200:
                # 提取回复内容
                if hasattr(response, "output") and hasattr(response.output, "choices"):
                    content = response.output.choices[0].message.content
                    return {"success": True, "content": content, "error": None}
                elif isinstance(response, dict) and "output" in response:
                    if "choices" in response["output"]:
                        content = response["output"]["choices"][0]["message"]["content"]
                        return {"success": True, "content": content, "error": None}

            return {
                "success": False,
                "content": None,
                "error": f"API 调用失败: {response.status_code if hasattr(response, 'status_code') else 'unknown'}, {getattr(response, 'message', str(response))}",
            }

        return {
            "success": False,
            "content": None,
            "error": "dashscope 或 openai 库未安装，请安装: pip install dashscope openai",
        }

    except Exception as e:
        import traceback

        error_detail = traceback.format_exc()
        return {
            "success": False,
            "content": None,
            "error": f"解析失败: {str(e)}\n{error_detail}",
        }


def batch_parse_images(
    directory: str,
    prompt: str = "请详细描述这张图片的内容，包括所有文字、表格、图表等信息。",
    output_dir: Optional[str] = None,
    api_key: Optional[str] = None,
    model: str = "qwen-vl-plus-2025-12-19",
    image_extensions: List[str] = [".jpg", ".jpeg", ".png", ".bmp", ".gif"],
) -> None:
    """
    批量处理目录下所有图片

    Args:
        directory: 图片目录路径
        prompt: 提示词
        output_dir: 输出目录（如果为 None，则在图片目录下创建 parsed 子目录）
        api_key: DashScope API Key
        model: 模型名称
        image_extensions: 支持的图片扩展名列表
    """
    dir_path = Path(directory)

    if not dir_path.exists():
        print(f"错误: 目录不存在: {directory}")
        return

    if not dir_path.is_dir():
        print(f"错误: 不是目录: {directory}")
        return

    # 查找所有图片文件
    image_files = []
    for ext in image_extensions:
        image_files.extend(dir_path.glob(f"*{ext}"))
        image_files.extend(dir_path.glob(f"*{ext.upper()}"))

    if not image_files:
        print(f"在 {directory} 目录中未找到图片文件")
        return

    # 按文件名排序
    image_files.sort(key=lambda x: x.name)
    total_files = len(image_files)

    print(f"找到 {total_files} 张图片")
    print(f"提示词: {prompt}")
    print(f"模型: {model}")
    print("=" * 60)

    # 确定输出目录
    if output_dir:
        output_path = Path(output_dir)
    else:
        output_path = dir_path / "parsed"

    output_path.mkdir(parents=True, exist_ok=True)

    # 将图片文件路径列表转换为字符串列表
    image_paths = [str(img_file) for img_file in image_files]

    result = parse_image_with_llm(
        image_paths, prompt=prompt, api_key=api_key, model=model
    )

    if result["success"]:
        # 保存合并的 Markdown 文件
        markdown_file = output_path / "merged_content.md"
        with open(markdown_file, "w", encoding="utf-8") as f:
            # 写入文件头
            f.write(f"# 图片解析结果合并\n\n")
            f.write(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"**模型**: {model}\n\n")
            f.write(f"**处理图片数**: {len(image_paths)} 张\n\n")
            f.write(f"---\n\n")
            f.write(f"## 解析内容\n\n")
            f.write(f"{result['content']}\n\n")

        print("\n" + "=" * 60)
        print("批量处理完成")
        print("=" * 60)
        print(f"✓ 解析成功")
        print(f"结果保存在: {output_path}")
        print(f"Markdown 文件: {markdown_file}")
    else:
        print("\n" + "=" * 60)
        print("批量处理失败")
        print("=" * 60)
        print(f"✗ 解析失败: {result['error']}")

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="使用 Qwen3-VL-Plus-2025-12-19 模型解析图片内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 解析单张图片
  python test/pdf_images/parse_images_with_llm.py images/GB-31613.2-2021/page_001_img_001.jpg
  
  # 批量处理目录下所有图片
  python test/pdf_images/parse_images_with_llm.py images/GB-31613.2-2021/ --batch
  
  # 使用自定义提示词
  python test/pdf_images/parse_images_with_llm.py images/page_001.jpg --prompt "请提取这张图片中的所有文字和表格内容，以Markdown格式输出"
  
  # 指定输出文件
  python test/pdf_images/parse_images_with_llm.py images/page_001.jpg --output results/page_001_result.json
  
  # 使用指定的模型版本
  python test/pdf_images/parse_images_with_llm.py images/page_001.jpg --model qwen3-vl-plus-2025-12-19
        """,
    )

    parser.add_argument(
        "input",
        help="图片文件路径或包含图片的目录（使用 --batch 模式）",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="批量处理模式：处理目录下所有图片",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default="请详细描述这张图片的内容，包括所有文字、表格、图表等信息。",
        help="提示词（默认: 请详细描述这张图片的内容，包括所有文字、表格、图表等信息。）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="输出文件路径（单张图片模式）或输出目录（批量模式，默认: 图片目录下的 parsed 子目录）",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default=None,
        help="DashScope API Key（如果未提供，则使用配置中的）",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="qwen3-vl-plus-2025-12-19",
        help="模型名称（默认: qwen3-vl-plus-2025-12-19）",
    )

    args = parser.parse_args()

    # 检查依赖
    if not DASHSCOPE_AVAILABLE and not OPENAI_COMPATIBLE_AVAILABLE:
        print("错误: dashscope 或 openai 库未安装")
        print("请安装: pip install dashscope openai")
        sys.exit(1)

    if not PIL_AVAILABLE:
        print("错误: Pillow 未安装")
        print("请安装: pip install Pillow")
        sys.exit(1)

    #     prompt = f"""你现在的任务是【原文转写】，不是解释、整理或描述图片内容，特殊情况可以描述图片内容，比如图谱，曲线图等。

    # 请严格按照以下规则处理我提供的图片：

    # 【任务目标】
    # 逐字逐行转写图片中出现的所有正文文字内容，并原样输出，特殊情况可以描述图片内容，比如图谱，曲线图等。

    # 【必须遵守的规则】
    # 1. 只允许输出图片中“实际可见的文字原文”。

    # 2. 不得对内容进行：
    #    - 分类
    #    - 归纳
    #    - 总结
    #    - 解释
    #    - 补充背景知识
    #    - 判断法律或技术属性

    # 3. 不得添加任何图片中不存在的文字，包括：
    #    - 区域标题（如“左上角信息”“补充说明”等）
    #    - 说明性语句
    #    - 推断性描述

    # 4. 严格保持图片中的视觉排版结构，包括：
    #    - 换行
    #    - 缩进
    #    - 标题与正文的行距层级

    # 5. 中文、英文、数字、符号（如破折号、点号）必须按原样输出，
    #    不得统一格式或替换符号。

    # 6. 对于图片中的图形、徽标、印章：
    #    - 如果其中包含可辨认文字，仅输出文字本身
    #    - 不得描述其颜色、形状、含义或用途

    # 7. 对于图片中的“图谱 / 图像信息类内容”（如色谱图、谱图、曲线图）：
    #    - 不输出图形本体、不还原坐标轴、不描述峰形
    #    - 基于该图谱，用一段话客观描述该图谱所对应的内容
    #    - 该句不得包含图片中未出现的概念或信息

    # 8. 图谱内容不得被忽略，但其输出形式仅限于上一条所述的一段话。

    # 9. 输出内容中不得出现任何说明性文字或标注性标题
    #     （图谱转写句本身除外，不得添加如“说明”“解读”等字样）。

    # 【输出要求】
    # 直接输出转写结果本身，不要附加任何前言或结论。
    # """

    prompt = f"""【任务目标】
逐字逐行转写图片中所有以独立印刷体文本行形式存在的内容（包括标题、说明、编号条目、图注、标签等），并对图谱/曲线图/色谱图等图像类内容仅添加且仅添加一句客观描述句。

【必须遵守的规则】

仅转写真实存在的独立文本行：

仅当某行文字在图片中以完整、独立的印刷体文本行形式呈现（如标题、段落、列表项、图注等），才可原样转写；
坐标轴刻度值（如“0”“20”“100”）、峰顶数值（如“4.34”“3.82”）、网格线标记、图形内部数字标签等视觉元素，一律不得拆解为分行文本输出；
图形中的文字标签（如“t/min”“相对丰度，%”“1”“2”）若以独立文本行形式存在（如坐标轴标题），则按原文转写；若嵌入图形内部（如色谱图右端序号），则仅在图谱描述句中提及。
图谱/曲线图/色谱图等图像类内容的处理：

禁止任何形式的坐标轴还原、峰形描述或数值分行转写；
必须且仅能用一段连贯陈述句描述该图像的整体构成，该句需：
严格基于图中明确可见的文字与符号（如坐标轴标签、峰时间值、图序号）；
包含图像类型（如“特征离子质量色谱图”）、标号范围（如“标号1至4”）、坐标轴定义（如“横坐标为保留时间t/min（0–10 min）”）、关键可见特征（如“可见两组峰位于约4.34 min处”）；
不得虚构、补充或解释任何未在图中直接显示的信息（如不添加“图中显示”“结果表明”等推断性表述）；
必须作为单句存在，不使用分号、项目符号或换行。
排版与内容边界：

严格保持原文换行、缩进及层级结构；
仅当图片中存在图谱类内容时，才在所有真实文本行之后、图注之前或之后（依原图逻辑顺序） 插入图谱描述句；
若图中无任何文字标签（如纯图形无标注），则不输出任何描述句。
绝对禁止行为：

添加区域标题（如“图谱部分”）、说明性语句（如“以下为图谱内容”）；
对内容分类、归纳、总结或补充背景知识；
修改原文符号（如将“—”替换为“-”）、统一数字格式或添加标点。
【输出要求】

仅输出转写结果本身，无前言、结论或标注；
顺序为：真实文本行 → （图谱描述句，若存在） → 其余真实文本行；
图谱描述句格式示例（需根据图片动态适配）：
“图中包含四组特征离子质量色谱图，标号1至4，横坐标为保留时间t/min（0–10 min），纵坐标为相对丰度（%），可见两组峰位于约4.34 min处、两组峰位于约3.82 min处，各图右侧标注对应序号。”

【页面级忽略规则】

如果图片内容整体符合以下任一情况，则该图片视为【出版物附属尾页】，不属于原文转写范围，应直接忽略并不输出任何内容：

1. 页面主要由以下类型文字构成：
   - 出版单位、印刷单位、发行单位
   - 地址、邮政编码、网址
   - 开本、印张、字数
   - 版次、印次、印刷时间
   - 书号、定价
   - “版权专有”“侵权必究”“举报电话”等版权声明

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
- 不输出“已忽略”等提示
"""

    # 执行解析
    try:
        batch_parse_images(
            directory=args.input,
            prompt=prompt,
            output_dir=args.output,
            api_key=args.api_key,
            model=args.model,
        )
    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
