"""
翻译API - 使用AI进行中英文翻译
"""

from typing import Literal, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from app.core.llm import get_llm
from app.core.config import settings

router = APIRouter()


class TranslateRequest(BaseModel):
    """翻译请求模型"""
    text: str
    direction: Literal["en_to_zh", "zh_to_en"] = "en_to_zh"  # 翻译方向：英文转中文 或 中文转英文
    context: Optional[str] = None  # 可选的上下文信息，用于辅助翻译


class TranslateResponse(BaseModel):
    """翻译响应模型"""
    original_text: str
    translated_text: str
    direction: str
    context: Optional[str] = None  # 使用的上下文信息


def _detect_language(text: str) -> str:
    """
    简单检测文本语言
    通过中文字符比例判断
    """
    chinese_chars = sum(1 for char in text if '\u4e00' <= char <= '\u9fff')
    total_chars = len([c for c in text if c.isalnum() or '\u4e00' <= c <= '\u9fff'])
    
    if total_chars == 0:
        return "unknown"
    
    chinese_ratio = chinese_chars / total_chars if total_chars > 0 else 0
    return "zh" if chinese_ratio > 0.3 else "en"


@router.post("/", response_model=TranslateResponse)
async def translate(request: TranslateRequest):
    """
    翻译文本
    
    支持英文转中文和中文转英文
    使用AI模型进行翻译，保证翻译质量和准确性
    
    可以提供上下文信息来辅助翻译，提高翻译的准确性和一致性
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="翻译文本不能为空")
    
    # 获取LLM实例
    llm = get_llm("ollama", {"model": settings.OLLAMA_MODEL})
    
    # 根据翻译方向构建提示词
    if request.direction == "en_to_zh":
        if request.context:
            prompt = f"""你是一位专业的中英文翻译专家。请将以下英文文本准确、流畅地翻译成中文。

要求：
1. 翻译必须准确，忠实于原文意思
2. 语言流畅自然，符合中文表达习惯
3. 保持原文的语气、风格和格式
4. 专业术语使用标准的中文翻译
5. 参考提供的上下文信息，确保翻译与上下文保持一致
6. 只输出翻译结果，不要添加任何解释、说明或标记

上下文信息（用于辅助翻译）：
{request.context}

英文原文：
{request.text}

中文翻译："""
        else:
            prompt = f"""你是一位专业的中英文翻译专家。请将以下英文文本准确、流畅地翻译成中文。

要求：
1. 翻译必须准确，忠实于原文意思
2. 语言流畅自然，符合中文表达习惯
3. 保持原文的语气、风格和格式
4. 专业术语使用标准的中文翻译
5. 只输出翻译结果，不要添加任何解释、说明或标记

英文原文：
{request.text}

中文翻译："""
    else:  # zh_to_en
        if request.context:
            prompt = f"""You are a professional translator between Chinese and English. Please accurately and fluently translate the following Chinese text into English.

Requirements:
1. The translation must be accurate and faithful to the original meaning
2. The language should be fluent and natural, conforming to English expression habits
3. Maintain the tone, style, and format of the original text
4. Use standard English translations for technical terms
5. Refer to the provided context to ensure consistency with the context
6. Only output the translation result, do not add any explanations, notes, or markers

Context (for reference):
{request.context}

Chinese text:
{request.text}

English translation:"""
        else:
            prompt = f"""You are a professional translator between Chinese and English. Please accurately and fluently translate the following Chinese text into English.

Requirements:
1. The translation must be accurate and faithful to the original meaning
2. The language should be fluent and natural, conforming to English expression habits
3. Maintain the tone, style, and format of the original text
4. Use standard English translations for technical terms
5. Only output the translation result, do not add any explanations, notes, or markers

Chinese text:
{request.text}

English translation:"""
    
    try:
        # 调用LLM进行翻译
        response = llm.invoke([HumanMessage(content=prompt)])
        
        # 提取翻译结果
        if hasattr(response, "content"):
            translated_text = response.content.strip()
        elif isinstance(response, str):
            translated_text = response.strip()
        else:
            translated_text = str(response).strip()
        
        # 清理可能的额外说明（如果LLM添加了）
        # 移除常见的提示性文字和标记
        lines = translated_text.split('\n')
        cleaned_lines = []
        
        if request.direction == "en_to_zh":
            # 移除可能的中文说明前缀
            skip_prefixes = ['翻译', '中文', '以下是', '译文', '翻译结果', '翻译：', '中文翻译：']
            for line in lines:
                line_stripped = line.strip()
                # 跳过空行和以说明性前缀开头的行
                if line_stripped and not any(line_stripped.startswith(prefix) for prefix in skip_prefixes):
                    cleaned_lines.append(line)
        else:
            # 移除可能的英文说明前缀
            skip_prefixes = ['translation', 'english', 'here', 'translated', 'translation:', 'english translation:']
            for line in lines:
                line_stripped = line.strip().lower()
                # 跳过空行和以说明性前缀开头的行
                if line.strip() and not any(line_stripped.startswith(prefix) for prefix in skip_prefixes):
                    cleaned_lines.append(line)
        
        # 如果清理后还有内容，使用清理后的；否则使用原始结果
        if cleaned_lines:
            translated_text = '\n'.join(cleaned_lines).strip()
        
        # 如果清理后为空，使用原始结果
        if not translated_text:
            translated_text = response.content.strip() if hasattr(response, "content") else str(response).strip()
        
        return TranslateResponse(
            original_text=request.text,
            translated_text=translated_text,
            direction=request.direction,
            context=request.context
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"翻译失败: {str(e)}"
        )


@router.post("/auto", response_model=TranslateResponse)
async def translate_auto(request: TranslateRequest):
    """
    自动检测语言并翻译
    
    自动检测输入文本的语言，然后翻译成另一种语言
    如果无法检测语言，将使用指定的direction参数（默认为en_to_zh）
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="翻译文本不能为空")
    
    # 检测语言
    detected_lang = _detect_language(request.text)
    
    # 如果检测到是中文，翻译成英文；如果是英文，翻译成中文
    if detected_lang == "zh":
        direction = "zh_to_en"
    elif detected_lang == "en":
        direction = "en_to_zh"
    else:
        # 无法检测，使用请求中的方向（默认为en_to_zh）
        direction = request.direction
    
    # 创建新的请求对象（保留上下文信息）
    auto_request = TranslateRequest(
        text=request.text, 
        direction=direction,
        context=request.context
    )
    
    # 调用翻译接口
    return await translate(auto_request)
