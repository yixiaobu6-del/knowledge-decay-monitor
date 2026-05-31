"""
企业知识库decay监控 - 报告生成
生成多种格式的时效性分析报告
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import yaml


class ReportGenerator:
    """报告生成器"""

    def __init__(self, config_path: str, analysis_results: list):
        """
        初始化报告生成器

        Args:
            config_path: 配置文件路径
            analysis_results: 分析结果列表
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.results = analysis_results
        self.report_config = self.config.get('report', {})

    def generate(self) -> dict:
        """生成所有配置格式的报告"""
        output_dir = Path(self.report_config.get('output_dir', './reports'))
        output_dir.mkdir(exist_ok=True, parents=True)

        output = {
            'json': None,
            'html': None,
            'csv': None
        }

        formats = self.report_config.get('formats', ['json'])

        if 'json' in formats:
            output['json'] = self.generate_json(output_dir / 'decay_report.json')

        if 'html' in formats:
            output['html'] = self.generate_html(output_dir / 'decay_report.html')

        if 'csv' in formats:
            output['csv'] = self.generate_csv(output_dir / 'decay_report.csv')

        return output

    def generate_json(self, output_path: Path) -> str:
        """生成JSON格式报告"""
        summary = self._build_summary()

        report = {
            'report_info': {
                'generated_at': datetime.now().isoformat(),
                'config': self.report_config
            },
            'summary': summary,
            'documents': []
        }

        for r in self.results:
            entry = {
                'title': r['title'],
                'path': r['path'],
                'age_days': r['age_days'],
                'last_modified': r['last_modified'],
                'last_author': r['last_author'],
                'decay_score': r['decay_score'],
                'severity': r['severity'],
                'needs_update': r['needs_update'],
                'scores': r['scores']
            }
            if self.report_config.get('include_details', True):
                entry.update({
                    'recommendations': r.get('recommendations', [])
                })
            report['documents'].append(entry)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"JSON报告已生成: {output_path}")
        return str(output_path)

    def generate_html(self, output_path: Path) -> str:
        """生成HTML可视化报告"""
        summary = self._build_summary()

        severity_colors = {
            'healthy': '#22c55e',
            'warning': '#eab308',
            'attention': '#f97316',
            'critical': '#ef4444'
        }

        severity_labels = {
            'healthy': '健康',
            'warning': '需关注',
            'attention': '需更新',
            'critical': '严重过期'
        }

        rows_html = ''
        for r in self.results:
            color = severity_colors.get(r['severity'], '#6b7280')
            label = severity_labels.get(r['severity'], r['severity'])
            recs = r.get('recommendations', [])
            rec_html = ''.join(f'<li>{rec}</li>' for rec in recs) if recs else '<li>无需处理</li>'

            rows_html += f"""
            <tr class="hover:bg-gray-50">
                <td class="p-3 border-b">{r['title']}</td>
                <td class="p-3 border-b">{r['age_days']:.0f}天</td>
                <td class="p-3 border-b">{r['decay_score']}</td>
                <td class="p-3 border-b">
                    <span class="px-2 py-1 rounded text-white text-xs" style="background:{color}">{label}</span>
                </td>
                <td class="p-3 border-b">{r.get('last_author', 'unknown')}</td>
                <td class="p-3 border-b">
                    <ul class="text-xs text-gray-600 list-disc pl-4">
                        {rec_html}
                    </ul>
                </td>
            </tr>
            """

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>知识库Decay监控报告</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 p-8">
    <div class="max-w-6xl mx-auto">
        <h1 class="text-3xl font-bold mb-6">知识库Decay监控报告</h1>
        <p class="text-gray-500 mb-8">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

        <div class="grid grid-cols-4 gap-4 mb-8">
            <div class="bg-white rounded-lg shadow p-4 text-center">
                <div class="text-2xl font-bold text-blue-600">{summary['total_docs']}</div>
                <div class="text-sm text-gray-500">文档总数</div>
            </div>
            <div class="bg-white rounded-lg shadow p-4 text-center">
                <div class="text-2xl font-bold text-green-600">{summary['healthy_count']}</div>
                <div class="text-sm text-gray-500">健康</div>
            </div>
            <div class="bg-white rounded-lg shadow p-4 text-center">
                <div class="text-2xl font-bold text-yellow-600">{summary['warning_count']}</div>
                <div class="text-sm text-gray-500">需关注</div>
            </div>
            <div class="bg-white rounded-lg shadow p-4 text-center">
                <div class="text-2xl font-bold text-red-600">{summary['critical_count']}</div>
                <div class="text-sm text-gray-500">严重过期</div>
            </div>
        </div>

        <div class="bg-white rounded-lg shadow overflow-hidden">
            <table class="w-full text-sm">
                <thead class="bg-gray-100">
                    <tr>
                        <th class="p-3 text-left">文档标题</th>
                        <th class="p-3 text-left">年龄</th>
                        <th class="p-3 text-left">Decay评分</th>
                        <th class="p-3 text-left">状态</th>
                        <th class="p-3 text-left">最后作者</th>
                        <th class="p-3 text-left">建议</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"HTML报告已生成: {output_path}")
        return str(output_path)

    def generate_csv(self, output_path: Path) -> str:
        """生成CSV格式报告"""
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['文档标题', '路径', '年龄(天)', '最后修改', 'Decay评分', '状态', '最后作者'])
            for r in self.results:
                writer.writerow([
                    r['title'],
                    r['path'],
                    r['age_days'],
                    r['last_modified'],
                    r['decay_score'],
                    r['severity'],
                    r.get('last_author', 'unknown')
                ])

        print(f"CSV报告已生成: {output_path}")
        return str(output_path)

    def _build_summary(self) -> dict:
        """构建汇总信息"""
        total = len(self.results)
        healthy = sum(1 for r in self.results if r['severity'] == 'healthy')
        warning = sum(1 for r in self.results if r['severity'] == 'warning')
        attention = sum(1 for r in self.results if r['severity'] == 'attention')
        critical = sum(1 for r in self.results if r['severity'] == 'critical')
        avg_score = sum(r['decay_score'] for r in self.results) / total if total > 0 else 0

        return {
            'total_docs': total,
            'healthy_count': healthy,
            'warning_count': warning,
            'attention_count': attention,
            'critical_count': critical,
            'average_score': round(avg_score, 2),
            'needs_update': critical + attention
        }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from scanner import KnowledgeBaseScanner
    from analyzer import DecayAnalyzer

    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'

    scanner = KnowledgeBaseScanner(config_path)
    scanner.scan()

    analyzer = DecayAnalyzer(config_path, scanner)
    results = analyzer.analyze()

    reporter = ReportGenerator(config_path, results)
    outputs = reporter.generate()

    print(f"\n报告已生成于: {Path(reporter.report_config.get('output_dir', './reports')).resolve()}")