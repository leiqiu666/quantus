/** 公式 token 模型与序列化 / 解析 / 校验 / 缩进布局。 */

export type FormulaToken =
  | { id: string; kind: 'feature'; name: string }
  | { id: string; kind: 'op'; value: string }
  | { id: string; kind: 'func'; name: string }
  | { id: string; kind: 'number'; value: string };

let _seq = 0;
export function newTokenId(): string {
  _seq += 1;
  return `t${_seq}_${Date.now().toString(36)}`;
}

const OPS = new Set(['+', '-', '*', '/', '(', ')', ',']);

export const FORMULA_FUNCS: { name: string; label: string; hint: string; arity: number }[] = [
  { name: 'DELAY', label: 'DELAY', hint: '滞后 N 日', arity: 2 },
  { name: 'DELTA', label: 'DELTA', hint: '差分 N 日', arity: 2 },
  { name: 'SUM', label: 'SUM', hint: '滚动求和', arity: 2 },
  { name: 'MEAN', label: 'MEAN', hint: '滚动均值', arity: 2 },
  { name: 'STD', label: 'STD', hint: '滚动标准差', arity: 2 },
  { name: 'ABS', label: 'ABS', hint: '绝对值', arity: 1 },
  { name: 'MAX', label: 'MAX', hint: '取大', arity: 2 },
  { name: 'MIN', label: 'MIN', hint: '取小', arity: 2 },
  { name: 'RANK', label: 'RANK', hint: '截面排名', arity: 1 },
  { name: 'LOG', label: 'LOG', hint: '自然对数', arity: 1 },
  { name: 'SIGN', label: 'SIGN', hint: '符号函数', arity: 1 },
];

const FUNC_NAMES = new Set(FORMULA_FUNCS.map((f) => f.name));

export function isParen(t: FormulaToken | undefined, which?: '(' | ')'): boolean {
  if (!t || t.kind !== 'op') return false;
  if (which) return t.value === which;
  return t.value === '(' || t.value === ')';
}

export function serializeTokens(tokens: FormulaToken[]): string {
  const parts: string[] = [];
  for (const t of tokens) {
    if (t.kind === 'feature' || t.kind === 'func') parts.push(t.name);
    else if (t.kind === 'number') parts.push(t.value);
    else parts.push(t.value);
  }
  let out = '';
  for (let i = 0; i < parts.length; i++) {
    const p = parts[i];
    const prev = parts[i - 1];
    if (i > 0) {
      const needSpace = /[A-Za-z0-9_.]$/.test(prev) && /^[A-Za-z0-9_.]/.test(p);
      out += needSpace ? ` ${p}` : p;
    } else {
      out += p;
    }
  }
  return out;
}

/** 类 JSON：括号换行 + 缩进（保存仍用紧凑 serialize）。 */
export function prettyPrintTokens(tokens: FormulaToken[], indentSize = 2): string {
  if (!tokens.length) return '';
  const lines = buildLayoutLines(tokens);
  return lines
    .map((line) => {
      const pad = ' '.repeat(line.depth * indentSize);
      const body = line.tokenIndices
        .map((i) => {
          const t = tokens[i];
          if (t.kind === 'feature' || t.kind === 'func') return t.name;
          if (t.kind === 'number') return t.value;
          return t.value;
        })
        .join(' ');
      return pad + body;
    })
    .join('\n');
}

export function parseFormula(raw: string | null | undefined): FormulaToken[] {
  const s = (raw || '').trim();
  if (!s) return [];
  const text = s.includes('｜[') ? s.split('｜[', 1)[0].trim() : s;
  const tokens: FormulaToken[] = [];
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (/\s/.test(ch)) {
      i += 1;
      continue;
    }
    if (OPS.has(ch)) {
      tokens.push({ id: newTokenId(), kind: 'op', value: ch });
      i += 1;
      continue;
    }
    if (/[0-9.]/.test(ch)) {
      let j = i + 1;
      while (j < text.length && /[0-9.]/.test(text[j])) j += 1;
      tokens.push({ id: newTokenId(), kind: 'number', value: text.slice(i, j) });
      i = j;
      continue;
    }
    if (/[A-Za-z_]/.test(ch)) {
      let j = i + 1;
      while (j < text.length && /[A-Za-z0-9_]/.test(text[j])) j += 1;
      const name = text.slice(i, j).toUpperCase();
      if (FUNC_NAMES.has(name)) {
        tokens.push({ id: newTokenId(), kind: 'func', name });
      } else {
        tokens.push({ id: newTokenId(), kind: 'feature', name });
      }
      i = j;
      continue;
    }
    i += 1;
  }
  return tokens;
}

export function insertTokens(
  tokens: FormulaToken[],
  cursor: number,
  incoming: FormulaToken[],
): { tokens: FormulaToken[]; cursor: number } {
  const next = [...tokens.slice(0, cursor), ...incoming, ...tokens.slice(cursor)];
  return { tokens: next, cursor: cursor + incoming.length };
}

export function removeTokenAt(
  tokens: FormulaToken[],
  cursor: number,
): { tokens: FormulaToken[]; cursor: number } {
  if (cursor <= 0 || tokens.length === 0) {
    return { tokens, cursor: 0 };
  }
  const next = [...tokens.slice(0, cursor - 1), ...tokens.slice(cursor)];
  return { tokens: next, cursor: cursor - 1 };
}

/** 找与 index 处括号匹配的另一侧；找不到返回 null。 */
export function findMatchingParen(
  tokens: FormulaToken[],
  index: number,
): number | null {
  const t = tokens[index];
  if (!isParen(t)) return null;
  if (t.value === '(') {
    let depth = 0;
    for (let i = index; i < tokens.length; i++) {
      if (isParen(tokens[i], '(')) depth += 1;
      else if (isParen(tokens[i], ')')) {
        depth -= 1;
        if (depth === 0) return i;
      }
    }
    return null;
  }
  let depth = 0;
  for (let i = index; i >= 0; i--) {
    if (isParen(tokens[i], ')')) depth += 1;
    else if (isParen(tokens[i], '(')) {
      depth -= 1;
      if (depth === 0) return i;
    }
  }
  return null;
}

/** 删除一对括号，保留内部。 */
export function unwrapParenPair(
  tokens: FormulaToken[],
  left: number,
  right: number,
): FormulaToken[] {
  if (left < 0 || right <= left) return tokens;
  return [...tokens.slice(0, left), ...tokens.slice(left + 1, right), ...tokens.slice(right + 1)];
}

/** 删除一对括号及内部全部。 */
export function removeParenPairWithContent(
  tokens: FormulaToken[],
  left: number,
  right: number,
): FormulaToken[] {
  if (left < 0 || right < left) return tokens;
  return [...tokens.slice(0, left), ...tokens.slice(right + 1)];
}

export type LayoutLine = { depth: number; tokenIndices: number[] };

/** 该左括号内部是否还有嵌套括号（无嵌套 = 最内层，应整段不换行）。 */
function isLeafParenPair(tokens: FormulaToken[], left: number): boolean {
  const right = findMatchingParen(tokens, left);
  if (right == null) return false;
  for (let i = left + 1; i < right; i++) {
    if (isParen(tokens[i], '(')) return false;
  }
  return true;
}

/**
 * 类 JSON / 代码缩进布局：
 * - 最内层 `(…)`（内部无括号）整段同行，跟在函数名或运算后
 * - 外层 `(` 后换行并加深缩进
 * - `,` 后换行；但逗号后为数字时不换行（`, 20`）
 * - `)` 默认贴在当前行末尾，其后不换行（`) + x`、`) , 20`）
 * - 若 `)` 后仍是 `)`（连续闭合），则换行并按层回退缩进，避免 `)))` 挤在一行
 */
export function buildLayoutLines(tokens: FormulaToken[]): LayoutLine[] {
  if (!tokens.length) return [];
  const lines: LayoutLine[] = [];
  let depth = 0;
  let lineDepth = 0;
  let current: number[] = [];

  const flush = () => {
    if (current.length === 0) return;
    lines.push({ depth: lineDepth, tokenIndices: [...current] });
    current = [];
    lineDepth = depth;
  };

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (isParen(t, '(')) {
      if (isLeafParenPair(tokens, i)) {
        const right = findMatchingParen(tokens, i)!;
        for (let j = i; j <= right; j++) current.push(j);
        i = right;
        continue;
      }
      current.push(i);
      flush();
      depth += 1;
      lineDepth = depth;
      continue;
    }
    if (isParen(t, ')')) {
      const nextIsClose = isParen(tokens[i + 1], ')');
      if (nextIsClose) {
        // 连续右括号：先结束内容行，再让本层 ) 单独一行并回退缩进
        flush();
        depth = Math.max(0, depth - 1);
        lineDepth = depth;
        current.push(i);
        flush();
      } else {
        current.push(i);
        depth = Math.max(0, depth - 1);
        // 单独一个 ) 占行时（内容已在上一行），缩进跟闭合层对齐
        if (current.length === 1) {
          lineDepth = depth;
        }
      }
      continue;
    }
    if (t.kind === 'op' && t.value === ',') {
      current.push(i);
      const next = tokens[i + 1];
      if (!(next && next.kind === 'number')) {
        flush();
      }
      continue;
    }
    current.push(i);
  }
  flush();
  return lines;
}

export type FormulaValidation = {
  ok: boolean;
  errors: string[];
  warnings: string[];
};

export function validateTokens(tokens: FormulaToken[]): FormulaValidation {
  const errors: string[] = [];
  const warnings: string[] = [];

  let depth = 0;
  let maxDepth = 0;
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (isParen(t, '(')) {
      depth += 1;
      maxDepth = Math.max(maxDepth, depth);
      const next = tokens[i + 1];
      if (isParen(next, ')')) {
        warnings.push(`位置 ${i + 1}：空括号 ()`);
      }
    } else if (isParen(t, ')')) {
      depth -= 1;
      if (depth < 0) {
        errors.push(`多余的右括号 )（约第 ${i + 1} 个符号）`);
        depth = 0;
      }
    }
  }
  if (depth > 0) {
    errors.push(`缺少 ${depth} 个右括号 )`);
  }

  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (t.kind === 'func') {
      const next = tokens[i + 1];
      if (!isParen(next, '(')) {
        errors.push(`函数 ${t.name} 后应紧跟左括号 (`);
      }
    }
  }

  const binaryOps = new Set(['+', '-', '*', '/']);
  for (let i = 0; i < tokens.length; i++) {
    const t = tokens[i];
    if (t.kind === 'op' && binaryOps.has(t.value)) {
      const prev = tokens[i - 1];
      const next = tokens[i + 1];
      const prevOk =
        prev &&
        (prev.kind === 'feature' ||
          prev.kind === 'number' ||
          prev.kind === 'func' ||
          isParen(prev, ')'));
      const nextOk =
        next &&
        (next.kind === 'feature' ||
          next.kind === 'number' ||
          next.kind === 'func' ||
          isParen(next, '(') ||
          (next.kind === 'op' && next.value === '-')); // 一元负号
      if (!prevOk && !(t.value === '-' && nextOk)) {
        warnings.push(`运算符 ${t.value} 左侧可能缺少操作数`);
      }
      if (!nextOk) {
        warnings.push(`运算符 ${t.value} 右侧可能缺少操作数`);
      }
    }
  }

  if (tokens.length && maxDepth === 0 && tokens.some((t) => t.kind === 'func')) {
    // fine
  }

  return { ok: errors.length === 0, errors, warnings };
}
