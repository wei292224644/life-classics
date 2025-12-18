# OCR 功能设置指南

## 概述

本系统已集成 OCR（光学字符识别）功能，用于处理图片型 PDF（扫描版 PDF）。当 PDF 页面无法直接提取文本时，系统会自动使用 OCR 提取图片中的文字内容。

## 安装步骤

### 1. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

这将安装以下 OCR 相关依赖：
- `pytesseract>=0.3.10` - Tesseract OCR 的 Python 包装器
- `Pillow>=10.0.0` - 图像处理库
- `pdf2image>=1.16.3` - PDF 转图片工具

### 2. 安装 Poppler（PDF 转图片工具的系统依赖）

`pdf2image` 需要 Poppler 来将 PDF 页面转换为图片。

#### macOS

```bash
brew install poppler
```

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install poppler-utils
```

#### Windows

1. 下载 Poppler for Windows：https://github.com/oschwartz10612/poppler-windows/releases
2. 解压并添加到系统 PATH，或设置环境变量

### 3. 安装 Tesseract OCR 系统依赖

#### macOS

```bash
brew install tesseract
brew install tesseract-lang  # 安装中文语言包
```

#### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-chi-sim  # 简体中文语言包
sudo apt-get install tesseract-ocr-eng      # 英文语言包
```

#### Windows

1. 下载 Tesseract 安装程序：https://github.com/UB-Mannheim/tesseract/wiki
2. 运行安装程序，安装到默认路径（如 `C:\Program Files\Tesseract-OCR`）
3. 将 Tesseract 添加到系统 PATH，或在代码中设置路径：
   ```python
   import pytesseract
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

### 4. 验证安装

运行以下命令验证依赖是否正确安装：

**验证 Poppler：**
```bash
pdfinfo --version  # 或 pdftoppm -h
```

**验证 Tesseract：**

```bash
tesseract --version
tesseract --list-langs  # 查看已安装的语言包
```

确保输出中包含 `chi_sim`（简体中文）和 `eng`（英文）。

## 配置选项

在 `.env` 文件或环境变量中可以配置以下选项：

```bash
# 是否启用 OCR 功能（默认: True）
ENABLE_OCR=True

# OCR 语言设置（默认: chi_sim+eng，即简体中文+英文）
# 可用选项：
# - chi_sim: 简体中文
# - chi_tra: 繁体中文
# - eng: 英文
# - chi_sim+eng: 简体中文+英文（推荐）
OCR_LANG=chi_sim+eng

# 如果提取的文本长度小于此值，尝试使用 OCR（默认: 10）
OCR_MIN_TEXT_LENGTH=10
```

## 使用方法

### 自动模式（推荐）

OCR 功能默认启用，系统会自动检测 PDF 页面是否有文本：

1. 如果页面可以直接提取文本，使用常规方法提取
2. 如果页面文本为空或太短（少于 `OCR_MIN_TEXT_LENGTH` 个字符），自动使用 OCR 提取

### 手动禁用 OCR

如果不需要 OCR 功能，可以在 `.env` 文件中设置：

```bash
ENABLE_OCR=False
```

## 工作原理

1. **文本提取尝试**：首先使用 `pdfplumber` 尝试直接提取 PDF 文本
2. **OCR 检测**：如果提取的文本长度小于阈值（默认 10 个字符），判断为图片型 PDF
3. **图片转换**：将 PDF 页面转换为高分辨率图片（300 DPI）
4. **OCR 识别**：使用 Tesseract OCR 识别图片中的文字
5. **结果合并**：将 OCR 提取的文本用于后续处理

## 注意事项

1. **性能**：OCR 处理速度较慢，特别是大文件。建议：
   - 使用 SSD 存储
   - 适当调整 DPI（默认 300，可降低到 200 以提高速度）
   - 对于纯文本 PDF，OCR 会自动跳过

2. **准确性**：OCR 识别准确度取决于：
   - 图片质量（清晰度、对比度）
   - 字体类型和大小
   - 页面布局复杂度
   - 语言设置是否正确

3. **内存使用**：`pdf2image` 会将 PDF 页面转换为图片，大文件可能占用较多内存

4. **依赖检查**：如果 OCR 相关库未安装，系统会自动降级到常规文本提取，不会报错

## 故障排除

### 问题：PDFInfoNotInstalledError - Poppler 未安装

**错误信息**：
```
PDFInfoNotInstalledError: Unable to get page count. Is poppler installed and in PATH?
```

**解决方案**：
1. 安装 Poppler：
   ```bash
   # macOS
   brew install poppler
   
   # Ubuntu/Debian
   sudo apt-get install poppler-utils
   ```
2. 验证安装：`pdfinfo --version`
3. 如果已安装但仍报错，检查 PATH 环境变量

### 问题：OCR 无法识别中文

**解决方案**：
1. 确认已安装中文语言包：`tesseract --list-langs`
2. 检查配置中的语言设置：`OCR_LANG=chi_sim+eng`
3. 如果仍未安装，运行：
   ```bash
   # macOS
   brew install tesseract-lang
   
   # Ubuntu/Debian
   sudo apt-get install tesseract-ocr-chi-sim
   ```

### 问题：找不到 tesseract 命令

**解决方案**：
- macOS/Linux：确保 Tesseract 在 PATH 中
- Windows：在代码中设置完整路径（见安装步骤）

### 问题：OCR 处理速度太慢

**解决方案**：
1. 检查图片质量，低质量图片识别更慢
2. 考虑降低 DPI（修改代码中的 `dpi=300` 为 `dpi=200`）
3. 对于纯文本 PDF，OCR 会自动跳过，无需担心

## 示例

处理图片型 PDF：

```python
from app.core.document_loader import DocumentLoader

loader = DocumentLoader()
documents = loader.load_file("files/GB-31613.2-2021.pdf")

# 系统会自动检测并使用 OCR 提取文本
for doc in documents:
    if doc.metadata.get("extracted_with_ocr"):
        print(f"页面 {doc.metadata['page_number']} 使用了 OCR")
```

## 相关文件

- `app/core/document_loader.py` - OCR 实现代码
- `app/core/config.py` - OCR 配置选项
- `requirements.txt` - Python 依赖列表
