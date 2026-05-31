"""
企业知识库decay监控 - 文档扫描框架
扫描知识库目录结构，提取文档元数据
"""

import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml


class KnowledgeBaseScanner:
    """知识库扫描器"""

    def __init__(self, config_path: str):
        """
        初始化扫描器

        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.config = self._load_config()

        self.kb_path = Path(self.config['knowledge_base']['path'])
        self.documents = []

    def _load_config(self) -> dict:
        """加载配置"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def scan(self) -> list:
        """
        扫描知识库

        Returns:
            文档列表
        """
        kb_config = self.config['knowledge_base']
        extensions = kb_config.get('supported_extensions', [])
        exclude_dirs = kb_config.get('exclude_dirs', [])
        recursive = kb_config.get('scan_recursive', True)

        if not self.kb_path.exists():
            print(f"[扫描] 知识库路径不存在: {self.kb_path}")
            return []

        pattern = '**/*' if recursive else '*'
        self.documents = []

        for file_path in self.kb_path.glob(pattern):
            if file_path.is_dir():
                continue

            # 检查排除目录
            should_exclude = False
            for exclude_dir in exclude_dirs:
                if exclude_dir in str(file_path):
                    should_exclude = True
                    break
            if should_exclude:
                continue

            # 检查扩展名
            if extensions and file_path.suffix.lower() not in extensions:
                continue

            doc = self._extract_metadata(file_path)
            if doc:
                self.documents.append(doc)

        print(f"[扫描] 完成: 发现 {len(self.documents)} 个文档")
        return self.documents

    def _extract_metadata(self, file_path: Path) -> Optional[dict]:
        """
        提取文档元数据

        Args:
            file_path: 文档路径

        Returns:
            文档元数据
        """
        try:
            stat = file_path.stat()

            # 基本元数据
            doc = {
                'id': hashlib.md5(str(file_path).encode()).hexdigest()[:12],
                'path': str(file_path),
                'filename': file_path.name,
                'extension': file_path.suffix.lower(),
                'size_bytes': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_birthtime).isoformat(),
                'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
                'last_accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
                'age_days': (time.time() - stat.st_mtime) / 86400,
                'directory': str(file_path.parent),
            }

            # 读取内容提取结构化信息
            try:
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                doc['content'] = content
                doc['line_count'] = content.count('\n') + 1
                doc['char_count'] = len(content)
                doc['word_count'] = len(re.findall(r'[\u4e00-\u9fff\w]+', content))

                # 提取标题
                title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
                doc['title'] = title_match.group(1).strip() if title_match else file_path.stem

                # 提取标签
                tags = re.findall(r'tags:\s*\[([^\]]+)\]', content)
                doc['tags'] = [t.strip() for t in tags[0].split(',')] if tags else []

                # 提取引用链接
                refs = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
                doc['references'] = [{'text': r[0], 'url': r[1]} for r in refs]

                # 提取最后更新人信息（如果有）
                author_match = re.search(r'last\s*(?:modified|updated)\s*(?:by|:)?\s*(\w+)', content, re.IGNORECASE)
                doc['last_author'] = author_match.group(1) if author_match else 'unknown'

            except Exception:
                doc['content'] = ''
                doc['line_count'] = 0
                doc['char_count'] = 0
                doc['word_count'] = 0
                doc['title'] = file_path.stem
                doc['tags'] = []
                doc['references'] = []
                doc['last_author'] = 'unknown'

            return doc

        except Exception as e:
            print(f"[扫描] 处理文件失败: {file_path} - {str(e)}")
            return None

    def get_statistics(self) -> dict:
        """获取扫描统计"""
        if not self.documents:
            return {'doc_count': 0}

        extensions = {}
        age_distribution = {'<=30天': 0, '31-90天': 0, '91-180天': 0, '181-365天': 0, '>365天': 0}
        total_size = 0

        for doc in self.documents:
            ext = doc.get('extension', 'unknown')
            extensions[ext] = extensions.get(ext, 0) + 1

            age = doc.get('age_days', 0)
            if age <= 30:
                age_distribution['<=30天'] += 1
            elif age <= 90:
                age_distribution['31-90天'] += 1
            elif age <= 180:
                age_distribution['91-180天'] += 1
            elif age <= 365:
                age_distribution['181-365天'] += 1
            else:
                age_distribution['>365天'] += 1

            total_size += doc.get('size_bytes', 0)

        return {
            'doc_count': len(self.documents),
            'total_size_mb': round(total_size / 1024 / 1024, 2),
            'extensions': extensions,
            'age_distribution': age_distribution,
            'average_age_days': round(
                sum(d.get('age_days', 0) for d in self.documents) / len(self.documents),
                1
            )
        }

    def save_results(self, output_path: str) -> None:
        """保存扫描结果"""
        results = {
            'scan_time': datetime.now().isoformat(),
            'config': {
                'kb_path': str(self.kb_path),
                'extensions': self.config['knowledge_base']['supported_extensions']
            },
            'statistics': self.get_statistics(),
            'documents': [
                {k: v for k, v in doc.items() if k != 'content'}  # 不保存完整内容
                for doc in self.documents
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"[扫描] 结果已保存至: {output_path}")


if __name__ == '__main__':
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'

    scanner = KnowledgeBaseScanner(config_path)
    docs = scanner.scan()

    stats = scanner.get_statistics()
    print(f"\n统计信息:")
    print(f"  文档数量: {stats['doc_count']}")
    print(f"  总大小: {stats['total_size_mb']} MB")
    print(f"  平均时效: {stats['average_age_days']} 天")

    scanner.save_results('output/scan_results.json')