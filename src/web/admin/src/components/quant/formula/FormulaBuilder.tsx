import { useEffect, useMemo, useRef, useState, type DragEvent, type KeyboardEvent, type MouseEvent } from 'react';
import {
  Alert,
  Button,
  InputNumber,
  Modal,
  Space,
  Tooltip,
  Typography,
  message,
} from 'antd';
import { getFeatureList } from '@/services/quant';
import type { FeatureMetaItem } from '@/types/quant';
import {
  FORMULA_FUNCS,
  type FormulaToken,
  buildLayoutLines,
  findMatchingParen,
  insertTokens,
  isParen,
  newTokenId,
  parseFormula,
  prettyPrintTokens,
  removeParenPairWithContent,
  serializeTokens,
  unwrapParenPair,
  validateTokens,
} from './formulaTokens';
import styles from './FormulaBuilder.module.css';

const { Text } = Typography;

const OP_BUTTONS: { value: string; label: string; title: string }[] = [
  { value: '+', label: '+', title: '加' },
  { value: '-', label: '−', title: '减' },
  { value: '*', label: '×', title: '乘' },
  { value: '/', label: '÷', title: '除' },
  { value: '()', label: '( )', title: '插入一对括号，光标在中间' },
  { value: ',', label: ',', title: '参数分隔（其后换行）' },
];

type Props = {
  value?: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
};

type DragPayload =
  | { source: 'palette'; tokens: FormulaToken[] }
  | { source: 'chip'; index: number };

type ParenDeleteState = {
  index: number;
  match: number;
  left: number;
  right: number;
};

function chipClass(t: FormulaToken): string {
  if (t.kind === 'feature') return `${styles.chip} ${styles.chipFeature}`;
  if (t.kind === 'func') return `${styles.chip} ${styles.chipFunc}`;
  if (t.kind === 'number') return `${styles.chip} ${styles.chipNumber}`;
  if (isParen(t)) return `${styles.chip} ${styles.chipParen}`;
  return `${styles.chip} ${styles.chipOp}`;
}

function chipLabel(t: FormulaToken): string {
  if (t.kind === 'feature' || t.kind === 'func') return t.name;
  if (t.kind === 'number') return t.value;
  if (t.value === '*') return '×';
  if (t.value === '/') return '÷';
  if (t.value === '-') return '−';
  return t.value;
}

export default function FormulaBuilder({ value, onChange, disabled }: Props) {
  const [tokens, setTokens] = useState<FormulaToken[]>(() => parseFormula(value));
  const [cursor, setCursor] = useState(() => parseFormula(value).length);
  const [features, setFeatures] = useState<FeatureMetaItem[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const [funcModal, setFuncModal] = useState<{
    name: string;
    arity: number;
    hint: string;
  } | null>(null);
  const [windowN, setWindowN] = useState<number>(20);
  const [parenDelete, setParenDelete] = useState<ParenDeleteState | null>(null);
  const [hoverParen, setHoverParen] = useState<number | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setTokens((prev) => {
      if (serializeTokens(prev) === (value || '')) {
        return prev;
      }
      const parsed = parseFormula(value);
      setCursor(parsed.length);
      return parsed;
    });
  }, [value]);

  useEffect(() => {
    void getFeatureList({ page: 1, page_size: 200, enabled: 1 })
      .then((res) => setFeatures(res.items))
      .catch(() => message.error('加载特征列表失败'));
  }, []);

  const validation = useMemo(() => validateTokens(tokens), [tokens]);
  const layout = useMemo(() => buildLayoutLines(tokens), [tokens]);
  const pretty = useMemo(() => prettyPrintTokens(tokens), [tokens]);
  const matchHighlight = useMemo(() => {
    const idx = hoverParen;
    if (idx == null) return new Set<number>();
    const m = findMatchingParen(tokens, idx);
    if (m == null) return new Set([idx]);
    return new Set([idx, m]);
  }, [hoverParen, tokens]);

  const emit = (next: FormulaToken[], nextCursor: number) => {
    setTokens(next);
    setCursor(nextCursor);
    onChange?.(serializeTokens(next));
  };

  const insert = (incoming: FormulaToken[], cursorAfter?: number) => {
    if (disabled) return;
    const r = insertTokens(tokens, cursor, incoming);
    emit(r.tokens, cursorAfter ?? r.cursor);
  };

  const insertFeature = (name: string) => {
    insert([{ id: newTokenId(), kind: 'feature', name }]);
  };

  const insertOp = (op: string) => {
    if (op === '()') {
      insert(
        [
          { id: newTokenId(), kind: 'op', value: '(' },
          { id: newTokenId(), kind: 'op', value: ')' },
        ],
        cursor + 1,
      );
      return;
    }
    insert([{ id: newTokenId(), kind: 'op', value: op }]);
  };

  const insertNumber = (digit: string) => {
    if (disabled) return;
    const prev = tokens[cursor - 1];
    if (prev?.kind === 'number') {
      const merged: FormulaToken = { ...prev, value: prev.value + digit };
      const next = [...tokens.slice(0, cursor - 1), merged, ...tokens.slice(cursor)];
      emit(next, cursor);
      return;
    }
    insert([{ id: newTokenId(), kind: 'number', value: digit }]);
  };

  const openFunc = (name: string, arity: number, hint: string) => {
    if (
      arity >= 2 &&
      (name === 'DELAY' ||
        name === 'DELTA' ||
        name === 'SUM' ||
        name === 'MEAN' ||
        name === 'STD')
    ) {
      setWindowN(name === 'STD' || name === 'MEAN' || name === 'SUM' ? 20 : 1);
      setFuncModal({ name, arity, hint });
      return;
    }
    // NAME(  ) 成对，光标在括号内
    insert(
      [
        { id: newTokenId(), kind: 'func', name },
        { id: newTokenId(), kind: 'op', value: '(' },
        { id: newTokenId(), kind: 'op', value: ')' },
      ],
      cursor + 2,
    );
  };

  const confirmFunc = () => {
    if (!funcModal || disabled) return;
    const { name } = funcModal;
    const incoming: FormulaToken[] = [
      { id: newTokenId(), kind: 'func', name },
      { id: newTokenId(), kind: 'op', value: '(' },
      { id: newTokenId(), kind: 'op', value: ',' },
      { id: newTokenId(), kind: 'number', value: String(windowN) },
      { id: newTokenId(), kind: 'op', value: ')' },
    ];
    const r = insertTokens(tokens, cursor, incoming);
    emit(r.tokens, cursor + 2);
    setFuncModal(null);
  };

  const requestDeleteAt = (deleteIndex: number) => {
    const t = tokens[deleteIndex];
    if (isParen(t)) {
      const match = findMatchingParen(tokens, deleteIndex);
      if (match == null) {
        // 孤立括号：直接删
        const next = [
          ...tokens.slice(0, deleteIndex),
          ...tokens.slice(deleteIndex + 1),
        ];
        emit(next, Math.min(deleteIndex, next.length));
        message.warning('已删除未配对的括号');
        return;
      }
      const left = Math.min(deleteIndex, match);
      const right = Math.max(deleteIndex, match);
      setParenDelete({ index: deleteIndex, match, left, right });
      return;
    }
    const next = [...tokens.slice(0, deleteIndex), ...tokens.slice(deleteIndex + 1)];
    emit(next, Math.min(deleteIndex, next.length));
  };

  const onBackspace = () => {
    if (disabled || cursor <= 0) return;
    requestDeleteAt(cursor - 1);
  };

  const applyParenDelete = (mode: 'unwrap' | 'purge') => {
    if (!parenDelete) return;
    const { left, right } = parenDelete;
    if (mode === 'unwrap') {
      const next = unwrapParenPair(tokens, left, right);
      emit(next, Math.min(left, next.length));
    } else {
      const next = removeParenPairWithContent(tokens, left, right);
      emit(next, Math.min(left, next.length));
    }
    setParenDelete(null);
  };

  const onClear = () => {
    if (disabled) return;
    emit([], 0);
  };

  const onCanvasClick = () => {
    if (disabled) return;
    canvasRef.current?.focus();
    setCursor(tokens.length);
  };

  const onChipClick = (index: number, e: MouseEvent) => {
    e.stopPropagation();
    if (disabled) return;
    canvasRef.current?.focus();
    setCursor(index + 1);
  };

  const onChipDoubleClick = (index: number, e: MouseEvent) => {
    e.stopPropagation();
    if (disabled) return;
    if (isParen(tokens[index])) {
      requestDeleteAt(index);
    }
  };

  const onCanvasKeyDown = (e: KeyboardEvent) => {
    if (disabled) return;
    if (e.key === 'Backspace') {
      e.preventDefault();
      onBackspace();
      return;
    }
    if (e.key === 'Delete') {
      e.preventDefault();
      if (cursor < tokens.length) requestDeleteAt(cursor);
      return;
    }
    if (e.key === 'ArrowLeft') {
      e.preventDefault();
      setCursor((c) => Math.max(0, c - 1));
      return;
    }
    if (e.key === 'ArrowRight') {
      e.preventDefault();
      setCursor((c) => Math.min(tokens.length, c + 1));
      return;
    }
    if (e.key === '(') {
      e.preventDefault();
      insertOp('()');
    }
  };

  const onPaletteDragStart = (e: DragEvent, incoming: FormulaToken[]) => {
    e.dataTransfer.setData(
      'application/x-formula',
      JSON.stringify({ source: 'palette', tokens: incoming } satisfies DragPayload),
    );
    e.dataTransfer.effectAllowed = 'copy';
  };

  const onChipDragStart = (e: DragEvent, index: number) => {
    e.dataTransfer.setData(
      'application/x-formula',
      JSON.stringify({ source: 'chip', index } satisfies DragPayload),
    );
    e.dataTransfer.effectAllowed = 'move';
  };

  const onCanvasDragOver = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const onCanvasDragLeave = () => setDragOver(false);

  const onCanvasDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    try {
      const raw = e.dataTransfer.getData('application/x-formula');
      if (!raw) return;
      const payload = JSON.parse(raw) as DragPayload;
      if (payload.source === 'palette') {
        const refreshed = payload.tokens.map((t) => ({ ...t, id: newTokenId() }));
        // 拖入左括号时自动配对
        if (
          refreshed.length === 1 &&
          refreshed[0].kind === 'op' &&
          refreshed[0].value === '('
        ) {
          insert(
            [
              { id: newTokenId(), kind: 'op', value: '(' },
              { id: newTokenId(), kind: 'op', value: ')' },
            ],
            cursor + 1,
          );
          return;
        }
        insert(refreshed);
        return;
      }
      if (payload.source === 'chip') {
        const from = payload.index;
        if (from < 0 || from >= tokens.length) return;
        const moving = tokens[from];
        const without = tokens.filter((_, i) => i !== from);
        let to = cursor;
        if (from < cursor) to = Math.max(0, cursor - 1);
        const next = [...without.slice(0, to), moving, ...without.slice(to)];
        emit(next, to + 1);
      }
    } catch {
      /* ignore */
    }
  };

  const lineStartSet = useMemo(() => {
    const s = new Set<number>();
    for (const line of layout) {
      if (line.tokenIndices.length) s.add(line.tokenIndices[0]);
    }
    return s;
  }, [layout]);

  /** 换行后光标只画在新行行首，避免上一行末尾重复。 */
  const showCursorBefore = (ti: number) =>
    cursor === ti && (ti === 0 || lineStartSet.has(ti));
  const showCursorAfter = (ti: number) =>
    cursor === ti + 1 && !lineStartSet.has(ti + 1);

  return (
    <div className={styles.wrap}>
      <div>
        <div className={styles.sectionTitle}>
          公式画布（最内层同行 · 连续 ) 换行回退 · 悬停配对）
        </div>
        <div
          ref={canvasRef}
          className={`${styles.canvas} ${dragOver ? styles.canvasDragOver : ''}`}
          tabIndex={0}
          role="textbox"
          aria-label="公式画布"
          onClick={onCanvasClick}
          onKeyDown={onCanvasKeyDown}
          onDragOver={onCanvasDragOver}
          onDragLeave={onCanvasDragLeave}
          onDrop={onCanvasDrop}
        >
          {tokens.length === 0 ? (
            <span className={styles.emptyHint}>从下方点选特征与运算符，或拖拽到此处</span>
          ) : (
            layout.map((line, lineIdx) => (
              <div
                key={`line-${lineIdx}`}
                className={`${styles.line} ${line.depth > 0 ? styles.lineNested : ''}`}
                style={{ paddingLeft: line.depth * 20 }}
              >
                {line.tokenIndices.map((ti) => (
                  <span key={tokens[ti].id} style={{ display: 'inline-flex', alignItems: 'center' }}>
                    {showCursorBefore(ti) ? (
                      <span className={styles.cursor} key={`c-b-${ti}`} />
                    ) : null}
                    <span
                      className={`${chipClass(tokens[ti])} ${
                        cursor === ti + 1 && !lineStartSet.has(ti + 1)
                          ? styles.chipActive
                          : ''
                      } ${matchHighlight.has(ti) ? styles.chipMatch : ''}`}
                      draggable={!disabled}
                      onDragStart={(e) => onChipDragStart(e, ti)}
                      onClick={(e) => onChipClick(ti, e)}
                      onDoubleClick={(e) => onChipDoubleClick(ti, e)}
                      onMouseEnter={() => {
                        if (isParen(tokens[ti])) setHoverParen(ti);
                      }}
                      onMouseLeave={() => setHoverParen(null)}
                      title={
                        isParen(tokens[ti])
                          ? '括号：悬停配对高亮；双击或退格删除时会询问'
                          : tokens[ti].kind === 'feature'
                            ? '特征'
                            : tokens[ti].kind === 'func'
                              ? '函数'
                              : undefined
                      }
                    >
                      {chipLabel(tokens[ti])}
                    </span>
                    {showCursorAfter(ti) ? (
                      <span className={styles.cursor} key={`c-a-${ti}`} />
                    ) : null}
                  </span>
                ))}
              </div>
            ))
          )}
          {tokens.length > 0 && cursor === tokens.length ? (
            <div className={styles.line}>
              <span className={styles.cursor} />
            </div>
          ) : null}
        </div>
      </div>

      {!validation.ok || validation.warnings.length > 0 ? (
        <Alert
          type={validation.ok ? 'warning' : 'error'}
          showIcon
          message={validation.ok ? '公式可保存，但有警告' : '公式未通过合法性校验'}
          description={
            <ul style={{ margin: 0, paddingLeft: 18 }}>
              {validation.errors.map((e) => (
                <li key={e} className={styles.validErr}>
                  {e}
                </li>
              ))}
              {validation.warnings.map((w) => (
                <li key={w} className={styles.validWarn}>
                  {w}
                </li>
              ))}
            </ul>
          }
        />
      ) : tokens.length > 0 ? (
        <Text className={styles.validOk}>括号配对正常</Text>
      ) : null}

      <div>
        <div className={styles.sectionTitle}>运算与编辑</div>
        <Space wrap size={[6, 6]}>
          {OP_BUTTONS.map((op) => (
            <Tooltip key={op.value} title={op.title}>
              <Button
                className={styles.paletteBtn}
                type={op.value === '()' ? 'primary' : 'default'}
                ghost={op.value === '()'}
                disabled={disabled}
                draggable={!disabled && op.value !== '()'}
                onDragStart={(e) => {
                  if (op.value === '()') return;
                  onPaletteDragStart(e, [{ id: newTokenId(), kind: 'op', value: op.value }]);
                }}
                onClick={() => insertOp(op.value)}
              >
                {op.label}
              </Button>
            </Tooltip>
          ))}
          <Button disabled={disabled} onClick={onBackspace}>
            退格
          </Button>
          <Button disabled={disabled} danger onClick={onClear}>
            清空
          </Button>
        </Space>
      </div>

      <div>
        <div className={styles.sectionTitle}>常用函数（自动带成对括号）</div>
        <div className={styles.palette}>
          {FORMULA_FUNCS.map((f) => (
            <Tooltip key={f.name} title={f.hint}>
              <Button
                size="small"
                className={styles.paletteBtn}
                disabled={disabled}
                onClick={() => openFunc(f.name, f.arity, f.hint)}
              >
                {f.label}
              </Button>
            </Tooltip>
          ))}
        </div>
      </div>

      <div>
        <div className={styles.sectionTitle}>数字</div>
        <Space wrap size={[6, 6]}>
          {['7', '8', '9', '4', '5', '6', '1', '2', '3', '0', '.'].map((d) => (
            <Button
              key={d}
              className={styles.paletteBtn}
              disabled={disabled}
              onClick={() => insertNumber(d)}
            >
              {d}
            </Button>
          ))}
        </Space>
      </div>

      <div>
        <div className={styles.sectionTitle}>
          特征（点击插入）· 已启用 {features.length} 个
        </div>
        <div className={styles.palette}>
          {features.map((f) => (
            <Tooltip
              key={f.feature_name}
              title={f.display_name || f.transform || f.feature_kind}
            >
              <Button
                size="small"
                type="primary"
                ghost
                className={styles.paletteBtn}
                disabled={disabled}
                draggable={!disabled}
                onDragStart={(e) =>
                  onPaletteDragStart(e, [
                    { id: newTokenId(), kind: 'feature', name: f.feature_name },
                  ])
                }
                onClick={() => insertFeature(f.feature_name)}
              >
                {f.feature_name}
                {f.display_name ? (
                  <Text type="secondary" style={{ marginLeft: 4, fontSize: 11 }}>
                    {f.display_name}
                  </Text>
                ) : null}
              </Button>
            </Tooltip>
          ))}
          {features.length === 0 ? (
            <Text type="secondary">暂无特征，请先在「特征管理」初始化种子</Text>
          ) : null}
        </div>
      </div>

      <div>
        <div className={styles.sectionTitle}>结构化预览 / 紧凑保存串</div>
        <div className={styles.preview}>{pretty || '（空）'}</div>
        <div className={styles.preview} style={{ marginTop: 6, opacity: 0.75 }}>
          保存：{serializeTokens(tokens) || '（空）'}
        </div>
      </div>

      <Modal
        title={funcModal ? `插入 ${funcModal.name}` : '插入函数'}
        open={!!funcModal}
        onCancel={() => setFuncModal(null)}
        onOk={confirmFunc}
        okText="插入"
        destroyOnHidden
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text type="secondary">
            {funcModal?.hint}。将插入成对括号，光标停在括号内以便点选特征。
          </Text>
          <div>
            <Text>窗口 / 滞后天数 N</Text>
            <InputNumber
              min={1}
              max={500}
              value={windowN}
              onChange={(v) => setWindowN(Number(v) || 1)}
              style={{ width: '100%', marginTop: 8 }}
            />
          </div>
        </Space>
      </Modal>

      <Modal
        title="删除括号"
        open={!!parenDelete}
        onCancel={() => setParenDelete(null)}
        footer={[
          <Button key="cancel" onClick={() => setParenDelete(null)}>
            取消
          </Button>,
          <Button key="unwrap" type="primary" onClick={() => applyParenDelete('unwrap')}>
            删括号，保留内部
          </Button>,
          <Button key="purge" danger onClick={() => applyParenDelete('purge')}>
            删括号及内部全部
          </Button>,
        ]}
        destroyOnHidden
      >
        <Space direction="vertical">
          <Text>检测到配对括号。请选择删除方式：</Text>
          <Text type="secondary">
            · <b>删括号，保留内部</b>：去掉这一对 ( )，中间内容留在原位
            <br />· <b>删括号及内部全部</b>：这一对括号与其中所有内容一起删除
          </Text>
          {parenDelete ? (
            <div className={styles.preview}>
              {prettyPrintTokens(tokens.slice(parenDelete.left, parenDelete.right + 1))}
            </div>
          ) : null}
        </Space>
      </Modal>
    </div>
  );
}
