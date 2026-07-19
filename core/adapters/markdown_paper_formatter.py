from datetime import date

from core.interfaces.paper_formatter import PaperFormatter
from core.models.schemas import PaperRequest, Question, QuestionTypes
from core.pdf.generator import SECTION_CONFIG


class MarkdownPaperFormatter(PaperFormatter):
    def render_paper(self, paper_request : PaperRequest, questions: list[Question]):
        total_marks = sum(q.marks for q in questions)
        today = date.today().strftime("%d-%m-%Y")

        chapters_str = ", ".join(paper_request.chapters)

        # 1. Build the Header using standard Pandoc-supported HTML table for a borderless side-by-side metadata layout
        md = f"""<table width="100%" border="0" cellspacing="0" cellpadding="0" style="width:100%; border:none;">
          <tr style="border:none;">
            <td align="left" valign="top" style="border:none; text-align:left; font-family:serif;">
              <strong>Subject:</strong> {paper_request.subject}<br>
              <strong>Standard:</strong> {paper_request.standard}
            </td>
            <td align="right" valign="top" style="border:none; text-align:right; font-family:serif;">
              <strong>Date:</strong> {today}<br>
              <strong>Chapters:</strong> {chapters_str}
            </td>
          </tr>
        </table>

        <p align="center" style="text-align:center; font-family:serif; margin-top:20px; margin-bottom:5px;">
          <span style="font-size:18pt; font-weight:bold; text-transform:uppercase; letter-spacing:1px;">{paper_request.institution_name.upper()}</span>
        </p>
        <p align="center" style="text-align:center; font-family:serif; margin-bottom:15px;">
          <strong>Total Marks: {total_marks}</strong>
        </p>

        <hr style="border:none; border-top:2px solid #000000; height:1px; margin-bottom:20px;" />

        """

        # Group questions by type
        grouped = {}
        for q in questions:
            if q.question_type not in grouped:
                grouped[q.question_type] = []
            grouped[q.question_type].append(q)

        q_number = 1
        section_number = 1

        for q_type, heading in SECTION_CONFIG.items():
            if q_type not in grouped:
                continue

            questions = grouped[q_type]
            section_marks = sum(q.marks for q in questions)

            md += f"## Section {section_number}: {heading} ({section_marks} Marks)\n\n"

            for q in questions:
                # Replaces HTML-specific breaks with clean newlines for Markdown
                q_text = q.question_text.replace("<br>", "\n").replace("\n", "  \n")
                md += f"**Q{q_number}.** {q_text} *[{q.marks} Mark{'s' if q.marks > 1 else ''}]*\n\n"

                # MCQ Options Rendering
                if q.question_type == QuestionTypes.MCQ and q.options:
                    import re
                    for idx, opt in enumerate(q.options):
                        label = chr(97 + idx)  # a, b, c, d
                        opt_str = opt.strip()
                        if re.match(r'^[\(\[a-dA-D]?[a-dA-D][\)\.\s]\s*', opt_str):
                            md += f"  * {opt_str}\n"
                        else:
                            md += f"  * ({label}) {opt_str}\n"
                    md += "\n"

                # Match the Column Table Rendering
                elif q.question_type == QuestionTypes.MATCH_THE_COLUMN and q.options:
                    has_pipe = any("|" in opt for opt in q.options)
                    if has_pipe:
                        md += "| Column A | Column B |\n"
                        md += "| :--- | :--- |\n"
                        for opt in q.options:
                            if "|" in opt:
                                col_a, col_b = opt.split("|", 1)
                                md += f"| {col_a.strip()} | {col_b.strip()} |\n"
                            else:
                                md += f"| {opt.strip()} | |\n"
                        md += "\n"
                    else:
                        for idx, opt in enumerate(q.options):
                            label = chr(97 + idx)
                            md += f"  * ({label}) {opt}\n"
                        md += "\n"

                # Diagram Placeholder Box (Single-Cell Table)
                if q.diagram_prompt:
                    md += f"| **[ DIAGRAM PLACEHOLDER: Labeled Diagram Space ]** |\n"
                    md += "| :--- |\n"
                    md += f"| **Copy this prompt into Gemini to generate the diagram:**  \n`{q.diagram_prompt}`  \n\n*Once generated, paste the diagram here and delete this text.* |\n\n"

                q_number += 1

            section_number += 1
            md += "\n"

        return md

    def render_answer_key(self, paper_request : PaperRequest, questions: list[Question]):
        pass