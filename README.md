# 企业知识库decay监控

监控企业内部知识文档的时效性衰减情况，及时提醒文档更新维护。

## 项目简介

企业知识库中的文档会随时间老化，信息过时、引用失效、数据过期的文档不仅帮助有限，还可能误导读者。本工具系统性地扫描知识库中的文档，评估其时效性衰减程度，生成维护报告，帮助知识库管理者安排文档更新。

## 核心功能

- **文档扫描**：递归扫描知识库目录中的文档
- **时效性评估**：基于多维指标计算文档时效性分数
- **decay检测**：识别已过期和即将过期的文档
- **报告生成**：输出可视化报告，标注需要维护的文档
- **配置驱动**：灵活的规则配置，适配不同业务场景

## 技术架构

```
企业知识库decay监控/
├── config.yaml          # 配置文件
├── scanner.py           # 文档扫描框架
├── analyzer.py          # 时效性分析
├── report.py            # 报告生成
├── requirements.txt
└── README.md
```

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行扫描

```bash
python scanner.py
python analyzer.py
python report.py
```

### Python调用

```python
from scanner import KnowledgeBaseScanner
from analyzer import DecayAnalyzer
from report import ReportGenerator

# 扫描文档
scanner = KnowledgeBaseScanner("config.yaml")
scanner.scan()

# 分析时效性
analyzer = DecayAnalyzer("config.yaml", scanner)
results = analyzer.analyze()

# 生成报告
reporter = ReportGenerator("config.yaml", results)
reporter.generate()
```

## 配置说明

```yaml
knowledge_base:
  path: ./docs            # 知识库路径
  scan_recursive: true    # 是否递归扫描
  supported_extensions: [.md, .rst, .txt]

decay:
  max_age_days: 365       # 文档最长有效期
  critical_age_days: 180  # 关键期
  check_references: true  # 是否校验引用

scoring:
  last_updated_weight: 0.3    # 更新时间权重
  reference_freshness: 0.2    # 引用时效权重
  content_stability: 0.1      # 内容稳定权重
```

## 应用场景

- **技术文档库**：及时发现过时的API文档
- **内部Wiki**：提醒团队更新陈旧页面
- **知识管理系统**：辅助知识库维护决策
- **合规文档**：确保政策文档跟上最新法规

## 许可证

MIT License