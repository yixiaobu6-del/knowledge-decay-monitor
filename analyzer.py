"""
企业知识库decay监控 - 时效性分析
评估文档的时效性衰减程度
"""

import json
import math
import re
from datetime import datetime, timedelta
from pathlib import Path

import yaml


class DecayAnalyzer:
    """时效性分析器"""

    def __init__(self, config_path: str, scanner):
        """
        初始化分析器

        Args:
            config_path: 配置文件路径
            scanner: 扫描器实例（需包含documents列表）
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

        self.documents = scanner.documents
        self.decay_config = self.config.get('decay', {})
        self.weights = self.config.get('scoring', {}).get('weights', {})

    def analyze(self) -> list:
        """
        执行时效性分析

        Returns:
            分析结果列表（含评分）
        """
        results = []

        for doc in self.documents:
            analysis = self._analyze_document(doc)
            results.append(analysis)

        # 按decay分数排序（最需要更新的排前面）
        results.sort(key=lambda x: x['decay_score'])

        print(f"[分析] 完成: 分析了 {len(results)} 篇文档")
        return results

    def _analyze_document(self, doc: dict) -> dict:
        """分析单篇文档"""
        scores = {}

        # 1. 更新时间评分
        scores['last_updated'] = self._score_last_updated(doc)

        # 2. 引用时效评分
        scores['reference_freshness'] = self._score_references(doc)

        # 3. 内容稳定性评分
        scores['content_stability'] = self._score_stability(doc)

        # 4. 话题相关性评分
        scores['topic_relevance'] = self._score_relevance(doc)

        # 5. 访问频率评分
        scores['read_frequency'] = self._score_frequency(doc)

        # 6. 作者活跃度评分
        scores['author_activity'] = self._score_author(doc)

        # 综合decay分数（0-100，越低越需要更新）
        decay_score = sum(
            scores.get(key, 0) * self.weights.get(key, 0.1)
            for key in self.weights
        )

        # 严重等级判定
        severity = self._determine_severity(decay_score)

        # 是否需要更新
        needs_update = decay_score < self.config['severity'].get('yellow', 60)

        return {
            'doc_id': doc['id'],
            'title': doc.get('title', doc['filename']),
            'filename': doc['filename'],
            'path': doc['path'],
            'age_days': round(doc.get('age_days', 0), 1),
            'last_modified': doc.get('last_modified', ''),
            'last_author': doc.get('last_author', 'unknown'),
            'scores': scores,
            'decay_score': round(decay_score, 2),
            'severity': severity,
            'needs_update': needs_update,
            'recommendations': self._generate_recommendations(doc, scores, severity)
        }

    def _score_last_updated(self, doc: dict) -> float:
        """基于最后更新时间的评分"""
        age_days = doc.get('age_days', 0)
        config = self.decay_config

        max_age = config.get('max_age_days', 365)
        warning_age = config.get('warning_age_days', 180)
        critical_age = config.get('critical_age_days', 90)

        if age_days <= critical_age:
            return 100.0
        elif age_days <= warning_age:
            # 线性衰减
            return 100 - (age_days - critical_age) / (warning_age - critical_age) * 30
        elif age_days <= max_age:
            return 70 - (age_days - warning_age) / (max_age - warning_age) * 40
        else:
            return max(0, 30 - (age_days - max_age) / max_age * 30)

    def _score_references(self, doc: dict) -> float:
        """基于引用时效性的评分"""
        references = doc.get('references', [])

        if not references:
            return 70.0  # 无引用给中等分数

        stale_links = 0
        total_links = len(references)

        for ref in references:
            url = ref.get('url', '')
            # 简单检测：包含"2020"或"2021"等早期年份很可能过时
            for year in ['2020', '2021', '2022']:
                if year in url:
                    stale_links += 1
                    break

        if total_links == 0:
            return 70.0

        freshness_ratio = (total_links - stale_links) / total_links
        return freshness_ratio * 100

    def _score_stability(self, doc: dict) -> float:
        """基于内容稳定性的评分"""
        content = doc.get('content', '')
        if not content:
            return 50.0

        # 检查是否包含时效性敏感词
        time_sensitive_patterns = [
            r'(最新|当前|今年|本月|截至目前)',
            r'(截至\d{4}年\d{1,2}月)',
            r'(的\d{4}年数据)',
            r'(预计\d{4}年)',
            r'(已达|突破)\d{1,10}',
        ]

        time_sensitive_count = 0
        for pattern in time_sensitive_patterns:
            time_sensitive_count += len(re.findall(pattern, content))

        # 越少时效性词汇，内容越稳定
        if time_sensitive_count == 0:
            return 85.0
        elif time_sensitive_count <= 2:
            return 65.0
        elif time_sensitive_count <= 5:
            return 45.0
        else:
            return max(0, 45 - (time_sensitive_count - 5) * 5)

    def _score_relevance(self, doc: dict) -> float:
        """基于话题相关性的评分"""
        tags = doc.get('tags', [])

        if not tags:
            return 60.0

        outdated_tags = ['旧版', '遗留', '废弃', 'EOL', 'deprecated']
        relevant_tags_count = len([t for t in tags if t not in outdated_tags])

        if not tags:
            return 60.0

        return (relevant_tags_count / len(tags)) * 100

    def _score_frequency(self, doc: dict) -> float:
        """基于访问频率的评分"""
        # 基于最后访问时间估算
        last_accessed_str = doc.get('last_accessed', '')
        try:
            last_access = datetime.fromisoformat(last_accessed_str)
            days_since_access = (datetime.now() - last_access).days
        except Exception:
            days_since_access = 365

        if days_since_access <= 30:
            return 90.0
        elif days_since_access <= 90:
            return 70.0
        elif days_since_access <= 180:
            return 50.0
        elif days_since_access <= 365:
            return 30.0
        else:
            return 10.0

    def _score_author(self, doc: dict) -> float:
        """基于作者活跃度的评分"""
        author = doc.get('last_author', '')
        if author == 'unknown':
            return 40.0
        return 60.0  # 有作者信息但不清楚活跃度

    def _determine_severity(self, score: float) -> str:
        """判定严重等级"""
        severity_config = self.config.get('severity', {})
        if score >= severity_config.get('green', 80):
            return 'healthy'
        elif score >= severity_config.get('yellow', 60):
            return 'warning'
        elif score >= severity_config.get('orange', 40):
            return 'attention'
        else:
            return 'critical'

    def _generate_recommendations(self, doc: dict, scores: dict,
                                   severity: str) -> list:
        """生成维护建议"""
        recommendations = []
        age_days = doc.get('age_days', 0)

        # 根据评分生成建议
        if scores.get('last_updated', 100) < 50:
            recommendations.append(f"文档已有 {round(age_days)} 天未更新，建议尽快审查和更新内容")

        if scores.get('reference_freshness', 100) < 50:
            recommendations.append("文档中的引用的链接可能已失效，需要验证和更新的引用来源")

        if scores.get('content_stability', 100) < 50:
            recommendations.append("文档包含时效性表述（如'今年'、'最新'等），建议将这些内容改为更通用的表述")

        if severity == 'critical':
            recommendations.insert(0, "【紧急】此文档已严重过期，需要立即重写或删除")
        elif severity == 'attention':
            recommendations.insert(0, "建议将此文档列入下个维护周期的待处理列表")

        return recommendations

    def get_summary(self, results: list) -> dict:
        """获取分析汇总"""
        if not results:
            return {}

        severity_count = {'healthy': 0, 'warning': 0, 'attention': 0, 'critical': 0}
        total_score = 0

        for r in results:
            severity_count[r['severity']] = severity_count.get(r['severity'], 0) + 1
            total_score += r['decay_score']

        avg_score = total_score / len(results)
        needs_update_count = sum(1 for r in results if r['needs_update'])

        return {
            'total_docs': len(results),
            'average_decay_score': round(avg_score, 2),
            'average_age_days': round(
                sum(r['age_days'] for r in results) / len(results), 1
            ),
            'severity_distribution': severity_count,
            'needs_update_count': needs_update_count,
            'needs_update_pct': round(needs_update_count / len(results) * 100, 1),
            'critical_docs': [r['filename'] for r in results if r['severity'] == 'critical']
        }


if __name__ == '__main__':
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from scanner import KnowledgeBaseScanner

    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'

    scanner = KnowledgeBaseScanner(config_path)
    scanner.scan()

    analyzer = DecayAnalyzer(config_path, scanner)
    results = analyzer.analyze()

    summary = analyzer.get_summary(results)
    print(f"\n分析汇总:")
    print(f"  平均decay分数: {summary['average_decay_score']}")
    print(f"  需要更新的文档: {summary['needs_update_count']} ({summary['needs_update_pct']}%)")
    print(f"  严重等级分布: {summary['severity_distribution']}")
    print(f"  严重过期文档: {summary['critical_docs']}")