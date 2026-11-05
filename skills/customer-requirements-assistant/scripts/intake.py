"""Create an immutable text snapshot with stable, locally resolvable segment IDs."""
import copy
import hashlib
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
from common import MAX_FILE_BYTES, MAX_SOURCE_CHARS, MAX_TOTAL_CHARS, MAX_FILES, safe_text

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def docx_segments(path):
    with zipfile.ZipFile(path) as z:
        if sum(i.file_size for i in z.infolist()) > 30 * 1024 * 1024:
            raise ValueError('DOCX 解压体积超过 30 MiB。')
        raw = z.read('word/document.xml')
    if b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('不支持带 DTD 的文档。')
    body = ET.fromstring(raw).find(W + 'body')
    if body is None:
        raise ValueError('DOCX 缺少正文。')
    result = []
    def para_text(p):
        return ''.join(n.text or '' if n.tag == W+'t' else '\t' if n.tag == W+'tab' else '\n'
                       for n in p.iter() if n.tag in (W+'t', W+'tab', W+'br'))
    for index, child in enumerate(body, 1):
        if child.tag == W + 'p':
            result.append((f'正文块{index}段落', para_text(child)))
        elif child.tag == W + 'tbl':
            for ri, row in enumerate(child.findall(W+'tr'), 1):
                for ci, cell in enumerate(row.findall(W+'tc'), 1):
                    value = '\n'.join(para_text(p) for p in cell.iter(W+'p'))
                    result.append((f'正文块{index}表格行{ri}列{ci}', value))
    return result, ['仅提取正文段落与表格；页眉页脚、批注、文本框、图片及修订显示语义未纳入，请人工检查。']


def extract(path):
    ext = path.suffix.lower()
    if ext in ('.txt', '.md'):
        raw = path.read_bytes()
        try:
            text = raw.decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                text = raw.decode('gb18030')
            except UnicodeDecodeError as e:
                raise ValueError('文本编码无法识别，请另存为 UTF-8。') from e
        if '\x00' in text:
            raise ValueError('文本包含 NUL 字节，请另存为 UTF-8 纯文本。')
        return [(f'行{i}', t) for i,t in enumerate(text.splitlines(),1)], []
    if ext == '.docx':
        return docx_segments(path)
    if ext == '.pdf':
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise ValueError('缺少可选依赖 pypdf；请由宿主读取或先转为带页码的文本。') from e
        reader = PdfReader(str(path))
        if reader.is_encrypted:
            raise ValueError('不读取加密 PDF，请提供解密副本或纯文本。')
        if len(reader.pages) > 100:
            raise ValueError('PDF 超过 100 页，请分批处理。')
        segments, warnings = [], []
        for i,page in enumerate(reader.pages,1):
            text = page.extract_text() or ''
            if not text.strip():
                warnings.append(f'第{i}页无可提取文本，可能为扫描页；本次未读取该页。')
            else:
                segments.append((f'第{i}页', text))
        warnings.append('PDF 按文本层提取，阅读顺序及表格结构需人工复核。')
        return segments, warnings
    raise ValueError(f'不支持 {ext or "无扩展名"}；支持 TXT、MD、DOCX、带文本层的 PDF。')


def ingest(paths, previous=None):
    if not paths:
        raise ValueError('至少提供一个明确授权的资料文件。')
    if len(paths) > MAX_FILES:
        raise ValueError('每批最多 20 个文件。')
    bundle = copy.deepcopy(previous) if previous else {'schema_version': '1.0', 'sources': []}
    if not isinstance(bundle,dict) or not isinstance(bundle.get('sources'),list):
        raise ValueError('旧来源索引格式错误。')
    if len(bundle['sources']) + len(paths) > 40:
        raise ValueError('累计来源最多 40 个，请新建批次并保留旧批次。')
    total = sum(len(s['text']) for src in bundle['sources'] for s in src.get('segments',[]))
    seen = {(s.get('filename'),s.get('sha256')) for s in bundle['sources'] if s.get('status') == 'ok'}
    for path in paths:
        path = Path(path)
        source = {'id': f'S{len(bundle["sources"])+1:03d}', 'filename': path.name,
                  'sha256': None, 'status': 'error', 'warnings': [], 'segments': []}
        try:
            if not path.is_file():
                raise ValueError('文件不存在或不是普通文件。')
            if path.stat().st_size > MAX_FILE_BYTES:
                raise ValueError('单文件超过 5 MiB，请分批处理。')
            source['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            if (path.name, source['sha256']) in seen:
                continue
            parts, warnings = extract(path)
            source['warnings'] = warnings
            for i,(locator, text) in enumerate(parts,1):
                clean = safe_text(text).strip()
                if clean:
                    source['segments'].append({'id': f'{source["id"]}:{i:04d}', 'locator': locator, 'text': clean})
            chars = sum(len(s['text']) for s in source['segments'])
            if not chars:
                raise ValueError('没有可读取文本；扫描件需人工转写或另行 OCR。')
            if chars > MAX_SOURCE_CHARS or total + chars > MAX_TOTAL_CHARS:
                raise ValueError('超过单来源 20 万字或整批 50 万字上限，请拆分，未截断读取。')
            total += chars
            source['status'] = 'ok'
            seen.add((path.name,source['sha256']))
        except Exception as exc:
            source['segments'] = []
            source['error'] = f'{type(exc).__name__}: {exc}'
        bundle['sources'].append(source)
    return bundle
