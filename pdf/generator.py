from models.schemas import Question, PaperRequest, QuestionTypes
from datetime import date
from collections import OrderedDict
import asyncio
import pathlib
from playwright.sync_api import sync_playwright

# Display order and headings for each question type
SECTION_CONFIG = OrderedDict({
    QuestionTypes.MCQ: "Multiple Choice Questions",
    QuestionTypes.TRUE_FALSE: "True or False",
    QuestionTypes.FILL_IN_THE_BLANK: "Fill in the Blanks",
    QuestionTypes.ONE_WORD_ANS: "One Word Answer",
    QuestionTypes.MATCH_THE_COLUMN: "Match the Following",
    QuestionTypes.TWO_MARK_ANS: "Short Answer Questions (2 Marks)",
    QuestionTypes.THREE_MARK_ANS: "Short Answer Questions (3 Marks)",
    QuestionTypes.FOUR_MARK_ANS: "Long Answer Questions (4 Marks)",
})


def _render_question_html(q: Question, q_number: int) -> str:
    """Renders a single question as HTML."""
    html = f'<div class="question"><span class="q-text"><strong>Q{q_number}.</strong> {q.question_text}</span>'
    html += f'<span class="q-marks">[{q.marks}]</span></div>\n'

    # Render MCQ options
    if q.question_type == QuestionTypes.MCQ and q.options:
        html += '<div class="options">\n'
        for i, opt in enumerate(q.options):
            label = chr(97 + i)  # a, b, c, d
            html += f'  <span class="option">({label}) {opt}</span>\n'
        html += '</div>\n'

    # Render Match the Column as a table
    if q.question_type == QuestionTypes.MATCH_THE_COLUMN and q.options:
        html += '<table class="match-table">\n'
        html += '<tr><th>Column A</th><th>Column B</th></tr>\n'
        for opt in q.options:
            if "|" in opt:
                col_a, col_b = opt.split("|", 1)
                html += f'<tr><td>{col_a.strip()}</td><td>{col_b.strip()}</td></tr>\n'
            else:
                html += f'<tr><td colspan="2">{opt}</td></tr>\n'
        html += '</table>\n'

    return html


def generate_paper_html(selected_questions: list[Question], paper_request: PaperRequest) -> str:
    """
    Takes selected questions and paper request, returns a complete HTML string
    for the question paper.
    """
    total_marks = sum(q.marks for q in selected_questions)
    today = date.today().strftime("%d-%m-%Y")
    chapters_str = ", ".join(paper_request.chapters)

    # Group questions by type
    grouped: dict[QuestionTypes, list[Question]] = {}
    for q in selected_questions:
        if q.question_type not in grouped:
            grouped[q.question_type] = []
        grouped[q.question_type].append(q)

    # Build sections HTML in the defined order
    sections_html = ""
    q_number = 1
    section_number = 1

    for q_type, heading in SECTION_CONFIG.items():
        if q_type not in grouped:
            continue

        questions = grouped[q_type]
        section_marks = sum(q.marks for q in questions)

        sections_html += f"""
        <div class="section">
            <div class="section-header">
                <span class="section-title">Section {section_number}: {heading}</span>
                <span class="section-marks">[{section_marks} Marks]</span>
            </div>
        """

        for q in questions:
            sections_html += _render_question_html(q, q_number)
            q_number += 1

        sections_html += "</div>\n"
        section_number += 1

    # Build full HTML
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{paper_request.subject} - Question Paper</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Times New Roman', serif;
            font-size: 13pt;
            line-height: 1.6;
            padding: 40px 50px;
            max-width: 210mm;
            margin: 0 auto;
            color: #000;
        }}

        /* ── Header ── */
        .paper-header {{
            border-bottom: 2px solid #000;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}

        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 4px;
        }}

        .header-left {{
            text-align: left;
        }}

        .header-right {{
            text-align: right;
        }}

        .institution-name {{
            text-align: center;
            font-size: 18pt;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }}

        .total-marks {{
            text-align: center;
            font-size: 13pt;
            font-weight: bold;
            margin-top: 4px;
        }}

        .header-meta {{
            font-size: 11pt;
        }}

        /* ── Sections ── */
        .section {{
            margin-bottom: 22px;
        }}

        .section-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #666;
            padding-bottom: 4px;
            margin-bottom: 12px;
        }}

        .section-title {{
            font-weight: bold;
            font-size: 13pt;
        }}

        .section-marks {{
            font-weight: bold;
            font-size: 12pt;
        }}

        /* ── Questions ── */
        .question {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
            padding-left: 8px;
        }}

        .q-text {{
            flex: 1;
            padding-right: 16px;
        }}

        .q-marks {{
            white-space: nowrap;
            font-weight: bold;
            min-width: 35px;
            text-align: right;
        }}

        /* ── MCQ Options ── */
        .options {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 24px;
            padding-left: 32px;
            margin-bottom: 10px;
        }}

        .option {{
            font-size: 12pt;
        }}

        /* ── Match the Column Table ── */
        .match-table {{
            width: 70%;
            margin: 8px auto 12px 32px;
            border-collapse: collapse;
        }}

        .match-table th,
        .match-table td {{
            border: 1px solid #333;
            padding: 5px 12px;
            text-align: left;
            font-size: 12pt;
        }}

        .match-table th {{
            background: #f0f0f0;
            font-weight: bold;
        }}

        @media print {{
            body {{
                padding: 20px 30px;
            }}
        }}
    </style>
</head>
<body>

    <div class="paper-header">
        <div class="header-top">
            <div class="header-left">
                <div class="header-meta"><strong>Subject:</strong> {paper_request.subject}</div>
                <div class="header-meta"><strong>Standard:</strong> {paper_request.standard}</div>
            </div>
            <div class="header-right">
                <div class="header-meta"><strong>Date:</strong> {today}</div>
                <div class="header-meta"><strong>Chapters:</strong> {chapters_str}</div>
            </div>
        </div>
        <div class="institution-name">{paper_request.institution_name}</div>
        <div class="total-marks">Total Marks: {total_marks}</div>
    </div>

    {sections_html}

    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: "$$", right: "$$", display: true}},
                    {{left: "$", right: "$", display: false}}
                ]
            }});
        }});
    </script>

</body>
</html>"""

    return html


def _render_answer_html(q: Question, q_number: int) -> str:
    """Renders a single question and its structured answer key as HTML."""
    html = f'<div class="question-block" style="margin-bottom: 20px; page-break-inside: avoid;">'
    html += f'  <div class="question" style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px;">'
    html += f'    <span class="q-text" style="flex: 1; padding-right: 16px;"><strong>Q{q_number}.</strong> {q.question_text}</span>'
    html += f'    <span class="q-marks" style="white-space: nowrap; font-weight: bold; min-width: 35px; text-align: right;">[{q.marks} Marks]</span>'
    html += f'  </div>'
    
    # Format the correct answer content
    ans_content = q.correct_answer.strip()
    formatted_ans = ""
    
    if ans_content.startswith("-") or "\n-" in ans_content:
        # Convert markdown list to HTML list
        lines = ans_content.split("\n")
        formatted_ans += '<ul class="answer-list" style="margin-left: 20px; padding-left: 10px; list-style-type: disc;">\n'
        for line in lines:
            line_str = line.strip()
            if line_str.startswith("-"):
                line_str = line_str.lstrip("-").strip()
            if line_str:
                formatted_ans += f'  <li style="margin-bottom: 4px;">{line_str}</li>\n'
        formatted_ans += '</ul>\n'
    else:
        # Standard block formatting
        formatted_ans = f'<p style="margin: 0; line-height: 1.5;">{ans_content.replace(chr(10), "<br>")}</p>'

    html += f'  <div class="answer-box" style="margin-left: 24px; padding: 10px 15px; border-left: 3px solid #0056b3; background-color: #f8f9fa; border-radius: 0 4px 4px 0;">'
    html += f'    <strong style="color: #0056b3; font-size: 11pt; text-transform: uppercase; letter-spacing: 0.5px; display: block; margin-bottom: 4px;">Evaluation & Marking Scheme:</strong>'
    html += f'    <div class="answer-text" style="font-size: 12pt;">{formatted_ans}</div>'
    html += f'  </div>'
    html += f'</div>\n'
    return html


def generate_answer_html(selected_questions: list[Question], paper_request: PaperRequest) -> str:
    """
    Takes selected questions and paper request, returns a complete HTML string
    for the Answer Key & Marking Scheme.
    """
    total_marks = sum(q.marks for q in selected_questions)
    today = date.today().strftime("%d-%m-%Y")
    chapters_str = ", ".join(paper_request.chapters)

    # Group questions by type
    grouped: dict[QuestionTypes, list[Question]] = {}
    for q in selected_questions:
        if q.question_type not in grouped:
            grouped[q.question_type] = []
        grouped[q.question_type].append(q)

    # Build sections HTML in the defined order
    sections_html = ""
    q_number = 1
    section_number = 1

    for q_type, heading in SECTION_CONFIG.items():
        if q_type not in grouped:
            continue

        questions = grouped[q_type]
        sections_html += f"""
        <div class="section" style="margin-bottom: 25px;">
            <div class="section-header" style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #666; padding-bottom: 4px; margin-bottom: 15px;">
                <span class="section-title" style="font-weight: bold; font-size: 13pt;">Section {section_number}: {heading} (Answers)</span>
            </div>
        """

        for q in questions:
            sections_html += _render_answer_html(q, q_number)
            q_number += 1

        sections_html += "</div>\n"
        section_number += 1

    # Build full HTML with the same beautiful typography and KaTeX support
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Answer Key: {paper_request.subject}</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.css">
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/katex.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/katex@0.16.9/dist/contrib/auto-render.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'Times New Roman', serif;
            font-size: 13pt;
            line-height: 1.6;
            padding: 40px 50px;
            max-width: 210mm;
            margin: 0 auto;
            color: #000;
        }}

        /* ── Header ── */
        .paper-header {{
            border-bottom: 2px solid #000;
            padding-bottom: 12px;
            margin-bottom: 20px;
        }}

        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 4px;
        }}

        .header-left {{
            text-align: left;
        }}

        .header-right {{
            text-align: right;
        }}

        .institution-name {{
            text-align: center;
            font-size: 18pt;
            font-weight: bold;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 4px;
        }}

        .total-marks {{
            text-align: center;
            font-size: 13pt;
            font-weight: bold;
            margin-top: 4px;
        }}

        .header-meta {{
            font-size: 11pt;
        }}

        .q-marks {{
            white-space: nowrap;
            font-weight: bold;
            min-width: 35px;
            text-align: right;
        }}

        @media print {{
            body {{
                padding: 20px 30px;
            }}
        }}
    </style>
</head>
<body>

    <div class="paper-header">
        <div class="header-top">
            <div class="header-left">
                <div class="header-meta"><strong>Subject:</strong> {paper_request.subject}</div>
                <div class="header-meta"><strong>Standard:</strong> {paper_request.standard}</div>
            </div>
            <div class="header-right">
                <div class="header-meta"><strong>Date:</strong> {today}</div>
                <div class="header-meta"><strong>Chapters:</strong> {chapters_str}</div>
            </div>
        </div>
        <div class="institution-name">{paper_request.institution_name}</div>
        <div class="total-marks" style="color: #0056b3;">ANSWER KEY & EVALUATION SCHEME</div>
    </div>

    {sections_html}

    <script>
        document.addEventListener("DOMContentLoaded", function() {{
            renderMathInElement(document.body, {{
                delimiters: [
                    {{left: "$$", right: "$$", display: true}},
                    {{left: "$", right: "$", display: false}}
                ]
            }});
        }});
    </script>

</body>
</html>"""

    return html



def generate_pdf(paper_string, answer_string, paper_output_path, answer_output_path):
    with sync_playwright() as p:
        browser = p.chromium.launch()
        paper_page = browser.new_page()
        answer_page = browser.new_page()
        
        paper_page.set_content(paper_string)
        answer_page.set_content(answer_string)
        
        paper_page.pdf(
            path=paper_output_path,
            format="A4",
            print_background=True,
        )
        
        answer_page.pdf(
            path=answer_output_path,
            format="A4",
            print_background=True
        )
        
        
        browser.close()
    
    