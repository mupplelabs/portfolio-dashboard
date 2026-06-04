import io
import re
import os
import tempfile
import pandas as pd
import plotly.express as px
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, XPreformatted, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_DIR = os.path.join(os.path.dirname(__file__), 'fonts')
HAS_DEJAVU = False
try:
    if os.path.exists(os.path.join(FONT_DIR, 'DejaVuSans.ttf')):
        pdfmetrics.registerFont(TTFont('DejaVuSans', os.path.join(FONT_DIR, 'DejaVuSans.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf')))
        pdfmetrics.registerFont(TTFont('DejaVuSansMono', os.path.join(FONT_DIR, 'DejaVuSansMono.ttf')))
        HAS_DEJAVU = True
except Exception as e:
    print("Warning: Could not register DejaVu fonts:", e)

HAS_FA = False
try:
    if os.path.exists(os.path.join(FONT_DIR, 'fa-solid-900.ttf')):
        pdfmetrics.registerFont(TTFont('FontAwesome', os.path.join(FONT_DIR, 'fa-solid-900.ttf')))
        HAS_FA = True
except Exception as e:
    print("Warning: Could not register FontAwesome:", e)

def clean_unsupported_chars(text):
    # Strip all characters outside the Basic Multilingual Plane (mostly emojis)
    # Since we explicitly handle known emojis later, this acts as a fallback to prevent squares
    text = re.sub(r'[\U00010000-\U0010FFFF]', '', text)
    
    # Strip Variation Selectors (e.g., U+FE0F) and Combining Enclosing Keycaps (U+20E3)
    # This prevents '1️⃣' from rendering as '1□', turning it into just '1'.
    text = re.sub(r'[\uFE00-\uFE0F\u20E3]', '', text)
    
    return text

def parse_markdown_to_platypus(md_text, styles):
    """
    Parses simple Markdown to a list of ReportLab Flowables.
    Supports headings, bold, italic, lists, and tables.
    """
    flowables = []
    if not md_text:
        return flowables
        
    lines = md_text.split('\n')
    normal_style = styles['Normal']
    
    current_paragraph = []
    in_table = False
    in_code_block = False
    code_block_content = []
    table_data = []
    
    def process_inline(text):
        # Escape XML entities for ReportLab XML parser
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Replace known emojis with FontAwesome icons if available
        if HAS_FA:
            fa_map = {
                '✅': ('&#xf00c;', '#27AE60'), '❌': ('&#xf00d;', '#E74C3C'), '🚨': ('&#xf071;', '#E74C3C'),
                '💡': ('&#xf0eb;', '#F1C40F'), '⚠️': ('&#xf071;', '#F39C12'), '🛑': ('&#xf05e;', '#C0392B'),
                '🔥': ('&#xf06d;', '#E67E22'), '📈': ('&#xf201;', '#27AE60'), '📉': ('&#xf204;', '#E74C3C'),
                '💰': ('&#xf0d6;', '#F1C40F'), '🔍': ('&#xf002;', '#3498DB'), '📊': ('&#xf080;', '#2980B9'),
                '🧮': ('&#xf640;', '#7F8C8D'), 'ℹ️': ('&#xf05a;', '#3498DB'),
                '🔴': ('&#xf111;', '#E74C3C'), '🟡': ('&#xf111;', '#F1C40F'), '🟢': ('&#xf111;', '#27AE60'),
                '🔵': ('&#xf111;', '#3498DB'), '🟠': ('&#xf111;', '#E67E22')
            }
            for emoji_char, (fa_code, color) in fa_map.items():
                text = text.replace(emoji_char, f'<font name="FontAwesome" color="{color}">{fa_code}</font>')
        
        # Remove any remaining emojis that break reportlab
        text = clean_unsupported_chars(text)
        
        # Then replace our pseudo-markdown
        text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
        text = re.sub(r'\*(.*?)\*', r'<i>\1</i>', text)
        mono_font = 'DejaVuSansMono' if HAS_DEJAVU else 'Courier'
        text = re.sub(r'`(.*?)`', f'<font name="{mono_font}">\\1</font>', text)
        # Preserve consecutive spaces for alignment
        text = text.replace('  ', '&nbsp; ')
        return text

    def flush_paragraph():
        if current_paragraph:
            # Escape and process inline elements FIRST, so we don't escape our own <br/> tag
            processed_lines = [process_inline(line) for line in current_paragraph]
            text = "<br/>\n".join(processed_lines)
            flowables.append(Paragraph(text, normal_style))
            flowables.append(Spacer(1, 6))
            current_paragraph.clear()
            
    def render_table(data):
        if not data: return
        formatted_data = []
        for r_idx, row in enumerate(data):
            formatted_row = []
            for cell in row:
                text = process_inline(cell)
                if r_idx == 0:
                    text = f"<b><font color='white'>{text}</font></b>"
                formatted_row.append(Paragraph(text, normal_style))
            formatted_data.append(formatted_row)
            
        t = Table(formatted_data, repeatRows=1)
        t_style = TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#21496B")), # Dark Blue like Claude PDF
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('TOPPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.white),
        ])
        
        # add alternating row colors
        for i in range(1, len(data)):
            bg_color = colors.HexColor("#F0F4F8") if i % 2 == 1 else colors.white
            t_style.add('BACKGROUND', (0, i), (-1, i), bg_color)
            
        t.setStyle(t_style)
        flowables.append(KeepTogether(t))
        flowables.append(Spacer(1, 12))

    for line in lines:
        stripped_line = line.strip()
        
        # Handle Code Blocks
        if stripped_line.startswith('```'):
            if in_code_block:
                in_code_block = False
                code_text = "\n".join(code_block_content)
                code_text = process_inline(code_text)
                flowables.append(XPreformatted(code_text, styles['CustomCodeBox']))
                flowables.append(Spacer(1, 6))
                code_block_content = []
            else:
                flush_paragraph()
                in_code_block = True
            continue
            
        if in_code_block:
            code_block_content.append(line)
            continue
            
        line = stripped_line
        
        # Handle Table
        if line.startswith('|') and line.endswith('|'):
            flush_paragraph()
            in_table = True
            row = [cell.strip() for cell in line.split('|')[1:-1]]
            # Check if separator row
            if set(''.join(row).replace('-', '').replace(':', '').strip()) == set():
                continue
            table_data.append(row)
            continue
        elif in_table:
            render_table(table_data)
            in_table = False
            table_data = []
            
        if not line:
            flush_paragraph()
            continue
            
        # Handle Headings
        if line.startswith('### '):
            flush_paragraph()
            flowables.append(Paragraph(process_inline(line[4:]), styles['Heading3']))
            flowables.append(Spacer(1, 4))
        elif line.startswith('## '):
            flush_paragraph()
            flowables.append(Paragraph(process_inline(line[3:]), styles['Heading2']))
            flowables.append(Spacer(1, 6))
        elif line.startswith('# '):
            flush_paragraph()
            flowables.append(Paragraph(process_inline(line[2:]), styles['Heading1']))
            flowables.append(Spacer(1, 8))
        elif line.startswith('- ') or line.startswith('* '):
            flush_paragraph()
            text = process_inline(line[2:])
            # Bullet point
            flowables.append(Paragraph(f"• {text}", normal_style))
            flowables.append(Spacer(1, 3))
        else:
            current_paragraph.append(line)
            
    flush_paragraph()
    if in_table:
        render_table(table_data)
        
    return flowables

def generate_portfolio_pdf(portfolio_df, gesamtwert, summary_text, chat_history=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    styles = getSampleStyleSheet()
    
    default_font = 'DejaVuSans' if HAS_DEJAVU else 'Helvetica'
    default_bold = 'DejaVuSans-Bold' if HAS_DEJAVU else 'Helvetica-Bold'
    mono_font = 'DejaVuSansMono' if HAS_DEJAVU else 'Courier'
    
    if HAS_DEJAVU:
        for style in styles.byName.values():
            if hasattr(style, 'fontName'):
                if style.fontName == 'Helvetica':
                    style.fontName = 'DejaVuSans'
                elif style.fontName == 'Helvetica-Bold':
                    style.fontName = 'DejaVuSans-Bold'
                elif style.fontName == 'Times-Roman':
                    style.fontName = 'DejaVuSans'
                    
    # Prevent orphaned headings by keeping them with the next paragraph
    for h_level in range(1, 7):
        h_name = f'Heading{h_level}'
        if h_name in styles:
            styles[h_name].keepWithNext = True
    
    # Custom Styles
    styles.add(ParagraphStyle(
        name='TitleBox',
        parent=styles['Normal'],
        fontSize=24,
        leading=28,
        textColor=colors.white,
        fontName=default_bold
    ))
    styles.add(ParagraphStyle(
        name='SubtitleBox',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.white,
        spaceBefore=10
    ))
    styles.add(ParagraphStyle(
        name='CustomCodeBox',
        parent=styles['Normal'],
        fontName=mono_font,
        fontSize=9,
        leading=11,
        backColor=colors.HexColor("#F4F6F7"),
        textColor=colors.HexColor("#2C3E50"),
        borderPadding=6,
        borderColor=colors.HexColor("#BDC3C7"),
        borderWidth=1,
        borderRadius=3
    ))
    
    flowables = []
    
    # 1. Title Box (Dark Blue Background)
    title_data = [
        [Paragraph("Portfolio-Analyse & Handlungsempfehlungen", styles['TitleBox'])],
        [Paragraph(f"Gesamtwert: <b>{gesamtwert:,.2f} EUR</b>", styles['SubtitleBox'])]
    ]
    title_table = Table(title_data, colWidths=[A4[0] - 4*cm])
    title_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#1B2A47")),
        ('TOPPADDING', (0,0), (-1,-1), 20),
        ('BOTTOMPADDING', (0,0), (-1,-1), 20),
        ('LEFTPADDING', (0,0), (-1,-1), 20),
        ('RIGHTPADDING', (0,0), (-1,-1), 20),
    ]))
    flowables.append(title_table)
    flowables.append(Spacer(1, 20))
    
    # 2. Portfolio Table
    flowables.append(Paragraph("Aktuelle Positionen", styles['Heading2']))
    flowables.append(Spacer(1, 10))
    
    table_data = [["Wertpapier", "Anteile", "Akt. Kurs", "Gesamtwert"]]
    for _, row in portfolio_df.iterrows():
        wp = str(row.get('Wertpapier', ''))
        if len(wp) > 40:
            wp = wp[:37] + "..."
        ant = row.get('St_Nom', 0)
        kurs = row.get('Aktueller Kurs', row.get('Ø Kaufkurs', 0))
        wert = row.get('Akt. Wert', row.get('Wert', 0))
        
        table_data.append([
            Paragraph(wp, styles['Normal']),
            f"{ant:,.2f}",
            f"{kurs:,.2f} EUR",
            f"{wert:,.2f} EUR"
        ])
        
    t = Table(table_data, colWidths=[A4[0]*0.4, A4[0]*0.15, A4[0]*0.15, A4[0]*0.15], repeatRows=1)
    t_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#21496B")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.white),
    ])
    if HAS_DEJAVU:
        t_style.add('FONTNAME', (0,0), (-1,-1), 'DejaVuSans')
        t_style.add('FONTNAME', (0,0), (-1,0), 'DejaVuSans-Bold')
        
    for i in range(1, len(table_data)):
        bg_color = colors.HexColor("#F0F4F8") if i % 2 == 1 else colors.white
        t_style.add('BACKGROUND', (0, i), (-1, i), bg_color)
    t.setStyle(t_style)
    flowables.append(KeepTogether(t))
    flowables.append(Spacer(1, 20))
    
    # 3. Add Chart Image if kaleido is available
    tmp_img_path = os.path.join(tempfile.gettempdir(), "portfolio_chart.png")
    try:
        fig = px.pie(
            portfolio_df, 
            values='_Plot_Wert' if '_Plot_Wert' in portfolio_df.columns else 'Wert', 
            names='Wertpapier', 
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig.update_layout(showlegend=True, paper_bgcolor='white', plot_bgcolor='white', font=dict(color='black'))
        fig.write_image(tmp_img_path, width=600, height=400)
        flowables.append(Image(tmp_img_path, width=400, height=266))
        flowables.append(Spacer(1, 20))
    except Exception:
        pass # kaleido not installed or image failed
        
    # 4. KI Executive Summary
    flowables.append(Paragraph("KI Executive Summary", styles['Heading2']))
    flowables.append(Spacer(1, 10))
    flowables.extend(parse_markdown_to_platypus(summary_text, styles))
    
    # 5. Chat-basierte Analyse-Kapitel
    if chat_history:
        last_user_msg = None
        for msg in chat_history:
            if msg['role'] == "user":
                last_user_msg = str(msg.get('display') or msg.get('content')).strip()
            elif msg['role'] == "model":
                text_to_render = msg.get('display') or msg.get('content')
                if isinstance(text_to_render, list):
                    text_parts = [part['text'] for part in text_to_render if isinstance(part, dict) and 'text' in part]
                    text_to_render = "".join(text_parts)
                else:
                    text_to_render = str(text_to_render)
                
                flowables.append(PageBreak())
                
                # Check if AI text already starts with a markdown heading
                has_heading = text_to_render.lstrip().startswith('#')
                
                if not has_heading and last_user_msg:
                    # Clean up user message for use as a heading (take first line if multi-line)
                    heading_text = last_user_msg.split('\\n')[0][:80]
                    if len(last_user_msg.split('\\n')[0]) > 80:
                        heading_text += "..."
                    flowables.append(Paragraph(heading_text, styles['Heading2']))
                    flowables.append(Spacer(1, 10))
                    
                flowables.extend(parse_markdown_to_platypus(text_to_render, styles))
                last_user_msg = None
            
    # Build Document
    try:
        doc.build(flowables)
        pdf_bytes = buffer.getvalue()
    finally:
        if os.path.exists(tmp_img_path):
            os.remove(tmp_img_path)
            
    return pdf_bytes

def export_text_to_pdf_reportlab(text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    
    flowables = []
    flowables.append(Paragraph("KI Antwort", styles['Title']))
    flowables.append(Spacer(1, 20))
    flowables.extend(parse_markdown_to_platypus(text, styles))
    
    doc.build(flowables)
    return buffer.getvalue()
