// Shared helpers for building DocuVerify project documents with docx-js
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, PageBreak, LevelFormat, ImageRun, TableOfContents,
  Header, Footer, PageNumber, VerticalAlign
} = require("docx");
const fs = require("fs");

const FONT = "Calibri";
const BLUE = "1F3864";
const GREY = "F2F2F2";

function run(text, opts = {}) {
  return new TextRun({ text, font: FONT, size: opts.size || 22, bold: opts.bold, italics: opts.italics, color: opts.color });
}

function p(text, opts = {}) {
  const runs = Array.isArray(text) ? text : [run(text, opts)];
  return new Paragraph({
    children: runs,
    alignment: opts.align || AlignmentType.JUSTIFIED,
    spacing: { after: opts.after ?? 120, line: opts.line ?? 300 },
    indent: opts.indent,
  });
}

function center(text, opts = {}) {
  return new Paragraph({
    children: [run(text, opts)],
    alignment: AlignmentType.CENTER,
    spacing: { after: opts.after ?? 120 },
  });
}

function h1(text) { return new Paragraph({ text, heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 160 } }); }
function h2(text) { return new Paragraph({ text, heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 120 } }); }
function h3(text) { return new Paragraph({ text, heading: HeadingLevel.HEADING_3, spacing: { before: 160, after: 80 } }); }

function bullets(items, ref = "bullets") {
  return items.map((t) => new Paragraph({
    children: Array.isArray(t) ? t : [run(t)],
    numbering: { reference: ref, level: 0 },
    spacing: { after: 80, line: 280 },
    alignment: AlignmentType.JUSTIFIED,
  }));
}

let _numCounter = 0;
function numbered(items, ref) {
  ref = ref || ("numbers" + (_numCounter++ % 12));
  return items.map((t) => new Paragraph({
    children: Array.isArray(t) ? t : [run(t)],
    numbering: { reference: ref, level: 0 },
    spacing: { after: 80, line: 280 },
    alignment: AlignmentType.JUSTIFIED,
  }));
}

function cell(text, width, opts = {}) {
  const lines = Array.isArray(text) ? text : [text];
  return new TableCell({
    width: { size: width, type: WidthType.DXA },
    shading: opts.header ? { type: ShadingType.CLEAR, fill: BLUE, color: "auto" } : (opts.fill ? { type: ShadingType.CLEAR, fill: opts.fill, color: "auto" } : undefined),
    verticalAlign: VerticalAlign.CENTER,
    margins: { top: 60, bottom: 60, left: 80, right: 80 },
    children: lines.map((l) => new Paragraph({
      children: [run(String(l), { size: opts.size || 19, bold: opts.header, color: opts.header ? "FFFFFF" : undefined })],
      alignment: opts.align || AlignmentType.LEFT,
      spacing: { after: 0, line: 260 },
    })),
  });
}

// rows: array of arrays; first row header. widths in DXA, must sum to total.
function table(rows, widths, opts = {}) {
  const total = widths.reduce((a, b) => a + b, 0);
  const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
  return new Table({
    width: { size: total, type: WidthType.DXA },
    columnWidths: widths,
    borders: { top: border, bottom: border, left: border, right: border, insideHorizontal: border, insideVertical: border },
    rows: rows.map((r, i) => new TableRow({
      tableHeader: i === 0,
      children: r.map((c, j) => cell(c, widths[j], { header: i === 0, fill: (i % 2 === 0 && i > 0) ? GREY : undefined, size: opts.size, align: opts.aligns ? opts.aligns[j] : undefined })),
    })),
  });
}

function caption(text) {
  return new Paragraph({ children: [run(text, { italics: true, size: 19 })], alignment: AlignmentType.CENTER, spacing: { before: 80, after: 200 } });
}

function image(path, width, height, cap) {
  const out = [new Paragraph({
    children: [new ImageRun({ type: "png", data: fs.readFileSync(path), transformation: { width, height } })],
    alignment: AlignmentType.CENTER, spacing: { before: 120, after: 60 },
  })];
  if (cap) out.push(caption(cap));
  return out;
}

function pageBreak() { return new Paragraph({ children: [new PageBreak()] }); }

function spacer(n = 1) { return Array.from({ length: n }, () => new Paragraph({ children: [run("")], spacing: { after: 120 } })); }

function buildDoc(sections, opts = {}) {
  return new Document({
    creator: opts.creator || "Bank IQ Project",
    title: opts.title || "Bank IQ",
    styles: {
      default: { document: { run: { font: FONT, size: 22 } } },
      paragraphStyles: [
        { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 30, bold: true, color: BLUE, font: FONT }, paragraph: { spacing: { before: 360, after: 160 }, outlineLevel: 0 } },
        { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 26, bold: true, color: BLUE, font: FONT }, paragraph: { spacing: { before: 240, after: 120 }, outlineLevel: 1 } },
        { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
          run: { size: 23, bold: true, color: "2E5496", font: FONT }, paragraph: { spacing: { before: 160, after: 80 }, outlineLevel: 2 } },
      ],
    },
    numbering: {
      config: [
        { reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
        ...Array.from({ length: 12 }, (_, i) => ({ reference: "numbers" + i, levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] })),
        { reference: "refs", levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "[%1]", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 720, hanging: 720 } } } }] },
      ],
    },
    sections: sections.map((s) => ({
      properties: { page: { margin: { top: 1440, bottom: 1440, left: 1440, right: 1296 } } },
      headers: { default: new Header({ children: [new Paragraph({ children: [run(opts.header || "Bank IQ – Regulatory Digital Twin with an ML Intelligence Layer", { size: 18, color: "666666" })], alignment: AlignmentType.RIGHT, border: { bottom: { style: BorderStyle.SINGLE, size: 4, color: "999999", space: 4 } } })] }) },
      footers: { default: new Footer({ children: [new Paragraph({ children: [new TextRun({ children: ["Page ", PageNumber.CURRENT], font: FONT, size: 18, color: "666666" })], alignment: AlignmentType.CENTER })] }) },
      children: s,
    })),
  });
}

async function save(doc, path) {
  const buf = await Packer.toBuffer(doc);
  fs.writeFileSync(path, buf);
  console.log("wrote", path);
}

module.exports = { run, p, center, h1, h2, h3, bullets, numbered, table, caption, image, pageBreak, spacer, buildDoc, save, TableOfContents, AlignmentType, Paragraph, TextRun };
