import os
import subprocess

from src.paper.compilers.interfaces.interface import DocumentCompiler
from playwright.sync_api import  sync_playwright


class CustomDocumentCompiler(DocumentCompiler):
    def generate_pdf(self, paper_html: str, paper_output_path: str, answer_html : str, answer_output_path: str):
        with sync_playwright() as p:
            browser = p.chromium.launch()
            paper_page = browser.new_page()
            answer_page = browser.new_page()

            paper_page.set_content(paper_html)
            answer_page.set_content(answer_html)

            paper_page.wait_for_load_state("networkidle", timeout=90000)
            answer_page.wait_for_load_state("networkidle", timeout=90000)

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

    def generate_docx(self, markdown: str, output_path: str):
        temp_md_path = output_path + ".temp.md"

        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        try:
            cmd = ["pandoc", "-f", "markdown", "-t", "docx", temp_md_path, "-o", output_path]
            subprocess.run(cmd, check=True)
            print(f"🎉 DOCX Question Paper compiled successfully to {output_path}")
        except Exception as e:
            print(f"⚠️ Pandoc DOCX compilation failed: {e}")
        finally:
            if os.path.exists(temp_md_path):
                os.remove(temp_md_path)



