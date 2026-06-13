from pathlib import Path

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


SOURCE_PDF = Path(
    r"C:\Users\Administrator\Documents\xwechat_files\broncin_80df\msg\file\2026-06\AI生图商业合作方案-Toni.aisa.pdf"
)
OUTPUT_PDF = SOURCE_PDF.with_name("AI生图商业合作方案-Toni.aisa-对内补充版.pdf")
SUPPLEMENT_PDF = Path(r"D:\Toni\code\得物生图\docs\AI生图商业合作方案-商业成本利润测算补充页.pdf")


def register_fonts() -> str:
    font_path = Path(r"C:\Windows\Fonts\msyh.ttc")
    bold_path = Path(r"C:\Windows\Fonts\msyhbd.ttc")
    pdfmetrics.registerFont(TTFont("MicrosoftYaHei", str(font_path)))
    pdfmetrics.registerFont(TTFont("MicrosoftYaHei-Bold", str(bold_path)))
    return "MicrosoftYaHei"


def make_styles(font_name: str) -> dict:
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="CNTitle",
            parent=styles["Title"],
            fontName="MicrosoftYaHei-Bold",
            fontSize=18,
            leading=24,
            spaceAfter=10,
            textColor=colors.HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNHeading",
            parent=styles["Heading2"],
            fontName="MicrosoftYaHei-Bold",
            fontSize=12,
            leading=16,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor("#111827"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNBody",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=8.8,
            leading=13,
            spaceAfter=5,
            textColor=colors.HexColor("#1f2937"),
        )
    )
    styles.add(
        ParagraphStyle(
            name="CNNote",
            parent=styles["BodyText"],
            fontName=font_name,
            fontSize=8,
            leading=11,
            spaceAfter=4,
            textColor=colors.HexColor("#4b5563"),
        )
    )
    return styles


def p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>"), style)


def table(data, widths=None, font_size=7.6):
    converted = [[Paragraph(str(cell), ParagraphStyle("Cell", fontName="MicrosoftYaHei", fontSize=font_size, leading=10)) for cell in row] for row in data]
    t = Table(converted, colWidths=widths, repeatRows=1, hAlign="LEFT")
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef2ff")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                ("FONTNAME", (0, 0), (-1, 0), "MicrosoftYaHei-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#d1d5db")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return t


def build_supplement() -> None:
    font = register_fonts()
    styles = make_styles(font)
    doc = SimpleDocTemplate(
        str(SUPPLEMENT_PDF),
        pagesize=A4,
        rightMargin=1.25 * cm,
        leftMargin=1.25 * cm,
        topMargin=1.25 * cm,
        bottomMargin=1.2 * cm,
        title="商业成本与利润分配测算补充页",
    )
    story = []

    story.append(p("对内补充页：商业成本与利润分配测算", styles["CNTitle"]))
    story.append(
        p(
            "本补充页直接追加在原对外版 BP 之后，仅供内部讨论。原 PDF 不做任何修改；本文件用于确认三方团队在 P0/P1 阶段的成本、保底量、卖家压力和利润分配。",
            styles["CNBody"],
        )
    )

    story.append(p("1. 基础口径", styles["CNHeading"]))
    story.append(
        table(
            [
                ["项目", "中位数假设"],
                ["一组图", "6 张"],
                ["标准售价", "5 元/张"],
                ["标准组价", "30 元/组"],
                ["P0 直接成本中位数", "收入的 31%，净利润池 69%"],
                ["P1 直接成本中位数", "收入的 48%，净利润池 52%"],
            ],
            [4.2 * cm, 12.0 * cm],
        )
    )
    story.append(
        p(
            "净利润池 = 客户实收收入 - 第三方工具/API/GPU - 支付税费/存储/下载整理 - 返修退款/质检预留 - 必要人工复核或后期成本。",
            styles["CNNote"],
        )
    )

    story.append(p("2. 月收入与净利润池", styles["CNHeading"]))
    story.append(
        table(
            [
                ["月组数", "月收入", "P0 净利润池", "P1 净利润池"],
                ["1000 组", "3 万", "2.07 万", "1.56 万"],
                ["2000 组", "6 万", "4.14 万", "3.12 万"],
                ["3000 组", "9 万", "6.21 万", "4.68 万"],
                ["5000 组", "15 万", "10.35 万", "7.80 万"],
                ["15000 组", "45 万", "31.05 万", "23.40 万"],
            ],
            [3.4 * cm, 4.0 * cm, 4.4 * cm, 4.4 * cm],
        )
    )

    story.append(p("3. 利润分配规则", styles["CNHeading"]))
    story.append(
        table(
            [
                ["阶段/条件", "技术方", "代运营", "后期"],
                ["P0 无保底或低于 2000 组/月", "55%", "35%", "10%"],
                ["P0 保底 2000 组/月，承担回款售后", "50%", "45%", "5%"],
                ["P0 保底 3000 组/月以上，承担差额补足或预付", "45%", "50%", "5%"],
                ["P1 无保底或低于 2000 组/月", "50%", "35%", "15%"],
                ["P1 保底 2000-4999 组/月，承担回款售后", "45%", "45%", "10%"],
                ["P1 保底 5000 组/月以上，承担差额补足或预付", "40%", "50%", "10%"],
            ],
            [7.0 * cm, 3.0 * cm, 3.0 * cm, 3.0 * cm],
        )
    )
    story.append(
        p(
            "代运营上浮必须绑定真实保底：如果未达到保底量，仍按保底量结算技术底价，或由代运营方补足差额。代运营整体封顶 50%。",
            styles["CNNote"],
        )
    )

    story.append(PageBreak())
    story.append(p("4. P0 月利润分配", styles["CNHeading"]))
    story.append(
        table(
            [
                ["月组数", "技术方总额", "技术方内 30% 渠道费", "技术/IP/研发保留", "代运营", "后期"],
                ["1000 组", "1.14 万", "0.34 万", "0.80 万", "0.72 万", "0.21 万"],
                ["2000 组", "2.07 万", "0.62 万", "1.45 万", "1.86 万", "0.21 万"],
                ["3000 组", "2.79 万", "0.84 万", "1.96 万", "3.11 万", "0.31 万"],
                ["5000 组", "4.66 万", "1.40 万", "3.26 万", "5.18 万", "0.52 万"],
                ["15000 组", "13.97 万", "4.19 万", "9.78 万", "15.53 万", "1.55 万"],
            ],
            [2.4 * cm, 3.0 * cm, 3.6 * cm, 3.6 * cm, 2.8 * cm, 2.4 * cm],
        )
    )

    story.append(p("5. P1 月利润分配", styles["CNHeading"]))
    story.append(
        table(
            [
                ["月组数", "技术方总额", "技术方内 30% 渠道费", "技术/IP/研发保留", "代运营", "后期"],
                ["1000 组", "0.78 万", "0.23 万", "0.55 万", "0.55 万", "0.23 万"],
                ["2000 组", "1.40 万", "0.42 万", "0.98 万", "1.40 万", "0.31 万"],
                ["3000 组", "2.11 万", "0.63 万", "1.47 万", "2.11 万", "0.47 万"],
                ["5000 组", "3.12 万", "0.94 万", "2.18 万", "3.90 万", "0.78 万"],
                ["15000 组", "9.36 万", "2.81 万", "6.55 万", "11.70 万", "2.34 万"],
            ],
            [2.4 * cm, 3.0 * cm, 3.6 * cm, 3.6 * cm, 2.8 * cm, 2.4 * cm],
        )
    )

    story.append(p("6. 卖家数量压力", styles["CNHeading"]))
    story.append(
        table(
            [
                ["月组数", "全轻量卖家", "混合卖家池", "全标准卖家", "全活跃卖家"],
                ["1000 组", "100 家", "41 家", "34 家", "17 家"],
                ["2000 组", "200 家", "82 家", "67 家", "34 家"],
                ["3000 组", "300 家", "123 家", "100 家", "50 家"],
                ["5000 组", "500 家", "205 家", "167 家", "84 家"],
                ["15000 组", "1500 家", "613 家", "500 家", "250 家"],
            ],
            [3.0 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm, 3.2 * cm],
        )
    )
    story.append(
        p(
            "压力判断：2000 组/月作为第一次上浮点合理，需要约 82 个混合卖家或 34 个活跃卖家；5000 组/月才适合代运营在 P1 拿到 50% 封顶分成；15000 组/月才适合讨论 3 元/张大规模价格。",
            styles["CNBody"],
        )
    )

    story.append(p("7. 价格敏感性参考", styles["CNHeading"]))
    story.append(
        table(
            [
                ["3000 组/月价格", "月收入", "P0 净利润池", "P1 净利润池"],
                ["18 元/组，3 元/张", "5.4 万", "3.73 万", "2.81 万"],
                ["30 元/组，5 元/张", "9.0 万", "6.21 万", "4.68 万"],
                ["48 元/组，8 元/张", "14.4 万", "9.94 万", "7.49 万"],
            ],
            [5.2 * cm, 3.6 * cm, 3.8 * cm, 3.8 * cm],
        )
    )

    story.append(p("8. 内部结论", styles["CNHeading"]))
    story.append(
        p(
            "P0 无保底时按技术方 55%、代运营 35%、后期 10%；代运营保底 2000 组/月并承担销售、回款、客户维护、平台沟通和售后协调时，上浮到 45%；保底 3000 组/月以上且承担差额补足或预付时，P0 可封顶 50%。P1 无保底时按技术方 50%、代运营 35%、后期 15%；保底 2000-4999 组/月时技术方和代运营各 45%；保底 5000 组/月以上时代运营封顶 50%。",
            styles["CNBody"],
        )
    )
    story.append(
        p(
            "技术方比例较高的原因：技术方承担模型路线、工作流系统、provider 替换、质检规则、数据闭环和后续成本下降能力；P1/P2 的研发投入主要由技术方承担，且技术方份额中还需内部拿出 30% 作为渠道/BD/合作激励。",
            styles["CNBody"],
        )
    )

    doc.build(story)


def append_pdf() -> None:
    writer = PdfWriter()
    for path in [SOURCE_PDF, SUPPLEMENT_PDF]:
        reader = PdfReader(str(path))
        for page in reader.pages:
            writer.add_page(page)
    with OUTPUT_PDF.open("wb") as f:
        writer.write(f)


def main() -> None:
    if not SOURCE_PDF.exists():
        raise FileNotFoundError(SOURCE_PDF)
    build_supplement()
    append_pdf()
    print(OUTPUT_PDF)


if __name__ == "__main__":
    main()
