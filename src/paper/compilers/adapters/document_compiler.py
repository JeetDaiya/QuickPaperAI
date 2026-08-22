import os
import subprocess
import asyncio

from src.paper.compilers.interfaces.interface import DocumentCompiler
from playwright.async_api import async_playwright


class CustomDocumentCompiler(DocumentCompiler):
    async def generate_pdf(self, paper_html: str, paper_output_path: str, answer_html: str, answer_output_path: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            paper_page = await browser.new_page()
            answer_page = await browser.new_page()

            await paper_page.set_content(paper_html)
            await answer_page.set_content(answer_html)

            try:
                await paper_page.wait_for_load_state("load", timeout=15000)
                await answer_page.wait_for_load_state("load", timeout=15000)
            except Exception as err:
                print(f"[WARN] Playwright load state timeout (proceeding to generate PDF): {err}")

            await paper_page.pdf(
                path=paper_output_path,
                format="A4",
                print_background=True,
            )

            await answer_page.pdf(
                path=answer_output_path,
                format="A4",
                print_background=True
            )

            await browser.close()

    async def generate_docx(self, markdown: str, output_path: str):
        temp_md_path = output_path + ".temp.md"

        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        try:
            cmd = ["pandoc", "-f", "markdown", "-t", "docx", temp_md_path, "-o", output_path]
            proc = await asyncio.create_subprocess_exec(*cmd)
            await proc.communicate()
            print(f"[INFO] DOCX Question Paper compiled successfully to {output_path}")
        except Exception as e:
            print(f"[WARN] Pandoc DOCX compilation failed: {e}")
        finally:
            if os.path.exists(temp_md_path):
                os.remove(temp_md_path)
