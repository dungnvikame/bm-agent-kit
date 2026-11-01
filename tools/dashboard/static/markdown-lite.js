/* Minimal, safe Markdown -> HTML for the kit's own documents (headings, lists, tables, code, bold, inline code, links).
   Everything is HTML-escaped first, so document content can never inject markup. */
const Markdown = {
  inline(s) {
    s = Dash.esc(s);
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    s = s.replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
    s = s.replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');
    return s;
  },
  render(text) {
    const lines = (text || '').replace(/\r/g, '').split('\n');
    const out = [];
    let i = 0;
    const isRow = l => /^\s*\|/.test(l);
    while (i < lines.length) {
      const line = lines[i];
      if (/^\s*```/.test(line)) {
        const buf = []; i++;
        while (i < lines.length && !/^\s*```/.test(lines[i])) buf.push(lines[i++]);
        i++; out.push('<pre>' + Dash.esc(buf.join('\n')) + '</pre>'); continue;
      }
      const h = line.match(/^(#{1,6})\s+(.*)$/);
      if (h) { const n = Math.min(h[1].length + 1, 4); out.push(`<h${n}>${Markdown.inline(h[2])}</h${n}>`); i++; continue; }
      if (isRow(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{2,}/.test(lines[i + 1])) {
        const cells = l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => Markdown.inline(c.trim()));
        let html = '<table><thead><tr>' + cells(line).map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
        i += 2;
        while (i < lines.length && isRow(lines[i])) html += '<tr>' + cells(lines[i++]).map(c => `<td>${c}</td>`).join('') + '</tr>';
        out.push(html + '</tbody></table>'); continue;
      }
      if (/^\s*([-*]|\d+\.)\s+/.test(line)) {
        const ordered = /^\s*\d+\./.test(line);
        let html = ordered ? '<ol>' : '<ul>';
        while (i < lines.length && /^\s*([-*]|\d+\.)\s+/.test(lines[i])) {
          let item = lines[i].replace(/^\s*([-*]|\d+\.)\s+/, ''); i++;
          while (i < lines.length && /^\s{2,}\S/.test(lines[i]) && !/^\s*([-*]|\d+\.)\s+/.test(lines[i])) item += ' ' + lines[i++].trim();
          html += `<li>${Markdown.inline(item)}</li>`;
        }
        out.push(html + (ordered ? '</ol>' : '</ul>')); continue;
      }
      if (/^\s*>\s?/.test(line)) { out.push(`<blockquote>${Markdown.inline(line.replace(/^\s*>\s?/, ''))}</blockquote>`); i++; continue; }
      if (/^\s*---+\s*$/.test(line)) { out.push('<hr>'); i++; continue; }
      if (line.trim() === '') { i++; continue; }
      const buf = [];
      while (i < lines.length && lines[i].trim() !== '' && !/^(#{1,6}\s|\s*```|\s*([-*]|\d+\.)\s|\s*\||\s*>)/.test(lines[i])) buf.push(lines[i++]);
      if (buf.length) out.push(`<p>${Markdown.inline(buf.join(' '))}</p>`); else i++;
    }
    return out.join('\n');
  },
  /* Strip a YAML front-matter block (SKILL.md files start with one) and return {meta, body}. */
  splitFrontMatter(text) {
    const m = (text || '').match(/^---\n([\s\S]*?)\n---\n?([\s\S]*)$/);
    if (!m) return { meta: {}, body: text || '' };
    const meta = {};
    for (const l of m[1].split('\n')) { const kv = l.match(/^(\w+):\s*(.*)$/); if (kv) meta[kv[1]] = kv[2]; }
    return { meta, body: m[2] };
  },
  node(text) { return Dash.el('div', { class: 'md', html: Markdown.render(text) }); },
};
