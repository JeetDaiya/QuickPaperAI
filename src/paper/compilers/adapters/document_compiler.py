import os
import asyncio

from src.paper.compilers.interfaces.interface import DocumentCompiler
from playwright.async_api import async_playwright


# Chromium flags needed to run headless inside the worker container: no sandbox (no user
# namespaces) and /dev/shm off (the default 64MB shm crashes Chromium on larger pages).
CHROMIUM_ARGS = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]


class CustomDocumentCompiler(DocumentCompiler):
    async def generate_pdf(self, paper_html: str, paper_output_path: str, answer_html: str, answer_output_path: str):
        async with async_playwright() as p:
            browser = await p.chromium.launch(args=CHROMIUM_ARGS)
            # try/finally so a failure during set_content/pdf() still closes the browser —
            # otherwise every error leaks a zombie Chromium process in the worker container.
            try:
                paper_page = await browser.new_page()
                answer_page = await browser.new_page()

                await asyncio.gather(
                    paper_page.set_content(paper_html),
                    answer_page.set_content(answer_html),
                )

                try:
                    await asyncio.gather(
                        paper_page.wait_for_load_state("load", timeout=15000),
                        answer_page.wait_for_load_state("load", timeout=15000),
                    )
                except Exception as err:
                    print(f"[WARN] Playwright load state timeout (proceeding to generate PDF): {err}")

                await asyncio.gather(
                    paper_page.pdf(
                        path=paper_output_path,
                        format="A4",
                        print_background=True,
                    ),
                    answer_page.pdf(
                        path=answer_output_path,
                        format="A4",
                        print_background=True
                    ),
                )
            finally:
                await browser.close()

    async def generate_docx(self, markdown: str, output_path: str):
        temp_md_path = output_path + ".temp.md"

        with open(temp_md_path, "w", encoding="utf-8") as f:
            f.write(markdown)
        try:
            cmd = ["pandoc", "-f", "markdown", "-t", "docx", temp_md_path, "-o", output_path]
            proc = await asyncio.create_subprocess_exec(*cmd, stderr=asyncio.subprocess.PIPE)
            try:
                _, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise RuntimeError("Pandoc DOCX compilation timed out after 60s")

            # communicate() doesn't raise on a non-zero exit — check it explicitly, else a failed
            # conversion would look like success and leave no (or a corrupt) DOCX behind.
            if proc.returncode != 0:
                err = stderr.decode(errors="replace").strip() if stderr else ""
                raise RuntimeError(f"Pandoc exited with code {proc.returncode}: {err}")

            print(f"[INFO] DOCX Question Paper compiled successfully to {output_path}")
        finally:
            if os.path.exists(temp_md_path):
                os.remove(temp_md_path)
