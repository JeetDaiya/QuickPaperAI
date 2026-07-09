from abc import  ABC, abstractmethod

class DocumentCompiler(ABC):
    @abstractmethod
    def generate_pdf(self, html: str, output_path: str):
        pass

    @abstractmethod
    def generate_docx(self, html: str, output_path: str):
        pass

