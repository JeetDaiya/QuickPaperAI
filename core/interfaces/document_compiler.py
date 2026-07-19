from abc import  ABC, abstractmethod

class DocumentCompiler(ABC):
    @abstractmethod
    def generate_pdf(self, paper_html: str, paper_output_path: str, answer_html : str, answer_output_path: str):
        pass

    @abstractmethod
    def generate_docx(self, markdown: str, output_path: str):
        pass