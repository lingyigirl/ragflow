"""
MinerU V2 数据模型。

独立的 mineru_section_v2 表，与 V1 的 mineru_section 表完全分离。
"""
from api.db.db_models import DataBaseModel, JSONField, LongTextField
from peewee import BigAutoField, BooleanField, CharField, IntegerField, TextField


class MineruSectionV2(DataBaseModel):
    """
    MinerU V2 解析结果存储表。

    与 MineruSection（V1）的关键区别：
    - 新增 inline_formula 字段（span 级内联公式）
    - table_html 替代 table_body（更明确语义）
    - span_json 存储原始 span 数组（完整保真）
    - 块类型使用 V2 语义类型名（title/paragraph/list/...）
    - content 字段直接存储纯文本聚合结果
    """

    # 主键与关联
    id = BigAutoField(primary_key=True)
    kb_id = CharField(max_length=64, null=False, index=True)
    doc_id = CharField(max_length=64, null=False, index=True)
    chunk_id = CharField(max_length=64, null=False, index=True)

    # V2 块类型：paragraph / title / list / table / image / page_header / page_footer
    type = CharField(max_length=20, null=False)

    # 基本内容
    text = LongTextField(null=True)        # span 聚合后的纯文本
    content = LongTextField(null=True)     # 图片描述等非 span 内容
    bbox = JSONField(null=True)            # 原始边界框 [x0, y0, x1, y1]（千分比坐标，MinerU 原始输出）
    bbox_rotated = JSONField(null=True)    # 旋转修正后的边界框（仅当原始 PDF 有 /Rotate 时非空）
    is_rotated = BooleanField(null=False, default=False)  # MinerU 是否生成了 _rotated.pdf（内容自动摆正）
    page_idx = IntegerField(null=True)     # 页码（来自 V2 顶层数组下标）

    # 标题层级（title 类型专用）
    text_level = IntegerField(null=True)   # 1-6 对应 h1-h6

    # 图片相关
    img_path = CharField(max_length=2048, null=True)
    image_caption = JSONField(null=True)   # span 数组
    image_footnote = JSONField(null=True)  # span 数组

    # 表格相关（V2 专用字段名）
    table_html = LongTextField(null=True)       # 表格 HTML（V1: table_body）
    table_caption = JSONField(null=True)        # span 数组
    table_footnote = JSONField(null=True)       # span 数组

    # 列表相关
    list_items = JSONField(null=True)     # 结构化列表项数组
    list_type = CharField(max_length=32, null=True)  # text_list / bullet_list / ...

    # V2 新增字段
    inline_formula = JSONField(null=True)  # 内联公式 LaTeX 数组 [{"latex": "...", "index": 0}]
    span_json = JSONField(null=True)       # 原始 span 数组（完整保真，JSON 格式）
    sub_type = CharField(max_length=50, null=True)  # 子类型（如图片: natural_image/seal）

    # 检索相关（与 V1 对齐）
    es_id = CharField(max_length=64, null=True, index=True)  # ES/Infinity 文档 ID
    es_tab2text = LongTextField(null=True)   # 表格转文本（用于检索）
    llm_tab2text = LongTextField(null=True)  # LLM 表格转文本

    class Meta:
        db_table = "mineru_section_v2"


def init_mineru_v2_table():
    """初始化 mineru_section_v2 表。由 api/ragflow_server.py 启动时调用。"""
    import logging
    from playhouse.migrate import migrate

    if not MineruSectionV2.table_exists():
        MineruSectionV2.create_table()
        logging.info("[custom.mineru_v2] mineru_section_v2 表创建成功")
        return True

    # 增量迁移：添加后续新增的列
    from common import settings
    from api.db.db_models import DatabaseMigrator
    migrator = DatabaseMigrator[settings.DATABASE_TYPE.upper()].value(
        MineruSectionV2._meta.database
    )
    for _col in [
        ("bbox_rotated", JSONField(null=True)),
        ("is_rotated", BooleanField(null=False, default=False)),
    ]:
        try:
            migrate(migrator.add_column("mineru_section_v2", _col[0], _col[1]))
            logging.info("[custom.mineru_v2] 迁移完成: 添加列 %s", _col[0])
        except Exception:
            pass  # 列已存在则忽略
    return False
