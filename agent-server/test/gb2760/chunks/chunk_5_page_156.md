作为“食品安全国家标准解析专家”，我将对输入的 PDF 文本坐标数据进行**结构化解析**，并将其转换为【食品添加剂香料信息】领域的专用 DSL（Domain Specific Language）格式。该 DSL 专用于构建食品用天然香料知识库，遵循以下设计原则：

---

### ✅ **DSL 设计规范**
```dsl
{
  "standard": "GB2760—2024",
  "table": "B.2(续)",
  "type": "food_natural_flavor",
  "entries": [
    {
      "serial_number": Integer,
      "code": String,                    // 如 N078
      "chinese_name": String,
      "english_name": String,
      "fema_number": String | null       // "---" 或缺失表示无 FEMA 编号
    },
    ...
  ]
}
```

---

### 🧩 解析策略说明

1. **表头识别**：通过 `line_id=1` 的字段识别列名。
2. **行切分**：基于 `y0` 坐标聚类，合并跨行文本（如英文名称断行）。
3. **字段映射**：
   - 序号 → `serial_number`
   - 编码 → `code`
   - 中文名称 → `chinese_name`
   - 英文名称 → `english_name`（注意拼接）
   - FEMA 编号 → `fema_number`（“—” 视为 null）

4. **多行合并逻辑**：
   - 若两行 y 值相近且未完整结束括号或单词，则合并。
   - 利用 block_id 和 line_id 辅助判断段落归属。

5. **特殊处理**：
   - “(又名...)” 属于中文名一部分。
   - 括号内拉丁学名属于英文名的一部分。
   - “terpeneless”、“concrete”、“tincture”、“extract”、“absolute” 等术语需保留在英文名中。

---

### ✅ 最终输出：DSL 格式数据

```json
{
  "standard": "GB2760—2024",
  "table": "B.2(续)",
  "type": "food_natural_flavor",
  "entries": [
    {
      "serial_number": 77,
      "code": "N078",
      "chinese_name": "姜黄浸膏",
      "english_name": "Turmeric extract (Curcuma longa L.)",
      "fema_number": "3086"
    },
    {
      "serial_number": 78,
      "code": "N079",
      "chinese_name": "葫芦巴酊",
      "english_name": "Fenugreek tincture (extract) (Trigonella foenum-graecum L.)",
      "fema_number": "2485"
    },
    {
      "serial_number": 79,
      "code": "N080",
      "chinese_name": "玳玳花油",
      "english_name": "Daidai flower oil (Citrus aurantium L. ‘Daidai’)",
      "fema_number": "2771"
    },
    {
      "serial_number": 80,
      "code": "N081",
      "chinese_name": "玳玳花浸膏",
      "english_name": "Daidai flower concrete (Citrus aurantium L. ‘Daidai’)",
      "fema_number": "2771"
    },
    {
      "serial_number": 81,
      "code": "N082",
      "chinese_name": "玳玳果油",
      "english_name": "Daidai fruit oil (Citrus aurantium L. ‘Daidai’)",
      "fema_number": "2771"
    },
    {
      "serial_number": 82,
      "code": "N083",
      "chinese_name": "柚皮油",
      "english_name": "Pummelo peel oil [Citrus grandis (L.) Osbeck]",
      "fema_number": null
    },
    {
      "serial_number": 83,
      "code": "N084",
      "chinese_name": "柏木叶油(北美香柏)",
      "english_name": "Cedar leaf oil (Thuja occidentalis L.)",
      "fema_number": "2267"
    },
    {
      "serial_number": 84,
      "code": "N085",
      "chinese_name": "枯茗籽油(又名孜然油)",
      "english_name": "Cumin seed oil (Cuminum cyminum L.)",
      "fema_number": "2343"
    },
    {
      "serial_number": 85,
      "code": "N086",
      "chinese_name": "柠檬油",
      "english_name": "Lemon oil [Citrus limon (L.) Burm. f.]",
      "fema_number": "2625"
    },
    {
      "serial_number": 86,
      "code": "N087",
      "chinese_name": "无萜柠檬油",
      "english_name": "Lemon oil, terpeneless [Citrus limon (L.) Burm. f.]",
      "fema_number": "2626"
    },
    {
      "serial_number": 87,
      "code": "N088",
      "chinese_name": "柠檬油萜烯",
      "english_name": "Terpenes of lemon oil",
      "fema_number": null
    },
    {
      "serial_number": 88,
      "code": "N089",
      "chinese_name": "柠檬叶油",
      "english_name": "Petitgrain lemon oil [Citrus limon (L.) Burm. f.]",
      "fema_number": "2853"
    },
    {
      "serial_number": 89,
      "code": "N090",
      "chinese_name": "柠檬草油",
      "english_name": "Lemongrass oil (Cymbopogon citratus DC. and C. flexuosus)",
      "fema_number": "2624"
    },
    {
      "serial_number": 90,
      "code": "N091",
      "chinese_name": "栀子花浸膏",
      "english_name": "Gardenia flower concrete (Gardenia jasminoides Ellis)",
      "fema_number": null
    },
    {
      "serial_number": 91,
      "code": "N092",
      "chinese_name": "树兰花油",
      "english_name": "Aglaia odorata flower oil",
      "fema_number": null
    },
    {
      "serial_number": 92,
      "code": "N093",
      "chinese_name": "树兰花酊",
      "english_name": "Aglaia odorata flower tincture",
      "fema_number": null
    },
    {
      "serial_number": 93,
      "code": "N094",
      "chinese_name": "树兰花浸膏",
      "english_name": "Aglaia odorata flower concrete",
      "fema_number": null
    },
    {
      "serial_number": 94,
      "code": "N095",
      "chinese_name": "树苔净油",
      "english_name": "Tree moss absolute (Evernia furfuraceae)",
      "fema_number": null
    },
    {
      "serial_number": 95,
      "code": "N096",
      "chinese_name": "树苔浸膏",
      "english_name": "Tree moss concrete (Evernia furfuraceae)",
      "fema_number": null
    },
    {
      "serial_number": 96,
      "code": "N097",
      "chinese_name": "香叶油(又名玫瑰香叶油)",
      "english_name": "Geranium oil (geranium rose oil) (Pelargonium graveolens L’Her)",
      "fema_number": "2508"
    },
    {
      "serial_number": 97,
      "code": "N098",
      "chinese_name": "除萜香叶油",
      "english_name": "Geranium oil terpeneless",
      "fema_number": "2508"
    },
    {
      "serial_number": 98,
      "code": "N099",
      "chinese_name": "香风茶油(又名香茶菜油)",
      "english_name": "Xiang Fengchao oil (Rabdosia spp.)",
      "fema_number": null
    },
    {
      "serial_number": 99,
      "code": "N101",
      "chinese_name": "香柠檬油",
      "english_name": "Bergamot oil (Citrus aurantium L. subsp. bergamia)",
      "fema_number": "2153"
    },
    {
      "serial_number": 100,
      "code": "N102",
      "chinese_name": "香根油",
      "english_name": "Vertiver oil (Vetiveria zizanioides Nash.)",
      "fema_number": null
    }
  ]
}
```

---

### 🔍 补充说明

- **序号从77开始**，符合“续表”特征。
- **N100 缺失**：原文中直接跳过 `N100` 出现 `N101`，可能是排版遗漏或有意跳过，按原始数据保留。
- **英文名标准化**：已添加空格、修正连字符断裂词（如 `foenum graecum` → `foenum-graecum`）、统一括号格式。
- **拉丁文学名** 完整保留，是香料鉴别关键依据。

---

✅ 此 DSL 输出可直接导入 Neo4j / MongoDB / RDF 知识图谱系统，支持语义查询与合规性校验。  
是否需要导出为 TTL（RDF/Turtle）或生成 SQL Schema？