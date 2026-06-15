import re
from html.parser import HTMLParser


class _TableCell:
    __slots__ = ("text", "colspan", "rowspan")

    def __init__(self, text="", colspan=1, rowspan=1):
        self.text = text.strip() if text else ""
        self.colspan = max(1, colspan)
        self.rowspan = max(1, rowspan)


class _TableGridBuilder(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current_row = None
        self.current_cell = None
        self.cell_text = ""
        self.in_cell = False
        self.col_count = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tr":
            self.current_row = []
            self.col_count = 0
        elif tag in ("td", "th"):
            self.in_cell = True
            self.cell_text = ""
            colspan = 1
            rowspan = 1
            try:
                colspan = int(attrs.get("colspan", 1))
            except (TypeError, ValueError):
                pass
            try:
                rowspan = int(attrs.get("rowspan", 1))
            except (TypeError, ValueError):
                pass
            self.current_cell = _TableCell(colspan=colspan, rowspan=rowspan)

    def handle_data(self, data):
        if self.in_cell:
            self.cell_text += data

    def handle_endtag(self, tag):
        if tag in ("td", "th"):
            self.in_cell = False
            if self.current_cell is not None:
                self.current_cell.text = self.cell_text.strip()
                self.current_row.append(self.current_cell)
                self.col_count += self.current_cell.colspan
                self.current_cell = None
        elif tag == "tr":
            if self.current_row is not None:
                self.rows.append(self.current_row)
            self.current_row = None


def _build_grid(rows):
    col_count = 0
    for row in rows:
        row_cols = sum(c.colspan for c in row)
        if row_cols > col_count:
            col_count = row_cols

    grid = [[None for _ in range(col_count)] for _ in range(len(rows))]

    for r, row in enumerate(rows):
        c = 0
        for cell in row:
            while c < col_count and grid[r][c] is not None:
                c += 1
            if c >= col_count:
                break
            for dr in range(cell.rowspan):
                for dc in range(cell.colspan):
                    rr = r + dr
                    cc = c + dc
                    if rr < len(grid) and cc < col_count:
                        grid[rr][cc] = cell.text
            c += cell.colspan

    return grid


def _is_numeric(text):
    if not text:
        return False
    cleaned = re.sub(r'[,\s%℃¥$€£元万亿千百十兆\-\+（）()]', '', text)
    try:
        float(cleaned)
        return True
    except (TypeError, ValueError):
        return False


def _is_empty_cell(text):
    return not text or not text.strip()


def _min_text_len(grid, row_idx):
    if not grid[row_idx]:
        return 0
    max_len = 0
    for cell in grid[row_idx]:
        if cell and not _is_empty_cell(cell) and not _is_numeric(cell):
            cleaned = _clean_val(cell)
            if len(cleaned) > max_len:
                max_len = len(cleaned)
    return max_len


def _detect_header_rows(grid):
    if not grid or not grid[0]:
        return set()

    header_indices = set()
    seen_numeric_row = False
    for r, row in enumerate(grid):
        if not row:
            header_indices.add(r)
            continue

        cell_count = sum(1 for cell in row if cell is not None and not _is_empty_cell(cell))
        if cell_count == 0:
            continue

        numeric_count = 0
        non_numeric_count = 0
        for cell in row:
            if cell and not _is_empty_cell(cell):
                if _is_numeric(cell):
                    numeric_count += 1
                else:
                    non_numeric_count += 1

        total = numeric_count + non_numeric_count
        has_any_numeric = numeric_count > 0

        if total > 0 and non_numeric_count > numeric_count:
            if not seen_numeric_row:
                header_indices.add(r)
            elif has_any_numeric:
                header_indices.add(r)
            elif _min_text_len(grid, r) > 2:
                header_indices.add(r)
        else:
            if has_any_numeric:
                seen_numeric_row = True

    return header_indices


def _nearest_header_labels(grid, data_row, header_indices, col_count):
    if not header_indices:
        return [""] * col_count
    recent_indices = []
    for hr in sorted(header_indices, reverse=True):
        if hr >= data_row:
            continue
        if not recent_indices:
            recent_indices.append(hr)
            continue
        prev = recent_indices[-1]
        if hr == prev - 1:
            recent_indices.append(hr)
        else:
            break
    recent_indices.reverse()
    labels = []
    for c in range(col_count):
        parts = []
        for hr in recent_indices:
            if c < len(grid[hr]) and grid[hr][c] and not _is_empty_cell(grid[hr][c]):
                parts.append(_clean_val(grid[hr][c]))
        labels.append(" ".join(parts).strip())
    return labels


def _detect_row_label_col(grid, header_indices):
    if not grid:
        return -1

    for r, row in enumerate(grid):
        if r in header_indices:
            continue
        if not row:
            continue
        for c, cell in enumerate(row):
            if cell and not _is_empty_cell(cell) and not _is_numeric(cell):
                return c
        break
    return -1


def _clean_val(text):
    if not text:
        return ""
    t = text.strip()
    t = re.sub(r'\s+', '', t)
    return t


def grid_to_es_tab2text(grid):
    if not grid or not grid[0]:
        return ""

    header_indices = _detect_header_rows(grid)
    label_col = _detect_row_label_col(grid, header_indices)
    col_count = len(grid[0])

    lines = []
    seq = 0
    for r in range(len(grid)):
        if r in header_indices:
            continue
        row = grid[r]
        if not row:
            continue

        row_label = ""
        if label_col >= 0 and label_col < len(row) and row[label_col] is not None:
            row_label = _clean_val(row[label_col])

        if not row_label:
            continue

        col_headers = _nearest_header_labels(grid, r, header_indices, col_count)
        cell_texts = []
        for c in range(col_count):
            if c == label_col:
                continue
            val = row[c] if c < len(row) and row[c] is not None else ""
            val = _clean_val(val)
            if not val:
                continue
            col_header = col_headers[c] if c < len(col_headers) else ""
            if col_header:
                cell_texts.append(f"{col_header} - {row_label} - {val}")
            else:
                cell_texts.append(f"{row_label} - {val}")

        if cell_texts:
            seq += 1
            lines.append(f"{seq}. " + "，".join(cell_texts))

    return "\n".join(lines)


def grid_to_llm_tab2text(grid):
    if not grid or not grid[0]:
        return ""

    header_indices = _detect_header_rows(grid)
    label_col = _detect_row_label_col(grid, header_indices)
    col_count = len(grid[0])

    lines = []
    for r in range(len(grid)):
        if r in header_indices:
            continue
        row = grid[r]
        if not row:
            continue

        row_label = ""
        if label_col >= 0 and label_col < len(row) and row[label_col] is not None:
            row_label = _clean_val(row[label_col])

        if not row_label:
            continue

        col_headers = _nearest_header_labels(grid, r, header_indices, col_count)
        value_parts = []
        for c in range(col_count):
            if c == label_col:
                continue
            val = row[c] if c < len(row) and row[c] is not None else ""
            val = _clean_val(val)
            if not val:
                continue
            col_header = col_headers[c] if c < len(col_headers) else ""
            if col_header:
                value_parts.append(f"{col_header} {val}")
            else:
                value_parts.append(val)

        if value_parts:
            lines.append(f"{row_label}：" + "，".join(value_parts))

    return "\n".join(lines)


def convert_html_table(html_text):
    if not html_text or not isinstance(html_text, str):
        return "", ""

    lower = html_text.lower()
    if "<table" not in lower:
        return "", ""

    parser = _TableGridBuilder()
    try:
        parser.feed(html_text)
    except Exception:
        return "", ""

    if not parser.rows:
        return "", ""

    grid = _build_grid(parser.rows)
    if not grid or not grid[0]:
        return "", ""

    es_text = grid_to_es_tab2text(grid)
    llm_text = grid_to_llm_tab2text(grid)

    return es_text, llm_text
