"""PostgreSQL 数据库操作基础类"""

from __future__ import annotations

import threading
from typing import List, Dict, Any, Optional, Union, Type, Tuple, Sequence

from sqlalchemy import create_engine, inspect, text, select, update, delete
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import OperationalError, IntegrityError
from sqlalchemy.dialects import postgresql

from src.common.setting import settings

# ETL 单次 batch 上限：按日全市场 ~5800、按股全历史 ~8600，统一分批阈值
DEFAULT_BULK_UPSERT_CHUNK_SIZE: int = 10000

_engine: Engine | None = None
_session_factory: sessionmaker | None = None
_engine_url: str | None = None
_engine_lock = threading.Lock()


def get_shared_engine(database_url: str | None = None) -> Engine:
    """进程内共享 SQLAlchemy Engine（连接池单例）。"""
    global _engine, _session_factory, _engine_url
    url = database_url or settings.postgresql_url
    with _engine_lock:
        if _engine is None or _engine_url != url:
            if _engine is not None:
                _engine.dispose()
            _engine = create_engine(
                url,
                echo=settings.postgresql_echo,
                pool_size=settings.postgresql_pool_size,
                max_overflow=settings.postgresql_max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            _engine_url = url
            _session_factory = sessionmaker(
                bind=_engine, autocommit=False, autoflush=False,
            )
        return _engine


def get_shared_session_factory(database_url: str | None = None) -> sessionmaker:
    get_shared_engine(database_url)
    assert _session_factory is not None
    return _session_factory


def _normalize_pg_type_for_compare(type_sql: str) -> str:
    """
    PostgreSQL 中部分类型有多种写法且等价，同步表时避免误判为“类型变化”。
    例如 DOUBLE PRECISION 与 FLOAT 在 PG 中都是 8 字节双精度，视为相同。
    """
    s = type_sql.upper().strip()
    # 双精度：DOUBLE PRECISION / FLOAT / FLOAT8 / FLOAT(8) 等价
    if s in ("DOUBLE PRECISION", "FLOAT8", "FLOAT(8)"):
        return "FLOAT"
    if s == "FLOAT":
        return "FLOAT"
    # 单精度：REAL / FLOAT4 / FLOAT(4) 等价
    if s in ("REAL", "FLOAT4", "FLOAT(4)"):
        return "REAL"
    return s


class Database:
    """PostgreSQL 数据库操作基础类"""
    
    def __init__(self, database_url: Optional[str] = None):
        """
        初始化数据库连接
        
        Args:
            database_url: 数据库连接 URL，如果为 None 则使用 settings 中的配置
        """
        self.database_url = database_url or settings.postgresql_url
        default_url = settings.postgresql_url
        if database_url is None or database_url == default_url:
            self.engine = get_shared_engine(self.database_url)
            self.SessionLocal = get_shared_session_factory(self.database_url)
        else:
            self.engine = create_engine(self.database_url, echo=False)
            self.SessionLocal = sessionmaker(
                bind=self.engine, autocommit=False, autoflush=False,
            )
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()

    def ensure_table(self, model_class: Type[Any]) -> None:
        """若表不存在则静默创建（不交互、不修改已有表结构）。"""
        table_name = model_class.__tablename__
        inspector = inspect(self.engine)
        if table_name not in inspector.get_table_names():
            model_class.__table__.metadata.create_all(self.engine)
    
    # ========== 基础 CRUD 操作 ==========
    
    def create(self, model_class: Type[Any], **kwargs) -> Any:
        """
        创建单条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            **kwargs: 字段键值对
        
        Returns:
            创建的模型实例
        """
        session = self.get_session()
        try:
            instance = model_class(**kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def get_by_id(self, model_class: Type[Any], record_id: Any) -> Optional[Any]:
        """
        根据 ID 查询单条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            record_id: 记录 ID
        
        Returns:
            模型实例，如果不存在则返回 None
        """
        session = self.get_session()
        try:
            return session.query(model_class).filter(model_class.id == record_id).first()
        finally:
            session.close()
    
    def get_one(self, model_class: Type[Any], **filters) -> Optional[Any]:
        """
        根据条件查询单条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            **filters: 查询条件
        
        Returns:
            模型实例，如果不存在则返回 None
        """
        session = self.get_session()
        try:
            query = session.query(model_class)
            for key, value in filters.items():
                query = query.filter(getattr(model_class, key) == value)
            return query.first()
        finally:
            session.close()
    
    def get_all(self, model_class: Type[Any], **filters) -> List[Any]:
        """
        根据条件查询多条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            **filters: 查询条件；若某条件值为 list/tuple，则生成 IN 子句（如 exchange=["SSE","SZSE"]）
        
        Returns:
            模型实例列表
        """
        session = self.get_session()
        try:
            query = session.query(model_class)
            for key, value in filters.items():
                col = getattr(model_class, key)
                if isinstance(value, (list, tuple)):
                    if not value:
                        query = query.filter(False)  # 空列表等价于不匹配
                    else:
                        query = query.filter(col.in_(value))
                else:
                    query = query.filter(col == value)
            return query.all()
        finally:
            session.close()
    
    def fetch_model_columns(
        self,
        model_class: Type[Any],
        return_fields: Tuple[str, ...],
        **filters: Any,
    ) -> List[Tuple[Any, ...]]:
        """
        只查询指定列的多条记录，返回元组列表（顺序与 return_fields 一致）。
        筛选语义与 get_all 一致（等值或 list/tuple 生成 IN）。
        """
        if not return_fields:
            raise ValueError("return_fields 不能为空")
        table_columns = model_class.__table__.columns
        for name in return_fields:
            if name not in table_columns:
                raise ValueError(f"模型 {model_class.__name__} 不存在列: {name!r}")
        session = self.get_session()
        try:
            columns = [getattr(model_class, name) for name in return_fields]
            query = session.query(*columns)
            for key, value in filters.items():
                col = getattr(model_class, key)
                if isinstance(value, (list, tuple)):
                    if not value:
                        query = query.filter(False)
                    else:
                        query = query.filter(col.in_(value))
                else:
                    query = query.filter(col == value)
            rows = query.all()
            return [tuple(row) for row in rows]
        finally:
            session.close()

    def select_grouped(
        self,
        model_class: Type[Any],
        *select_entities: Any,
        group_by: Sequence[Any],
        order_by: Optional[Sequence[Any]] = None,
        where_clauses: Optional[Sequence[Any]] = None,
        **filters: Any,
    ) -> List[Tuple[Any, ...]]:
        """
        分组聚合查询：等价于 query(*select_entities).filter(...).group_by(...).order_by(...)。

        **filters 与 get_all 一致（等值；list/tuple 生成 IN）。额外条件用 where_clauses（SQLAlchemy 布尔表达式，AND 连接）。

        Args:
            model_class: ORM 模型类；**filters 的键须为该模型上的列名。
            *select_entities: SELECT 列或表达式（如 模型列、func.count(...)）。
            group_by: GROUP BY 列或表达式序列。
            order_by: ORDER BY 列或表达式序列，可选。
            where_clauses: 追加的 filter 条件，可选。
            **filters: 等值 / IN 筛选。

        Returns:
            与 select_entities 顺序一致的元组列表。
        """
        if not select_entities:
            raise ValueError("select_entities 不能为空")
        session = self.get_session()
        try:
            query = session.query(*select_entities)
            for key, value in filters.items():
                col = getattr(model_class, key)
                if isinstance(value, (list, tuple)):
                    if not value:
                        query = query.filter(False)
                    else:
                        query = query.filter(col.in_(value))
                else:
                    query = query.filter(col == value)
            if where_clauses:
                for clause in where_clauses:
                    query = query.filter(clause)
            query = query.group_by(*group_by)
            if order_by:
                query = query.order_by(*order_by)
            rows = query.all()
            return [tuple(row) for row in rows]
        finally:
            session.close()
    
    def update(self, model_class: Type[Any], record_id: Any, **kwargs) -> Optional[Any]:
        """
        更新单条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            record_id: 记录 ID
            **kwargs: 要更新的字段键值对
        
        Returns:
            更新后的模型实例，如果不存在则返回 None
        """
        session = self.get_session()
        try:
            instance = session.query(model_class).filter(model_class.id == record_id).first()
            if instance:
                for key, value in kwargs.items():
                    setattr(instance, key, value)
                session.commit()
                session.refresh(instance)
                return instance
            return None
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete(self, model_class: Type[Any], record_id: Any) -> bool:
        """
        删除单条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            record_id: 记录 ID
        
        Returns:
            是否删除成功
        """
        session = self.get_session()
        try:
            instance = session.query(model_class).filter(model_class.id == record_id).first()
            if instance:
                session.delete(instance)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def delete_by_filter(self, model_class: Type[Any], **filters) -> int:
        """
        根据条件删除多条记录
        
        Args:
            model_class: SQLAlchemy 模型类
            **filters: 删除条件
        
        Returns:
            删除的记录数
        """
        session = self.get_session()
        try:
            query = session.query(model_class)
            for key, value in filters.items():
                query = query.filter(getattr(model_class, key) == value)
            count = query.count()
            query.delete(synchronize_session=False)
            session.commit()
            return count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # ========== 批量操作 ==========
    
    def bulk_create(self, model_class: Type[Any], records: List[Dict[str, Any]]) -> List[Any]:
        """
        批量创建记录
        
        Args:
            model_class: SQLAlchemy 模型类
            records: 记录字典列表
        
        Returns:
            创建的模型实例列表
        """
        session = self.get_session()
        try:
            instances = [model_class(**record) for record in records]
            session.bulk_save_objects(instances)
            session.commit()
            # 刷新实例以获取生成的 ID
            for instance in instances:
                session.refresh(instance)
            return instances
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def bulk_update(self, model_class: Type[Any], records: List[Dict[str, Any]], 
                   update_fields: Optional[List[str]] = None) -> int:
        """
        批量更新记录
        
        Args:
            model_class: SQLAlchemy 模型类
            records: 记录字典列表，必须包含主键字段
            update_fields: 要更新的字段列表，如果为 None 则更新所有非主键字段
        
        Returns:
            更新的记录数
        """
        session = self.get_session()
        try:
            if update_fields is None:
                # 获取所有非主键字段
                primary_keys = {col.name for col in model_class.__table__.primary_key.columns}
                update_fields = [col.name for col in model_class.__table__.columns 
                               if col.name not in primary_keys]
            
            # 构建更新对象列表
            update_objects = []
            for record in records:
                update_obj = {field: record.get(field) for field in update_fields if field in record}
                # 添加主键用于匹配
                for pk_col in model_class.__table__.primary_key.columns:
                    if pk_col.name in record:
                        update_obj[pk_col.name] = record[pk_col.name]
                update_objects.append(update_obj)
            
            session.bulk_update_mappings(model_class, update_objects)
            session.commit()
            return len(update_objects)
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    # ========== Upsert 操作 ==========
    
    def upsert(self, model_class: Type[Any], record: Dict[str, Any], 
              conflict_keys: Optional[List[str]] = None) -> Any:
        """
        Upsert 单条记录（存在则更新，不存在则插入）
        
        Args:
            model_class: SQLAlchemy 模型类
            record: 记录字典
            conflict_keys: 冲突检测的字段列表，如果为 None 则使用主键
        
        Returns:
            模型实例
        """
        session = self.get_session()
        try:
            if conflict_keys is None:
                # 使用主键作为冲突检测字段
                conflict_keys = [col.name for col in model_class.__table__.primary_key.columns]
            
            # 只保留模型中存在的字段，避免传入无效字段
            valid_columns = {col.name for col in model_class.__table__.columns}
            filtered_record = {k: v for k, v in record.items() if k in valid_columns}
            
            # 构建查询条件
            filters = {key: filtered_record[key] for key in conflict_keys if key in filtered_record}
            
            # 查询是否存在
            existing = self.get_one(model_class, **filters)
            
            if existing:
                # 更新现有记录
                for key, value in filtered_record.items():
                    if key not in conflict_keys:
                        setattr(existing, key, value)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # 创建新记录
                instance = model_class(**filtered_record)
                session.add(instance)
                session.commit()
                session.refresh(instance)
                return instance
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def _check_field_lengths(self, model_class: Type[Any], records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """
        检查记录中哪些字段的值超过了数据库字段定义的长度
        
        Args:
            model_class: SQLAlchemy 模型类
            records: 记录字典列表
        
        Returns:
            超长字段信息字典，格式：{字段名: {'max_length': 定义长度, 'violations': [超长值列表]}}
        """
        violations = {}
        table = model_class.__table__
        
        for record in records:
            for col_name, value in record.items():
                if col_name not in table.columns:
                    continue
                
                col = table.columns[col_name]
                
                # 检查字符串类型字段的长度
                if hasattr(col.type, 'length') and col.type.length is not None:
                    if isinstance(value, str) and len(value) > col.type.length:
                        if col_name not in violations:
                            violations[col_name] = {
                                'max_length': col.type.length,
                                'violations': []
                            }
                        # 记录超长值（去重）
                        violation_info = {
                            'value': value,
                            'actual_length': len(value),
                            'max_length': col.type.length
                        }
                        if violation_info not in violations[col_name]['violations']:
                            violations[col_name]['violations'].append(violation_info)
        
        return violations
    
    def bulk_upsert(self, model_class: Type[Any], records: List[Dict[str, Any]], 
                   conflict_keys: Optional[List[str]] = None) -> int:
        """
        批量 Upsert 记录（存在则更新，不存在则插入）
        
        Args:
            model_class: SQLAlchemy 模型类
            records: 记录字典列表
            conflict_keys: 冲突检测的字段列表，如果为 None 则使用主键
        
        Returns:
            处理的记录数
        """
        # 检查字段长度违规
        violations = self._check_field_lengths(model_class, records)
        if violations:
            print("\n" + "=" * 80)
            print("[错误] 发现字段长度超限，无法插入数据！")
            print("=" * 80)
            for col_name, info in violations.items():
                print(f"\n字段: {col_name}")
                print(f"  数据库定义的最大长度: {info['max_length']}")
                print(f"  发现 {len(info['violations'])} 个超长值:")
                for i, violation in enumerate(info['violations'][:10], 1):  # 只显示前10个
                    print(f"    {i}. 值: '{violation['value']}' (实际长度: {violation['actual_length']}, 超出: {violation['actual_length'] - violation['max_length']})")
                if len(info['violations']) > 10:
                    print(f"    ... 还有 {len(info['violations']) - 10} 个超长值未显示")
                # 找出最大实际长度
                max_actual_length = max(v['actual_length'] for v in info['violations'])
                print(f"  建议: 将字段长度从 {info['max_length']} 修改为至少 {max_actual_length}")
            print("\n" + "=" * 80)
            print("请修改数据表结构后重试！")
            raise ValueError(f"字段长度超限，请修改表结构。详情见上方输出。")
        
        # 只保留模型中存在的字段，避免传入无效字段导致 ORM 报错
        valid_columns = {col.name for col in model_class.__table__.columns}
        filtered_records: List[Dict[str, Any]] = []
        for record in records:
            filtered_records.append({k: v for k, v in record.items() if k in valid_columns})

        session = self.get_session()
        try:
            if conflict_keys is None:
                conflict_keys = [col.name for col in model_class.__table__.primary_key.columns]
            
            processed_count = 0
            
            for record in filtered_records:
                # 构建查询条件
                filters = {key: record[key] for key in conflict_keys if key in record}
                
                # 在当前 session 中查询是否存在（重要：必须在同一个 session 中）
                query = session.query(model_class)
                for key, value in filters.items():
                    query = query.filter(getattr(model_class, key) == value)
                existing = query.first()
                
                if existing:
                    # 更新现有记录
                    update_dict = {key: value for key, value in record.items() 
                                 if key not in conflict_keys}
                    if update_dict:
                        for key, value in update_dict.items():
                            setattr(existing, key, value)
                        processed_count += 1
                else:
                    # 创建新记录
                    instance = model_class(**record)
                    session.add(instance)
                    processed_count += 1
            
            session.commit()
            return processed_count
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def _has_unique_constraint(self, model_class: Type[Any], conflict_keys: List[str]) -> bool:
        """
        检查表中是否存在指定字段的唯一约束或唯一索引
        
        Args:
            model_class: SQLAlchemy 模型类
            conflict_keys: 要检查的字段列表
        
        Returns:
            是否存在唯一约束
        """
        inspector = inspect(self.engine)
        table_name = model_class.__table__.name
        
        # 检查唯一约束
        unique_constraints = inspector.get_unique_constraints(table_name)
        for constraint in unique_constraints:
            if set(constraint['column_names']) == set(conflict_keys):
                return True
        
        # 检查唯一索引
        indexes = inspector.get_indexes(table_name)
        for index in indexes:
            if index.get('unique', False) and set(index['column_names']) == set(conflict_keys):
                return True
        
        # 检查主键（主键也是唯一约束）
        pk_constraint = inspector.get_pk_constraint(table_name)
        if pk_constraint and set(pk_constraint['constrained_columns']) == set(conflict_keys):
            return True
        
        return False
    
    def bulk_upsert_postgresql(
        self,
        model_class: Type[Any],
        records: List[Dict[str, Any]],
        conflict_keys: Optional[List[str]] = None,
        fallback_on_error: bool = True,
        skip_length_check: bool = False,
        chunk_size: Optional[int] = DEFAULT_BULK_UPSERT_CHUNK_SIZE,
        update_on_conflict: bool = True,
        update_columns: Optional[List[str]] = None,
    ) -> int:
        """
        使用 PostgreSQL 的 ON CONFLICT 语法进行批量 Upsert（性能更好）

        Args:
            model_class: SQLAlchemy 模型类
            records: 记录字典列表
            conflict_keys: 冲突检测的字段列表，如果为 None 则使用主键
            fallback_on_error: 如果 PostgreSQL 方法失败，是否自动回退到通用方法
            skip_length_check: 为 True 时跳过字段长度校验，适用于上游已校验的可信数据，可减少 CPU/内存
            chunk_size: 按该条数分批 execute（仍一次 commit）；默认
                DEFAULT_BULK_UPSERT_CHUNK_SIZE（10000）。传 None 表示不分批。

        Returns:
            处理的记录数

        Raises:
            Exception: 如果所有方法都失败，抛出最后一个异常
        """
        if not records:
            return 0
        
        # 如果调用方未显式指定 conflict_keys，则尝试自动推断：
        # 1. 优先使用“唯一索引/唯一约束”（当且仅当恰好找到 1 个候选）；
        # 2. 否则退回到主键列。
        if conflict_keys is None:
            table = model_class.__table__

            # 收集模型层声明的唯一索引 / 唯一约束列集合
            unique_key_candidates = []
            from sqlalchemy import Index, UniqueConstraint  # 延迟导入以避免循环

            table_args = getattr(model_class, "__table_args__", ())
            if not isinstance(table_args, tuple):
                table_args = (table_args,)

            for arg in table_args:
                if isinstance(arg, Index) and getattr(arg, "unique", False):
                    cols = [c.name if hasattr(c, "name") else str(c) for c in arg.columns]
                    unique_key_candidates.append(cols)
                elif isinstance(arg, UniqueConstraint):
                    cols = [c.name if hasattr(c, "name") else str(c) for c in arg.columns]
                    unique_key_candidates.append(cols)

            if len(unique_key_candidates) == 1:
                # 仅当模型上只声明了一个唯一索引/约束时，才自动采用它作为 upsert 冲突键
                conflict_keys = unique_key_candidates[0]
            else:
                # 否则退回到主键列
                conflict_keys = [col.name for col in table.primary_key.columns]
        
        # 检查是否存在唯一约束，如果没有则直接使用 bulk_upsert
        if not self._has_unique_constraint(model_class, conflict_keys):
            if fallback_on_error:
                # 没有唯一约束，直接使用 bulk_upsert 方法
                return self.bulk_upsert(model_class, records, conflict_keys)
            else:
                raise ValueError(
                    f"表 {model_class.__tablename__} 中不存在字段 {conflict_keys} 的唯一约束或唯一索引，"
                    "无法使用 ON CONFLICT 语法。请创建唯一约束或使用 fallback_on_error=True"
                )

        table = model_class.__table__
        
        # 构建 INSERT ... ON CONFLICT ... DO UPDATE 语句
        insert_stmt = postgresql.insert(table)

        if update_on_conflict:
            if update_columns is not None:
                allowed = frozenset(update_columns)
                update_dict = {
                    col.name: insert_stmt.excluded[col.name]
                    for col in table.columns
                    if col.name in allowed and col.name not in conflict_keys
                }
            else:
                update_dict = {
                    col.name: insert_stmt.excluded[col.name]
                    for col in table.columns
                    if col.name not in conflict_keys
                }
            upsert_stmt = insert_stmt.on_conflict_do_update(
                index_elements=conflict_keys,
                set_=update_dict,
            )
        else:
            upsert_stmt = insert_stmt.on_conflict_do_nothing(
                index_elements=conflict_keys,
            )

        if not skip_length_check:
            violations = self._check_field_lengths(model_class, records)
            if violations:
                print("\n" + "=" * 80)
                print("[错误] 发现字段长度超限，无法插入数据！")
                print("=" * 80)
                for col_name, info in violations.items():
                    print(f"\n字段: {col_name}")
                    print(f"  数据库定义的最大长度: {info['max_length']}")
                    print(f"  发现 {len(info['violations'])} 个超长值:")
                    for i, violation in enumerate(info['violations'][:10], 1):
                        print(f"    {i}. 值: '{violation['value']}' (实际长度: {violation['actual_length']}, 超出: {violation['actual_length'] - violation['max_length']})")
                    if len(info['violations']) > 10:
                        print(f"    ... 还有 {len(info['violations']) - 10} 个超长值未显示")
                    max_actual_length = max(v['actual_length'] for v in info['violations'])
                    print(f"  建议: 将字段长度从 {info['max_length']} 修改为至少 {max_actual_length}")
                print("\n" + "=" * 80)
                print("请修改数据表结构后重试！")
                raise ValueError(f"字段长度超限，请修改表结构。详情见上方输出。")

        # 预计算列信息，避免在循环中重复访问 table
        valid_columns = tuple(col.name for col in table.columns)
        pk_columns = frozenset(col.name for col in table.primary_key.columns)
        values = []
        for record in records:
            row = {}
            for col_name in valid_columns:
                if col_name in pk_columns and record.get(col_name) is None:
                    continue
                row[col_name] = record.get(col_name)
            values.append(row)

        session = self.get_session()
        try:
            affected = 0
            rowcount_ok = True
            if chunk_size and len(values) > chunk_size:
                for i in range(0, len(values), chunk_size):
                    chunk = values[i : i + chunk_size]
                    result = session.execute(upsert_stmt, chunk)
                    rc = result.rowcount
                    if rc is None or rc < 0:
                        rowcount_ok = False
                        break
                    affected += rc
            else:
                result = session.execute(upsert_stmt, values)
                rc = result.rowcount
                if rc is None or rc < 0:
                    rowcount_ok = False
                else:
                    affected = rc
            session.commit()
            # rowcount 不可用时（部分驱动 executemany 返回 -1）回退为提交条数
            return affected if rowcount_ok else len(records)
        except Exception as e:
            session.rollback()
            # 如果启用回退且是数据库相关错误，尝试使用通用方法
            if fallback_on_error:
                try:
                    # 回退到通用的 bulk_upsert 方法
                    return self.bulk_upsert(model_class, records, conflict_keys)
                except Exception as e2:
                    # 如果备用方法也失败，抛出最后一个异常
                    raise e2
            else:
                # 不启用回退，直接抛出异常
                raise e
        finally:
            session.close()
    
    # ========== 查询辅助方法 ==========
    
    def count(self, model_class: Type[Any], **filters) -> int:
        """
        统计记录数
        
        Args:
            model_class: SQLAlchemy 模型类
            **filters: 查询条件
        
        Returns:
            记录数
        """
        session = self.get_session()
        try:
            query = session.query(model_class)
            for key, value in filters.items():
                query = query.filter(getattr(model_class, key) == value)
            return query.count()
        finally:
            session.close()
    
    def exists(self, model_class: Type[Any], **filters) -> bool:
        """
        检查记录是否存在
        
        Args:
            model_class: SQLAlchemy 模型类
            **filters: 查询条件
        
        Returns:
            是否存在
        """
        return self.count(model_class, **filters) > 0


def sync_table(model_class: Type[Any], database_url: Optional[str] = None, 
               interactive: bool = True) -> bool:
    """
    同步表结构（创建或更新表）
    
    Args:
        model_class: SQLAlchemy 模型类
        database_url: 数据库连接 URL，如果为 None 则使用 settings 中的配置
        interactive: 是否交互式确认（需要用户输入 yes）
    
    Returns:
        是否成功执行了操作
    """
    
    if database_url is None:
        database_url = settings.postgresql_url
    
    engine = create_engine(database_url)
    inspector = inspect(engine)
    table_name = model_class.__tablename__
    
    try:
        # 检查表是否存在
        tables = inspector.get_table_names()
        table_exists = table_name in tables
        
        if not table_exists:
            # ========== 创建表模式 ==========
            print("=" * 60)
            print(f"检测到表 '{table_name}' 不存在，准备创建新表")
            print("=" * 60)
            
            # 显示表结构信息
            print(f"\n表名: {table_name}")
            print(f"\n字段列表 ({len(model_class.__table__.columns)} 个字段):")
            print("-" * 60)
            for col in model_class.__table__.columns:
                col_type = str(col.type)
                comment = col.comment if col.comment else "无注释"
                nullable = "可空" if col.nullable else "非空"
                primary_key = " [主键]" if col.primary_key else ""
                print(f"  - {col.name:20s} | {col_type:15s} | {nullable:4s} | {comment}{primary_key}")
            
            # 显示索引信息
            model_indexes = {}
            if hasattr(model_class, '__table_args__'):
                table_args = model_class.__table_args__
                if isinstance(table_args, tuple):
                    from sqlalchemy import Index
                    for arg in table_args:
                        if isinstance(arg, Index):
                            model_indexes[arg.name] = arg
            
            if model_indexes:
                print(f"\n索引列表 ({len(model_indexes)} 个索引):")
                print("-" * 60)
                for idx_name, idx in model_indexes.items():
                    columns = [col.name if hasattr(col, 'name') else str(col) for col in idx.columns]
                    unique_flag = " [唯一]" if idx.unique else ""
                    print(f"  - {idx_name:30s} | 字段: {', '.join(columns)}{unique_flag}")
            
            if interactive:
                # 等待用户确认
                print("\n" + "-" * 60)
                user_input = input("是否创建此表？(输入 yes 确认，其他任意键取消): ").strip().lower()
                
                if user_input != "yes":
                    print("[取消] 用户取消创建表操作")
                    return False
            
            print("\n正在创建表...")
            # 使用模型的 metadata 创建表
            model_class.__table__.metadata.create_all(engine)
            print(f"[成功] 表 '{table_name}' 创建成功！")
            
            # 验证创建结果（刷新 inspector 缓存）
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            if table_name in tables:
                columns = inspector.get_columns(table_name)
                print(f"[验证] 表包含 {len(columns)} 个字段")
            else:
                print(f"[警告] 表创建后验证失败")
            
            return True
        
        else:
            # ========== 更新表模式 ==========
            print("=" * 60)
            print(f"检测到表 '{table_name}' 已存在，准备检查更新")
            print("=" * 60)
            
            # 获取现有表的字段
            existing_columns = {col['name']: col for col in inspector.get_columns(table_name)}
            existing_column_names = set(existing_columns.keys())
            
            # 获取模型定义的字段
            model_columns = {col.name: col for col in model_class.__table__.columns}
            model_column_names = set(model_columns.keys())
            
            # 找出需要添加/删除的字段
            new_columns = model_column_names - existing_column_names
            removed_columns = existing_column_names - model_column_names
            
            # 使用 PostgreSQL dialect 的 type compiler，比对真实 SQL 类型字符串
            dialect = postgresql.dialect()
            type_compiler = dialect.type_compiler
            
            # 找出“字段存在但类型发生变化”的字段（例如字符串长度变化）
            modified_columns = {}
            for col_name in sorted(existing_column_names & model_column_names):
                existing_col = existing_columns[col_name]
                model_col = model_columns[col_name]
                existing_type = existing_col.get("type")
                model_type = model_col.type
                if existing_type is None or model_type is None:
                    continue
                try:
                    existing_sql = type_compiler.process(existing_type)
                    model_sql = type_compiler.process(model_type)
                except Exception:
                    # 回退到字符串对比，防止极端类型导致崩溃
                    existing_sql = str(existing_type)
                    model_sql = str(model_type)
                # 规范化后再比较，避免 FLOAT 与 DOUBLE PRECISION 等等价类型被误判为变化
                if _normalize_pg_type_for_compare(existing_sql) != _normalize_pg_type_for_compare(model_sql):
                    modified_columns[col_name] = {
                        "existing_type": existing_sql,
                        "model_type": model_type,  # 存类型对象，执行 ALTER 时需用 type_compiler.process(类型对象)
                    }
            
            if not new_columns and not removed_columns and not modified_columns:
                print(f"\n[信息] 表 '{table_name}' 字段已是最新，无需更新")
                print(f"  现有字段数: {len(existing_columns)}")
                print(f"  模型字段数: {len(model_columns)}")
                # 不要 return，继续检查索引
            else:
                # 先给出总体概览，具体明细在每一步操作前分别展示
                print(f"\n表名: {table_name}")
                print(f"  现有字段数: {len(existing_columns)}")
                print(f"  模型字段数: {len(model_columns)}")
                if new_columns:
                    print(f"  - 待新增字段: {len(new_columns)} 个")
                if removed_columns:
                    print(f"  - 待删除字段: {len(removed_columns)} 个")
                if modified_columns:
                    print(f"  - 待修改类型/长度字段: {len(modified_columns)} 个")
                
                # 处理添加字段
                if new_columns:
                    if interactive:
                        # 展示新增字段明细并等待用户确认
                        print(f"\n需要添加的新字段 ({len(new_columns)} 个):")
                        print("-" * 60)
                        for col_name in sorted(new_columns):
                            col = model_columns[col_name]
                            col_type = str(col.type)
                            comment = col.comment if col.comment else "无注释"
                            nullable = "可空" if col.nullable else "非空"
                            print(f"  + {col_name:20s} | {col_type:15s} | {nullable:4s} | {comment}")
                        
                        print("\n" + "-" * 60)
                        user_input = input("是否执行新增字段更新？(输入 yes 确认，其他任意键取消): ").strip().lower()
                        
                        if user_input != "yes":
                            print("[取消] 用户取消新增字段操作")
                        else:
                            print("\n正在添加新字段...")
                            with engine.begin() as conn:
                                for col_name in sorted(new_columns):
                                    col = model_columns[col_name]
                                    
                                    # 直接使用 SQLAlchemy 类型系统生成 PostgreSQL 类型字符串
                                    type_obj = col.type
                                    col_type_sql = type_compiler.process(type_obj)
                                    
                                    # 处理 NULL/NOT NULL
                                    nullable_clause = "" if col.nullable else " NOT NULL"
                                    
                                    comment = col.comment if col.comment else ""
                                    
                                    # 构建 ALTER TABLE 语句
                                    alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type_sql}{nullable_clause}'
                                    
                                    try:
                                        conn.execute(text(alter_sql))
                                        print(f"  [成功] 添加字段: {col_name} ({col_type_sql}{nullable_clause})")
                                        
                                        # 如果有注释，添加注释
                                        if comment:
                                            # 转义单引号
                                            escaped_comment = comment.replace("'", "''")
                                            comment_sql = f"COMMENT ON COLUMN \"{table_name}\".\"{col_name}\" IS '{escaped_comment}'"
                                            conn.execute(text(comment_sql))
                                            
                                    except Exception as e:
                                        print(f"  [错误] 添加字段 {col_name} 失败: {e}")
                                        print(f"  [调试] 生成的 SQL: {alter_sql}")
                                        raise
                            
                            print(f"\n[成功] 表 '{table_name}' 新字段添加完成！")
                    else:
                        # 非交互模式，直接执行
                        print("\n正在添加新字段...")
                        with engine.begin() as conn:
                            for col_name in sorted(new_columns):
                                col = model_columns[col_name]
                                type_obj = col.type
                                col_type_sql = type_compiler.process(type_obj)
                                nullable_clause = "" if col.nullable else " NOT NULL"
                                comment = col.comment if col.comment else ""
                                alter_sql = f'ALTER TABLE "{table_name}" ADD COLUMN "{col_name}" {col_type_sql}{nullable_clause}'
                                try:
                                    conn.execute(text(alter_sql))
                                    print(f"  [成功] 添加字段: {col_name} ({col_type_sql}{nullable_clause})")
                                    if comment:
                                        escaped_comment = comment.replace("'", "''")
                                        comment_sql = f"COMMENT ON COLUMN \"{table_name}\".\"{col_name}\" IS '{escaped_comment}'"
                                        conn.execute(text(comment_sql))
                                except Exception as e:
                                    print(f"  [错误] 添加字段 {col_name} 失败: {e}")
                                    print(f"  [调试] 生成的 SQL: {alter_sql}")
                                    raise
                        print(f"\n[成功] 表 '{table_name}' 新字段添加完成！")
                
                # 处理删除字段
                if removed_columns:
                    if interactive:
                        print(f"\n需要删除的字段 ({len(removed_columns)} 个):")
                        print("-" * 60)
                        for col_name in sorted(removed_columns):
                            col_info = existing_columns[col_name]
                            col_type = str(col_info.get('type', '未知类型'))
                            nullable = "可空" if col_info.get('nullable', True) else "非空"
                            is_pk = col_info.get('primary_key', False)
                            pk_info = " [主键]" if is_pk else ""
                            print(f"  - {col_name:20s} | {col_type:15s} | {nullable:4s}{pk_info}")
                        print("\n警告：删除字段会永久删除该字段的所有数据，此操作不可逆！")
                        
                        print("\n" + "-" * 60)
                        user_input = input("是否删除上述字段？(输入 yes 确认，其他任意键取消): ").strip().lower()
                        
                        if user_input != "yes":
                            print("[取消] 用户取消删除字段操作")
                        else:
                            print("\n正在删除字段...")
                            
                            with engine.begin() as conn:
                                for col_name in sorted(removed_columns):
                                    col_info = existing_columns[col_name]
                                    
                                    # 检查是否是主键
                                    if col_info.get('primary_key', False):
                                        print(f"  [跳过] 字段 {col_name} 是主键，无法删除")
                                        continue
                                    
                                    # 构建 DROP COLUMN 语句
                                    drop_sql = f'ALTER TABLE "{table_name}" DROP COLUMN "{col_name}"'
                                    
                                    try:
                                        conn.execute(text(drop_sql))
                                        print(f"  [成功] 删除字段: {col_name}")
                                    except Exception as e:
                                        print(f"  [错误] 删除字段 {col_name} 失败: {e}")
                                        print(f"  [调试] 生成的 SQL: {drop_sql}")
                                        # 如果是外键约束错误，提供更友好的提示
                                        if "constraint" in str(e).lower() or "foreign key" in str(e).lower():
                                            print(f"  [提示] 字段 {col_name} 可能被外键引用，请先删除相关约束")
                                        raise
                            
                            print(f"\n[成功] 表 '{table_name}' 字段删除完成！")
                    else:
                        print("\n正在删除字段...")
                        with engine.begin() as conn:
                            for col_name in sorted(removed_columns):
                                col_info = existing_columns[col_name]
                                if col_info.get('primary_key', False):
                                    print(f"  [跳过] 字段 {col_name} 是主键，无法删除")
                                    continue
                                drop_sql = f'ALTER TABLE "{table_name}" DROP COLUMN "{col_name}"'
                                try:
                                    conn.execute(text(drop_sql))
                                    print(f"  [成功] 删除字段: {col_name}")
                                except Exception as e:
                                    print(f"  [错误] 删除字段 {col_name} 失败: {e}")
                                    print(f"  [调试] 生成的 SQL: {drop_sql}")
                                    if "constraint" in str(e).lower() or "foreign key" in str(e).lower():
                                        print(f"  [提示] 字段 {col_name} 可能被外键引用，请先删除相关约束")
                                    raise
                        print(f"\n[成功] 表 '{table_name}' 字段删除完成！")
                
                # 处理字段类型/长度修改
                if modified_columns:
                    if interactive:
                        print(f"\n需要修改类型/长度的字段 ({len(modified_columns)} 个):")
                        print("-" * 60)
                        for col_name, info in modified_columns.items():
                            old_type = str(info["existing_type"])
                            new_type = type_compiler.process(info["model_type"])
                            print(f"  * {col_name:20s} | 现有类型: {old_type:15s} -> 新类型: {new_type:15s}")
                        print("\n说明：这里只修改字段的类型/长度（例如 VARCHAR(20) -> VARCHAR(100)），不自动处理 NULL/默认值等其他属性。")
                        
                        print("\n" + "-" * 60)
                        user_input = input("是否修改上述字段的类型/长度？(输入 yes 确认，其他任意键取消): ").strip().lower()
                        
                        if user_input != "yes":
                            print("[取消] 用户取消字段类型/长度修改操作")
                        else:
                            print("\n正在修改字段类型/长度...")
                            with engine.begin() as conn:
                                for col_name, info in modified_columns.items():
                                    model_type = info["model_type"]
                                    new_type_sql = type_compiler.process(model_type)
                                    alter_sql = f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" TYPE {new_type_sql}'
                                    try:
                                        conn.execute(text(alter_sql))
                                        print(f"  [成功] 修改字段: {col_name} -> {new_type_sql}")
                                    except Exception as e:
                                        print(f"  [错误] 修改字段 {col_name} 类型失败: {e}")
                                        print(f"  [调试] 生成的 SQL: {alter_sql}")
                                        raise
                            print(f"\n[成功] 表 '{table_name}' 字段类型/长度修改完成！")
                    else:
                        print("\n正在修改字段类型/长度...")
                        with engine.begin() as conn:
                            for col_name, info in modified_columns.items():
                                model_type = info["model_type"]
                                new_type_sql = type_compiler.process(model_type)
                                alter_sql = f'ALTER TABLE "{table_name}" ALTER COLUMN "{col_name}" TYPE {new_type_sql}'
                                try:
                                    conn.execute(text(alter_sql))
                                    print(f"  [成功] 修改字段: {col_name} -> {new_type_sql}")
                                except Exception as e:
                                    print(f"  [错误] 修改字段 {col_name} 类型失败: {e}")
                                    print(f"  [调试] 生成的 SQL: {alter_sql}")
                                    raise
                        print(f"\n[成功] 表 '{table_name}' 字段类型/长度修改完成！")
                
                # 验证最终结果
                final_columns = {col['name']: col for col in inspector.get_columns(table_name)}
                print(f"[验证] 最终表包含 {len(final_columns)} 个字段")
        
        # ========== 同步索引 ==========
        # 获取数据库中现有的索引
        existing_indexes = {idx['name']: idx for idx in inspector.get_indexes(table_name)}
        existing_index_names = set(existing_indexes.keys())
        
        # 获取模型中定义的索引
        model_indexes = {}
        if hasattr(model_class, '__table_args__'):
            table_args = model_class.__table_args__
            if isinstance(table_args, tuple):
                from sqlalchemy import Index
                for arg in table_args:
                    if isinstance(arg, Index):
                        model_indexes[arg.name] = arg
        
        model_index_names = set(model_indexes.keys())
        
        # 同名但列或 unique 定义不同的索引（需先删后建）
        modified_indexes = set()
        for idx_name in (existing_index_names & model_index_names):
            if idx_name.endswith("_pkey"):
                continue
            ex = existing_indexes[idx_name]
            mo = model_indexes[idx_name]
            ex_cols = tuple(ex.get("column_names", []))
            mo_cols = tuple(
                col.name if hasattr(col, "name") else str(col) for col in mo.columns
            )
            ex_unique = ex.get("unique", False)
            mo_unique = getattr(mo, "unique", False)
            if ex_cols != mo_cols or ex_unique != mo_unique:
                modified_indexes.add(idx_name)
        
        # 需要删除的：模型中已删除的 + 定义变更的（先删后建）
        removed_indexes = (existing_index_names - model_index_names) | modified_indexes
        # 排除主键索引（通常以 _pkey 结尾）
        removed_indexes = {idx for idx in removed_indexes if not idx.endswith("_pkey")}
        # 需要创建的：模型中新增的 + 定义变更的（用新定义重建）
        new_indexes = (model_index_names - existing_index_names) | modified_indexes
        
        if new_indexes or removed_indexes:
            print("\n" + "=" * 60)
            print("索引同步")
            print("=" * 60)
            print(f"  现有索引数: {len(existing_indexes)}")
            print(f"  模型索引数: {len(model_indexes)}")
            
            if new_indexes:
                print(f"\n需要创建的新索引 ({len(new_indexes)} 个):")
                print("-" * 60)
                for idx_name in sorted(new_indexes):
                    idx = model_indexes[idx_name]
                    columns = [col.name if hasattr(col, 'name') else str(col) for col in idx.columns]
                    unique_flag = " [唯一]" if idx.unique else ""
                    suffix = " （定义已变更，将先删后建）" if idx_name in modified_indexes else ""
                    print(f"  + {idx_name:30s} | 字段: {', '.join(columns)}{unique_flag}{suffix}")
            
            if removed_indexes:
                print(f"\n需要删除的索引 ({len(removed_indexes)} 个):")
                print("-" * 60)
                for idx_name in sorted(removed_indexes):
                    idx_info = existing_indexes.get(idx_name, {})
                    columns = idx_info.get('column_names', [])
                    unique_flag = " [唯一]" if idx_info.get('unique', False) else ""
                    suffix = " （定义已变更，将先删后建）" if idx_name in modified_indexes else ""
                    print(f"  - {idx_name:30s} | 字段: {', '.join(columns)}{unique_flag}{suffix}")
            
            # 先处理删除索引
            if removed_indexes:
                if interactive:
                    print("\n" + "-" * 60)
                    user_input = input("是否删除上述索引？(输入 yes 确认，其他任意键跳过): ").strip().lower()
                    
                    if user_input == "yes":
                        print("\n正在删除索引...")
                        for idx_name in sorted(removed_indexes):
                            drop_idx_sql = f'DROP INDEX IF EXISTS "{idx_name}"'
                            try:
                                with engine.begin() as conn:
                                    conn.execute(text(drop_idx_sql))
                                print(f"  [成功] 删除索引: {idx_name}")
                            except Exception as e:
                                print(f"  [错误] 删除索引 {idx_name} 失败: {e}")
                        print(f"\n[成功] 索引删除完成！")
                    else:
                        print("[跳过] 用户跳过删除索引操作")
            
            if new_indexes:
                if interactive:
                    print("\n" + "-" * 60)
                    user_input = input("是否创建新索引？(输入 yes 确认，其他任意键取消): ").strip().lower()
                    
                    if user_input != "yes":
                        print("[取消] 用户取消创建索引操作")
                        return True  # 字段已更新成功，只是索引未创建
                
                print("\n正在创建索引...")
                success_count = 0
                fail_count = 0
                
                for idx_name in sorted(new_indexes):
                    idx = model_indexes[idx_name]
                    columns = [col.name if hasattr(col, 'name') else str(col) for col in idx.columns]
                    
                    # 构建 CREATE INDEX 语句
                    unique_clause = "UNIQUE " if idx.unique else ""
                    columns_sql = ', '.join([f'"{col}"' for col in columns])
                    create_idx_sql = f'CREATE {unique_clause}INDEX "{idx_name}" ON "{table_name}" ({columns_sql})'
                    
                    # 每个索引使用独立事务，避免一个失败导致全部回滚
                    try:
                        with engine.begin() as conn:
                            conn.execute(text(create_idx_sql))
                        print(f"  [成功] 创建索引: {idx_name} ({columns_sql})")
                        success_count += 1
                    except Exception as e:
                        if "already exists" in str(e).lower():
                            print(f"  [跳过] 索引 {idx_name} 已存在")
                        else:
                            print(f"  [错误] 创建索引 {idx_name} 失败: {e}")
                            print(f"  [调试] 生成的 SQL: {create_idx_sql}")
                            fail_count += 1
                
                if fail_count > 0:
                    print(f"\n[警告] 索引同步部分完成：成功 {success_count} 个，失败 {fail_count} 个")
                else:
                    print(f"\n[成功] 索引同步完成！创建了 {success_count} 个索引")
                
                # 刷新 inspector 缓存并验证索引
                inspector = inspect(engine)
                final_indexes = inspector.get_indexes(table_name)
                print(f"[验证] 最终表包含 {len(final_indexes)} 个索引")
        else:
            if model_indexes:
                print(f"\n[信息] 索引已是最新，无需更新")
                print(f"  现有索引数: {len(existing_indexes)}")
                print(f"  模型索引数: {len(model_indexes)}")
        
        return True
    
    except OperationalError as e:
        print(f"[错误] 数据库连接错误: {e}")
        raise
    except Exception as e:
        print(f"[错误] 操作失败: {e}")
        raise
    finally:
        engine.dispose()


# 创建全局数据库实例（可选）
db = Database()
